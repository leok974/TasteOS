"""Create cook_session_events table

Revision ID: f7a8b9c0d1e2
Revises: e6c7b5611bd1
Create Date: 2026-01-25 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e426570bcb89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('cook_session_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=True),
        sa.Column('bullet_index', sa.Integer(), nullable=True),
        sa.Column('timer_id', sa.String(length=36), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['cook_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cook_events_ws_created', 'cook_session_events', ['workspace_id', 'created_at'], unique=False)
    op.create_index('ix_cook_events_ws_session_created', 'cook_session_events', ['workspace_id', 'session_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_cook_events_ws_session_created', table_name='cook_session_events')
    op.drop_index('ix_cook_events_ws_created', table_name='cook_session_events')
    op.drop_table('cook_session_events')
