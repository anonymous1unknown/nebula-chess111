"""
Game Service — server-authoritative game state.

Live state  → Redis  (speed, pub/sub)
Persistence → PostgreSQL via SQLAlchemy ORM Unit-of-Work (correctness, type safety)

Key invariants
──────────────
• old_fen is captured BEFORE state["fen"] is mutated, so Move.fen_before
  and Move.fen_after always differ.
• finalize_game() uses a single db.get() + attribute mutation + db.flush(),
  eliminating the dual-update() pattern and the native-enum cast crash.
• Redis I/O is wrapped in retry helpers with exponential back-off; failures
  are logged but never propagate as unhandled exceptions.
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Optional

import structlog
from redis.exceptions import ConnectionError as RedisConnError, TimeoutError as RedisTimeout
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chess_engine import make_move, STARTING_FEN, MoveResult
from app.core.elo import new_ratings
from app.models.game import (
    Game,
    GameMode,
    GameResult,
    GameStatus,
    GameTermination,
    TimeControl,
)
from app.models.move import Move
from app.models.user import User
from app.redis_client import get_redis

log = structlog.get_logger()

GAME_STATE_PREFIX = "game_state:"
GAME_STATE_TTL    = 60 * 60 * 24   # 24 h
_REDIS_RETRIES    = 3
_REDIS_BACKOFF    = 0.25            # seconds; doubles each retry


# ── Redis helpers ─────────────────────────────────────────────────────────────

async def _redis_get(key: str) -> Optional[str]:
    delay = _REDIS_BACKOFF
    for attempt in range(_REDIS_RETRIES):
        try:
            r = await get_redis()
            return await r.get(key)
        except (RedisConnError, RedisTimeout, OSError) as exc:
            if attempt == _REDIS_RETRIES - 1:
                log.error("redis.get_failed", key=key, error=str(exc))
                return None
            log.warning("redis.get_retry", key=key, attempt=attempt + 1, delay=delay)
            await asyncio.sleep(delay)
            delay *= 2


async def _redis_setex(key: str, ttl: int, value: str) -> bool:
    delay = _REDIS_BACKOFF
    for attempt in range(_REDIS_RETRIES):
        try:
            r = await get_redis()
            await r.setex(key, ttl, value)
            return True
        except (RedisConnError, RedisTimeout, OSError) as exc:
            if attempt == _REDIS_RETRIES - 1:
                log.error("redis.setex_failed", key=key, error=str(exc))
                return False
            log.warning("redis.setex_retry", key=key, attempt=attempt + 1, delay=delay)
            await asyncio.sleep(delay)
            delay *= 2
    return False


async def _redis_publish(channel: str, message: str) -> None:
    delay = _REDIS_BACKOFF
    for attempt in range(_REDIS_RETRIES):
        try:
            r = await get_redis()
            await r.publish(channel, message)
            return
        except (RedisConnError, RedisTimeout, OSError) as exc:
            if attempt == _REDIS_RETRIES - 1:
                log.warning("redis.publish_failed", channel=channel, error=str(exc))
                return
            await asyncio.sleep(delay)
            delay *= 2


# ── State helpers ─────────────────────────────────────────────────────────────

def _state_key(game_id: str) -> str:
    return f"{GAME_STATE_PREFIX}{game_id}"


async def load_game_state(game_id: str) -> Optional[dict]:
    raw = await _redis_get(_state_key(game_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.error("redis.corrupt_state", game_id=game_id)
        return None


async def save_game_state(game_id: str, state: dict) -> bool:
    return await _redis_setex(_state_key(game_id), GAME_STATE_TTL, json.dumps(state))


async def init_game_state(
    game: Game, white_username: str, black_username: str
) -> dict:
    state = {
        "game_id":         str(game.id),
        "white_id":        str(game.white_id),
        "black_id":        str(game.black_id) if game.black_id else None,
        "white_username":  white_username,
        "black_username":  black_username,
        "fen":             STARTING_FEN,
        "status":          "active",
        "result":          None,
        "termination":     None,
        "white_time_ms":   game.initial_time * 1000,
        "black_time_ms":   game.initial_time * 1000,
        "increment_ms":    game.increment * 1000,
        "turn":            "white",
        "move_count":      0,
        "last_move_time":  time.time(),
        "moves_san":       [],
        "moves_uci":       [],
        "draw_offered_by": None,
        "is_ai":           game.is_ai_game,
        "ai_difficulty":   game.ai_difficulty,
    }
    await save_game_state(str(game.id), state)
    return state


# ── Move application ──────────────────────────────────────────────────────────

async def apply_move(
    game_id:   str,
    uci_move:  str,
    player_id: str,
    db:        AsyncSession,
) -> tuple[Optional[MoveResult], Optional[dict], str]:
    """
    Validate and apply one move server-side.

    Returns
    -------
    (MoveResult, updated_state, "")   on success
    (None,       None,          msg)  on failure
    """
    state = await load_game_state(game_id)
    if not state:
        return None, None, "Game not found or Redis unavailable"

    if state["status"] != "active":
        return None, None, "Game is not active"

    if state["turn"] == "white" and player_id != state["white_id"]:
        return None, None, "Not your turn"
    if state["turn"] == "black" and player_id != state["black_id"]:
        return None, None, "Not your turn"

    # ── FIX 1: capture old FEN before ANY mutation ────────────────────────────
    # Both fen_before and fen_after on the Move row will now always differ.
    old_fen = state["fen"]

    result = make_move(old_fen, uci_move)
    if not result.valid:
        return None, None, result.error

    # ── Clock ─────────────────────────────────────────────────────────────────
    now        = time.time()
    elapsed_ms = int((now - state["last_move_time"]) * 1000)

    if state["turn"] == "white":
        state["white_time_ms"] = max(
            0, state["white_time_ms"] - elapsed_ms + state["increment_ms"]
        )
        if state["white_time_ms"] <= 0:
            state.update(status="finished", result="black_wins", termination="timeout")
    else:
        state["black_time_ms"] = max(
            0, state["black_time_ms"] - elapsed_ms + state["increment_ms"]
        )
        if state["black_time_ms"] <= 0:
            state.update(status="finished", result="white_wins", termination="timeout")

    # ── State mutation (FEN is updated HERE, after old_fen is safe) ───────────
    state["fen"]             = result.fen_after
    state["moves_san"].append(result.san)
    state["moves_uci"].append(uci_move)
    state["move_count"]     += 1
    state["last_move_time"]  = now
    state["turn"]            = "black" if state["turn"] == "white" else "white"
    state["draw_offered_by"] = None

    if result.is_game_over and state["status"] == "active":
        state.update(
            status="finished",
            result=result.game_result,
            termination=result.termination,
        )

    await save_game_state(game_id, state)

    # ── Persist Move row ──────────────────────────────────────────────────────
    clock_after_move = (
        state["white_time_ms"] if state["turn"] == "black"
        else state["black_time_ms"]
    )
    db_move = Move(
        game_id             = uuid.UUID(game_id),
        player_id           = uuid.UUID(player_id) if player_id else None,
        move_number         = state["move_count"],
        san                 = result.san,
        uci                 = uci_move,
        fen_before          = old_fen,           # ← FIX 1: position BEFORE the move
        fen_after           = result.fen_after,  # ← position AFTER the move
        time_spent_ms       = elapsed_ms,
        clock_remaining_ms  = clock_after_move,
    )
    db.add(db_move)
    await db.flush()

    if state["status"] == "finished":
        await finalize_game(game_id, state, db)

    return result, state, ""


# ── Game finalization ─────────────────────────────────────────────────────────

# Lookup tables — string keys because Redis state uses plain strings
_RESULT_MAP: dict[str, GameResult] = {
    "white_wins": GameResult.white_wins,
    "black_wins": GameResult.black_wins,
    "draw":       GameResult.draw,
    "aborted":    GameResult.aborted,
}

_TERMINATION_MAP: dict[str, GameTermination] = {
    "checkmate":              GameTermination.checkmate,
    "resignation":            GameTermination.resignation,
    "timeout":                GameTermination.timeout,
    "stalemate":              GameTermination.stalemate,
    "insufficient_material":  GameTermination.insufficient_material,
    "threefold_repetition":   GameTermination.threefold_repetition,
    "fifty_move_rule":        GameTermination.fifty_move_rule,
    "agreement":              GameTermination.agreement,
    "abandoned":              GameTermination.abandoned,
}


async def finalize_game(game_id: str, state: dict, db: AsyncSession) -> None:
    """
    Write the final result to PostgreSQL.

    ── FIX 2: ORM Unit-of-Work pattern ─────────────────────────────────────────
    Instead of two separate core update() statements (which bypass SQLAlchemy's
    type system and cause the native-enum cast crash), we:

      1. db.get(Game, ...)          → one SELECT
      2. mutate game.* attributes   → SQLAlchemy ORM handles enum casting
      3. mutate user.* attributes   → same session / identity map
      4. db.flush()                 → ONE UPDATE per dirty object

    This eliminates the crash AND the redundant DB round-trip.
    """
    game: Optional[Game] = await db.get(Game, uuid.UUID(game_id))
    if game is None:
        log.error("game.finalize_not_found", game_id=game_id)
        return

    now             = datetime.now(timezone.utc)
    result_str      = state.get("result", "draw")
    termination_str = state.get("termination", "")

    # ── Mutate game object — ORM resolves Python enum → PostgreSQL native type ─
    game.status      = GameStatus.finished                           # always finished here
    game.result      = _RESULT_MAP.get(result_str, GameResult.draw)
    game.termination = _TERMINATION_MAP.get(termination_str)
    game.current_fen = state["fen"]
    game.move_count  = state["move_count"]
    game.finished_at = now

    # ── ELO — mutate on the same game object (no second update()) ─────────────
    is_rated = (
        not state.get("is_ai")
        and result_str in ("white_wins", "black_wins", "draw")
        and state.get("white_id")
        and state.get("black_id")
    )

    if is_rated:
        white_user: Optional[User] = await db.get(User, uuid.UUID(state["white_id"]))
        black_user: Optional[User] = await db.get(User, uuid.UUID(state["black_id"]))

        if white_user and black_user:
            delta_w, delta_b = new_ratings(white_user.elo, black_user.elo, result_str)

            # Record pre-game ratings and deltas directly on the game row
            game.white_elo_before = white_user.elo
            game.black_elo_before = black_user.elo
            game.white_elo_change = delta_w
            game.black_elo_change = delta_b

            # Apply rating changes
            white_user.elo      = max(100, white_user.elo + delta_w)
            black_user.elo      = max(100, black_user.elo + delta_b)
            white_user.peak_elo = max(white_user.peak_elo, white_user.elo)
            black_user.peak_elo = max(black_user.peak_elo, black_user.elo)

            # Win / loss / draw tallies
            if result_str == "white_wins":
                white_user.games_won  += 1
                black_user.games_lost += 1
            elif result_str == "black_wins":
                black_user.games_won  += 1
                white_user.games_lost += 1
            else:
                white_user.games_drawn += 1
                black_user.games_drawn += 1

            white_user.games_played += 1
            black_user.games_played += 1

    # Single flush — SQLAlchemy emits one UPDATE per dirty mapped object
    await db.flush()
    log.info("game.finalized", game_id=game_id, result=result_str)
