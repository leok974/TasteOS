"""add ingredient density overrides

Revision ID: 2c331c2c5e6c
Revises: 83ea189c810c
Create Date: 2026-02-06 20:42:24.998746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c331c2c5e6c'
down_revision: Union[str, None] = '83ea189c810c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely create table with IF NOT EXISTS
    op.execute("""
    CREATE TABLE IF NOT EXISTS ingredient_density_overrides (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        ingredient_key TEXT NOT NULL,
        display_name TEXT NOT NULL,
        density_g_per_ml NUMERIC(10,6) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        updated_at TIMESTAMP NOT NULL DEFAULT now(),
        UNIQUE (workspace_id, ingredient_key)
    );
    """)
    
    # Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_ingredient_density_overrides_workspace_id ON ingredient_density_overrides(workspace_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ingredient_density_overrides_ingredient_key ON ingredient_density_overrides(ingredient_key);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingredient_density_overrides;")
