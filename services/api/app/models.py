"""SQLAlchemy ORM models for TasteOS.

Tables:
- workspaces: Multi-tenant workspace isolation (auth-free MVP uses single "local" workspace)
- recipes: Core recipe data with workspace scoping
- recipe_steps: Ordered cooking steps for a recipe
- recipe_images: AI-generated images with status tracking
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    Boolean,
    Float,
    ForeignKey,
    Index,
    ARRAY,
    desc,
    text,
    Numeric,
    UniqueConstraint
)
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, false
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON

from .db import Base
from .orm_types import GUID


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Workspace(Base):
    """Workspace for multi-tenant isolation.
    
    MVP: Single "local" workspace, resolved via header/env/fallback.
    Future: Multiple workspaces per user for family sharing.
    """
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Unit Preferences (JSONB)
    unit_prefs_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )

    # Relationships
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="workspace", cascade="all, delete-orphan"
    )
    
    density_overrides: Mapped[list["IngredientDensityOverride"]] = relationship(
        "IngredientDensityOverride", back_populates="workspace", cascade="all, delete-orphan"
    )

class IngredientDensityOverride(Base):
    """User-defined density overrides for ingredients."""
    __tablename__ = "ingredient_density_overrides"
    __table_args__ = (
        Index("ix_ingredient_density_workspace_id", "workspace_id"),
        Index("ix_ingredient_density_key", "ingredient_key"),
        UniqueConstraint("workspace_id", "ingredient_key", name="uq_workspace_ingredient_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    ingredient_key: Mapped[str] = mapped_column(String(255), nullable=False) # Normalized
    display_name: Mapped[str] = mapped_column(String(255), nullable=False) 
    density_g_per_ml: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default='user')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="density_overrides")

class Recipe(Base):
    """Core recipe with workspace scoping."""
    __tablename__ = "recipes"
    __table_args__ = (
        Index("ix_recipes_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cuisines: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(80)), nullable=True, default=list
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(80)), nullable=True, default=list
    )
    servings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Cook Time Badge Fields
    total_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_minutes_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # "explicit" | "estimated"
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Nutrition
    macros: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'"))

    # Active image pointer (for deterministic display)
    active_image_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recipe_images.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )
    
    # Source Hash for Seed Idempotency
    source_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="recipes")

    steps: Mapped[list["RecipeStep"]] = relationship(
        "RecipeStep", back_populates="recipe", cascade="all, delete-orphan",
        order_by="RecipeStep.step_index"
    )
    images: Mapped[list["RecipeImage"]] = relationship(
        "RecipeImage", back_populates="recipe", cascade="all, delete-orphan",
        foreign_keys="[RecipeImage.recipe_id]"
    )
    
    active_image: Mapped[Optional["RecipeImage"]] = relationship(
        "RecipeImage", foreign_keys="[Recipe.active_image_id]", post_update=True
    )
    
    # Variants (Versioning)
    active_variant_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recipe_variants.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )
    variants: Mapped[list["RecipeVariant"]] = relationship(
        "RecipeVariant", back_populates="recipe", foreign_keys="[RecipeVariant.recipe_id]",
        cascade="all, delete-orphan"
    )
    active_variant: Mapped[Optional["RecipeVariant"]] = relationship(
        "RecipeVariant", foreign_keys="[Recipe.active_variant_id]", post_update=True
    )

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    notes_history: Mapped[list["RecipeNoteEntry"]] = relationship(
        "RecipeNoteEntry", back_populates="recipe", cascade="all, delete-orphan",
        order_by="desc(RecipeNoteEntry.created_at)"
    )

    @property
    def primary_image(self) -> Optional["RecipeImage"]:
        """Get the active image, or fall back to first ready."""
        if self.active_image and self.active_image.status == "ready":
            return self.active_image
            
        # Fallback (legacy/migration safety)
        for img in self.images:
            if img.status == "ready":
                return img
        return None


class RecipeStep(Base):
    """Ordered cooking step within a recipe."""
    __tablename__ = "recipe_steps"
    __table_args__ = (
        Index("ix_recipe_steps_recipe_id", "recipe_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    bullets: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), nullable=True, default=list
    )
    minutes_est: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="steps")


class MealLog(Base):
    """Logs a user's meal intake based on a recipe."""
    __tablename__ = "meal_logs"
    __table_args__ = (
        Index("ix_meal_logs_workspace_id", "workspace_id"),
        Index("ix_meal_logs_timestamp", "timestamp"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id"), nullable=False
    )
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Stores snapshot: {"calories": 500, "protein_g": 30, ...}
    macros_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RecipeImage(Base):
    """AI-generated image for a recipe with status tracking."""
    __tablename__ = "recipe_images"
    __table_args__ = (
        Index("ix_recipe_images_recipe_id", "recipe_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    
    # Status: pending | processing | ready | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    
    # Worker locking (prevents race conditions)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Retry logic
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # AI provider info
    provider: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # e.g., "gemini"
    model: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # e.g., "gemini-2.5-flash-image"
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Storage info
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    recipe: Mapped["Recipe"] = relationship(
        "Recipe", back_populates="images", foreign_keys="[RecipeImage.recipe_id]"
    )


class RecipeVariant(Base):
    """Immutable version of a recipe (structured draft)."""
    __tablename__ = "recipe_variants"
    __table_args__ = (
        Index("ix_recipe_variants_recipe_id", "recipe_id"),
        Index("ix_recipe_variants_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    
    label: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "Original", "Spicy v2"
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(50), nullable=False, server_default='ai') # ai | user
    model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="variants", foreign_keys=[recipe_id])



class RecipeNoteEntry(Base):
    """History of notes added to a recipe."""
    __tablename__ = "recipe_note_entries"
    __table_args__ = (
        Index("ix_recipe_note_entries_workspace_id", "workspace_id"),
        Index("ix_recipe_note_entries_recipe_lookup", "workspace_id", "recipe_id", "created_at"),
        Index("ix_recipe_note_entries_session_lookup", "workspace_id", "session_id"),
        Index("ix_recipe_note_entries_unique_session", "session_id", "recipe_id", unique=True), # Removed postgresql_where for SQLite compat in tests
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("cook_sessions.id", ondelete="SET NULL"), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # manual | cook_session | ai_polish
    source: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    
    # v11: Searchable tags
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    data_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    applied_to_recipe_notes: Mapped[bool] = mapped_column(Boolean, default=False)
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="notes_history")

class RecipeMacroEntry(Base):
    """History of macro estimates for a recipe."""
    __tablename__ = "recipe_macro_entries"
    __table_args__ = (
        Index("ix_recipe_macro_ws_recipe_created", "workspace_id", "recipe_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Macros (Min/Max ranges)
    calories_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calories_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protein_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protein_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    carbs_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    carbs_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fat_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fat_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # user | ai | heuristic
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    context_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class RecipeTipEntry(Base):
    """History of tips (storage, reheating) for a recipe."""
    __tablename__ = "recipe_tip_entries"
    __table_args__ = (
        Index("ix_recipe_tips_ws_recipe_scope_created", "workspace_id", "recipe_id", "scope", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scope: Mapped[str] = mapped_column(String(50), nullable=False)  # storage | reheat
    tips_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default='[]')
    food_safety_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default='[]')

    # Metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # user | ai
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    context_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe")
    workspace: Mapped["Workspace"] = relationship("Workspace")


from sqlalchemy import Date, Numeric

class PantryItem(Base):
    """Pantry item for inventory management."""
    __tablename__ = "pantry_items"
    __table_args__ = (
        Index("ix_pantry_items_workspace_id_expires_on", "workspace_id", "expires_on"),
        Index("ix_pantry_items_workspace_id_lower_name", "workspace_id", func.lower("name")),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Expiry for "use soon" logic
    expires_on: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    opened_on: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    use_soon_at: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Source: manual | scan | leftover | recipe | grocery
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")


class PantryTransaction(Base):
    """Audit log for pantry changes and undo capability."""
    __tablename__ = "pantry_transactions"
    __table_args__ = (
        Index("ix_pantry_transactions_workspace_item", "workspace_id", "pantry_item_id", desc("created_at")),
        Index("ix_pantry_transactions_ref", "workspace_id", "ref_type", "ref_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    pantry_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("pantry_items.id", ondelete="CASCADE"), nullable=False)
    
    source: Mapped[str] = mapped_column(String(50), nullable=False) # cook, grocery, manual
    ref_type: Mapped[str] = mapped_column(String(50), nullable=False) # cook_session, grocery_list
    ref_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    delta_qty: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    undone_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Leftover(Base):
    """Leftovers tracking linked to plan entries."""
    __tablename__ = "leftovers"
    __table_args__ = (
        Index("ix_leftovers_workspace_active", "workspace_id", postgresql_where=text("consumed_at IS NULL")),
        Index("ix_leftovers_dedupe_active", "workspace_id", "plan_entry_id", unique=True, postgresql_where=text("consumed_at IS NULL")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    
    plan_entry_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("meal_plan_entries.id", ondelete="SET NULL"), nullable=True)
    recipe_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    pantry_item_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("pantry_items.id", ondelete="SET NULL"), nullable=True)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    servings_left: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")
    pantry_item: Mapped[Optional["PantryItem"]] = relationship("PantryItem")


class RecipeIngredient(Base):
    """Structured ingredient for a recipe."""
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        Index("ix_recipe_ingredients_recipe_id", "recipe_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")


class GroceryList(Base):
    """Grocery list (v1 persistent)."""
    __tablename__ = "grocery_lists"
    __table_args__ = (
        Index("idx_grocery_lists_workspace_created_at", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, server_default="manual") # manual | generated
    source: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # { plan_id, recipe_ids, ... }
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    items: Mapped[list["GroceryListItem"]] = relationship(
        "GroceryListItem", back_populates="list", cascade="all, delete-orphan",
        order_by="[GroceryListItem.position, GroceryListItem.created_at]"
    )


class GroceryListItem(Base):
    """Item in a grocery list."""
    __tablename__ = "grocery_list_items"
    __table_args__ = (
        Index("idx_grocery_items_list_id", "list_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False
    )
    
    key: Mapped[str] = mapped_column(String(255), nullable=False) # Normalized key
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    raw: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True) 
    sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True) # Recipe refs
    
    checked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    list: Mapped["GroceryList"] = relationship("GroceryList", back_populates="items")


from sqlalchemy.dialects.postgresql import JSONB

class MealPlan(Base):
    """Weekly meal plan."""
    __tablename__ = "meal_plans"
    __table_args__ = (
        Index("ix_meal_plans_workspace_week", "workspace_id", "week_start"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    week_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    entries: Mapped[list["MealPlanEntry"]] = relationship(
        "MealPlanEntry", back_populates="meal_plan", cascade="all, delete-orphan",
        order_by="[MealPlanEntry.date, MealPlanEntry.meal_type]"
    )


class MealPlanEntry(Base):
    """Single slot in a meal plan (Lunch/Dinner)."""
    __tablename__ = "meal_plan_entries"
    __table_args__ = (
        Index("ix_meal_plan_entries_plan_date", "meal_plan_id", "date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    meal_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )
    
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False) # lunch | dinner
    
    # Recipe might be null if it's a "fend for yourself" or custom text slot (future)
    recipe_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    
    is_leftover: Mapped[bool] = mapped_column(default=False)
    force_cook: Mapped[bool] = mapped_column(default=False)
    
    # Method choice (e.g., "Air Fryer", "Microwave")
    method_choice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # AI generated options: { "Air Fryer": { time: "15m", trade-off: "Crispier" } }
    method_options_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    meal_plan: Mapped["MealPlan"] = relationship("MealPlan", back_populates="entries")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")


class UserPrefs(Base):
    """Workspace-scoped user preferences."""
    __tablename__ = "user_prefs"
    __table_args__ = (
        Index("ix_user_prefs_workspace", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    
    # intensity: low | medium | high (repeats)
    leftover_intensity: Mapped[str] = mapped_column(String(20), server_default="medium", nullable=False)
    
    # equipment: { "air_fryer": true, "instant_pot": false ... }
    equipment_flags: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CookSession(Base):
    """Cooking session with persistent state for timers and step checks."""
    __tablename__ = "cook_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # NEW: Track when session ended
    
    # Completion tracking (v10)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recap_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    # Servings scaling
    servings_base: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    servings_target: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_checks: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    timers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    hands_free: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Method Switching
    method_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    steps_override: Mapped[Optional[list[dict]]] = mapped_column(JSONB, nullable=True)
    method_tradeoffs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    method_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Adjust On The Fly
    adjustments_log: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default='[]')

    # Auto Step Detection
    auto_step_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    auto_step_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="suggest", server_default="suggest")
    auto_step_suggested_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    auto_step_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_step_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Manual Override Tracking
    manual_override_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_interaction_step_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    workspace: Mapped["Workspace"] = relationship()


class CookSessionEvent(Base):
    """Event log for cook session interactions (v6).
    
    Powers: "Why did auto-step trigger?", undo features, analytics.
    """
    __tablename__ = "cook_session_events"
    __table_args__ = (
        Index("ix_cook_events_ws_session_created", "workspace_id", "session_id", "created_at"),
        Index("ix_cook_events_ws_created", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("cook_sessions.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Enum-like type: session_start, step_nav, check_toggle, etc.
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Context
    step_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bullet_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Metadata (kept small)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    # Relationships
    session: Mapped["CookSession"] = relationship()




class NoteInsightsCache(Base):
    __tablename__ = "note_insights_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)  # "workspace" or "recipe"
    recipe_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    window_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    facts_hash: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
