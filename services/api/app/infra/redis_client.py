import os
from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis

from typing import Optional
_redis_async: Optional[AsyncRedis] = None
_redis_sync: Optional[SyncRedis] = None

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
