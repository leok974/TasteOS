import os
import random
import logging
from typing import List, Optional
from pydantic import BaseModel
from ..core.ai_client import ai_client
from ..settings import settings

logger = logging.getLogger("tasteos.ai")

class SubstitutionSuggestion(BaseModel):
    substitute: str
    instruction: str
    confidence: str  # high, medium, low
    impact: str = "close"  # exact, close, different
    pantry_match: Optional[dict] = None  # {item: str, quantity: str}
    source: str = "ai" # ai or heuristic

class MacroAnalysis(BaseModel):
    calories_range: dict  # {min: int, max: int}
    protein_range: Optional[dict] = None
    confidence: str  # high, medium, low
    disclaimer: str
    tags: List[str] = []
    source: str = "ai" # ai or heuristic

class AIService:
    def __init__(self):
        self.mode = settings.ai_mode

    def suggest_substitute(self, ingredient: str, pantry_items: List[str], context: str) -> SubstitutionSuggestion:
        if self.mode == "mock":
            return self._mock_substitute(ingredient, pantry_items)
        
        # Real AI implementation with Fallback
        try:
             # Construct prompt
             prompt = f"""
             You are a smart cooking assistant.
             Suggest the best substitute for '{ingredient}' for a recipe context: "{context}".
             
             Available Pantry Items: {', '.join(pantry_items) if pantry_items else 'None provided'}
             
             Priority:
             1. Matches from pantry items (exact or close).
             2. Common household substitutes.
             
             Output JSON matching the schema.
             pantry_match should be populated if the substitute is in the pantry list.
             """
             
             result = ai_client.generate_content_sync(
                 prompt=prompt,
                 response_model=SubstitutionSuggestion
             )
             
             if result:
                 result.source = "ai"
                 return result
                 
             logger.warning("AI substitution failed, falling back to heuristic")
             
        except Exception as e:
            logger.error(f"Error in suggest_substitute: {e}")
            
        return self._mock_substitute(ingredient, pantry_items)

    def summarize_macros(self, title: str, ingredients: List[str]) -> MacroAnalysis:
        if self.mode == "mock":
             return self._mock_macros(title)
        
        # Real AI Implementation with Fallback
        try:
            prompt = f"""
            Analyze the nutrition for this recipe:
            Title: {title}
            Ingredients: {', '.join(ingredients)}
            
            Provide:
            1. Estimated calorie range per serving (min/max).
            2. Estimated protein range per serving (min/max).
            3. Confidence level (high/medium/low).
            4. Relevant health tags (e.g. High Protein, Low Carb, Gluten Free, Vegan).
            5. A short 1-sentence disclaimer.
            
            Output JSON matching schema.
            """
            
            result = ai_client.generate_content_sync(
                prompt=prompt,
                response_model=MacroAnalysis
            )
            
            if result:
                result.source = "ai"
                return result
            
            logger.warning("AI macro analysis failed, falling back to heuristic")
            
        except Exception as e:
            logger.error(f"Error in summarize_macros: {e}")
            
        return self._mock_macros(title)

    def _normalize_ingredient(self, ingredient: str) -> str:
        """Normalize ingredient name for matching."""
        name = ingredient.lower().strip()
        # Simple singularization
        if name.endswith('s') and not name.endswith('ss'):
            name = name[:-1]
        return name

    def _mock_macros(self, title: str) -> MacroAnalysis:
         # HEURISTICS based on title words
         title_lower = title.lower()
         
         analysis = None
         if "salad" in title_lower:
             analysis = MacroAnalysis(
                 calories_range={"min": 200, "max": 400},
                 protein_range={"min": 5, "max": 15},
                 confidence="medium",
                 disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                 tags=["low-calorie", "high-fiber"]
             )
         elif "steak" in title_lower or "beef" in title_lower:
             analysis = MacroAnalysis(
                 calories_range={"min": 500, "max": 700},
                 protein_range={"min": 35, "max": 50},
                 confidence="medium",
                 disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                 tags=["high-protein"]
             )
         elif "cake" in title_lower or "cookie" in title_lower:
             analysis = MacroAnalysis(
                 calories_range={"min": 350, "max": 550},
                 confidence="low",
                 disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                 tags=["high-carb", "sweet"]
             )
         else:
             analysis = MacroAnalysis(
                 calories_range={"min": 400, "max": 600},
                 confidence="low",
                 disclaimer="Estimates based on ingredient heuristics. For precise values, use nutrition database.",
                 tags=["balanced"]
             )
         
         analysis.source = "heuristic"
         return analysis

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
                     pantry_match={"item": "milk, vinegar", "quantity": "available"},
                     source="heuristic"
                 )
        
        if "egg" in ingredient_normalized:
            if any("flax" in p for p in pantry_normalized):
                 return SubstitutionSuggestion(
                     substitute="Flax Egg", 
                     instruction="Mix 1 tbsp ground flaxseed with 3 tbsp water.",
                     confidence="medium",
                     impact="close",
                     pantry_match={"item": "flaxseed", "quantity": "available"},
                     source="heuristic"
                 )
        
        # Generic fallback
        return SubstitutionSuggestion(
            substitute=f"Check pantry for similar items",
            instruction="Consider texture and flavor profile when substituting.",
            confidence="low",
            impact="different",
            source="heuristic"
        )

ai_service = AIService()
