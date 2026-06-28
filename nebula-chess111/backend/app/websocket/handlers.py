"""
WebSocket endpoints for Nebula Chess.
Every move is validated server-side. The client never determines game legality.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.chess_engine import STARTING_FEN
from app.core.security import decode_access_token
from app.database import AsyncSessionLocal
from app.models.chat import ChatMessage
from app.models.game import Game
from app.models.user import User
from app.services.game_service import (
    apply_move,
    finalize_game,
    load_game_state,
    save_game_state,
)
from app.services.stockfish_service import get_ai_move
from app.websocket.manager import ws_manager

log    = structlog.get_logger()
router = APIRouter()

MAX_CHAT_LEN      = 280
AI_PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000001"

MSG_TYPES = frozenset([
    "move", "chat", "resign", "offer_draw", "accept_draw", "decline_draw",
    "ping", "request_state", "spectate_join",
])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_ws(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


def _ai_player_id(state: dict) -> Optional[str]:
    """Returns the AI's player_id if it is the AI's turn, else None."""
    if not state.get("is_ai"):
        return None
    turn  = state["turn"]
    ai_id = state["white_id"] if turn == "white" else state["black_id"]
    return ai_id if ai_id == AI_PLACEHOLDER_ID else None


def _public_state(state: dict) -> dict:
    """Strip internal server fields before sending to clients."""
    return {
        "game_id":         state.get("game_id"),
        "fen":             state.get("fen"),
        "turn":            state.get("turn"),
        "status":          state.get("status"),
        "result":          state.get("result"),
        "termination":     state.get("termination"),
        "white_time_ms":   state.get("white_time_ms"),
        "black_time_ms":   state.get("black_time_ms"),
        "move_count":      state.get("move_count"),
        "moves_san":       state.get("moves_san", []),
        "white_username":  state.get("white_username"),
        "black_username":  state.get("black_username"),
        "draw_offered_by": state.get("draw_offered_by"),
    }


# ── Role resolution ───────────────────────────────────────────────────────────

class _RoleInfo:
    """All data resolved from the DB for a connecting player."""
    __slots__ = ("role", "white_username", "black_username", "invite_code")

    def __init__(
        self,
        role:            str,
        white_username:  Optional[str] = None,
        black_username:  Optional[str] = None,
        invite_code:     Optional[str] = None,
    ):
        self.role           = role
        self.white_username = white_username
        self.black_username = black_username
        self.invite_code    = invite_code


async def _resolve_role(
    game_id: str,
    user_id: Optional[str],
    state:   Optional[dict],
) -> _RoleInfo:
    """
    Determine this connection's role and return supplementary game metadata.

    Stage 1 — Redis (active games):
        State is in Redis → compare str(user_id) against str(white_id / black_id).
        str() on both sides eliminates UUID-object-vs-string type mismatches.

    Stage 2 — PostgreSQL fallback (waiting PvP game, Redis not initialised yet):
        The creator connects right after create_game(). init_game_state() has
        NOT been called (it runs only when the second player calls /join).
        Redis is empty → state is None → we must check the DB to assign the
        correct role and retrieve the invite_code for the waiting-room screen.
    """
    if not user_id:
        return _RoleInfo("spectator")

    # ── Stage 1: Redis ────────────────────────────────────────────────────────
    if state:
        if str(state.get("white_id", "")) == str(user_id):
            return _RoleInfo("white",
                             state.get("white_username"),
                             state.get("black_username"))
        if str(state.get("black_id", "")) == str(user_id):
            return _RoleInfo("black",
                             state.get("white_username"),
                             state.get("black_username"))
        return _RoleInfo("spectator",
                         state.get("white_username"),
                         state.get("black_username"))

    # ── Stage 2: DB fallback ─────────────────────────────────────────────────
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return _RoleInfo("spectator")

    try:
        async with AsyncSessionLocal() as db:
            game = await db.get(Game, game_uuid)
            if game is None:
                return _RoleInfo("spectator")

            # Resolve usernames (black_id may be None for an open waiting game)
            white_username: Optional[str] = None
            black_username: Optional[str] = None

            if game.white_id:
                wu = await db.get(User, game.white_id)
                white_username = wu.username if wu else None
            if game.black_id:
                bu = await db.get(User, game.black_id)
                black_username = bu.username if bu else None

            invite_code = str(game.invite_code) if game.invite_code else None

            # str() is mandatory: game.white_id is uuid.UUID, user_id is str
            if game.white_id and str(game.white_id) == str(user_id):
                return _RoleInfo("white", white_username, black_username, invite_code)
            if game.black_id and str(game.black_id) == str(user_id):
                return _RoleInfo("black", white_username, black_username, invite_code)

            # User is not a player — spectator watching a waiting game.
            # Still return invite_code so the frontend can render a join prompt.
            return _RoleInfo("spectator", white_username, black_username, invite_code)

    except Exception as exc:
        log.warning("ws.role_resolve_db_error", game_id=game_id, error=str(exc))
        return _RoleInfo("spectator")


# ── Main WebSocket endpoint ───────────────────────────────────────────────────

@router.websocket("/ws/game/{game_id}")
async def game_ws(
    websocket: WebSocket,
    game_id:   str,
    token:     Optional[str] = Query(None),
):
    payload  = _auth_ws(token)
    user_id  = payload["sub"]                       if payload else None
    username = payload.get("username", "Anonymous") if payload else "Spectator"

    state    = await load_game_state(game_id)
    info     = await _resolve_role(game_id, user_id, state)

    log.info("ws.connected",
             game_id=game_id, username=username, role=info.role)

    conn = await ws_manager.connect_game(
        game_id, websocket, user_id, username, info.role
    )

    # ── Send initial state ────────────────────────────────────────────────────
    if state:
        # Active or finished game — full authoritative state from Redis
        await websocket.send_json({
            "type": "game_state",
            "data": _public_state(state),
        })

    else:
        # Game is still in "waiting" status (Redis not yet initialised).
        # Send a minimal waiting-state so the frontend can render the correct
        # screen for both the creator (WaitingLobby) and visitors (JoinPrompt).
        #
        # invite_code is included so the creator can display a correct shareable
        # link and the visitor's join prompt already has the code it needs.
        await websocket.send_json({
            "type": "game_state",
            "data": {
                "game_id":         game_id,
                "status":          "waiting",
                "fen":             STARTING_FEN,
                "turn":            "white",
                "result":          None,
                "termination":     None,
                "white_time_ms":   None,
                "black_time_ms":   None,
                "move_count":      0,
                "moves_san":       [],
                "white_username":  info.white_username,
                "black_username":  info.black_username,
                "draw_offered_by": None,
                # KEY FIX: sent to everyone connecting to a waiting game.
                # Creator uses it to build the shareable link.
                # Visitor uses it as the code to call /join/{invite_code}.
                "invite_code":     info.invite_code,
            },
        })

    await ws_manager.send_to_game(game_id, {
        "type": "room_info",
        "data": ws_manager.get_room_info(game_id),
    })

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                })
                continue

            msg_type = msg.get("type")
            if msg_type not in MSG_TYPES:
                continue

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})

            elif msg_type == "request_state":
                fresh = await load_game_state(game_id)
                if fresh:
                    await websocket.send_json({
                        "type": "game_state",
                        "data": _public_state(fresh),
                    })

            elif msg_type == "move":
                await _handle_move(
                    game_id, msg.get("data", {}), user_id, websocket, info.role
                )
            elif msg_type == "chat":
                await _handle_chat(
                    game_id, msg.get("data", {}), user_id, username
                )
            elif msg_type == "resign":
                await _handle_resign(game_id, user_id, info.role, username)
            elif msg_type == "offer_draw":
                await _handle_draw_offer(game_id, user_id, info.role, username)
            elif msg_type == "accept_draw":
                await _handle_accept_draw(game_id, user_id, info.role, username)
            elif msg_type == "decline_draw":
                await _handle_decline_draw(game_id, user_id, username)

    except WebSocketDisconnect:
        await ws_manager.disconnect_game(game_id, conn)
        await ws_manager.send_to_game(game_id, {
            "type": "player_disconnected",
            "data": {"username": username, "role": info.role},
        })
    except Exception as exc:
        log.error("ws.handler_error", game_id=game_id, error=str(exc))
        await ws_manager.disconnect_game(game_id, conn)


# ── Message handlers ──────────────────────────────────────────────────────────

async def _handle_move(
    game_id: str,
    data:    dict,
    user_id: Optional[str],
    ws:      WebSocket,
    role:    str,
) -> None:
    if not user_id:
        await ws.send_json({"type": "error", "data": {"message": "Authentication required"}})
        return

    uci = data.get("uci", "").strip()
    if not uci or len(uci) < 4:
        await ws.send_json({"type": "error", "data": {"message": "Invalid move format"}})
        return

    async with AsyncSessionLocal() as db:
        result, state, error = await apply_move(game_id, uci, user_id, db)
        await db.commit()

    if error or result is None or state is None:
        await ws.send_json({
            "type": "move_rejected",
            "data": {"reason": error or "Unknown error"},
        })
        return

    broadcast: dict = {
        "type": "move",
        "data": {
            "uci":           result.uci,
            "san":           result.san,
            "fen":           result.fen_after,
            "is_check":      result.is_check,
            "is_checkmate":  result.is_checkmate,
            "captured":      result.captured_piece,
            "white_time_ms": state["white_time_ms"],
            "black_time_ms": state["black_time_ms"],
            "turn":          state["turn"],
            "move_number":   state["move_count"],
        },
    }
    if result.is_game_over or state["status"] == "finished":
        broadcast["data"]["game_over"] = {
            "result":      state["result"],
            "termination": state["termination"],
        }
    await ws_manager.send_to_game(game_id, broadcast)

    # AI response (colour-aware)
    ai_id = _ai_player_id(state)
    if ai_id and state["status"] == "active":
        ai_uci = await get_ai_move(result.fen_after, state.get("ai_difficulty", 10))
        if ai_uci:
            async with AsyncSessionLocal() as db:
                ai_result, ai_state, _ = await apply_move(game_id, ai_uci, ai_id, db)
                await db.commit()

            if ai_result and ai_state:
                ai_msg: dict = {
                    "type": "move",
                    "data": {
                        "uci":           ai_result.uci,
                        "san":           ai_result.san,
                        "fen":           ai_result.fen_after,
                        "is_check":      ai_result.is_check,
                        "is_checkmate":  ai_result.is_checkmate,
                        "captured":      ai_result.captured_piece,
                        "white_time_ms": ai_state["white_time_ms"],
                        "black_time_ms": ai_state["black_time_ms"],
                        "turn":          ai_state["turn"],
                        "move_number":   ai_state["move_count"],
                    },
                }
                if ai_result.is_game_over or ai_state["status"] == "finished":
                    ai_msg["data"]["game_over"] = {
                        "result":      ai_state["result"],
                        "termination": ai_state["termination"],
                    }
                await ws_manager.send_to_game(game_id, ai_msg)


async def _handle_chat(
    game_id:  str,
    data:     dict,
    user_id:  Optional[str],
    username: str,
) -> None:
    message = str(data.get("message", "")).strip()[:MAX_CHAT_LEN]
    if not message:
        return

    async with AsyncSessionLocal() as db:
        db.add(ChatMessage(
            game_id=uuid.UUID(game_id),
            user_id=uuid.UUID(user_id) if user_id else None,
            username=username,
            message=message,
        ))
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "chat",
        "data": {
            "username": username,
            "message":  message,
            "ts":       datetime.now(timezone.utc).isoformat(),
        },
    })


async def _handle_resign(
    game_id:  str,
    user_id:  Optional[str],
    role:     str,
    username: str,
) -> None:
    if not user_id or role == "spectator":
        return
    state = await load_game_state(game_id)
    if not state or state["status"] != "active":
        return

    result_str = "black_wins" if role == "white" else "white_wins"
    state.update(status="finished", result=result_str, termination="resignation")
    await save_game_state(game_id, state)

    async with AsyncSessionLocal() as db:
        await finalize_game(game_id, state, db)
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "game_over",
        "data": {
            "result":      result_str,
            "termination": "resignation",
            "resigned_by": username,
        },
    })


async def _handle_draw_offer(
    game_id:  str,
    user_id:  Optional[str],
    role:     str,
    username: str,
) -> None:
    if not user_id or role == "spectator":
        return
    state = await load_game_state(game_id)
    if not state or state["status"] != "active":
        return

    state["draw_offered_by"] = role
    await save_game_state(game_id, state)
    await ws_manager.send_to_game(game_id, {
        "type": "draw_offered",
        "data": {"by": username, "role": role},
    })


async def _handle_accept_draw(
    game_id:  str,
    user_id:  Optional[str],
    role:     str,
    username: str,
) -> None:
    if not user_id or role == "spectator":
        return
    state = await load_game_state(game_id)
    if not state or state["status"] != "active":
        return

    offered_by = state.get("draw_offered_by")
    if not offered_by or offered_by == role:
        return

    state.update(status="finished", result="draw", termination="agreement")
    await save_game_state(game_id, state)

    async with AsyncSessionLocal() as db:
        await finalize_game(game_id, state, db)
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "game_over",
        "data": {"result": "draw", "termination": "agreement"},
    })


async def _handle_decline_draw(
    game_id:  str,
    user_id:  Optional[str],
    username: str,
) -> None:
    if not user_id:
        return
    state = await load_game_state(game_id)
    if not state:
        return
    state["draw_offered_by"] = None
    await save_game_state(game_id, state)
    await ws_manager.send_to_game(game_id, {
        "type": "draw_declined",
        "data": {"by": username},
    })
