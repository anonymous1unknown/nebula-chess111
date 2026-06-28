import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Float, Integer, Text, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class CheatFlagStatus(str, enum.Enum):
    pending = "pending"
    reviewing = "reviewing"
    confirmed = "confirmed"
    dismissed = "dismissed"
    appealed = "appealed"


class CheatFlag(Base):
    __tablename__ = "cheat_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    # Scores (0.0–1.0)
    engine_correlation: Mapped[float | None] = mapped_column(Float)
    accuracy_score: Mapped[float | None] = mapped_column(Float)
    time_anomaly_score: Mapped[float | None] = mapped_column(Float)
    overall_suspicion_score: Mapped[float | None] = mapped_column(Float)

    # Details
    engine_match_count: Mapped[int | None] = mapped_column(Integer)
    total_moves: Mapped[int | None] = mapped_column(Integer)
    avg_centipawn_loss: Mapped[float | None] = mapped_column(Float)
    suspicious_moves: Mapped[str | None] = mapped_column(Text)  # JSON list

    status: Mapped[CheatFlagStatus] = mapped_column(SAEnum(CheatFlagStatus), default=CheatFlagStatus.pending)
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    auto_flagged: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    game: Mapped["Game"] = relationship(back_populates="cheat_flags")
