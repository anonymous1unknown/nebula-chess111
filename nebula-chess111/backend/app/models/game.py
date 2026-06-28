"""
game.py — Option 2: VARCHAR-backed Python Enums (native_enum=False)
Use this together with 001_initial_option2_varchar.py (or the existing migration
which already creates String(16) columns — no migration changes needed).

native_enum=False means:
  • PostgreSQL stores the value as a plain VARCHAR
  • SQLAlchemy validates values against the Python Enum on read/write
  • No custom PG type is created, referenced, or needed
  • No cast() is needed anywhere in queries
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class GameStatus(str, enum.Enum):
    waiting   = "waiting"
    active    = "active"
    finished  = "finished"
    abandoned = "abandoned"


class GameResult(str, enum.Enum):
    white_wins  = "white_wins"
    black_wins  = "black_wins"
    draw        = "draw"
    in_progress = "in_progress"
    aborted     = "aborted"


class GameTermination(str, enum.Enum):
    checkmate             = "checkmate"
    resignation           = "resignation"
    timeout               = "timeout"
    stalemate             = "stalemate"
    insufficient_material = "insufficient_material"
    threefold_repetition  = "threefold_repetition"
    fifty_move_rule       = "fifty_move_rule"
    agreement             = "agreement"
    abandoned             = "abandoned"


class TimeControl(str, enum.Enum):
    bullet         = "bullet"
    blitz          = "blitz"
    rapid          = "rapid"
    classical      = "classical"
    correspondence = "correspondence"


class GameMode(str, enum.Enum):
    ranked     = "ranked"
    casual     = "casual"
    ai         = "ai"
    tournament = "tournament"
    daily      = "daily"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invite_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)

    white_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    black_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # native_enum=False = stored as VARCHAR in PostgreSQL, validated in Python only.
    # Matches the existing migration which creates these columns as String(16/32).
    # No PG type "gamestatus" is created — no cast() needed in any query.
    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus, native_enum=False, name="gamestatus"),
        default=GameStatus.waiting, nullable=False,
    )
    result: Mapped[GameResult] = mapped_column(
        SAEnum(GameResult, native_enum=False, name="gameresult"),
        default=GameResult.in_progress, nullable=False,
    )
    termination: Mapped[GameTermination | None] = mapped_column(
        SAEnum(GameTermination, native_enum=False, name="gametermination"),
    )
    mode: Mapped[GameMode] = mapped_column(
        SAEnum(GameMode, native_enum=False, name="gamemode"),
        default=GameMode.casual, nullable=False,
    )
    time_control: Mapped[TimeControl] = mapped_column(
        SAEnum(TimeControl, native_enum=False, name="timecontrol"),
        default=TimeControl.rapid, nullable=False,
    )

    initial_time: Mapped[int]           = mapped_column(Integer, default=600)
    increment: Mapped[int]              = mapped_column(Integer, default=5)
    white_time_remaining: Mapped[float] = mapped_column(Float,   default=600.0)
    black_time_remaining: Mapped[float] = mapped_column(Float,   default=600.0)

    current_fen: Mapped[str] = mapped_column(
        Text,
        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    )
    pgn: Mapped[str | None]  = mapped_column(Text)
    move_count: Mapped[int]  = mapped_column(Integer, default=0)

    white_elo_before: Mapped[int | None] = mapped_column(Integer)
    black_elo_before: Mapped[int | None] = mapped_column(Integer)
    white_elo_change: Mapped[int | None] = mapped_column(Integer)
    black_elo_change: Mapped[int | None] = mapped_column(Integer)

    is_ai_game: Mapped[bool]         = mapped_column(Boolean, default=False)
    ai_difficulty: Mapped[int | None] = mapped_column(Integer)

    tournament_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    white_disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    black_disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    moves: Mapped[list["Move"]] = relationship(
        back_populates="game",
        order_by="Move.move_number",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    cheat_flags: Mapped[list["CheatFlag"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class GameInvitation(Base):
    __tablename__ = "game_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE")
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    invite_code: Mapped[str]     = mapped_column(String(16), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted: Mapped[bool]       = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
