import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class TournamentStatus(str, enum.Enum):
    upcoming  = "upcoming"
    active    = "active"
    finished  = "finished"
    cancelled = "cancelled"


class TournamentFormat(str, enum.Enum):
    swiss                = "swiss"
    round_robin          = "round_robin"
    single_elimination   = "single_elimination"
    arena                = "arena"


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # FIX: migration stores both as String(16/32) — native_enum=False avoids type mismatch
    format: Mapped[TournamentFormat] = mapped_column(
        SAEnum(TournamentFormat, native_enum=False, name="tournamentformat"),
        default=TournamentFormat.swiss,
    )
    status: Mapped[TournamentStatus] = mapped_column(
        SAEnum(TournamentStatus, native_enum=False, name="tournamentstatus"),
        default=TournamentStatus.upcoming,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    max_participants: Mapped[int] = mapped_column(Integer, default=16)
    current_round:   Mapped[int] = mapped_column(Integer, default=0)
    total_rounds:    Mapped[int] = mapped_column(Integer, default=5)
    initial_time:    Mapped[int] = mapped_column(Integer, default=600)
    increment:       Mapped[int] = mapped_column(Integer, default=5)

    min_elo: Mapped[int | None] = mapped_column(Integer)
    max_elo: Mapped[int | None] = mapped_column(Integer)

    starts_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:  Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    score:     Mapped[float]       = mapped_column(Float, default=0.0)
    rank:      Mapped[int | None]  = mapped_column(Integer)
    joined_at: Mapped[datetime]    = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tournament: Mapped["Tournament"] = relationship(back_populates="participants")
