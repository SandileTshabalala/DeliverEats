"""menu sections, dish options (spice level, extras...) and the picks on each order line

Revision ID: b3e5c7d9f1a2
Revises: a7d2e4f6b8c1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b3e5c7d9f1a2'
down_revision: Union[str, Sequence[str], None] = 'a7d2e4f6b8c1'
branch_labels = None
depends_on = None

NEW = (
    ('menu_items', 'section', lambda: sa.String(40)),
    ('menu_items', 'options', sa.JSON),
    ('order_items', 'options', sa.JSON),
    ('restaurants', 'menu_sections', sa.JSON),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, column, kind in NEW:
        if column not in {c['name'] for c in inspector.get_columns(table)}:
            op.add_column(table, sa.Column(column, kind(), nullable=True))


def downgrade() -> None:
    for table, column, _ in reversed(NEW):
        op.drop_column(table, column)
