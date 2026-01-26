"""create_note_insights_cache

Revision ID: fa97b87008f1
Revises: 4f0630e8ef46
Create Date: 2026-01-26 01:01:49.995292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa97b87008f1'
down_revision: Union[str, None] = '4f0630e8ef46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'note_insights_cache',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('workspace_id', sa.String(36), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('recipe_id', sa.String(36), nullable=True),
        sa.Column('window_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('facts_hash', sa.Text(), nullable=False),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_note_insights_cache_workspace_id'), 'note_insights_cache', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_note_insights_cache_recipe_id'), 'note_insights_cache', ['recipe_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_note_insights_cache_recipe_id'), table_name='note_insights_cache')
    op.drop_index(op.f('ix_note_insights_cache_workspace_id'), table_name='note_insights_cache')
    op.drop_table('note_insights_cache')
