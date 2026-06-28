"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), default="player"),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("bio", sa.Text),
        sa.Column("country", sa.String(3)),
        sa.Column("elo", sa.Integer, default=1200),
        sa.Column("elo_rapid", sa.Integer, default=1200),
        sa.Column("elo_blitz", sa.Integer, default=1200),
        sa.Column("elo_bullet", sa.Integer, default=1200),
        sa.Column("peak_elo", sa.Integer, default=1200),
        sa.Column("games_played", sa.Integer, default=0),
        sa.Column("games_won", sa.Integer, default=0),
        sa.Column("games_lost", sa.Integer, default=0),
        sa.Column("games_drawn", sa.Integer, default=0),
        sa.Column("puzzles_solved", sa.Integer, default=0),
        sa.Column("puzzle_streak", sa.Integer, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("is_banned", sa.Boolean, default=False),
        sa.Column("ban_reason", sa.Text),
        sa.Column("theme", sa.String(32), default="nebula"),
        sa.Column("board_theme", sa.String(32), default="cosmic"),
        sa.Column("piece_set", sa.String(32), default="neo"),
        sa.Column("show_coordinates", sa.Boolean, default=True),
        sa.Column("auto_promote_queen", sa.Boolean, default=True),
        sa.Column("sound_enabled", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_elo", "users", ["elo"])

    # Refresh tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_refresh_tokens_hash", "refresh_tokens", ["token_hash"])

    # Friendships
    op.create_table(
        "friendships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("addressee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("status", sa.String(16), default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # Tournaments (needed before games)
    op.create_table(
        "tournaments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("format", sa.String(32), default="swiss"),
        sa.Column("status", sa.String(16), default="upcoming"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("max_participants", sa.Integer, default=16),
        sa.Column("current_round", sa.Integer, default=0),
        sa.Column("total_rounds", sa.Integer, default=5),
        sa.Column("initial_time", sa.Integer, default=600),
        sa.Column("increment", sa.Integer, default=5),
        sa.Column("min_elo", sa.Integer),
        sa.Column("max_elo", sa.Integer),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # Games
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invite_code", sa.String(16), unique=True),
        sa.Column("white_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("black_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(16), default="waiting"),
        sa.Column("result", sa.String(16), default="in_progress"),
        sa.Column("termination", sa.String(32)),
        sa.Column("mode", sa.String(16), default="casual"),
        sa.Column("time_control", sa.String(16), default="rapid"),
        sa.Column("initial_time", sa.Integer, default=600),
        sa.Column("increment", sa.Integer, default=5),
        sa.Column("white_time_remaining", sa.Float, default=600.0),
        sa.Column("black_time_remaining", sa.Float, default=600.0),
        sa.Column("current_fen", sa.Text),
        sa.Column("pgn", sa.Text),
        sa.Column("move_count", sa.Integer, default=0),
        sa.Column("white_elo_before", sa.Integer),
        sa.Column("black_elo_before", sa.Integer),
        sa.Column("white_elo_change", sa.Integer),
        sa.Column("black_elo_change", sa.Integer),
        sa.Column("is_ai_game", sa.Boolean, default=False),
        sa.Column("ai_difficulty", sa.Integer),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tournaments.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("white_disconnected_at", sa.DateTime(timezone=True)),
        sa.Column("black_disconnected_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_games_invite_code", "games", ["invite_code"])
    op.create_index("ix_games_white_id", "games", ["white_id"])
    op.create_index("ix_games_black_id", "games", ["black_id"])
    op.create_index("ix_games_status", "games", ["status"])

    # Moves
    op.create_table(
        "moves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE")),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("san", sa.String(16), nullable=False),
        sa.Column("uci", sa.String(10), nullable=False),
        sa.Column("fen_before", sa.String(100)),
        sa.Column("fen_after", sa.String(100)),
        sa.Column("time_spent_ms", sa.Integer),
        sa.Column("clock_remaining_ms", sa.Integer),
        sa.Column("timestamp", sa.DateTime(timezone=True)),
        sa.Column("eval_before", sa.Float),
        sa.Column("eval_after", sa.Float),
        sa.Column("best_move", sa.String(10)),
        sa.Column("is_best_move", sa.Boolean),
        sa.Column("centipawn_loss", sa.Float),
        sa.Column("move_classification", sa.String(16)),
        sa.Column("engine_match", sa.Boolean),
    )
    op.create_index("ix_moves_game_id", "moves", ["game_id"])

    # Chat messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_system", sa.Boolean, default=False),
        sa.Column("timestamp", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_chat_game_id", "chat_messages", ["game_id"])

    # Cheat flags
    op.create_table(
        "cheat_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("engine_correlation", sa.Float),
        sa.Column("accuracy_score", sa.Float),
        sa.Column("time_anomaly_score", sa.Float),
        sa.Column("overall_suspicion_score", sa.Float),
        sa.Column("engine_match_count", sa.Integer),
        sa.Column("total_moves", sa.Integer),
        sa.Column("avg_centipawn_loss", sa.Float),
        sa.Column("suspicious_moves", sa.Text),
        sa.Column("status", sa.String(16), default="pending"),
        sa.Column("reviewer_notes", sa.Text),
        sa.Column("auto_flagged", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )

    # Achievements
    op.create_table(
        "achievements",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon", sa.String(64)),
        sa.Column("rarity", sa.String(16), default="common"),
    )

    op.create_table(
        "user_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("achievement_id", sa.String(64), sa.ForeignKey("achievements.id")),
        sa.Column("earned_at", sa.DateTime(timezone=True)),
    )

    # Tournament participants
    op.create_table(
        "tournament_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tournaments.id", ondelete="CASCADE")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("score", sa.Float, default=0.0),
        sa.Column("rank", sa.Integer),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
    )

    # Game invitations
    op.create_table(
        "game_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE")),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("invite_code", sa.String(16), unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("accepted", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    for table in [
        "game_invitations", "tournament_participants", "user_achievements",
        "achievements", "cheat_flags", "chat_messages", "moves", "games",
        "tournaments", "friendships", "refresh_tokens", "users",
    ]:
        op.drop_table(table)
