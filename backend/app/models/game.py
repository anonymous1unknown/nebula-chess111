import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import enum

from app.database import Base


class GameStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    finished = "finished"
    abandoned = "abandoned"


class GameResult(str, enum.Enum):
    white_wins = "white_wins"
    black_wins = "black_wins"
    draw = "draw"
    in_progress = "in_progress"
    aborted = "aborted"


class GameTermination(str, enum.Enum):
    checkmate = "checkmate"
    resignation = "resignation"
    timeout = "timeout"
    stalemate = "stalemate"
    insufficient_material = "insufficient_material"
    threefold_repetition = "threefold_repetition"
    fifty_move_rule = "fifty_move_rule"
    agreement = "agreement"
    abandoned = "abandoned"


class TimeControl(str, enum.Enum):
    bullet = "bullet"       # < 3 min
    blitz = "blitz"         # 3-10 min
    rapid = "rapid"         # 10-30 min
    classical = "classical" # > 30 min
    correspondence = "correspondence"


class GameMode(str, enum.Enum):
    ranked = "ranked"
    casual = "casual"
    ai = "ai"
    tournament = "tournament"
    daily = "daily"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invite_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)

    white_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    black_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    status: Mapped[GameStatus] = mapped_column(SAEnum(GameStatus), default=GameStatus.waiting)
    result: Mapped[GameResult] = mapped_column(SAEnum(GameResult), default=GameResult.in_progress)
    termination: Mapped[GameTermination | None] = mapped_column(SAEnum(GameTermination))
    mode: Mapped[GameMode] = mapped_column(SAEnum(GameMode), default=GameMode.casual)
    time_control: Mapped[TimeControl] = mapped_column(SAEnum(TimeControl), default=TimeControl.rapid)

    # Time control (seconds)
    initial_time: Mapped[int] = mapped_column(Integer, default=600)
    increment: Mapped[int] = mapped_column(Integer, default=5)
    white_time_remaining: Mapped[float] = mapped_column(Float, default=600.0)
    black_time_remaining: Mapped[float] = mapped_column(Float, default=600.0)

    # Chess state
    current_fen: Mapped[str] = mapped_column(
        Text,
        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    pgn: Mapped[str | None] = mapped_column(Text)
    move_count: Mapped[int] = mapped_column(Integer, default=0)

    # ELO
    white_elo_before: Mapped[int | None] = mapped_column(Integer)
    black_elo_before: Mapped[int | None] = mapped_column(Integer)
    white_elo_change: Mapped[int | None] = mapped_column(Integer)
    black_elo_change: Mapped[int | None] = mapped_column(Integer)

    # AI
    is_ai_game: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_difficulty: Mapped[int | None] = mapped_column(Integer)

    # Tournament
    tournament_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="SET NULL"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Disconnection tracking
    white_disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    black_disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    moves: Mapped[list["Move"]] = relationship(back_populates="game", order_by="Move.move_number", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    cheat_flags: Mapped[list["CheatFlag"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class GameInvitation(Base):
    __tablename__ = "game_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"))
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
