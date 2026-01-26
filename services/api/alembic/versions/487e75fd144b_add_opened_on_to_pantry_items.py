"""add opened_on to pantry_items

Revision ID: 487e75fd144b
Revises: loop_v2_1
Create Date: 2026-01-26 20:27:17.867829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '487e75fd144b'
down_revision: Union[str, None] = 'loop_v2_1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pantry_items', sa.Column('opened_on', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('pantry_items', 'opened_on')
