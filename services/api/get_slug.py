from app.db import SessionLocal
from app.models import Workspace
from sqlalchemy import select

db = SessionLocal()()
ws = db.execute(select(Workspace)).scalars().first()
if ws:
    print(ws.slug)
db.close()
