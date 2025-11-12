"""Initial database schema for AI Web notes platform."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


membership_status_enum = postgresql.ENUM(
    "active",
    "canceled",
    "expired",
    "past_due",
    name="membership_status",
    create_type=False,
)

message_role_enum = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    "tool",
    name="message_role",
    create_type=False,
)

attachment_kind_enum = postgresql.ENUM(
    "pdf",
    "image",
    "audio",
    "video",
    "file",
    "other",
    name="attachment_kind",
    create_type=False,
)

transcription_source_enum = postgresql.ENUM(
    "realtime",
    "batch",
    name="transcription_source",
    create_type=False,
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    conn = op.get_bind()
    membership_status_enum.create(conn, checkfirst=True)
    message_role_enum.create(conn, checkfirst=True)
    attachment_kind_enum.create(conn, checkfirst=True)
    transcription_source_enum.create(conn, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("member_plan", sa.String(length=50), nullable=True),
        sa.Column("member_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("status", membership_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_memberships_user", "memberships", ["user_id"], unique=False)

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_notes_user_updated", "notes", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )

    op.create_table(
        "note_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.UniqueConstraint("note_id", "seq", name="uq_note_sections_seq"),
    )
    op.create_index("idx_note_sections_note", "note_sections", ["note_id"], unique=False)

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", attachment_kind_enum, nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("mime", sa.String(length=255), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=128), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_attachments_note", "attachments", ["note_id"], unique=False)
    op.create_index("idx_attachments_user", "attachments", ["user_id"], unique=False)
    op.create_index("idx_attachments_sha", "attachments", ["sha256"], unique=False)

    op.create_table(
        "transcription_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", transcription_source_enum, nullable=False),
        sa.Column("session_uid", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("engine", sa.String(length=255), nullable=True),
        sa.Column("lang", sa.String(length=32), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_ts_user_created", "transcription_sessions", ["user_id", "created_at"], unique=False)
    op.create_index("idx_ts_note_created", "transcription_sessions", ["note_id", "created_at"], unique=False)
    op.create_index("idx_ts_attachment_created", "transcription_sessions", ["attachment_id", "created_at"], unique=False)

    op.create_table(
        "note_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("note_id", "seq", name="uq_note_messages_seq"),
    )
    op.create_index("idx_note_messages_note", "note_messages", ["note_id", "created_at"], unique=False)

    op.create_table(
        "transcription_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transcription_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=True),
        sa.Column("content_index", sa.Integer(), nullable=True),
        sa.Column("ts_seconds", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.String(length=32), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("session_id", "seq", name="uq_ts_segments_seq"),
    )
    op.create_index("idx_ts_segments_session", "transcription_segments", ["session_id", "seq"], unique=False)

    op.create_table(
        "note_tags",
        sa.Column("note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("note_tags")
    op.drop_index("idx_ts_segments_session", table_name="transcription_segments")
    op.drop_table("transcription_segments")
    op.drop_index("idx_note_messages_note", table_name="note_messages")
    op.drop_table("note_messages")
    op.drop_index("idx_ts_attachment_created", table_name="transcription_sessions")
    op.drop_index("idx_ts_note_created", table_name="transcription_sessions")
    op.drop_index("idx_ts_user_created", table_name="transcription_sessions")
    op.drop_table("transcription_sessions")
    op.drop_index("idx_attachments_sha", table_name="attachments")
    op.drop_index("idx_attachments_user", table_name="attachments")
    op.drop_index("idx_attachments_note", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("idx_note_sections_note", table_name="note_sections")
    op.drop_table("note_sections")
    op.drop_table("tags")
    op.drop_index("idx_notes_user_updated", table_name="notes")
    op.drop_table("notes")
    op.drop_index("idx_memberships_user", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    conn = op.get_bind()
    transcription_source_enum.drop(conn, checkfirst=True)
    attachment_kind_enum.drop(conn, checkfirst=True)
    message_role_enum.drop(conn, checkfirst=True)
    membership_status_enum.drop(conn, checkfirst=True)
