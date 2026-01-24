from fastapi import APIRouter

router = APIRouter()


@router.get("/ready")
def ready():
    return {"ok": True}
