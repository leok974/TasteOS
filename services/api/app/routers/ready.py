from fastapi import APIRouter
from app.infra.redis_client import get_redis

router = APIRouter()


@router.get("/ready")
async def ready():
    redis_ok = False
    try:
        r = await get_redis()
        pong = await r.ping()
        redis_ok = True
    except Exception:
        pass
    return {"ok": True, "redis_ok": redis_ok}
