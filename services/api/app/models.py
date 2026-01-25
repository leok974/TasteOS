"""SQLAlchemy ORM models for TasteOS.

Tables:
- workspaces: Multi-tenant workspace isolation (auth-free MVP uses single "local" workspace)
- recipes: Core recipe data with workspace scoping
- recipe_steps: Ordered cooking steps for a recipe
- recipe_images: AI-generated images with status tracking
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    ForeignKey,
    Index,
    ARRAY,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .db import Base


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

    # Relationships
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="workspace", cascade="all, delete-orphan"
    )


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
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Active image pointer (for deterministic display)
    active_image_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recipe_images.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )
    
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
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
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
    
    # Source: manual | scan | leftover | recipe
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
    """Generated grocery list."""
    __tablename__ = "grocery_lists"
    __table_args__ = (
        Index("ix_grocery_lists_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    
    # source: "plan:{id}" | "recipes:{ids}"
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    items: Mapped[list["GroceryListItem"]] = relationship(
        "GroceryListItem", back_populates="grocery_list", cascade="all, delete-orphan"
    )


class GroceryListItem(Base):
    """Item in a grocery list."""
    __tablename__ = "grocery_list_items"
    __table_args__ = (
        Index("ix_grocery_list_items_list_id", "grocery_list_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    grocery_list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # status: need | have | optional | purchased
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="need")
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    grocery_list: Mapped["GroceryList"] = relationship("GroceryList", back_populates="items")


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
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # NEW: Track when session ended
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_checks: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    timers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    workspace: Mapped["Workspace"] = relationship()


