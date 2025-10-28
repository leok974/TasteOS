"""
Router package initialization.

This module exports all API routers for the TasteOS FastAPI application.
"""

from tasteos_api.routers import auth, billing, feedback, ready, recipes, variants

__all__ = ["auth", "billing", "feedback", "ready", "recipes", "variants"]
