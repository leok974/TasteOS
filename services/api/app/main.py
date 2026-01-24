from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .routers.ready import router as ready_router
from .routers.recipes import router as recipes_router
from .routers.pantry import router as pantry_router
from .routers.grocery import router as grocery_router
from .routers.plan import router as plan_router
from .routers.ai import router as ai_router
from .routers.dev import router as dev_router
from .routers.workspaces import router as workspaces_router

app = FastAPI(title="TasteOS API", version="0.1.0")

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
app.include_router(dev_router, prefix="/api", tags=["dev"])
