"""
WebSocket connection manager.
- Tracks active connections per game room.
- Uses Redis pub/sub so messages work across multiple FastAPI workers.
- Supports spectators, reconnect, player roles.
"""
import asyncio
import json
import uuid
from collections import defaultdict
from typing import Optional
import structlog

from fastapi import WebSocket
import redis.asyncio as aioredis

from app.redis_client import get_redis

log = structlog.get_logger()

GAME_CHANNEL_PREFIX = "nebula:game:"
LOBBY_CHANNEL = "nebula:lobby"


class ConnectionInfo:
    def __init__(self, ws: WebSocket, user_id: Optional[str], username: str, role: str):
        self.ws = ws
        self.user_id = user_id
        self.username = username
        self.role = role  # "white" | "black" | "spectator"
        self.connected = True


class WebSocketManager:
    def __init__(self):
        # game_id → list[ConnectionInfo]
        self._rooms: dict[str, list[ConnectionInfo]] = defaultdict(list)
        # lobby connections
        self._lobby: list[ConnectionInfo] = []
        self._pubsub_tasks: dict[str, asyncio.Task] = {}

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

        # Start pub/sub listener for this game room if not already running
        channel = f"{GAME_CHANNEL_PREFIX}{game_id}"
        if channel not in self._pubsub_tasks:
            task = asyncio.create_task(self._listen_channel(channel, game_id))
            self._pubsub_tasks[channel] = task

        log.info("ws.connected", game_id=game_id, username=username, role=role)
        return info

    async def disconnect_game(self, game_id: str, info: ConnectionInfo):
        info.connected = False
        room = self._rooms.get(game_id, [])
        if info in room:
            room.remove(info)
        if not room:
            self._rooms.pop(game_id, None)
        log.info("ws.disconnected", game_id=game_id, username=info.username)

    async def send_to_game(self, game_id: str, message: dict):
        """Publish message via Redis so all workers receive it."""
        redis = await get_redis()
        channel = f"{GAME_CHANNEL_PREFIX}{game_id}"
        await redis.publish(channel, json.dumps(message))

    async def broadcast_local(self, game_id: str, message: dict, exclude: Optional[ConnectionInfo] = None):
        """Send message directly to all local connections in a room."""
        dead = []
        for conn in list(self._rooms.get(game_id, [])):
            if conn is exclude or not conn.connected:
                continue
            try:
                await conn.ws.send_json(message)
            except Exception:
                dead.append(conn)

        for d in dead:
            await self.disconnect_game(game_id, d)

    async def send_to_player(self, game_id: str, user_id: str, message: dict):
        """Send message to a specific player only (locally)."""
        for conn in list(self._rooms.get(game_id, [])):
            if conn.user_id == user_id and conn.connected:
                try:
                    await conn.ws.send_json(message)
                except Exception:
                    pass

    async def _listen_channel(self, channel: str, game_id: str):
        """Redis pub/sub listener — forwards messages to local WS connections."""
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                try:
                    data = json.loads(raw["data"])
                    await self.broadcast_local(game_id, data)
                except Exception as e:
                    log.error("ws.pubsub_error", error=str(e))
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            self._pubsub_tasks.pop(channel, None)

    def get_room_info(self, game_id: str) -> dict:
        connections = self._rooms.get(game_id, [])
        return {
            "players": [c.username for c in connections if c.role in ("white", "black")],
            "spectators": [c.username for c in connections if c.role == "spectator"],
            "count": len(connections),
        }

    def is_player_connected(self, game_id: str, user_id: str) -> bool:
        return any(c.user_id == user_id and c.connected for c in self._rooms.get(game_id, []))


# Singleton
ws_manager = WebSocketManager()
