"""
TasteOS API - Main FastAPI Application

This module sets up the FastAPI application with all necessary routers,
middleware, and configuration for the TasteOS backend API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tasteos_api.core.config import get_settings
from tasteos_api.core.database import init_db
from tasteos_api.routers import (
    auth,
    billing,
    feedback,
    imports,
    nutrition,
    pantry,
    planner,
    ready,
    recipes,
    shopping,
    variants,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application lifecycle events."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Clean up resources
    pass


# Create FastAPI application
app = FastAPI(
    title="TasteOS API",
    description="Backend API for TasteOS - AI-powered recipe engine",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint with basic API information."""
    return JSONResponse({
        "message": "TasteOS API",
        "version": "0.1.0",
        "status": "healthy"
    })


# Include routers
app.include_router(ready.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(recipes.router, prefix="/api/v1/recipes", tags=["recipes"])
app.include_router(variants.router, prefix="/api/v1/variants", tags=["variants"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(imports.router, prefix="/api/v1", tags=["imports"])
app.include_router(nutrition.router, prefix="/api/v1", tags=["nutrition"])
app.include_router(pantry.router, prefix="/api/v1", tags=["pantry"])
app.include_router(planner.router, prefix="/api/v1", tags=["planner"])
app.include_router(shopping.router, prefix="/api/v1", tags=["shopping"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "tasteos_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
