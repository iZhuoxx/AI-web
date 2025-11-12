"""Rename notes tables

Revision ID: ad129feab278
Revises: 0001_initial_schema
Create Date: 2025-10-29 23:38:49.455901

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ad129feab278"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop deprecated note messages table.
    op.drop_index("idx_note_messages_note", table_name="note_messages")
    op.drop_table("note_messages")

    # Rename high-level notes table to notebooks and drop the old content column.
    op.rename_table("notes", "notebooks")
    op.execute(sa.text("ALTER INDEX idx_notes_user_updated RENAME TO idx_notebooks_user_updated"))
    op.drop_column("notebooks", "content")

    # Rename note_sections to notes and align constraint/index names.
    op.rename_table("note_sections", "notes")
    op.alter_column("notes", "note_id", new_column_name="notebook_id", existing_type=sa.UUID(), existing_nullable=False)
    op.execute(sa.text("ALTER TABLE notes RENAME CONSTRAINT uq_note_sections_seq TO uq_notes_seq"))
    op.execute(sa.text("ALTER INDEX idx_note_sections_note RENAME TO idx_notes_notebook"))

    # Update attachments to reference notebooks.
    op.alter_column(
        "attachments",
        "note_id",
        new_column_name="notebook_id",
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            "ALTER TABLE attachments RENAME CONSTRAINT attachments_note_id_fkey TO attachments_notebook_id_fkey"
        )
    )
    op.execute(sa.text("ALTER INDEX idx_attachments_note RENAME TO idx_attachments_notebook"))

    # Update note_tags join table to reference notebooks.
    op.alter_column(
        "note_tags",
        "note_id",
        new_column_name="notebook_id",
        existing_type=sa.UUID(),
        existing_nullable=False,
    )
    op.execute(
        sa.text("ALTER TABLE note_tags RENAME CONSTRAINT note_tags_note_id_fkey TO note_tags_notebook_id_fkey")
    )

    # Update transcription sessions to reference notebooks.
    op.alter_column(
        "transcription_sessions",
        "note_id",
        new_column_name="notebook_id",
        existing_type=sa.UUID(),
        existing_nullable=True,
    )
    op.execute(
        sa.text(
            "ALTER TABLE transcription_sessions RENAME CONSTRAINT transcription_sessions_note_id_fkey "
            "TO transcription_sessions_notebook_id_fkey"
        )
    )
    op.execute(sa.text("ALTER INDEX idx_ts_note_created RENAME TO idx_ts_notebook_created"))


def downgrade() -> None:
    # Revert transcription session changes.
    op.execute(sa.text("ALTER INDEX idx_ts_notebook_created RENAME TO idx_ts_note_created"))
    op.execute(
        sa.text(
            "ALTER TABLE transcription_sessions RENAME CONSTRAINT transcription_sessions_notebook_id_fkey "
            "TO transcription_sessions_note_id_fkey"
        )
    )
    op.alter_column(
        "transcription_sessions",
        "notebook_id",
        new_column_name="note_id",
        existing_type=sa.UUID(),
        existing_nullable=True,
    )

    # Revert note_tags join table changes.
    op.execute(
        sa.text("ALTER TABLE note_tags RENAME CONSTRAINT note_tags_notebook_id_fkey TO note_tags_note_id_fkey")
    )
    op.alter_column(
        "note_tags",
        "notebook_id",
        new_column_name="note_id",
        existing_type=sa.UUID(),
        existing_nullable=False,
    )

    # Revert attachments changes.
    op.execute(sa.text("ALTER INDEX idx_attachments_notebook RENAME TO idx_attachments_note"))
    op.execute(
        sa.text(
            "ALTER TABLE attachments RENAME CONSTRAINT attachments_notebook_id_fkey TO attachments_note_id_fkey"
        )
    )
    op.alter_column(
        "attachments",
        "notebook_id",
        new_column_name="note_id",
        existing_type=sa.UUID(),
        existing_nullable=False,
    )

    # Rename notes table back to note_sections.
    op.execute(sa.text("ALTER INDEX idx_notes_notebook RENAME TO idx_note_sections_note"))
    op.execute(sa.text("ALTER TABLE notes RENAME CONSTRAINT uq_notes_seq TO uq_note_sections_seq"))
    op.alter_column("notes", "notebook_id", new_column_name="note_id", existing_type=sa.UUID(), existing_nullable=False)
    op.rename_table("notes", "note_sections")

    # Restore notebooks table back to notes and add removed column.
    op.add_column("notebooks", sa.Column("content", sa.Text(), nullable=True))
    op.execute(sa.text("ALTER INDEX idx_notebooks_user_updated RENAME TO idx_notes_user_updated"))
    op.rename_table("notebooks", "notes")

    # Recreate note_messages table and index.
    op.create_table(
        "note_messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "assistant", "system", "tool", name="message_role"),
            nullable=False,
        ),
        sa.Column("content", sa.TEXT(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], name="note_messages_note_id_fkey", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="note_messages_pkey"),
        sa.UniqueConstraint("note_id", "seq", name="uq_note_messages_seq"),
    )
    op.create_index("idx_note_messages_note", "note_messages", ["note_id", "created_at"], unique=False)
