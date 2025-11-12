"""Add summary to the attachment

Revision ID: 4922e15c3899
Revises: ad129feab278
Create Date: 2025-10-30 23:14:40.648747

"""
from __future__ import annotations



from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4922e15c3899'
down_revision = 'ad129feab278'
branch_labels = None
depends_on = None



def upgrade() -> None:
    op.add_column('attachments', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('attachments', 'summary')
