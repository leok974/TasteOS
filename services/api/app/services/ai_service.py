import os
import random
from typing import List, Optional
from pydantic import BaseModel

class SubstitutionSuggestion(BaseModel):
    substitute: str
    instruction: str
    confidence: str # high, medium, low

class AIService:
    def __init__(self):
        self.mode = os.getenv("AI_MODE", "mock")

    def suggest_substitute(self, ingredient: str, pantry_items: List[str], context: str) -> SubstitutionSuggestion:
        if self.mode == "mock":
            return self._mock_substitute(ingredient, pantry_items)
        
        # Real AI implementation (Placeholder for future)
        # return self._call_llm(ingredient, pantry_items, context)
        return self._mock_substitute(ingredient, pantry_items)

    def summarize_macros(self, title: str, ingredients: List[str]) -> dict:
        if self.mode == "mock":
             # HEURISTICS based on title words
             title_lower = title.lower()
             if "salad" in title_lower:
                 return {"summary": "Low Calorie, High Fiber", "calories": "~300"}
             if "steak" in title_lower or "beef" in title_lower:
                 return {"summary": "High Protein", "calories": "~600"}
             if "cake" in title_lower or "cookie" in title_lower:
                 return {"summary": "High Carb, Sweet Treat", "calories": "~450"}
             return {"summary": "Balanced Meal", "calories": "~500"}
        
        # Real AI implementation (Placeholder for future)      
        # For now, return mock data even in real mode
        title_lower = title.lower()
        if "steak" in title_lower or "beef" in title_lower:
            return {"summary": "High Protein", "calories": "~600"}
        return {"summary": "Balanced Meal", "calories": "~500"}

    def _mock_substitute(self, ingredient: str, pantry_items: List[str]) -> SubstitutionSuggestion:
        # Simple heuristic or random mock
        ingredient_lower = ingredient.lower()
        
        # Heuristics
        if "buttermilk" in ingredient_lower:
            if any("milk" in p.lower() for p in pantry_items) and any("vinegar" in p.lower() for p in pantry_items):
                 return SubstitutionSuggestion(
                     substitute="Milk + Vinegar", 
                     instruction="Mix 1 cup milk with 1 tbsp vinegar and let sit for 5 mins.",
                     confidence="high"
                 )
        
        if "egg" in ingredient_lower:
            if any("flax" in p.lower() for p in pantry_items):
                 return SubstitutionSuggestion(
                     substitute="Flax Egg", 
                     instruction="Mix 1 tbsp ground flaxseed with 3 tbsp water.",
                     confidence="medium"
                 )
        
        # Generic fallback
        return SubstitutionSuggestion(
            substitute=f"Mock Substitute for {ingredient}",
            instruction="This is a mock suggestion. Ensure AI_MODE is set to 'real' for actual inference.",
            confidence="low"
        )

ai_service = AIService()
