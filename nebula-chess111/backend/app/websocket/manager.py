"""
WebSocket connection manager.

Guarantees:
• Redis failures in send_to_game fall back to direct local broadcast — no crash.
• disconnect_game cancels the pub/sub task when the last client leaves — no leak.
• _listen_channel cleans up _pubsub_tasks in ALL exit paths (normal + exception)
  so that the next connection to the same game always starts a fresh listener.
"""
import asyncio
import json
from collections import defaultdict
from typing import Optional

import structlog
from fastapi import WebSocket
from redis.exceptions import ConnectionError as RedisConnError, TimeoutError as RedisTimeout

from app.redis_client import get_redis

log = structlog.get_logger()

GAME_CHANNEL_PREFIX = "nebula:game:"
LOBBY_CHANNEL       = "nebula:lobby"


class ConnectionInfo:
    def __init__(
        self,
        ws: WebSocket,
        user_id: Optional[str],
        username: str,
        role: str,
    ):
        self.ws        = ws
        self.user_id   = user_id
        self.username  = username
        self.role      = role       # "white" | "black" | "spectator"
        self.connected = True


class WebSocketManager:
    def __init__(self):
        self._rooms: dict[str, list[ConnectionInfo]] = defaultdict(list)
        self._lobby: list[ConnectionInfo]            = []
        self._pubsub_tasks: dict[str, asyncio.Task] = {}

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect_game(
        self,
        game_id: str,
        ws: WebSocket,
        user_id: Optional[str],
        username: str,
        role: str,
    ) -> ConnectionInfo:
        await ws.accept()
        info = ConnectionInfo(ws, user_id, username, role)
        self._rooms[game_id].append(info)

        channel = f"{GAME_CHANNEL_PREFIX}{game_id}"
        task = self._pubsub_tasks.get(channel)

        # Start a fresh listener if none exists OR the previous one died
        if task is None or task.done():
            new_task = asyncio.create_task(self._listen_channel(channel, game_id))
            self._pubsub_tasks[channel] = new_task

        log.info("ws.connected", game_id=game_id, username=username, role=role)
        return info

    async def disconnect_game(self, game_id: str, info: ConnectionInfo) -> None:
        info.connected = False
        room = self._rooms.get(game_id, [])
        if info in room:
            room.remove(info)

        # If the room is now empty, cancel the pub/sub task to avoid a goroutine leak
        if not room:
            self._rooms.pop(game_id, None)
            channel = f"{GAME_CHANNEL_PREFIX}{game_id}"
            task = self._pubsub_tasks.pop(channel, None)
            if task and not task.done():
                task.cancel()

        log.info("ws.disconnected", game_id=game_id, username=info.username)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send_to_game(self, game_id: str, message: dict) -> None:
        """
        Publish via Redis pub/sub so all workers receive the message.
        FIX: if Redis is unavailable, fall back to direct local broadcast
        instead of propagating an unhandled exception.
        """
        payload = json.dumps(message)
        channel = f"{GAME_CHANNEL_PREFIX}{game_id}"
        try:
            r = await get_redis()
            await r.publish(channel, payload)
        except (RedisConnError, RedisTimeout, OSError, Exception) as exc:
            log.warning(
                "ws.redis_publish_failed",
                game_id=game_id,
                error=str(exc),
                fallback="local_broadcast",
            )
            # Fallback: deliver directly to connections on THIS worker
            await self.broadcast_local(game_id, message)

    async def broadcast_local(
        self,
        game_id: str,
        message: dict,
        exclude: Optional[ConnectionInfo] = None,
    ) -> None:
        """Deliver to all local connections in a room, pruning stale ones."""
        dead: list[ConnectionInfo] = []
        for conn in list(self._rooms.get(game_id, [])):
            if conn is exclude or not conn.connected:
                continue
            try:
                await conn.ws.send_json(message)
            except Exception:
                dead.append(conn)

        for d in dead:
            await self.disconnect_game(game_id, d)

    async def send_to_player(
        self, game_id: str, user_id: str, message: dict
    ) -> None:
        """Unicast to a specific player on this worker."""
        for conn in list(self._rooms.get(game_id, [])):
            if conn.user_id == user_id and conn.connected:
                try:
                    await conn.ws.send_json(message)
                except Exception:
                    pass

    # ── Redis pub/sub listener ────────────────────────────────────────────────

    async def _listen_channel(self, channel: str, game_id: str) -> None:
        """
        Subscribe to a Redis channel and forward messages to local connections.

        FIX: the entire function is wrapped in try/finally so that
        _pubsub_tasks[channel] is ALWAYS cleaned up — even if get_redis()
        raises on the first line. Without this, a crashed task would block
        future connections from ever starting a new listener.
        """
        pubsub = None
        try:
            r      = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)

            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                try:
                    data = json.loads(raw["data"])
                    await self.broadcast_local(game_id, data)
                except Exception as exc:
                    log.error("ws.pubsub_dispatch_error", channel=channel, error=str(exc))

        except asyncio.CancelledError:
            # Normal shutdown — room emptied and disconnect_game cancelled us
            pass
        except Exception as exc:
            log.error("ws.pubsub_listener_crashed", channel=channel, error=str(exc))
        finally:
            # Guaranteed cleanup — next connect_game will see task.done() == True
            # and start a new listener
            self._pubsub_tasks.pop(channel, None)
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:
                    pass

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_room_info(self, game_id: str) -> dict:
        connections = self._rooms.get(game_id, [])
        return {
            "players":    [c.username for c in connections if c.role in ("white", "black")],
            "spectators": [c.username for c in connections if c.role == "spectator"],
            "count":      len(connections),
        }

    def is_player_connected(self, game_id: str, user_id: str) -> bool:
        return any(
            c.user_id == user_id and c.connected
            for c in self._rooms.get(game_id, [])
        )


# Singleton
ws_manager = WebSocketManager()
