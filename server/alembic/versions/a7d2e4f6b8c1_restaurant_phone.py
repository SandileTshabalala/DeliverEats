"""restaurant phone: customers call it to change or cancel an order

Revision ID: a7d2e4f6b8c1
Revises: f8c3d1e7a2b4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7d2e4f6b8c1'
down_revision: Union[str, Sequence[str], None] = 'f8c3d1e7a2b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('restaurants')}
    if 'phone' not in columns:
        op.add_column('restaurants', sa.Column('phone', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurants', 'phone')
