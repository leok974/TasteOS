
import sys
import os
import re
from typing import Optional

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import SessionLocal
from app.models import Recipe, RecipeStep, RecipeIngredient
from app.core.ai_client import AIClient
from pydantic import BaseModel

class RepairedStep(BaseModel):
    text: str

def is_truncated(text: str) -> bool:
    if not text:
        return False
    # Check for ellipsis equivalents
    if text.strip().endswith("…") or text.strip().endswith("..."):
        return True
    
    # Check for short, incomplete sentences
    # e.g. "Add to Instant Pot: 1 cup water, 2 Tbsp Old Bay, and a lemon..." vs "Add to Instant Pot: 1 cup water, 2 Tbsp Old Bay, and a lemon"
    # Often truncations cut off mid-word or mid-sentence without punctuation
    
    clean = text.strip()
    if not clean: return False
    
    # Very short
    if len(clean) < 15:
        return False # Ignored in previous run, but actually many headers are short e.g. "Ingredeints". Let's assume headers are fine.
                     # Wait, user example: "Toss sliced beef" (header)
                     # Real truncation: "Toss the sliced beef in a bowl with cornstar…"
    
    # Ends with non-punctuation?
    last_char = clean[-1]
    if last_char not in ['.', '!', '?', ':', ')', '…']:
        # Suspect if it ends in a conjunction or preposition or looks cut off
        # e.g. "cut the"
        # But headers like "Step 1" don't have dots.
        # Heuristic: If it looks like a long sentence (>30 chars) and doesn't end in punctuation, it might be cut.
        if len(clean) > 30:
            return True
        
        # Or if it ends in common cut off words
        if clean.lower().split()[-1] in ['and', 'the', 'with', 'for', 'to', 'in', 'of', 'a']:
            return True

    return False

def fix_recipes():
    print("Initializing Database...")
    db = SessionLocal()()
    
    print("Checking for truncated steps...")
    
    # We look for steps that end in "…" or "..."
    # SQLAlchemy like check
    
    # Get all recipes first (naive but safe for small DB)
    recipes = db.query(Recipe).all()
    
    ai = AIClient.get_instance()
    
    if not ai.is_available():
        print("AI Client not available (check GEMINI_API_KEY). Cannot repair.")
        return

    count = 0
    
    for recipe in recipes:
        if not recipe.steps:
            continue
            
        dirty = False
        print(f"Checking {recipe.title}...")
        
        # Collect ingredients for context
        ing_list = ", ".join([f"{i.qty or ''} {i.unit or ''} {i.name}" for i in recipe.ingredients])
        
        for step in recipe.steps:
            # Check bullets
            new_bullets = []
            step_dirty = False
            
            # The current parsing logic puts the instruction in 'bullets' list usually as a single item
            if step.bullets:
                for b in step.bullets:
                    if is_truncated(b):
                        print(f"  -> Found truncated bullet in step {step.step_index}: '{b}'")
                        
                        prompt = f"""
                        You are a culinary data repair agent.
                        The recipe is "{recipe.title}".
                        Ingredients: {ing_list}
                        
                        The step instruction was truncated during import: "{b}"
                        Title of step (context): "{step.title}"
                        Previous step (context): "{recipe.steps[step.step_index-2].title if step.step_index > 1 else 'None'}"
                        
                        Please reconstruct the full, natural, imperative instruction for this step based on the truncated fragment and context.
                        Do not interpret '...' literally. Complete the sentence logically.
                        Just return the text.
                        """
                        
                        try:
                            repaired_obj = ai.generate_content_sync(
                                prompt=prompt,
                                response_model=RepairedStep
                            )
                            if repaired_obj:
                                print(f"     ✅ Repaired: '{repaired_obj.text}'")
                                new_bullets.append(repaired_obj.text)
                                step_dirty = True
                                dirty = True
                            else:
                                print("     ❌ AI failed to repair, keeping original.")
                                new_bullets.append(b)
                        except Exception as e:
                            print(f"     ⚠ Error repairing: {e}")
                            new_bullets.append(b)
                    else:
                        new_bullets.append(b)
                
                if step_dirty:
                    step.bullets = new_bullets
                    # Also check title? Sometimes title is just "Step 1" or fragment
                    # But user complained about the body.
        
        if dirty:
            print(f"  💾 Saving changes for {recipe.title}")
            db.add(recipe) # Cascade updates steps
            db.commit()
            count += 1
            
    print(f"Repair complete. Updated {count} recipes.")

def fix_steps_ai():
    fix_recipes()

if __name__ == "__main__":
    # Ensure stdout is flushed immediately so logs appear in docker exec
    sys.stdout.reconfigure(line_buffering=True)
    fix_steps_ai()
