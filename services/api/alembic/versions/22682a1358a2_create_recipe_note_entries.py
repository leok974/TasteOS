"""create_recipe_note_entries

Revision ID: 22682a1358a2
Revises: b3cf48d03393
Create Date: 2026-01-26 00:03:45.343591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22682a1358a2'
down_revision: Union[str, None] = 'b3cf48d03393'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # recipe_note_entries
    op.create_table(
        'recipe_note_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('recipe_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=False),
        sa.Column('applied_to_recipe_notes', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['cook_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recipe_note_entries_workspace_id', 'recipe_note_entries', ['workspace_id'], unique=False)
    op.create_index('ix_recipe_note_entries_recipe_lookup', 'recipe_note_entries', ['workspace_id', 'recipe_id', 'created_at'], unique=False)
    op.create_index('ix_recipe_note_entries_session_lookup', 'recipe_note_entries', ['workspace_id', 'session_id'], unique=False)
    
    # Partial unique index to prevent duplicate saves for the same session (unless deleted)
    op.create_index(
        'ix_recipe_note_entries_unique_session', 
        'recipe_note_entries', 
        ['session_id', 'recipe_id'], 
        unique=True, 
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    op.drop_index('ix_recipe_note_entries_unique_session', table_name='recipe_note_entries')
    op.drop_index('ix_recipe_note_entries_session_lookup', table_name='recipe_note_entries')
    op.drop_index('ix_recipe_note_entries_recipe_lookup', table_name='recipe_note_entries')
    op.drop_index('ix_recipe_note_entries_workspace_id', table_name='recipe_note_entries')
    op.drop_table('recipe_note_entries')
