"""Drop attachment.last_transcription_session_id and enforce 1:1 sessions.

Revision ID: 0b4b60edd8f0
Revises: 8f1dd654eb5d
Create Date: 2024-05-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0b4b60edd8f0"
down_revision = "8f1dd654eb5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "attachments_last_transcription_session_id_fkey",
        "attachments",
        type_="foreignkey",
    )
    op.drop_column("attachments", "last_transcription_session_id")
    op.create_unique_constraint(
        "uq_transcription_sessions_attachment_id",
        "transcription_sessions",
        ["attachment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transcription_sessions_attachment_id",
        "transcription_sessions",
        type_="unique",
    )
    op.add_column(
        "attachments",
        sa.Column("last_transcription_session_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "attachments_last_transcription_session_id_fkey",
        "attachments",
        "transcription_sessions",
        ["last_transcription_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
