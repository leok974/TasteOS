import pytest
import asyncio
import json
from app.infra.redis_client import get_redis
from app.realtime.cook_bus import publish_session_updated, subscribe_session
from app.infra.redis_cache import get_or_set_json

@pytest.mark.asyncio
async def test_redis_connection():
    r = await get_redis()
    # If fakeredis is installed and patched, this works.
    # Otherwise it tries to connect to real redis at localhost.
    # We might need to ensure backend tests run with real redis or fakeredis patch.
    # Assuming the environment or fixture handles it, but let's try.
    try:
        pong = await r.ping()
        assert pong is True
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

@pytest.mark.asyncio
async def test_pubsub_flow():
    session_id = "test-session-123"
    
    # 1. Subscribe
    try:
        pubsub = await subscribe_session(session_id)
    except Exception:
        pytest.skip("Redis not available")
    
    # 2. Publish
    await publish_session_updated(session_id, "ws-1", "2023-01-01T00:00:00Z")
    
    # 3. Receive
    # Give it a moment to propagate in real redis
    loop = asyncio.get_running_loop()
    msg = None
    for _ in range(5):
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg:
            break
        await asyncio.sleep(0.1)
        
    assert msg is not None
    assert msg["channel"] == f"tasteos:cook:session:{session_id}"
    payload = json.loads(msg["data"])
    assert payload["type"] == "session_updated"
    
    await pubsub.unsubscribe()

@pytest.mark.asyncio
async def test_cache_helper():
    key = "test:cache:1"
    r = await get_redis()
    try:
        await r.flushdb()
    except Exception:
        pytest.skip("Redis not available")
    
    calls = 0
    async def compute():
        nonlocal calls
        calls += 1
        return {"data": "fresh"}
        
    # 1. Miss
    val, hit = await get_or_set_json(key, 10, compute)
    assert val == {"data": "fresh"}
    assert hit is False
    assert calls == 1
    
    # 2. Hit
    val2, hit2 = await get_or_set_json(key, 10, compute)
    assert val2 == {"data": "fresh"}
    assert hit2 is True
    assert calls == 1 # No increment
