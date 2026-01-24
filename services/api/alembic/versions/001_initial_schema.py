"""Initial schema with workspaces, recipes, recipe_steps, recipe_images

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("cuisines", postgresql.ARRAY(sa.String(80)), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(80)), nullable=True),
        sa.Column("servings", sa.Integer, nullable=True),
        sa.Column("time_minutes", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recipes_workspace_id", "recipes", ["workspace_id"])

    # Recipe steps table
    op.create_table(
        "recipe_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipe_id", sa.String(36), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("bullets", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("minutes_est", sa.Integer, nullable=True),
    )
    op.create_index("ix_recipe_steps_recipe_id", "recipe_steps", ["recipe_id"])

    # Recipe images table
    op.create_table(
        "recipe_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipe_id", sa.String(36), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recipe_images_recipe_id", "recipe_images", ["recipe_id"])


def downgrade() -> None:
    op.drop_table("recipe_images")
    op.drop_table("recipe_steps")
    op.drop_table("recipes")
    op.drop_table("workspaces")
