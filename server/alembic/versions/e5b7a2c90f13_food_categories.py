"""food categories managed by the platform owner

Revision ID: e5b7a2c90f13
Revises: c41f0a7d9e21
Create Date: 2026-11-14

The starting list is created by the app on startup
(app.services.categories.ensure_defaults), which also links restaurants that
had already picked a category.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5b7a2c90f13'
down_revision: Union[str, Sequence[str], None] = 'c41f0a7d9e21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if 'categories' not in tables:
        op.create_table(
            'categories',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(40), nullable=False, unique=True),
            sa.Column('image_url', sa.String(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    if 'restaurant_categories' not in tables:
        op.create_table(
            'restaurant_categories',
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('category_id', sa.String(), sa.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        )
        op.create_index('ix_restaurant_categories_category_id', 'restaurant_categories', ['category_id'])


def downgrade() -> None:
    op.drop_index('ix_restaurant_categories_category_id', table_name='restaurant_categories')
    op.drop_table('restaurant_categories')
    op.drop_table('categories')
