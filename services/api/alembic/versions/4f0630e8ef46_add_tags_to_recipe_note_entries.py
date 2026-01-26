"""add_tags_to_recipe_note_entries

Revision ID: 4f0630e8ef46
Revises: 22682a1358a2
Create Date: 2026-01-26 00:41:17.914213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f0630e8ef46'
down_revision: Union[str, None] = '22682a1358a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tags column
    op.add_column('recipe_note_entries', sa.Column('tags', sa.ARRAY(sa.Text()), nullable=False, server_default='{}'))
    op.create_index('ix_recipe_note_entries_tags', 'recipe_note_entries', ['tags'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_recipe_note_entries_tags', table_name='recipe_note_entries')
    op.drop_column('recipe_note_entries', 'tags')
