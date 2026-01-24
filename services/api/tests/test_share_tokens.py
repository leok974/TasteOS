import pytest
from app.parsing.token_encoder import encode_recipe_token, decode_recipe_token

def test_token_encoder_logic():
    data = {"title": "Test", "ingredients": [{"name": "flour"}]}
    token = encode_recipe_token(data)
    
    assert token.startswith("tasteos-v1:")
    decoded = decode_recipe_token(token)
    assert decoded["title"] == "Test"
    assert decoded["ingredients"][0]["name"] == "flour"

def test_token_encoder_invalid():
    with pytest.raises(ValueError):
        decode_recipe_token("invalid-pantry-item")

def test_get_share_token_endpoint(client, workspace):
    # Seed a recipe first using ingest
    text = "Token Recipe\nIngredients: 1 banana"
    headers = {"X-Workspace-ID": workspace.slug}
    client.post("/api/recipes/ingest", json={"text": text}, headers=headers)
    
    # List to get ID
    recipes = client.get("/api/recipes", headers=headers).json()
    recipe_id = recipes[0]["id"]
    
    # Get Token
    response = client.get(f"/api/recipes/{recipe_id}/share-token", headers=headers)
    assert response.status_code == 200
    token = response.json()["token"]
    assert token.startswith("tasteos-v1:")

def test_ingest_share_token(client, workspace):
    # 1. Create token directly
    data = {
        "title": "Imported Token Recipe",
        "cuisines": ["Magic"],
        "ingredients": [{"name": "magic dust", "qty": 1, "unit": "tsp", "category": "spices"}],
        "steps": [{"step_index": 0, "title": "Poof", "bullets": ["Disappear"]}]
    }
    # We need to wrap it in "recipe" key because PortableRecipe structure expects it?
    # Let's check export_recipe in recipes.py... yes, it returns PortableRecipe which has 'recipe' field.
    # So the encoded data usually comes from export_recipe which is PortableRecipe.
    # Let's mock that structure.
    from app.share_schemas import PortableRecipeDetail
    
    # The dictionary expected by PortableRecipe input is { "schema_version": ..., "recipe": ... }
    full_payload = {
        "schema_version": "tasteos.recipe.v1",
        "recipe": data
    }
    
    token = encode_recipe_token(full_payload)
    
    # 2. Ingest it
    headers = {"X-Workspace-ID": workspace.slug}
    response = client.post(
        "/api/recipes/ingest",
        json={"text": token}, 
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"DEBUG: {response.text}")
        
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Imported Token Recipe"
    assert created["cuisines"] == ["Magic"]
    assert len(created["steps"]) == 1
