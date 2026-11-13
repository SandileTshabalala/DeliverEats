"""restaurant tenancy, per-restaurant payments and subscriptions

Revision ID: c41f0a7d9e21
Revises: 1864f03ae64a
Create Date: 2026-11-13

- drivers.restaurant_id: drivers now belong to a restaurant
- restaurant_payment_settings: how each restaurant gets paid
- restaurant_delivery_settings: what each restaurant charges for delivery
- subscription_plans / restaurant_subscriptions / subscription_payments

Every step checks what already exists, because the app also creates missing
tables at startup; running this on such a database must not fail.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c41f0a7d9e21'
down_revision: Union[str, Sequence[str], None] = '1864f03ae64a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if 'restaurant_id' not in {c['name'] for c in inspector.get_columns('drivers')}:
        op.add_column('drivers', sa.Column('restaurant_id', sa.String(), nullable=True))
        op.create_foreign_key(
            'fk_drivers_restaurant_id_restaurants', 'drivers', 'restaurants',
            ['restaurant_id'], ['id'], ondelete='SET NULL'
        )
        op.create_index('ix_drivers_restaurant_id', 'drivers', ['restaurant_id'])

    if 'restaurant_payment_settings' not in tables:
        op.create_table(
            'restaurant_payment_settings',
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('accepts_cash', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('accepts_card_machine', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('payfast_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('payfast_merchant_id', sa.String(), nullable=True),
            sa.Column('payfast_merchant_key_enc', sa.String(), nullable=True),
            sa.Column('payfast_passphrase_enc', sa.String(), nullable=True),
            sa.Column('payfast_sandbox', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if 'restaurant_delivery_settings' not in tables:
        op.create_table(
            'restaurant_delivery_settings',
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('base_fee', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('per_km_fee', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('free_delivery_over', sa.Numeric(10, 2), nullable=True),
            sa.Column('max_distance_km', sa.Float(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if 'subscription_plans' not in tables:
        op.create_table(
            'subscription_plans',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False, unique=True),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('price', sa.Numeric(10, 2), nullable=False),
            sa.Column('interval_months', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('trial_days', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_orders_per_month', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()),
            sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    if 'restaurant_subscriptions' not in tables:
        op.create_table(
            'restaurant_subscriptions',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('plan_id', sa.String(), sa.ForeignKey('subscription_plans.id'), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='trialing'),
            sa.Column('current_period_end', sa.DateTime(), nullable=False),
            sa.Column('payfast_token', sa.String(), nullable=True),
            sa.Column('note', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_restaurant_subscriptions_restaurant_id', 'restaurant_subscriptions', ['restaurant_id'])

    if 'subscription_payments' not in tables:
        op.create_table(
            'subscription_payments',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('plan_id', sa.String(), sa.ForeignKey('subscription_plans.id'), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('method', sa.String(), nullable=False, server_default='payfast'),
            sa.Column('parent_id', sa.String(), nullable=True),
            sa.Column('reference', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_subscription_payments_restaurant_id', 'subscription_payments', ['restaurant_id'])
        op.create_index('ix_subscription_payments_parent_id', 'subscription_payments', ['parent_id'])
        op.create_index('ix_subscription_payments_reference', 'subscription_payments', ['reference'])


def downgrade() -> None:
    op.drop_table('subscription_payments')
    op.drop_table('restaurant_subscriptions')
    op.drop_table('subscription_plans')
    op.drop_table('restaurant_delivery_settings')
    op.drop_table('restaurant_payment_settings')
    op.drop_index('ix_drivers_restaurant_id', table_name='drivers')
    op.drop_constraint('fk_drivers_restaurant_id_restaurants', 'drivers', type_='foreignkey')
    op.drop_column('drivers', 'restaurant_id')
