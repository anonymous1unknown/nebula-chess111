from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/")
async def leaderboard(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(User)
        .where(User.is_active == True, User.is_banned == False, User.games_played >= 5)
        .order_by(desc(User.elo))
        .limit(min(limit, 100))
        .offset(offset)
    )
    users = q.scalars().all()
    return [
        {
            "rank": offset + i + 1,
            "username": u.username,
            "elo": u.elo,
            "games_played": u.games_played,
            "win_rate": round(u.games_won / u.games_played * 100, 1) if u.games_played > 0 else 0,
            "country": u.country,
            "avatar_url": u.avatar_url,
        }
        for i, u in enumerate(users)
    ]
