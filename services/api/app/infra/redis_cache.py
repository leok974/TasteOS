import json
from app.infra.redis_client import get_redis, get_sync_redis

async def get_json(key: str):
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None

async def set_json(key: str, value, ttl_sec: int):
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl_sec)

async def get_or_set_json(key: str, ttl_sec: int, compute_coro):
    hit = await get_json(key)
    if hit is not None:
        return hit, True
    val = await compute_coro()
    await set_json(key, val, ttl_sec)
    return val, False

def get_or_set_json_sync(key: str, ttl_sec: int, compute_func):
    r = get_sync_redis()
    raw = r.get(key)
    if raw:
        return json.loads(raw), True
    
    val = compute_func()
    r.set(key, json.dumps(val), ex=ttl_sec)
    return val, False
