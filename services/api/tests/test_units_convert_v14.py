"""
Tests for Unit Conversion Service (v14).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_convert_mass_simple():
    # 1 kg = 1000 g
    response = client.post("/api/units/convert", json={
        "qty": 1,
        "from_unit": "kg",
        "to_unit": "g"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["qty"] == 1000
    assert data["unit"] == "g"
    assert data["confidence"] == "high"
    assert data["is_approx"] is False

def test_convert_volume_simple():
    # 1 tbsp = 3 tsp (approx)
    # 1 tbsp = 14.7868 ml
    # 1 tsp = 4.92892 ml
    response = client.post("/api/units/convert", json={
        "qty": 1,
        "from_unit": "tbsp",
        "to_unit": "tsp"
    })
    assert response.status_code == 200
    data = response.json()
    # 14.7868 / 4.92892 = 3.0
    assert abs(data["qty"] - 3.0) < 0.01
    assert data["confidence"] == "high"

def test_convert_cross_flour():
    # 1 cup flour -> grams
    # 1 cup = 236.588 ml
    # Flour density = 0.593 g/ml
    # Expected g = 236.588 * 0.593 = 140.29
    
    response = client.post("/api/units/convert", json={
        "qty": 1,
        "from_unit": "cup",
        "to_unit": "g",
        "ingredient_name": "All Purpose Flour"
    })
    assert response.status_code == 200
    data = response.json()
    
    expected = 236.588 * 0.593
    assert abs(data["qty"] - expected) < 1.0 # Allow some float drift
    assert data["confidence"] == "medium" # or low depending on generic match
    assert data["is_approx"] is True

def test_convert_cross_water_default():
    # 1 cup "mystery liquid" -> grams
    # Density default = 1.0
    # Expected g = 236.588 * 1.0 = 236.588
    
    response = client.post("/api/units/convert", json={
        "qty": 1,
        "from_unit": "cup",
        "to_unit": "g",
        "ingredient_name": "Mystery Liquid",
        "force_cross_type": True
    })
    assert response.status_code == 200
    data = response.json()
    
    assert abs(data["qty"] - 236.588) < 0.1
    assert data["confidence"] == "none" # Default water density
    assert "density" in data["note"] or "approximated" in data["note"].lower()

def test_convert_synonyms():
    # "T" -> tbsp
    response = client.post("/api/units/convert", json={
        "qty": 2,
        "from_unit": "T",
        "to_unit": "tablespoons"
    })
    assert response.status_code == 200
    data = response.json()
    assert abs(data["qty"] - 2.0) < 0.001
    assert data["unit"] == "tablespoons" # it returns normalized or requested? 
    # Logic returns `norm_to` which is "tablespoons" (normalized from "tablespoons")
    
def test_normalization_plural():
    response = client.post("/api/units/convert", json={
        "qty": 100,
        "from_unit": "grams",
        "to_unit": "kg"
    })
    assert response.status_code == 200
    assert response.json()["qty"] == 0.1

def test_unknown_unit():
    response = client.post("/api/units/convert", json={
        "qty": 10,
        "from_unit": "glarps",
        "to_unit": "g"
    })
    assert response.status_code == 200
    data = response.json()
    # Should fail or return same with low confidence?
    # Logic: if not norm_from or not norm_to -> confidence low, is_approx True
    assert data["confidence"] == "low"
    assert "Unknown unit" in data["note"]
