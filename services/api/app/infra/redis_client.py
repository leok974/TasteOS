import os
from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis

_redis_async: AsyncRedis | None = None
_redis_sync: SyncRedis | None = None

def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_redis() -> AsyncRedis:
    global _redis_async
    if _redis_async is None:
        _redis_async = AsyncRedis.from_url(redis_url(), decode_responses=True)
    return _redis_async

def get_sync_redis() -> SyncRedis:
    global _redis_sync
    if _redis_sync is None:
        _redis_sync = SyncRedis.from_url(redis_url(), decode_responses=True)
    return _redis_sync
