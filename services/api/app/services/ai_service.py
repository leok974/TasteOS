import os
import random
from typing import List, Optional
from pydantic import BaseModel

class SubstitutionSuggestion(BaseModel):
    substitute: str
    instruction: str
    confidence: str  # high, medium, low
    impact: str = "close"  # exact, close, different
    pantry_match: Optional[dict] = None  # {item: str, quantity: str}

class MacroAnalysis(BaseModel):
    calories_range: dict  # {min: int, max: int}
    protein_range: Optional[dict] = None
    confidence: str  # high, medium, low
    disclaimer: str
    tags: List[str] = []

class AIService:
    def __init__(self):
        self.mode = os.getenv("AI_MODE", "mock")

    def suggest_substitute(self, ingredient: str, pantry_items: List[str], context: str) -> SubstitutionSuggestion:
        if self.mode == "mock":
            return self._mock_substitute(ingredient, pantry_items)
        
        # Real AI implementation (Placeholder for future)
        return self._mock_substitute(ingredient, pantry_items)

    def summarize_macros(self, title: str, ingredients: List[str]) -> MacroAnalysis:
        if self.mode == "mock":
             # HEURISTICS based on title words
             title_lower = title.lower()
             
             if "salad" in title_lower:
                 return MacroAnalysis(
                     calories_range={"min": 200, "max": 400},
                     protein_range={"min": 5, "max": 15},
                     confidence="medium",
                     disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                     tags=["low-calorie", "high-fiber"]
                 )
             if "steak" in title_lower or "beef" in title_lower:
                 return MacroAnalysis(
                     calories_range={"min": 500, "max": 700},
                     protein_range={"min": 35, "max": 50},
                     confidence="medium",
                     disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                     tags=["high-protein"]
                 )
             if "cake" in title_lower or "cookie" in title_lower:
                 return MacroAnalysis(
                     calories_range={"min": 350, "max": 550},
                     confidence="low",
                     disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                     tags=["high-carb", "sweet"]
                 )
             
             return MacroAnalysis(
                 calories_range={"min": 400, "max": 600},
                 confidence="low",
                 disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                 tags=["balanced"]
             )
        
        # Real AI implementation
        return MacroAnalysis(
            calories_range={"min": 400, "max": 600},
            confidence="low",
            disclaimer="AI analysis not available. Enable AI_MODE for detailed analysis.",
            tags=[]
        )

    def _normalize_ingredient(self, ingredient: str) -> str:
        """Normalize ingredient name for matching."""
        name = ingredient.lower().strip()
        # Simple singularization
        if name.endswith('s') and not name.endswith('ss'):
            name = name[:-1]
        return name

    def _mock_substitute(self, ingredient: str, pantry_items: List[str]) -> SubstitutionSuggestion:
        # Normalize for matching
        ingredient_normalized = self._normalize_ingredient(ingredient)
        pantry_normalized = [self._normalize_ingredient(p) for p in pantry_items]
        
        # Heuristics with pantry awareness
        if "buttermilk" in ingredient_normalized:
            if any("milk" in p for p in pantry_normalized) and any("vinegar" in p for p in pantry_normalized):
                 return SubstitutionSuggestion(
                     substitute="Milk + Vinegar", 
                     instruction="Mix 1 cup milk with 1 tbsp vinegar and let sit for 5 mins.",
                     confidence="high",
                     impact="exact",
                     pantry_match={"item": "milk, vinegar", "quantity": "available"}
                 )
        
        if "egg" in ingredient_normalized:
            if any("flax" in p for p in pantry_normalized):
                 return SubstitutionSuggestion(
                     substitute="Flax Egg", 
                     instruction="Mix 1 tbsp ground flaxseed with 3 tbsp water.",
                     confidence="medium",
                     impact="close",
                     pantry_match={"item": "flaxseed", "quantity": "available"}
                 )
        
        # Generic fallback
        return SubstitutionSuggestion(
            substitute=f"Check pantry for similar items",
            instruction="Consider texture and flavor profile when substituting.",
            confidence="low",
            impact="different"
        )

ai_service = AIService()
