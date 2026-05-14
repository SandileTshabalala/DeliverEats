"""add image_url to menu_items

Revision ID: 116d4825f9bb
Revises: d7143437688d
Create Date: 2026-01-28 13:24:59.960984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2ab4e112ad0'
down_revision: Union[str, Sequence[str], None] = 'd7143437688d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
