import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter()


class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    country: Optional[str] = None
    theme: Optional[str] = None
    board_theme: Optional[str] = None
    piece_set: Optional[str] = None
    show_coordinates: Optional[bool] = None
    auto_promote_queen: Optional[bool] = None
    sound_enabled: Optional[bool] = None


def _user_public(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "elo": user.elo,
        "elo_rapid": user.elo_rapid,
        "elo_blitz": user.elo_blitz,
        "elo_bullet": user.elo_bullet,
        "peak_elo": user.peak_elo,
        "games_played": user.games_played,
        "games_won": user.games_won,
        "games_lost": user.games_lost,
        "games_drawn": user.games_drawn,
        "puzzles_solved": user.puzzles_solved,
        "puzzle_streak": user.puzzle_streak,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "country": user.country,
        "theme": user.theme,
        "board_theme": user.board_theme,
        "piece_set": user.piece_set,
        "show_coordinates": user.show_coordinates,
        "auto_promote_queen": user.auto_promote_queen,
        "sound_enabled": user.sound_enabled,
        "created_at": user.created_at.isoformat(),
        "last_seen": user.last_seen.isoformat(),
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_public(current_user)


@router.patch("/me")
async def update_me(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    return _user_public(current_user)


@router.get("/{username}")
async def get_user(username: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.username == username))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return _user_public(user)
