import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Move(Base):
    __tablename__ = "moves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    san: Mapped[str] = mapped_column(String(16), nullable=False)   # Standard Algebraic Notation  e.g. Nf3
    uci: Mapped[str] = mapped_column(String(10), nullable=False)   # UCI format e.g. g1f3
    fen_before: Mapped[str] = mapped_column(String(100), nullable=False)
    fen_after: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timing
    time_spent_ms: Mapped[int | None] = mapped_column(Integer)
    clock_remaining_ms: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Analysis (filled by Stockfish post-game)
    eval_before: Mapped[float | None] = mapped_column(Float)   # centipawns
    eval_after: Mapped[float | None] = mapped_column(Float)
    best_move: Mapped[str | None] = mapped_column(String(10))
    is_best_move: Mapped[bool | None] = mapped_column(Boolean)
    centipawn_loss: Mapped[float | None] = mapped_column(Float)
    move_classification: Mapped[str | None] = mapped_column(String(16))  # brilliant/good/inaccuracy/mistake/blunder

    # Anti-cheat
    engine_match: Mapped[bool | None] = mapped_column(Boolean)

    # Relationships
    game: Mapped["Game"] = relationship(back_populates="moves")
