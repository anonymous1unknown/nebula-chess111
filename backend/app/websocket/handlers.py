"""
WebSocket endpoints for Nebula Chess.
Every message is validated server-side. The client cannot determine game state.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db, AsyncSessionLocal
from app.models.chat import ChatMessage
from app.models.game import Game, GameStatus
from app.models.user import User
from app.services.game_service import apply_move, load_game_state, save_game_state
from app.services.stockfish_service import get_ai_move
from app.websocket.manager import ws_manager

log = structlog.get_logger()
router = APIRouter()

MAX_CHAT_LEN = 280
MSG_TYPES = frozenset([
    "move", "chat", "resign", "offer_draw", "accept_draw", "decline_draw",
    "ping", "request_state", "spectate_join",
])


def _auth_ws(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@router.websocket("/ws/game/{game_id}")
async def game_ws(
    websocket: WebSocket,
    game_id: str,
    token: Optional[str] = Query(None),
):
    payload = _auth_ws(token)
    user_id = payload["sub"] if payload else None
    username = payload.get("username", "Anonymous") if payload else "Spectator"

    # Determine role
    state = await load_game_state(game_id)
    role = "spectator"
    if state and user_id:
        if user_id == state.get("white_id"):
            role = "white"
        elif user_id == state.get("black_id"):
            role = "black"

    conn = await ws_manager.connect_game(game_id, websocket, user_id, username, role)

    # Send current state immediately
    if state:
        await websocket.send_json({"type": "game_state", "data": _public_state(state)})

    # Send room info to all
    await ws_manager.send_to_game(game_id, {
        "type": "room_info",
        "data": ws_manager.get_room_info(game_id),
    })

    try:
        while True:
            raw = await websocket.receive_text()

            # Rate limiting (simple per-connection)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"message": "Invalid JSON"}})
                continue

            msg_type = msg.get("type")
            if msg_type not in MSG_TYPES:
                continue

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
                continue

            if msg_type == "request_state":
                fresh = await load_game_state(game_id)
                if fresh:
                    await websocket.send_json({"type": "game_state", "data": _public_state(fresh)})
                continue

            if msg_type == "move":
                await _handle_move(game_id, msg.get("data", {}), user_id, websocket, role)

            elif msg_type == "chat":
                await _handle_chat(game_id, msg.get("data", {}), user_id, username, websocket)

            elif msg_type == "resign":
                await _handle_resign(game_id, user_id, role, username)

            elif msg_type == "offer_draw":
                await _handle_draw_offer(game_id, user_id, role, username)

            elif msg_type == "accept_draw":
                await _handle_accept_draw(game_id, user_id, role, username)

            elif msg_type == "decline_draw":
                await _handle_decline_draw(game_id, user_id, username)

    except WebSocketDisconnect:
        await ws_manager.disconnect_game(game_id, conn)
        await ws_manager.send_to_game(game_id, {
            "type": "player_disconnected",
            "data": {"username": username, "role": role},
        })
    except Exception as e:
        log.error("ws.handler_error", game_id=game_id, error=str(e))
        await ws_manager.disconnect_game(game_id, conn)


async def _handle_move(game_id: str, data: dict, user_id: Optional[str], ws: WebSocket, role: str):
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

    if error:
        await ws.send_json({"type": "move_rejected", "data": {"reason": error}})
        return

    broadcast_msg = {
        "type": "move",
        "data": {
            "uci": result.uci,
            "san": result.san,
            "fen": result.fen_after,
            "is_check": result.is_check,
            "is_checkmate": result.is_checkmate,
            "captured": result.captured_piece,
            "white_time_ms": state["white_time_ms"],
            "black_time_ms": state["black_time_ms"],
            "turn": state["turn"],
            "move_number": state["move_count"],
        },
    }

    if result.is_game_over or state["status"] == "finished":
        broadcast_msg["data"]["game_over"] = {
            "result": state["result"],
            "termination": state["termination"],
        }

    await ws_manager.send_to_game(game_id, broadcast_msg)

    # AI move if needed
    if state.get("is_ai") and state["turn"] == "black" and state["status"] == "active":
        difficulty = state.get("ai_difficulty", 10)
        ai_uci = await get_ai_move(result.fen_after, difficulty)
        if ai_uci:
            async with AsyncSessionLocal() as db:
                ai_result, ai_state, ai_error = await apply_move(
                    game_id, ai_uci, state["black_id"], db
                )
                await db.commit()
            if ai_result:
                ai_msg = {
                    "type": "move",
                    "data": {
                        "uci": ai_result.uci,
                        "san": ai_result.san,
                        "fen": ai_result.fen_after,
                        "is_check": ai_result.is_check,
                        "is_checkmate": ai_result.is_checkmate,
                        "captured": ai_result.captured_piece,
                        "white_time_ms": ai_state["white_time_ms"],
                        "black_time_ms": ai_state["black_time_ms"],
                        "turn": ai_state["turn"],
                        "move_number": ai_state["move_count"],
                    },
                }
                if ai_result.is_game_over or ai_state["status"] == "finished":
                    ai_msg["data"]["game_over"] = {
                        "result": ai_state["result"],
                        "termination": ai_state["termination"],
                    }
                await ws_manager.send_to_game(game_id, ai_msg)


async def _handle_chat(game_id: str, data: dict, user_id: Optional[str], username: str, ws: WebSocket):
    message = str(data.get("message", "")).strip()[:MAX_CHAT_LEN]
    if not message:
        return

    async with AsyncSessionLocal() as db:
        chat = ChatMessage(
            game_id=uuid.UUID(game_id),
            user_id=uuid.UUID(user_id) if user_id else None,
            username=username,
            message=message,
        )
        db.add(chat)
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "chat",
        "data": {
            "username": username,
            "message": message,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    })


async def _handle_resign(game_id: str, user_id: Optional[str], role: str, username: str):
    if not user_id or role == "spectator":
        return
    state = await load_game_state(game_id)
    if not state or state["status"] != "active":
        return

    result = "black_wins" if role == "white" else "white_wins"
    state["status"] = "finished"
    state["result"] = result
    state["termination"] = "resignation"
    await save_game_state(game_id, state)

    async with AsyncSessionLocal() as db:
        from app.services.game_service import finalize_game
        await finalize_game(game_id, state, db)
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "game_over",
        "data": {
            "result": result,
            "termination": "resignation",
            "resigned_by": username,
        },
    })


async def _handle_draw_offer(game_id: str, user_id: Optional[str], role: str, username: str):
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


async def _handle_accept_draw(game_id: str, user_id: Optional[str], role: str, username: str):
    if not user_id or role == "spectator":
        return
    state = await load_game_state(game_id)
    if not state or state["status"] != "active":
        return

    offered_by = state.get("draw_offered_by")
    if not offered_by or offered_by == role:
        return  # Can't accept own draw offer

    state["status"] = "finished"
    state["result"] = "draw"
    state["termination"] = "agreement"
    await save_game_state(game_id, state)

    async with AsyncSessionLocal() as db:
        from app.services.game_service import finalize_game
        await finalize_game(game_id, state, db)
        await db.commit()

    await ws_manager.send_to_game(game_id, {
        "type": "game_over",
        "data": {"result": "draw", "termination": "agreement"},
    })


async def _handle_decline_draw(game_id: str, user_id: Optional[str], username: str):
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


def _public_state(state: dict) -> dict:
    """Strip internal server data before sending to clients."""
    return {
        "game_id": state.get("game_id"),
        "fen": state.get("fen"),
        "turn": state.get("turn"),
        "status": state.get("status"),
        "result": state.get("result"),
        "termination": state.get("termination"),
        "white_time_ms": state.get("white_time_ms"),
        "black_time_ms": state.get("black_time_ms"),
        "move_count": state.get("move_count"),
        "moves_san": state.get("moves_san", []),
        "white_username": state.get("white_username"),
        "black_username": state.get("black_username"),
        "draw_offered_by": state.get("draw_offered_by"),
    }
