from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://tasteos:tasteos@localhost:5432/tasteos"
    redis_url: str = "redis://localhost:6379/0"

    # Workspace resolution
    default_workspace_slug: str = "local"

    # AI
    ai_enabled: bool = False  # Gate for image generation
    ai_mode: str = "mock"  # "mock" or "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash-image"

    # Object store (S3-compatible)
    object_store_endpoint: str = "http://localhost:9000"
    object_store_region: str = "auto"
    object_store_bucket: str = "tasteos-images"
    object_store_access_key_id: str = "minioadmin"
    object_store_secret_access_key: str = "minioadmin"
    object_public_base_url: str = "http://localhost:9000/tasteos-images"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost",
        "http://127.0.0.1",
    ]


settings = Settings()
