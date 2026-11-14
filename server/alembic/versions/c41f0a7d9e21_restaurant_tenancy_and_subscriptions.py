"""restaurant tenancy, per-restaurant payments and subscriptions

Revision ID: c41f0a7d9e21
Revises: 1864f03ae64a
Create Date: 2026-11-13

- order_status_enum / role_enum: add values the code already used
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

    # Enum values the code uses but the database types never received.
    # ADD VALUE cannot run inside a transaction block on older Postgres versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE order_status_enum ADD VALUE IF NOT EXISTS 'WAITING_FOR_DRIVER'")
        op.execute("ALTER TYPE role_enum ADD VALUE IF NOT EXISTS 'ADMIN'")

    if 'restaurant_id' not in {c['name'] for c in inspector.get_columns('drivers')}:
        op.add_column('drivers', sa.Column('restaurant_id', sa.String(), nullable=True))
        op.create_foreign_key(
            'fk_drivers_restaurant_id_restaurants', 'drivers', 'restaurants',
            ['restaurant_id'], ['id'], ondelete='SET NULL'
        )
        op.create_index('ix_drivers_restaurant_id', 'drivers', ['restaurant_id'])

    restaurant_columns = {c['name'] for c in inspector.get_columns('restaurants')}
    if 'category' not in restaurant_columns:
        op.add_column('restaurants', sa.Column('category', sa.String(), nullable=True))
    if 'accepting_orders' not in restaurant_columns:
        op.add_column('restaurants', sa.Column('accepting_orders', sa.Boolean(), nullable=False, server_default=sa.true()))
    if 'opens_at' not in restaurant_columns:
        op.add_column('restaurants', sa.Column('opens_at', sa.String(5), nullable=True))
    if 'closes_at' not in restaurant_columns:
        op.add_column('restaurants', sa.Column('closes_at', sa.String(5), nullable=True))
    if 'vat_number' not in restaurant_columns:
        op.add_column('restaurants', sa.Column('vat_number', sa.String(20), nullable=True))

    if 'platform_settings' not in tables:
        op.create_table(
            'platform_settings',
            sa.Column('key', sa.String(64), primary_key=True),
            sa.Column('value', sa.String(500), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if 'order_reviews' not in tables:
        op.create_table(
            'order_reviews',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('restaurant_id', sa.String(), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('customer_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=False),
            sa.Column('comment', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_order_reviews_restaurant_id', 'order_reviews', ['restaurant_id'])

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
    payment_columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('restaurant_payment_settings')}
    for name, column_type, default in (
        ('ozow_enabled', sa.Boolean(), sa.false()), ('ozow_site_code', sa.String(), None),
        ('ozow_client_id', sa.String(), None), ('ozow_client_secret_enc', sa.String(), None),
        ('ozow_sandbox', sa.Boolean(), sa.false()), ('peach_enabled', sa.Boolean(), sa.false()),
        ('peach_entity_id', sa.String(), None), ('peach_secret_token_enc', sa.String(), None),
        ('peach_sandbox', sa.Boolean(), sa.false()),
    ):
        if name not in payment_columns:
            op.add_column('restaurant_payment_settings', sa.Column(
                name, column_type, nullable=default is None, server_default=default))

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
    if 'invoice_number' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('subscription_payments')}:
        op.add_column('subscription_payments', sa.Column('invoice_number', sa.Integer(), nullable=True))
        op.create_index('uq_subscription_payments_invoice_number', 'subscription_payments', ['invoice_number'], unique=True)


def downgrade() -> None:
    op.drop_table('subscription_payments')
    op.drop_table('restaurant_subscriptions')
    op.drop_table('subscription_plans')
    op.drop_table('order_reviews')
    op.drop_table('platform_settings')
    for column in ('vat_number', 'closes_at', 'opens_at', 'accepting_orders', 'category'):
        op.drop_column('restaurants', column)
    op.drop_table('restaurant_delivery_settings')
    op.drop_table('restaurant_payment_settings')
    op.drop_index('ix_drivers_restaurant_id', table_name='drivers')
    op.drop_constraint('fk_drivers_restaurant_id_restaurants', 'drivers', type_='foreignkey')
    op.drop_column('drivers', 'restaurant_id')
