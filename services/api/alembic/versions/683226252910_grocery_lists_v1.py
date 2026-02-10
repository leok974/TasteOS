"""grocery lists v1

Revision ID: 683226252910
Revises: loop_v2_1
Create Date: 2026-02-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '683226252910'
down_revision = ('loop_v2_1', '05c0902200be')
branch_labels = None
depends_on = None


def upgrade():
    # Only drop if they exist, but alembic doesn't have "drop if exists" easily without hack.
    # However since checks are hard, we assume they exist because of previous migration in history.
    # To be safe, we can try/except or inspect, but standard alembic is explicit.
    # Since we are in development and fixing a "broken" feature, aggressive drop is fine.
    
    # Check if table exists to avoid error if it was never created
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'grocery_list_items' in tables:
        op.drop_table('grocery_list_items')
    if 'grocery_lists' in tables:
        op.drop_table('grocery_lists')
    
    # Create new tables
    op.create_table('grocery_lists',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('kind', sa.String(length=50), server_default='manual', nullable=False),
        sa.Column('source', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_grocery_lists_workspace_created_at', 'grocery_lists', ['workspace_id', 'created_at'], unique=False)

    op.create_table('grocery_list_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('list_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('display', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['list_id'], ['grocery_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_grocery_items_list_id', 'grocery_list_items', ['list_id'], unique=False)


def downgrade():
    op.drop_table('grocery_list_items')
    op.drop_table('grocery_lists')
