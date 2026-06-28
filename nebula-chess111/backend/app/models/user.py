import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    player    = "player"
    moderator = "moderator"
    admin     = "admin"


class FriendshipStatus(str, enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    blocked  = "blocked"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    email:    Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # FIX: migration created this column as String(16) — native_enum=False matches that
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, name="userrole"),
        default=UserRole.player,
        nullable=False,
    )

    # Profile
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    bio:        Mapped[str | None] = mapped_column(Text)
    country:    Mapped[str | None] = mapped_column(String(3))

    # Ratings
    elo:        Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    elo_rapid:  Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    elo_blitz:  Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    elo_bullet: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    peak_elo:   Mapped[int] = mapped_column(Integer, default=1200, nullable=False)

    # Stats
    games_played:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    games_won:     Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    games_lost:    Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    games_drawn:   Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    puzzles_solved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    puzzle_streak:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Account state
    is_active:   Mapped[bool]        = mapped_column(Boolean, default=True,  nullable=False)
    is_verified: Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)
    is_banned:   Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)
    ban_reason:  Mapped[str | None]  = mapped_column(Text)

    # Preferences
    theme:             Mapped[str]  = mapped_column(String(32), default="nebula",  nullable=False)
    board_theme:       Mapped[str]  = mapped_column(String(32), default="cosmic",  nullable=False)
    piece_set:         Mapped[str]  = mapped_column(String(32), default="neo",     nullable=False)
    show_coordinates:  Mapped[bool] = mapped_column(Boolean, default=True)
    auto_promote_queen: Mapped[bool] = mapped_column(Boolean, default=True)
    sound_enabled:     Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sent_friendships: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.requester_id", back_populates="requester"
    )
    received_friendships: Mapped[list["Friendship"]] = relationship(
        foreign_keys="Friendship.addressee_id", back_populates="addressee"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked:    Mapped[bool]     = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Friendship(Base):
    __tablename__ = "friendships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    addressee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # FIX: migration uses String(16) — native_enum=False prevents native PG type mismatch
    status: Mapped[FriendshipStatus] = mapped_column(
        SAEnum(FriendshipStatus, native_enum=False, name="friendshipstatus"),
        default=FriendshipStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    requester: Mapped["User"] = relationship(
        foreign_keys=[requester_id], back_populates="sent_friendships"
    )
    addressee: Mapped["User"] = relationship(
        foreign_keys=[addressee_id], back_populates="received_friendships"
    )
