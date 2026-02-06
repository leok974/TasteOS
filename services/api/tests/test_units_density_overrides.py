import pytest
from app.models import IngredientDensityOverride
from app.services.ingredient_normalize import normalize_ingredient_key

@pytest.fixture
def auth_headers(workspace):
    return {"X-Workspace-Id": workspace.id}

def test_density_override_crud(client, auth_headers, workspace):
    """Test creating, reading, and updating density overrides."""
    
    # 1. Create Override (1 cup = 120g)
    # 120g / 236.588 ml = 0.507 g/ml
    payload = {
        "ingredient_name": "My Special Flour",
        "density": {
            "mass_value": 120,
            "mass_unit": "g",
            "vol_value": 1,
            "vol_unit": "cup"
        }
    }
    
    res = client.put(
        "/api/units/densities",
        json=payload,
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "My Special Flour"
    assert 0.50 < data["density_g_per_ml"] < 0.51
    
    # 2. List Overrides (Search)
    res = client.get(
        "/api/units/densities?query=flour",
        headers=auth_headers
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert items[0]["ingredient_key"] == normalize_ingredient_key("My Special Flour")

def test_conversion_with_override(client, auth_headers, workspace):
    """Test that conversion endpoint uses the override."""
    
    # 1. Create Override for "Heavy Metal" (1 ml = 10g) -> Density 10.0
    # Wait, 10.0 is outside sane range (5.0). Let's use "Sand" (1ml = 2g) -> Density 2.0
    
    payload = {
        "ingredient_name": "Heavy Sand",
        "density": {
            "mass_value": 200,
            "mass_unit": "grams",
            "vol_value": 100,
            "vol_unit": "ml"
        }
    }
    client.put("/api/units/densities", json=payload, headers=auth_headers)
    
    # 2. Convert Mass to Volume
    # 500g of Heavy Sand. 
    # Density = 2g/ml. 
    # Volume = 500 / 2 = 250 ml.
    
    conv_payload = {
        "qty": 500,
        "from_unit": "g",
        "to_unit": "ml",
        "ingredient_name": "Heavy Sand"
    }
    
    res = client.post("/api/units/convert", json=conv_payload, headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    
    assert data["qty"] == 250.0
    assert data["confidence"] == "high"
    assert data["is_approx"] == False # Override should be precise
    
def test_override_insane_values(client, auth_headers):
    """Test that insane density values are rejected."""
    # Lead: 11 g/ml
    payload = {
        "ingredient_name": "Lead",
        "density": {
            "mass_value": 11,
            "mass_unit": "g",
            "vol_value": 1,
            "vol_unit": "ml"
        }
    }
    res = client.put("/api/units/densities", json=payload, headers=auth_headers)
    assert res.status_code == 400
    assert "sane range" in res.json()["detail"]
