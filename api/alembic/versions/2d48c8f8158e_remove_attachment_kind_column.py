"""Remove attachment kind column and enum."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "2d48c8f8158e"
down_revision = "1b42a0d9a294"
branch_labels = None
depends_on = None


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


def upgrade() -> None:
    op.drop_column("attachments", "kind")
    attachment_kind_enum.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    attachment_kind_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "attachments",
        sa.Column("kind", attachment_kind_enum, nullable=False, server_default="file"),
    )
    op.alter_column("attachments", "kind", server_default=None)
