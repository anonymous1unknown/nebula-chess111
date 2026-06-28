"""
Game Service — manages authoritative game state in Redis.
Each game's live state (FEN, clocks, status) lives in Redis for speed.
Persistent data is written to PostgreSQL.
"""
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.chess_engine import make_move, get_legal_moves, STARTING_FEN, MoveResult
from app.core.elo import new_ratings
from app.models.game import Game, GameStatus, GameResult, GameTermination
from app.models.move import Move
from app.models.user import User
from app.redis_client import get_redis
from app.config import settings

log = structlog.get_logger()

GAME_STATE_PREFIX = "game_state:"
GAME_STATE_TTL = 60 * 60 * 24  # 24 hours


def _state_key(game_id: str) -> str:
    return f"{GAME_STATE_PREFIX}{game_id}"


async def load_game_state(game_id: str) -> Optional[dict]:
    redis = await get_redis()
    raw = await redis.get(_state_key(game_id))
    if raw is None:
        return None
    return json.loads(raw)


async def save_game_state(game_id: str, state: dict):
    redis = await get_redis()
    await redis.setex(_state_key(game_id), GAME_STATE_TTL, json.dumps(state))


async def init_game_state(game: Game, white_username: str, black_username: str) -> dict:
    """Create initial Redis state for a new game."""
    state = {
        "game_id": str(game.id),
        "white_id": str(game.white_id),
        "black_id": str(game.black_id) if game.black_id else None,
        "white_username": white_username,
        "black_username": black_username,
        "fen": STARTING_FEN,
        "status": "active",
        "result": None,
        "termination": None,
        "white_time_ms": game.initial_time * 1000,
        "black_time_ms": game.initial_time * 1000,
        "increment_ms": game.increment * 1000,
        "turn": "white",
        "move_count": 0,
        "last_move_time": time.time(),
        "moves_san": [],
        "moves_uci": [],
        "draw_offered_by": None,
        "is_ai": game.is_ai_game,
        "ai_difficulty": game.ai_difficulty,
    }
    await save_game_state(str(game.id), state)
    return state


async def apply_move(
    game_id: str,
    uci_move: str,
    player_id: str,
    db: AsyncSession,
) -> tuple[Optional[MoveResult], Optional[dict], str]:
    """
    Validate and apply a move.
    Returns (move_result, updated_state, error_message)
    """
    state = await load_game_state(game_id)
    if not state:
        return None, None, "Game not found"

    if state["status"] != "active":
        return None, None, "Game is not active"

    # Verify it's this player's turn
    if state["turn"] == "white" and player_id != state["white_id"]:
        return None, None, "Not your turn"
    if state["turn"] == "black" and player_id != state["black_id"]:
        return None, None, "Not your turn"

    result = make_move(state["fen"], uci_move)
    if not result.valid:
        return None, None, result.error

    # Clock update
    now = time.time()
    elapsed_ms = int((now - state["last_move_time"]) * 1000)

    if state["turn"] == "white":
        state["white_time_ms"] = max(0, state["white_time_ms"] - elapsed_ms + state["increment_ms"])
        if state["white_time_ms"] <= 0:
            state["status"] = "finished"
            state["result"] = "black_wins"
            state["termination"] = "timeout"
    else:
        state["black_time_ms"] = max(0, state["black_time_ms"] - elapsed_ms + state["increment_ms"])
        if state["black_time_ms"] <= 0:
            state["status"] = "finished"
            state["result"] = "white_wins"
            state["termination"] = "timeout"

    state["fen"] = result.fen_after
    state["moves_san"].append(result.san)
    state["moves_uci"].append(uci_move)
    state["move_count"] += 1
    state["last_move_time"] = now
    state["turn"] = "black" if state["turn"] == "white" else "white"
    state["draw_offered_by"] = None  # reset draw offer on move

    if result.is_game_over and state["status"] == "active":
        state["status"] = "finished"
        state["result"] = result.game_result
        state["termination"] = result.termination

    await save_game_state(game_id, state)

    # Persist move to DB asynchronously
    move_number = state["move_count"]
    db_move = Move(
        game_id=uuid.UUID(game_id),
        player_id=uuid.UUID(player_id) if player_id else None,
        move_number=move_number,
        san=result.san,
        uci=uci_move,
        fen_before=state["fen"],  # fen after is correct, before is state before push
        fen_after=result.fen_after,
        time_spent_ms=elapsed_ms,
        clock_remaining_ms=(
            state["white_time_ms"] if state["turn"] == "black"
            else state["black_time_ms"]
        ),
    )
    db.add(db_move)
    await db.flush()

    # If game over: finalize in DB
    if state["status"] == "finished":
        await finalize_game(game_id, state, db)

    return result, state, ""


async def finalize_game(game_id: str, state: dict, db: AsyncSession):
    """Write final result to PostgreSQL and update ELO."""
    now = datetime.now(timezone.utc)
    game_result = state.get("result", "draw")

    result_map = {
        "white_wins": GameResult.white_wins,
        "black_wins": GameResult.black_wins,
        "draw": GameResult.draw,
        "aborted": GameResult.aborted,
    }
    term_map = {
        "checkmate": GameTermination.checkmate,
        "resignation": GameTermination.resignation,
        "timeout": GameTermination.timeout,
        "stalemate": GameTermination.stalemate,
        "insufficient_material": GameTermination.insufficient_material,
        "threefold_repetition": GameTermination.threefold_repetition,
        "fifty_move_rule": GameTermination.fifty_move_rule,
        "agreement": GameTermination.agreement,
        "abandoned": GameTermination.abandoned,
    }

    db_result = result_map.get(game_result, GameResult.draw)
    db_termination = term_map.get(state.get("termination", ""), None)

    await db.execute(
        update(Game).where(Game.id == uuid.UUID(game_id)).values(
            status=GameStatus.finished,
            result=db_result,
            termination=db_termination,
            current_fen=state["fen"],
            move_count=state["move_count"],
            finished_at=now,
        )
    )

    # ELO update for ranked games
    if not state.get("is_ai") and game_result in ("white_wins", "black_wins", "draw"):
        white_id = uuid.UUID(state["white_id"])
        black_id = uuid.UUID(state["black_id"])

        white_user = await db.get(User, white_id)
        black_user = await db.get(User, black_id)

        if white_user and black_user:
            delta_w, delta_b = new_ratings(white_user.elo, black_user.elo, game_result)

            white_user.elo = max(100, white_user.elo + delta_w)
            black_user.elo = max(100, black_user.elo + delta_b)
            white_user.peak_elo = max(white_user.peak_elo, white_user.elo)
            black_user.peak_elo = max(black_user.peak_elo, black_user.elo)

            if game_result == "white_wins":
                white_user.games_won += 1
                black_user.games_lost += 1
            elif game_result == "black_wins":
                black_user.games_won += 1
                white_user.games_lost += 1
            else:
                white_user.games_drawn += 1
                black_user.games_drawn += 1

            white_user.games_played += 1
            black_user.games_played += 1

            await db.execute(
                update(Game).where(Game.id == uuid.UUID(game_id)).values(
                    white_elo_before=white_user.elo - delta_w,
                    black_elo_before=black_user.elo - delta_b,
                    white_elo_change=delta_w,
                    black_elo_change=delta_b,
                )
            )

    await db.flush()
    log.info("game.finalized", game_id=game_id, result=game_result)
