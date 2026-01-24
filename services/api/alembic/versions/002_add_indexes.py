"""Add unique index on workspaces.slug and composite index on recipes

Revision ID: 002_add_indexes
Revises: 001_initial_schema
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_add_indexes"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Unique index on workspaces.slug to prevent duplicates under race conditions
    op.create_index(
        "ix_workspaces_slug_unique", 
        "workspaces", 
        ["slug"], 
        unique=True
    )
    
    # Composite index for fast recipe list views (workspace + created_at desc)
    op.create_index(
        "ix_recipes_workspace_created_desc",
        "recipes",
        ["workspace_id", "created_at"],
        postgresql_using="btree",  # default, but explicit
    )


def downgrade() -> None:
    op.drop_index("ix_recipes_workspace_created_desc", table_name="recipes")
    op.drop_index("ix_workspaces_slug_unique", table_name="workspaces")
