import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.core.chess_engine import get_legal_moves, validate_fen, STARTING_FEN
from app.core.security import generate_invite_code
from app.database import get_db
from app.models.game import Game, GameInvitation, GameMode, GameStatus, TimeControl
from app.models.move import Move
from app.models.user import User
from app.services.game_service import init_game_state, load_game_state

router = APIRouter()


class CreateGameRequest(BaseModel):
    mode: GameMode = GameMode.casual
    time_seconds: int = 600
    increment: int = 5
    color: Optional[str] = None  # "white" | "black" | None (random)
    vs_ai: bool = False
    ai_difficulty: int = 10
    fen: Optional[str] = None   # custom starting position


class CreateGameResponse(BaseModel):
    game_id: str
    invite_code: Optional[str]
    color: str


class JoinGameRequest(BaseModel):
    invite_code: str


def _time_control(seconds: int) -> TimeControl:
    if seconds < 180:
        return TimeControl.bullet
    if seconds < 600:
        return TimeControl.blitz
    if seconds < 1800:
        return TimeControl.rapid
    return TimeControl.classical


@router.post("/create", response_model=CreateGameResponse)
async def create_game(
    body: CreateGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.fen and not validate_fen(body.fen):
        raise HTTPException(400, "Invalid FEN")

    # Determine color
    import random
    color = body.color or random.choice(["white", "black"])

    invite_code = generate_invite_code()
    game = Game(
        invite_code=invite_code,
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

    # vs AI: start immediately
    if body.vs_ai:
        ai_placeholder_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        if color == "white":
            game.black_id = ai_placeholder_id
        else:
            game.white_id = ai_placeholder_id
        game.status = GameStatus.active
        game.started_at = datetime.now(timezone.utc)

    db.add(game)
    await db.flush()

    # Init state in Redis
    white_name = current_user.username if color == "white" else "Stockfish"
    black_name = "Stockfish" if color == "white" else current_user.username
    if body.vs_ai:
        await init_game_state(game, white_name, black_name)

    return CreateGameResponse(
        game_id=str(game.id),
        invite_code=invite_code if not body.vs_ai else None,
        color=color,
    )


@router.post("/join/{invite_code}")
async def join_game(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Game).where(Game.invite_code == invite_code.upper()))
    game = q.scalar_one_or_none()
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.waiting:
        raise HTTPException(409, "Game already started or finished")

    # Assign color
    if game.white_id is None:
        game.white_id = current_user.id
        color = "white"
        white_name = current_user.username
        black_q = await db.execute(select(User).where(User.id == game.black_id))
        black_user = black_q.scalar_one_or_none()
        black_name = black_user.username if black_user else "Unknown"
    elif game.black_id is None:
        game.black_id = current_user.id
        color = "black"
        black_name = current_user.username
        white_q = await db.execute(select(User).where(User.id == game.white_id))
        white_user = white_q.scalar_one_or_none()
        white_name = white_user.username if white_user else "Unknown"
    else:
        raise HTTPException(409, "Game is full")

    game.status = GameStatus.active
    game.started_at = datetime.now(timezone.utc)
    await db.flush()

    await init_game_state(game, white_name, black_name)

    return {"game_id": str(game.id), "color": color}


@router.get("/{game_id}/state")
async def get_game_state(
    game_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    state = await load_game_state(game_id)
    if not state:
        raise HTTPException(404, "Game not found or expired")
    return state


@router.get("/{game_id}/legal-moves")
async def legal_moves(game_id: str, _: Optional[User] = Depends(get_optional_user)):
    state = await load_game_state(game_id)
    if not state:
        raise HTTPException(404, "Game not found")
    return {"moves": get_legal_moves(state["fen"])}


@router.get("/{game_id}/moves")
async def get_moves(game_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(Move)
        .where(Move.game_id == uuid.UUID(game_id))
        .order_by(Move.move_number)
    )
    moves = q.scalars().all()
    return [
        {
            "number": m.move_number,
            "san": m.san,
            "uci": m.uci,
            "fen_after": m.fen_after,
            "time_spent_ms": m.time_spent_ms,
            "clock_remaining_ms": m.clock_remaining_ms,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in moves
    ]


@router.get("/history/me")
async def my_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Game)
        .where(or_(Game.white_id == current_user.id, Game.black_id == current_user.id))
        .where(Game.status == GameStatus.finished)
        .order_by(desc(Game.finished_at))
        .limit(limit)
        .offset(offset)
    )
    games = q.scalars().all()
    return [_game_summary(g, current_user.id) for g in games]


def _game_summary(game: Game, viewer_id: uuid.UUID) -> dict:
    is_white = game.white_id == viewer_id
    return {
        "id": str(game.id),
        "result": game.result.value if game.result else None,
        "termination": game.termination.value if game.termination else None,
        "mode": game.mode.value,
        "time_control": game.time_control.value,
        "initial_time": game.initial_time,
        "increment": game.increment,
        "move_count": game.move_count,
        "played_as": "white" if is_white else "black",
        "elo_change": game.white_elo_change if is_white else game.black_elo_change,
        "finished_at": game.finished_at.isoformat() if game.finished_at else None,
    }
