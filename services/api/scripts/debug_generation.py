
import sys
import os
import asyncio

# Setup path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import SessionLocal
from app import models, schemas
from app.routers.grocery import generate_grocery_list_v3
from sqlalchemy import select
from sqlalchemy.orm import Session

# Mock dependency override for generate_grocery_list_v3 would be hard because it uses Depends(get_db)
# Instead, we will call the logic directly or manually instantiate.

def test_generation():
    db_maker = SessionLocal()
    db = db_maker()
    try:
        # 1. Fetch a recipe that has ingredients
        # Join ingredients to ensure we get one with data
        # Note: RecipeIngredient table implies we need to join
        stmt = select(models.Recipe).join(models.Recipe.ingredients).limit(1)
        recipe = db.execute(stmt).scalars().first()
        
        if not recipe:
            print("No recipes with ingredients found in DB. Seeding one...")
            # Create dummy recipe with ingredients?
            # Or just warn
            return

        print(f"Testing with Recipe: {recipe.title} (ID: {recipe.id})")
        
        # 2. Check its ingredients
        print("Ingredients (Raw DB):")
        for ing in recipe.ingredients:
            print(f" - Name: '{ing.name}', Qty: {ing.qty}, Unit: {ing.unit}")

        # 3. Simulate request
        request = schemas.GroceryGenerateRequestV3(
            title="Test Generation",
            recipe_ids=[recipe.id]
        )
        
        # We need a workspace context. Fetch first workspace.
        workspace = db.execute(select(models.Workspace)).scalars().first()
        if not workspace:
            print("No workspace found.")
            return
            
        print(f"Using Workspace: {workspace.id}")
        print(f"Recipe Workspace: {recipe.workspace_id}")
        
        if str(recipe.workspace_id) != str(workspace.id):
            print("MISMATCH! Recipe does not belong to test workspace. Skipping test logic for this recipe.")
            # Let's fix it by using the recipe's workspace?
            # Or fetching workspace BY ID?
            stmt_ws = select(models.Workspace).where(models.Workspace.id == recipe.workspace_id)
            ws_correct = db.execute(stmt_ws).scalar_one_or_none()
            if ws_correct:
                workspace = ws_correct
                print(f"Updated Workspace to match Recipe: {workspace.id}")
            else:
                 print("Cannot find workspace for recipe!")
                 return
        
        # Call the function directly? 
        # generate_grocery_list_v3 expects (request, workspace, db)
        
        try:
            result_list = generate_grocery_list_v3(request, workspace, db)
            print(f"\nGenerated List: {result_list.title} (ID: {result_list.id})")
            print(f"Items Count: {len(result_list.items)}")
            for item in result_list.items:
                print(f" - {item.display} ({item.quantity} {item.unit}) [Key: {item.key}]")
                
        except Exception as e:
            print(f"Error during generation: {e}")
            import traceback
            traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    test_generation()
