import hashlib, json, time
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.infra.redis_client import get_redis

DONE_TTL_SEC = 60 * 60 * 24
PROCESSING_TTL_SEC = 60

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hash_request(method: str, path: str, body_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(method.encode("utf-8"))
    h.update(b"|")
    h.update(path.encode("utf-8"))
    h.update(b"|")
    h.update(body_bytes or b"")
    return h.hexdigest()

def _idemp_redis_key(workspace_id: str, route_key: str, idem_key: str) -> str:
    return f"tasteos:idemp:{workspace_id}:{route_key}:{idem_key}"

from typing import Union, Optional
async def idempotency_precheck(request: Request, *, workspace_id: str, route_key: str) -> Union[tuple[str, str, bytes], JSONResponse]:
    """Return (redis_key, request_hash, body_bytes) if caller should proceed.
       Or return JSONResponse if a cached response should be replayed."""
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        # In this implementation, we allow non-idempotent requests if header is missing
        # But per requirements "Rules: required for protected endpoints"
        # Since I'm retrofitting, I should maybe enforcing it?
        # The prompt says: "required for protected endpoints in production (optional in dev if you want)"
        # I will enforce it if the function is called, implying the endpoint IS protected.
        # However, to be safe during transition, maybe I could make it optional?
        # The prompt code raises HTTPException(400) if missing. So I'll follow that.
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key header")

    body_bytes = await request.body()
    req_hash = _hash_request(request.method, request.url.path, body_bytes)

    rkey = _idemp_redis_key(workspace_id, route_key, idem_key)
    r = await get_redis()

    raw = await r.get(rkey)
    if raw:
        data = json.loads(raw)
        # Reject if same key is reused with different payload (prevents accidental collisions)
        if data.get("request_hash") and data["request_hash"] != req_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key reused with different request payload")
        if data.get("state") == "done":
            # replay stored response
            return JSONResponse(content=data.get("body"), status_code=int(data.get("status", 200)), headers=data.get("headers") or {})
        # processing
        raise HTTPException(status_code=409, detail="Request with this Idempotency-Key is still processing. Retry shortly.")

    # Acquire processing lock using SET NX
    processing_payload = {
        "state": "processing",
        "status": None,
        "headers": {"content-type": "application/json"},
        "body": None,
        "created_at": _iso_now(),
        "completed_at": None,
        "request_hash": req_hash,
    }
    ok = await r.set(rkey, json.dumps(processing_payload), ex=PROCESSING_TTL_SEC, nx=True)
    if not ok:
        # someone else won the race
        raise HTTPException(status_code=409, detail="Request with this Idempotency-Key is still processing. Retry shortly.")

    return (rkey, req_hash, body_bytes)

async def idempotency_store_result(redis_key: str, req_hash: str, *, status: int, body: dict, headers: Optional[dict] = None):
    r = await get_redis()
    payload = {
        "state": "done",
        "status": int(status),
        "headers": headers or {"content-type": "application/json"},
        "body": body,
        "created_at": None,  # not needed now
        "completed_at": _iso_now(),
        "request_hash": req_hash,
    }
    await r.set(redis_key, json.dumps(payload), ex=DONE_TTL_SEC)

async def idempotency_clear_key(redis_key: str):
    """Clear key on error"""
    try:
        r = await get_redis()
        await r.delete(redis_key)
    except Exception:
        pass
