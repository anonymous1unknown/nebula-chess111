"""
Games API — create, join, query.

Fixes applied
─────────────
1. _cast_*() lambdas REMOVED — with native_enum=False the columns are plain
   VARCHAR; casting to a non-existent PG type "gamestatus" crashes every query.
   Direct ORM comparison (Game.status == GameStatus.finished) is correct.

2. join_game now publishes a WebSocket "game_started" event via ws_manager so
   the waiting player (already connected on WS) knows the game has begun.

3. join_game prevents a player from joining their own game.

4. UUID validation helper wraps uuid.UUID() so invalid game_ids return 404
   instead of an unhandled ValueError → 500.

5. `import random` moved to module level.

6. Static routes (/active, /waiting, /history/me) placed BEFORE parameterised
   routes (/{game_id}/...) to guarantee correct FastAPI path matching.

7. /moves response now includes fen_before so clients can replay positions.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.core.chess_engine import get_legal_moves, validate_fen, STARTING_FEN
from app.core.security import generate_invite_code
from app.database import get_db
from app.models.game import (
    Game, GameInvitation,
    GameMode, GameStatus, GameResult, GameTermination, TimeControl,
)
from app.models.move import Move
from app.models.user import User
from app.services.game_service import init_game_state, load_game_state
from app.websocket.manager import ws_manager

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_uuid(value: str, label: str = "id") -> uuid.UUID:
    """Parse a UUID string and raise 404 (not 500) on invalid format."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail=f"Invalid {label}")


def _time_control(seconds: int) -> TimeControl:
    if seconds < 180:  return TimeControl.bullet
    if seconds < 600:  return TimeControl.blitz
    if seconds < 1800: return TimeControl.rapid
    return TimeControl.classical


def _game_summary(game: Game, viewer_id: uuid.UUID) -> dict:
    is_white = game.white_id == viewer_id
    return {
        "id":           str(game.id),
        "result":       game.result.value      if game.result      else None,
        "termination":  game.termination.value if game.termination else None,
        "mode":         game.mode.value,
        "time_control": game.time_control.value,
        "initial_time": game.initial_time,
        "increment":    game.increment,
        "move_count":   game.move_count,
        "played_as":    "white" if is_white else "black",
        "elo_change":   game.white_elo_change if is_white else game.black_elo_change,
        "finished_at":  game.finished_at.isoformat() if game.finished_at else None,
    }


# ── Request / Response schemas ────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    mode:          GameMode      = GameMode.casual
    time_seconds:  int           = 600
    increment:     int           = 5
    color:         Optional[str] = None   # "white" | "black" | None (random)
    vs_ai:         bool          = False
    ai_difficulty: int           = 10
    fen:           Optional[str] = None

    @field_validator("time_seconds")
    @classmethod
    def validate_time(cls, v: int) -> int:
        if not 30 <= v <= 86_400:
            raise ValueError("time_seconds must be between 30 and 86400")
        return v

    @field_validator("increment")
    @classmethod
    def validate_increment(cls, v: int) -> int:
        if not 0 <= v <= 60:
            raise ValueError("increment must be between 0 and 60")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("white", "black"):
            raise ValueError("color must be 'white', 'black', or null")
        return v

    @field_validator("ai_difficulty")
    @classmethod
    def validate_difficulty(cls, v: int) -> int:
        if not 1 <= v <= 20:
            raise ValueError("ai_difficulty must be between 1 and 20")
        return v


class CreateGameResponse(BaseModel):
    game_id:     str
    invite_code: Optional[str]
    color:       str


# ── Static routes FIRST — must precede /{game_id}/... to avoid shadowing ──────

@router.get("/history/me")
async def my_history(
    limit:        int  = 20,
    offset:       int  = 0,
    current_user: User = Depends(get_current_user),
    db:    AsyncSession = Depends(get_db),
):
    """Game history for the authenticated player."""
    q = await db.execute(
        select(Game)
        .where(
            or_(
                Game.white_id == current_user.id,
                Game.black_id == current_user.id,
            )
        )
        # FIX: direct ORM comparison — works with native_enum=False (VARCHAR).
        # The old cast(v.value, SAEnum(name="gamestatus", create_type=False))
        # crashed because PG type "gamestatus" does not exist in Option 2.
        .where(Game.status == GameStatus.finished)
        .order_by(desc(Game.finished_at))
        .limit(min(limit, 100))
        .offset(offset)
    )
    return [_game_summary(g, current_user.id) for g in q.scalars().all()]


@router.get("/active")
async def active_games(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Live PvP games — for the lobby spectate list."""
    q = await db.execute(
        select(Game)
        .where(Game.status == GameStatus.active)      # FIX: direct comparison
        .where(Game.is_ai_game == False)              # noqa: E712
        .order_by(desc(Game.started_at))
        .limit(min(limit, 50))
    )
    return [
        {
            "id":           str(g.id),
            "white_id":     str(g.white_id) if g.white_id else None,
            "black_id":     str(g.black_id) if g.black_id else None,
            "time_control": g.time_control.value,
            "initial_time": g.initial_time,
            "increment":    g.increment,
            "move_count":   g.move_count,
            "started_at":   g.started_at.isoformat() if g.started_at else None,
        }
        for g in q.scalars().all()
    ]


@router.get("/waiting")
async def waiting_games(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Open PvP games waiting for a second player."""
    q = await db.execute(
        select(Game)
        .where(Game.status == GameStatus.waiting)     # FIX: direct comparison
        .where(Game.is_ai_game == False)              # noqa: E712
        .order_by(desc(Game.created_at))
        .limit(min(limit, 50))
    )
    return [
        {
            "id":           str(g.id),
            "invite_code":  g.invite_code,
            "time_control": g.time_control.value,
            "initial_time": g.initial_time,
            "increment":    g.increment,
            "created_at":   g.created_at.isoformat(),
        }
        for g in q.scalars().all()
    ]


# ── Game creation & joining ───────────────────────────────────────────────────

@router.post("/create", response_model=CreateGameResponse)
async def create_game(
    body:         CreateGameRequest,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    if body.fen and not validate_fen(body.fen):
        raise HTTPException(400, "Invalid FEN string")

    color = body.color or random.choice(["white", "black"])

    game = Game(
        invite_code=generate_invite_code(),
        mode=body.mode,
        time_control=_time_control(body.time_seconds),
        initial_time=body.time_seconds,
        increment=body.increment,
        is_ai_game=body.vs_ai,
        ai_difficulty=body.ai_difficulty if body.vs_ai else None,
        current_fen=body.fen or STARTING_FEN,
    )

    if color == "white":
        game.white_id = current_user.id
    else:
        game.black_id = current_user.id

    if body.vs_ai:
        ai_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        game.black_id   = ai_id if color == "white" else game.black_id
        game.white_id   = ai_id if color == "black" else game.white_id
        game.status     = GameStatus.active
        game.started_at = datetime.now(timezone.utc)

    db.add(game)
    await db.flush()

    # AI game: initialise Redis state immediately (both players are known)
    # PvP game: Redis state is initialised in join_game when the opponent arrives
    if body.vs_ai:
        white_name = current_user.username if color == "white" else "Stockfish"
        black_name = "Stockfish"           if color == "white" else current_user.username
        await init_game_state(game, white_name, black_name)

    return CreateGameResponse(
        game_id=str(game.id),
        invite_code=game.invite_code if not body.vs_ai else None,
        color=color,
    )


@router.post("/join/{invite_code}")
async def join_game(
    invite_code:  str,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Game).where(Game.invite_code == invite_code.strip().upper())
    )
    game = q.scalar_one_or_none()
    if not game:
        raise HTTPException(404, "Game not found")

    if game.status != GameStatus.waiting:
        raise HTTPException(409, "Game is no longer open")

    # FIX: prevent a player from joining their own game
    if game.white_id == current_user.id or game.black_id == current_user.id:
        raise HTTPException(409, "You are already in this game")

    # Assign the joiner to whichever slot is open
    if game.white_id is None:
        game.white_id = current_user.id
        color = "white"
        other_q = await db.execute(select(User).where(User.id == game.black_id))
        other   = other_q.scalar_one_or_none()
        white_name = current_user.username
        black_name = other.username if other else "?"
    elif game.black_id is None:
        game.black_id = current_user.id
        color = "black"
        other_q = await db.execute(select(User).where(User.id == game.white_id))
        other   = other_q.scalar_one_or_none()
        white_name = other.username if other else "?"
        black_name = current_user.username
    else:
        raise HTTPException(409, "Game is full")

    game.status     = GameStatus.active
    game.started_at = datetime.now(timezone.utc)
    await db.flush()

    # Initialise authoritative state in Redis now that both players are known
    state = await init_game_state(game, white_name, black_name)

    # FIX: notify the creator who is already waiting on the WebSocket.
    # Without this, player 1 sits on the lobby page forever because their
    # open WS connection never receives a signal that the game has started.
    await ws_manager.send_to_game(str(game.id), {
        "type": "game_started",
        "data": {
            "game_id":        str(game.id),
            "white_username": white_name,
            "black_username": black_name,
            "fen":            state["fen"],
            "turn":           "white",
            "status":         "active",
            "white_time_ms":  state["white_time_ms"],
            "black_time_ms":  state["black_time_ms"],
            "move_count":     0,
            "moves_san":      [],
        },
    })

    return {"game_id": str(game.id), "color": color}


# ── Parameterised routes — AFTER all static routes ────────────────────────────

@router.get("/{game_id}/state")
async def get_game_state(
    game_id: str,
    _: Optional[User] = Depends(get_optional_user),
):
    _to_uuid(game_id, "game_id")          # FIX: 404 on invalid UUID, not 500
    state = await load_game_state(game_id)
    if not state:
        raise HTTPException(404, "Game not found or expired")
    return state


@router.get("/{game_id}/legal-moves")
async def legal_moves(
    game_id: str,
    _: Optional[User] = Depends(get_optional_user),
):
    _to_uuid(game_id, "game_id")
    state = await load_game_state(game_id)
    if not state:
        raise HTTPException(404, "Game not found")
    return {"moves": get_legal_moves(state["fen"])}


@router.get("/{game_id}/moves")
async def get_moves(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    gid = _to_uuid(game_id, "game_id")   # FIX: raises 404, not ValueError
    q = await db.execute(
        select(Move)
        .where(Move.game_id == gid)
        .order_by(Move.move_number)
    )
    return [
        {
            "number":             m.move_number,
            "san":                m.san,
            "uci":                m.uci,
            "fen_before":         m.fen_before,   # FIX: included for board replay
            "fen_after":          m.fen_after,
            "time_spent_ms":      m.time_spent_ms,
            "clock_remaining_ms": m.clock_remaining_ms,
            "timestamp":          m.timestamp.isoformat(),
            # Analysis fields — null until post-game Stockfish runs
            "eval_before":        m.eval_before,
            "eval_after":         m.eval_after,
            "centipawn_loss":     m.centipawn_loss,
            "move_classification": m.move_classification,
        }
        for m in q.scalars().all()
    ]
