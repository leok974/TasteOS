"""add_cook_sessions_table

Revision ID: 82205a222a97
Revises: 006_planner
Create Date: 2026-01-24 20:23:04.381089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '82205a222a97'
down_revision: Union[str, None] = '006_planner'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cook_sessions table
    op.create_table(
        'cook_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workspace_id', sa.String(36), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('recipe_id', sa.String(36), sa.ForeignKey('recipes.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('current_step_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('step_checks', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('timers', postgresql.JSONB, nullable=False, server_default='{}'),
    )
    
    # Create indexes for performance
    op.create_index(
        'ix_cook_sessions_workspace_status_started',
        'cook_sessions',
        ['workspace_id', 'status', sa.text('started_at DESC')]
    )
    op.create_index(
        'ix_cook_sessions_workspace_recipe_status',
        'cook_sessions',
        ['workspace_id', 'recipe_id', 'status']
    )


def downgrade() -> None:
    op.drop_index('ix_cook_sessions_workspace_recipe_status')
    op.drop_index('ix_cook_sessions_workspace_status_started')
    op.drop_table('cook_sessions')
