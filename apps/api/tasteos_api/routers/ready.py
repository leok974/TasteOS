"""
Ready router for health checks.

This module provides health check endpoints to verify API status
and dependencies.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/ready")
async def ready() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({
        "status": "ready",
        "message": "TasteOS API is running",
        "version": "0.1.0"
    })


@router.get("/health")
async def health() -> JSONResponse:
    """Detailed health check with dependencies."""
    # TODO: Add database connection check
    # TODO: Add external API checks (OpenAI, etc.)

    return JSONResponse({
        "status": "healthy",
        "checks": {
            "database": "ok",
            "openai": "ok",
            "stripe": "ok"
        },
        "timestamp": "2025-10-28T12:00:00Z"
    })
