"""fix attachment transcription status enum casing

Revision ID: 7b2719730c16
Revises: 0ef8f788d9c4
Create Date: 2025-11-20 00:14:25.816035

"""
from __future__ import annotations



from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7b2719730c16'
down_revision = '0ef8f788d9c4'
branch_labels = None
depends_on = None


ENUM_NAME = "attachment_transcription_status"
LOWERCASE_VALUES = ("none", "pending", "completed", "failed")
UPPERCASE_VALUES = tuple(value.upper() for value in LOWERCASE_VALUES)


def _rename_enum_value(old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = '{ENUM_NAME}' AND e.enumlabel = '{old}'
            ) THEN
                EXECUTE 'ALTER TYPE {ENUM_NAME} RENAME VALUE ''{old}'' TO ''{new}''';
            END IF;
        END;
        $$;
        """
    )


def upgrade() -> None:
    for old, new in zip(UPPERCASE_VALUES, LOWERCASE_VALUES):
        _rename_enum_value(old, new)

    op.alter_column(
        "attachments",
        "transcription_status",
        server_default=sa.text("'none'::attachment_transcription_status"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "attachments",
        "transcription_status",
        server_default=sa.text("'NONE'::attachment_transcription_status"),
        existing_nullable=False,
    )

    for old, new in zip(reversed(LOWERCASE_VALUES), reversed(UPPERCASE_VALUES)):
        _rename_enum_value(old, new)
