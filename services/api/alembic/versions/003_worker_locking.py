"""Add worker locking and retry fields to recipe_images

Revision ID: 003_worker_locking
Revises: 002_add_indexes
Create Date: 2026-01-23

State machine: pending → processing → ready | failed
Locking: locked_at + worker_id prevent race conditions
Retry: attempts + last_error + next_attempt_at enable backoff
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_worker_locking"
down_revision: Union[str, None] = "002_add_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add worker locking columns to recipe_images
    op.add_column("recipe_images", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recipe_images", sa.Column("worker_id", sa.String(64), nullable=True))
    op.add_column("recipe_images", sa.Column("attempts", sa.Integer, nullable=False, server_default="0"))
    op.add_column("recipe_images", sa.Column("last_error", sa.Text, nullable=True))
    op.add_column("recipe_images", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    
    # Add active_image_id to recipes
    op.add_column("recipes", sa.Column("active_image_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_recipes_active_image",
        "recipes",
        "recipe_images",
        ["active_image_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,  # Handle circular dependency
    )
    
    # Index for worker polling
    op.create_index(
        "ix_recipe_images_pending_poll",
        "recipe_images",
        ["status", "next_attempt_at"],
    )
    
    # Backfill active_image_id for existing recipes with ready images
    # Select distinct recipe_id, id from recipe_images where status='ready' order by created_at desc (via subquery logic)
    # Using raw SQL for the update for simplicity/portability in Alembic
    op.execute("""
        UPDATE recipes
        SET active_image_id = (
            SELECT id FROM recipe_images
            WHERE recipe_images.recipe_id = recipes.id
            AND status = 'ready'
            ORDER BY created_at DESC
            LIMIT 1
        )
        WHERE active_image_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_recipe_images_pending_poll", table_name="recipe_images")
    op.drop_constraint("fk_recipes_active_image", "recipes", type_="foreignkey")
    op.drop_column("recipes", "active_image_id")
    op.drop_column("recipe_images", "next_attempt_at")
    op.drop_column("recipe_images", "last_error")
    op.drop_column("recipe_images", "attempts")
    op.drop_column("recipe_images", "worker_id")
    op.drop_column("recipe_images", "locked_at")
