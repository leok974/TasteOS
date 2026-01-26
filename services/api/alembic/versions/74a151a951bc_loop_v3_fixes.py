"""loop_v3_fixes

Revision ID: 74a151a951bc
Revises: loop_v2
Create Date: 2026-01-26 03:45:41.213976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74a151a951bc'
down_revision: Union[str, None] = 'loop_v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename expires_at -> expires_on to match PantryItem
    op.alter_column('leftovers', 'expires_at', new_column_name='expires_on')
    
    # 2. Add pantry_item_id FK
    op.add_column('leftovers', sa.Column('pantry_item_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_leftovers_pantry_item', 'leftovers', 'pantry_items', ['pantry_item_id'], ['id'], ondelete='SET NULL')
    
    # 3. Add dedupe index: Only one active leftover per plan entry
    op.create_index('ix_leftovers_dedupe_active', 'leftovers', ['workspace_id', 'plan_entry_id'], unique=True, postgresql_where=sa.text('consumed_at IS NULL'))


def downgrade() -> None:
    op.drop_index('ix_leftovers_dedupe_active', table_name='leftovers')
    op.drop_constraint('fk_leftovers_pantry_item', 'leftovers', type_='foreignkey')
    op.drop_column('leftovers', 'pantry_item_id')
    op.alter_column('leftovers', 'expires_on', new_column_name='expires_at')
