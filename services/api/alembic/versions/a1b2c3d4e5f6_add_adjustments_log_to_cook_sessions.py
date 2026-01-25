"""Add adjustments_log to cook_sessions

Revision ID: a1b2c3d4e5f6
Revises: 1ce98d8ef389
Create Date: 2026-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '1ce98d8ef389'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cook_sessions', sa.Column('adjustments_log', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))


def downgrade() -> None:
    op.drop_column('cook_sessions', 'adjustments_log')
