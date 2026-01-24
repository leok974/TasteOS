
"""planner tables

Revision ID: 006_planner
Revises: 005_grocery
Create Date: 2026-01-23 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_planner'
down_revision = '4f77e906b671'
branch_labels = None
depends_on = None


def upgrade():
    # --- Meal Plans ---
    op.create_table('meal_plans',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('workspace_id', sa.String(36), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'week_start', name='uq_meal_plan_workspace_week')
    )
    op.create_index('ix_meal_plans_workspace_week', 'meal_plans', ['workspace_id', 'week_start'])

    # --- Meal Plan Entries ---
    op.create_table('meal_plan_entries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('meal_plan_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(), nullable=False), # lunch, dinner
        sa.Column('recipe_id', sa.String(36), nullable=True),
        sa.Column('is_leftover', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('method_choice', sa.Text(), nullable=True),
        sa.Column('method_options_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meal_plan_id', 'date', 'meal_type', name='uq_meal_plan_entry_slot')
    )
    op.create_index('ix_meal_plan_entries_plan_date', 'meal_plan_entries', ['meal_plan_id', 'date'])

    # --- User Prefs ---
    op.create_table('user_prefs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('workspace_id', sa.String(36), nullable=False),
        sa.Column('leftover_intensity', sa.String(), server_default='medium', nullable=False),
        sa.Column('equipment_flags', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', name='uq_user_prefs_workspace')
    )


def downgrade():
    op.drop_table('user_prefs')
    op.drop_table('meal_plan_entries')
    op.drop_table('meal_plans')
