import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_density_lifecycle():
    # 1. Setup clean state happens via fixture override in main test suite usually, 
    # but here we rely on the workspace from default deps mock or similar.
    # Note: Authenticated depends will need a workspace. 
    # The default TestClient might need a header if the app enforces it.
    # TasteOS "local" mode usually works without auth for now.
    
    # 2. Put (Create) Density
    # Flour: 120g / cup
    # 1 cup = 236.588 ml
    # Density = 120 / 236.588 ~ 0.507
    
    upsert_load = {
        "ingredient_name": "All-Purpose Flour",
        "density": {
            "value": 120,
            "per_unit": "cup"
        }
    }
    
    res = client.put("/api/units/densities", json=upsert_load)
    assert res.status_code == 200
    data = res.json()
    assert data["ingredient_key"] == "all purpose flour"
    assert 0.50 < data["density_g_per_ml"] < 0.51
    density_id = data["id"]
    
    # 3. List to verify
    res = client.get("/api/units/densities?query=flour")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    # Find our item
    found = next((i for i in items if i["id"] == density_id), None)
    assert found is not None
    assert found["ingredient_key"] == "all purpose flour"
    
    # 4. Conversion Usage
    # Convert 1 cup flour -> g
    # Should get exactly 120g (since we defined 120g/cup)
    conv_load = {
        "qty": 1,
        "from_unit": "cup",
        "to_unit": "g",
        "ingredient_name": "All-Purpose Flour" # Same name to match key
    }
    res = client.post("/api/units/convert", json=conv_load)
    assert res.status_code == 200
    cdata = res.json()
    assert 119.9 < cdata["qty"] < 120.1
    # Check flags for high confidence
    assert cdata["confidence"] == "high" 
    assert cdata["is_approx"] == False
    assert "override" in cdata["note"].lower()
    
    # 5. Delete
    res = client.delete(f"/api/units/densities/{density_id}")
    assert res.status_code == 200
    
    # 6. Fallback Usage (should be approx after delete)
    conv_load["force_cross_type"] = True # Force it if generic table is needed
    res = client.post("/api/units/convert", json=conv_load)
    assert res.status_code == 200
    cdata = res.json()
    # Generic flour density is ~0.593 (from unit_conversion.py) -> ~140g per cup
    # 120g is what we set. Common is heavier.
    assert cdata["qty"] > 130 # 140ish
    assert cdata["is_approx"] == True 
    assert cdata["confidence"] != "high" # medium or low

def test_density_validation():
    # Test sane bounds
    res = client.put("/api/units/densities", json={
        "ingredient_name": "Lead",
        "density": { "value": 5000, "per_unit": "cup" } # Way too heavy
    })
    assert res.status_code == 400
