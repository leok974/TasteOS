import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_smart_auto_metric():
    # US Cup -> Metric
    # Expected: 1 cup (~237ml) -> < 1000ml -> ml
    response = client.post("/api/units/convert", json={
        "qty": 1,
        "from_unit": "cup",
        "target_system": "metric"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["unit"] == "ml"
    assert 230 < data["qty"] < 240

def test_smart_auto_us():
    # 5 ml (1 tsp) -> US
    # Expected: "tsp"
    response = client.post("/api/units/convert", json={
        "qty": 5,
        "from_unit": "ml",
        "target_system": "us_customary"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["unit"] == "tsp"
    
def test_smart_auto_metric_large():
    # 4 Cups (~950ml) -> Metric 
    # Logic: < 1000ml -> ml. 
    # Let's try 5 Cups (~1180ml) -> l
    response = client.post("/api/units/convert", json={
        "qty": 5,
        "from_unit": "cup",
        "target_system": "metric"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["unit"] == "l"
    assert 1.1 < data["qty"] < 1.2
