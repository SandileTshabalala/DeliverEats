"""a PayFast charge (pf_payment_id) can be recorded as paid only once

Revision ID: f8c3d1e7a2b4
Revises: e5b7a2c90f13
Create Date: 2026-11-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f8c3d1e7a2b4'
down_revision: Union[str, Sequence[str], None] = 'e5b7a2c90f13'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_payments_pf_charge "
        "ON subscription_payments (reference) WHERE method = 'payfast' AND status = 'completed'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_subscription_payments_pf_charge")
