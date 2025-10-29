"""
Configuration settings for the TasteOS API.

This module provides centralized configuration management using Pydantic settings,
supporting environment variables and default values.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Environment
    environment: str = Field(default="development", alias="NODE_ENV")

    # Database
    database_url: str = Field(
        default="sqlite:///./tasteos.db",
        alias="DATABASE_URL"
    )

    # Authentication
    jwt_secret: str = Field(default="changeme", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000"
    ]

    # External APIs
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")

    # Stripe
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_pro: str = Field(default="", alias="STRIPE_PRICE_PRO")
    stripe_price_pro_year: str = Field(default="", alias="STRIPE_PRICE_PRO_YEAR")

    # Feature Flags
    tasteos_enable_pantry: str = Field(default="0", alias="TASTEOS_ENABLE_PANTRY")
    tasteos_enable_planner: str = Field(default="0", alias="TASTEOS_ENABLE_PLANNER")

    # Nutrition APIs
    nutrition_api_key: str = Field(default="", alias="NUTRITION_API_KEY")
    nutrition_provider: str = Field(default="edamam", alias="NUTRITION_PROVIDER")
    edamam_app_id: str = Field(default="", alias="EDAMAM_APP_ID")
    edamam_app_key: str = Field(default="", alias="EDAMAM_APP_KEY")

    # Application URLs
    frontend_url: str = Field(
        default="http://localhost:5173",
        alias="NEXT_PUBLIC_APP_URL"
    )
    marketing_url: str = Field(
        default="http://localhost:3000",
        alias="NEXT_PUBLIC_MARKETING_SITE_URL"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
