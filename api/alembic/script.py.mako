"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations

<%!
from textwrap import indent as _indent


def _indent_text(value, prefix="    "):
    try:
        text = value or ""
    except Exception:
        text = ""
    if not text:
        return ""
    return _indent(text, prefix)
%>

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

% if imports:
${imports}
% endif


def upgrade() -> None:
% if upgrades:
${_indent_text(upgrades)}
% else:
    pass
% endif


def downgrade() -> None:
% if downgrades:
${_indent_text(downgrades)}
% else:
    pass
% endif
