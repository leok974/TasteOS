import json
from app.infra.redis_client import get_redis, get_sync_redis

def channel_for_session(session_id: str) -> str:
    return f"tasteos:cook:session:{session_id}"

async def publish_session_updated(session_id: str, workspace_id: str, updated_at_iso: str):
    r = await get_redis()
    payload = {"type": "session_updated", "session_id": session_id, "workspace_id": workspace_id, "updated_at": updated_at_iso}
    await r.publish(channel_for_session(session_id), json.dumps(payload))

def publish_session_updated_sync(session_id: str, workspace_id: str, updated_at_iso: str):
    r = get_sync_redis()
    payload = {"type": "session_updated", "session_id": session_id, "workspace_id": workspace_id, "updated_at": updated_at_iso}
    r.publish(channel_for_session(session_id), json.dumps(payload))

async def subscribe_session(session_id: str):
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel_for_session(session_id))
    return pubsub
