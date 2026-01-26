"""loop automation v2.1

Revision ID: loop_v2_1
Revises: loop_v2
Create Date: 2026-01-26 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'loop_v2_1'
down_revision = '74a151a951bc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meal_plan_entries', sa.Column('force_cook', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    op.drop_column('meal_plan_entries', 'force_cook')
