"""
Ready router for health checks.

This module provides health check endpoints to verify API status
and dependencies.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tasteos_api.core.database import get_db_session

router = APIRouter()


@router.get("/ready")
async def ready(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> JSONResponse:
    """
    Phase 6.5:
    Lightweight healthcheck for CI / prod / smoke tests.

    Returns shape:
    {
      "status": "ok",
      "db": "ok"
    }
    """
    # Minimal "is DB alive" check. If session is broken, this will raise.
    # We don't care about result content, we only care that it didn't explode.
    try:
        # Touch connection; triggers failure if dead
        await session.connection()
        db_status = "ok"
    except Exception:
        db_status = "error"

    return JSONResponse({
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status
    })
