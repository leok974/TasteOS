"""loop automation v2

Revision ID: loop_v2
Revises: loop_v1
Create Date: 2026-01-26 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'loop_v2'
down_revision = 'loop_v1'
branch_labels = None
depends_on = None


def upgrade():
    # --- Pantry Transactions ---
    op.create_table('pantry_transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('pantry_item_id', sa.String(length=36), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False), # cook, grocery, manual
        sa.Column('ref_type', sa.String(length=50), nullable=False), # cook_session, grocery_list
        sa.Column('ref_id', sa.String(length=36), nullable=True),
        sa.Column('delta_qty', sa.Numeric(), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('undone_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pantry_item_id'], ['pantry_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pantry_transactions_workspace_item', 'pantry_transactions', ['workspace_id', 'pantry_item_id', sa.text('created_at DESC')])
    op.create_index('ix_pantry_transactions_ref', 'pantry_transactions', ['workspace_id', 'ref_type', 'ref_id'])

    # --- Leftovers ---
    op.create_table('leftovers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('plan_entry_id', sa.String(length=36), nullable=True),
        sa.Column('recipe_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.Date(), nullable=True),
        sa.Column('servings_left', sa.Numeric(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_entry_id'], ['meal_plan_entries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_leftovers_workspace_active', 'leftovers', ['workspace_id'], postgresql_where=sa.text('consumed_at IS NULL'))


def downgrade():
    op.drop_table('leftovers')
    op.drop_table('pantry_transactions')
