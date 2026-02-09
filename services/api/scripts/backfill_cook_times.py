import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add api path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

from app.db import Base
from app.models import Recipe, RecipeStep, RecipeIngredient
from app.services.time_estimate import estimate_recipe_time
from app.settings import settings

def backfill_cook_times():
    print(f"Connecting to {settings.database_url}...")
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all recipes where total_minutes is NULL
        recipes = session.query(Recipe).filter(Recipe.total_minutes == None).all()
        print(f"Found {len(recipes)} recipes to backfill.")
        
        for recipe in recipes:
            total, source = estimate_recipe_time(recipe)
            recipe.total_minutes = total
            recipe.total_minutes_source = source
            print(f"Recipe {recipe.id} ('{recipe.title}'): {total}m ({source})")
            
        session.commit()
        print("Backfill complete.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    backfill_cook_times()
