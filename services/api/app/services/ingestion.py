from sqlalchemy.orm import Session
from app.parsing import RuleBasedParser, ParsedRecipe
from app.models import Recipe, RecipeIngredient, RecipeStep
from app.schemas import RecipeCreate
import uuid

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        # We can inject different parsers here (LLM vs RuleBased)
        self.parser = RuleBasedParser()

    def ingest_text(self, workspace_id: str, text: str, hints: dict = None) -> Recipe:
        parsed: ParsedRecipe = self.parser.parse(text, hints)
        
        # Create Recipe
        recipe_id = str(uuid.uuid4())
        # Truncate title or fallback
        title = parsed.title[:200] if parsed.title else "Untitled Paste"
        
        recipe = Recipe(
            id=recipe_id,
            workspace_id=workspace_id,
            title=title,
            servings=parsed.servings,
            time_minutes=parsed.time_minutes,
            cuisines=parsed.cuisines,
            tags=parsed.tags,
            notes="Imported from text."
        )
        self.db.add(recipe)
        
        # Add Ingredients
        for i, ing in enumerate(parsed.ingredients):
            self.db.add(RecipeIngredient(
                id=str(uuid.uuid4()),
                recipe_id=recipe_id,
                name=ing.name[:200],
                qty=ing.qty,
                unit=ing.unit,
                category=ing.category
            ))
            
        # Add Steps
        for i, step in enumerate(parsed.steps):
            self.db.add(RecipeStep(
                id=str(uuid.uuid4()),
                recipe_id=recipe_id,
                step_index=step.step_index,
                title=step.title[:200],
                bullets=step.bullets,
                minutes_est=step.minutes_est
            ))
            
        self.db.commit()
        self.db.refresh(recipe)
        return recipe
