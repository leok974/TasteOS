import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sqlite3
import json

# Register adapters for SQLite to handle list/dict as JSON
sqlite3.register_adapter(list, json.dumps)
sqlite3.register_adapter(dict, json.dumps)


from app.main import app
from app.db import Base, get_db
from app.models import Workspace

# --- Test Database Setup ---

from sqlalchemy.types import ARRAY, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(ARRAY, 'sqlite')
def compile_array(element, compiler, **kw):
    return "JSON_ARRAY"

@compiles(JSONB, 'sqlite')
def compile_jsonb(element, compiler, **kw):
    return "JSON"
    
# Register adapters for SQLite to handle list/dict as JSON
sqlite3.register_adapter(list, json.dumps)
sqlite3.register_adapter(dict, json.dumps)
# Register converter for our custom type ONLY to avoid double-decoding standard JSON
sqlite3.register_converter("JSON_ARRAY", json.loads)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Note: check_same_thread is needed for SQLite. 
# We also add detect_types to enable the converter.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "detect_types": sqlite3.PARSE_DECLTYPES
    },
    poolclass=StaticPool # Important for in-memory to share connection across threads/sessions if needed
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True, scope="session")
def _set_test_env():
    # Use a temp SQLite file for unit tests (stable across connections).
    # Note: We are using ./test.db explicitly in engine above, so this might be redundant or conflicting if we want random temp file.
    # The list code had this. Let's keep it but ensure engine uses it?
    # Actually the code above uses "sqlite:///./test.db". 
    # Let's align them.
    os.environ["AI_MODE"] = "mock"
    yield

@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """Test client with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def db_session():
    """Direct database session for setup."""
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def workspace(db_session):
    """Create a test workspace."""
    # Use a valid UUID to ensure compatibility with GUID types
    ws = Workspace(id="00000000-0000-0000-0000-000000000000", slug="test", name="Test Workspace")
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)
    return ws

import fakeredis
import fakeredis.aioredis
from app.infra import redis_client

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    server = fakeredis.FakeServer()
    # Create fake clients sharing the same server
    async_redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    sync_redis = fakeredis.FakeRedis(server=server, decode_responses=True)
    
    # Force the clients into the infra module
    redis_client._redis_async = async_redis
    redis_client._redis_sync = sync_redis
    
    yield
    
    # Cleanup
    redis_client._redis_async = None
    redis_client._redis_sync = None
