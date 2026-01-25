# TasteOS API Main Entry Point
import logging
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .settings import settings
from .routers.ready import router as ready_router
from .routers.recipes import router as recipes_router
from .routers.pantry import router as pantry_router
from .routers.grocery import router as grocery_router
from .routers.plan import router as plan_router
from .routers.ai import router as ai_router
from .routers.cook import router as cook_router
from .routers.dev import router as dev_router
from .routers.workspaces import router as workspaces_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tasteos")

# Rate limiter (per-IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(title="TasteOS API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ready_router, prefix="/api", tags=["ready"])
app.include_router(workspaces_router, prefix="/api", tags=["workspaces"])
app.include_router(recipes_router, prefix="/api", tags=["recipes"])
app.include_router(pantry_router, prefix="/api/pantry", tags=["pantry"])
app.include_router(grocery_router, prefix="/api/grocery", tags=["grocery"])
app.include_router(plan_router, prefix="/api", tags=["plan"])
app.include_router(ai_router, prefix="/api", tags=["ai"])
app.include_router(cook_router, prefix="/api", tags=["cook"])
app.include_router(dev_router, prefix="/api", tags=["dev"])
