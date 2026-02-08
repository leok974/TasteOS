import os
import random
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
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

class RecipeTipsResponse(BaseModel):
    tips: List[str]
    food_safety: List[str]
    confidence: str  # high, medium, low
    source: str = "ai"  # ai or heuristic

class DraftYield(BaseModel):
    servings: int
    unit: str

class DraftIngredient(BaseModel):
    item: str
    quantity: Optional[float]
    unit: Optional[str]
    section: str
    notes: Optional[str]

class DraftStep(BaseModel):
    title: str = Field(description="SHORT LABEL ONLY (2-5 words). Not a full sentence. No period.", max_length=30, min_length=2)
    bullets: List[str] = Field(description="Checklist items. Min 1. Each max 120 chars.", min_items=1, max_items=8)
    minutes: Optional[int] = Field(None, description="Estimated time for this step.", ge=0, le=240)

class DraftRecipe(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    yield_data: DraftYield = Field(alias="yield")
    total_time_minutes: int
    ingredients: List[DraftIngredient]
    steps: List[DraftStep]
    tags: List[str]
    notes: Optional[str]

class RecipeDraftResponse(BaseModel):
    assistant_message: str
    recipe_json: DraftRecipe
    suggested_label: str

class AIService:
    def __init__(self):
        self.mode = settings.ai_mode

    def generate_recipe_draft(self, message: str, context_recipe: Optional[dict] = None) -> RecipeDraftResponse:
        """Generate a structured recipe draft from a user request."""
        
        # System Prompt
        system_prompt = """
        You are TasteOS Chef. Output ONLY valid JSON matching the provided schema. No markdown, no prose, no code fences.

        CRITICAL STEP RULES (NON-NEGOTIABLE):
        - steps[].title must be a SHORT LABEL (2–5 words). NOT a sentence. NO period. NO colon.
        - steps[].bullets must be a checklist array. Prefer 2–6 bullets. Each bullet is one action.
        - Do NOT put instructions in the title. If you wrote a sentence title, move it to bullets[0] and replace title with a label like "Prep", "Mix", "Cook", "Bake", "Serve".
        - No duplicate text between title and bullets.
        - If any bullet contains multiple sentences, split into multiple bullets.
        - Never return empty bullets. If you cannot produce bullets, produce at least one bullet with the full instruction.

        FORMAT STYLE:
        - Bullets start with a verb (e.g. "Slice…", "Mix…", "Bake…").
        - Keep bullets concise (<= 120 chars).
        - Steps should match how a human would cook: group actions into logical phases (prep, cook, finish).

        Return JSON ONLY.
        """
        
        user_content = f"Request: {message}"
        if context_recipe:
            user_content += f"\n\nBase Recipe Context (JSON): {context_recipe}"
            
        if self.mode == "mock":
            return self._mock_recipe_draft(message, context_recipe)

        try:
            # Call Gemini
            response = ai_client.generate_content_sync(
                prompt=user_content,
                system_instruction=system_prompt,
                response_model=RecipeDraftResponse
            )
            
            if not response:
                raise ValueError("Empty response from AI service")
                
            return self._sanitize_draft(response)
            
        except Exception as e:
            logger.error(f"Recipe draft generation failed: {e}")
            raise e

    def _sanitize_draft(self, draft: RecipeDraftResponse) -> RecipeDraftResponse:
        """Sanitize markdown artifacts from AI text."""
        from ..core.text import clean_md, normalize_step_structure

        if draft.recipe_json.title:
            draft.recipe_json.title = clean_md(draft.recipe_json.title)
        
        if draft.recipe_json.steps:
            for step in draft.recipe_json.steps:
                # 1. Clean basic markdown
                step.title = clean_md(step.title)
                step.bullets = [clean_md(b) for b in step.bullets]
                
                # 2. Enforce Salsa Verde Structure via Normalizer
                # Using the centralized normalizer ensures Preview matches DB
                normalized = normalize_step_structure(step.title, step.bullets)
                step.title = normalized["title"]
                step.bullets = normalized["bullets"]
            
        return draft

    def _mock_recipe_draft(self, message: str, context_recipe: Optional[dict]) -> RecipeDraftResponse:
        """Return a dummy recipe for testing."""
        return RecipeDraftResponse(
            assistant_message=f"Here is a mock draft for: {message}",
            suggested_label="Mock Version",
            recipe_json={
                "title": "Mock Recipe",
                "yield": {"servings": 4, "unit": "servings"},
                "ingredients": [
                    {"section": "Main", "quantity": 1, "unit": "cup", "item": "mock ingredient"}
                ],
                "steps": [
                    {
                        "title": "Mix ingredients",
                        "bullets": ["Combine flour and sugar", "Whisk until smooth"],
                        "minutes": 5
                    },
                    {
                        "title": "Cook",
                        "bullets": ["Heat pan", "Fry for 5 mins"],
                        "minutes": 10
                    }
                ],
                "total_time_minutes": 15
            }
        )

    def generate_tips(self, recipe_title: str, ingredients: List[str], scope: str) -> RecipeTipsResponse:
        """Generate storage or reheat tips for a recipe."""
        if self.mode == "mock":
            return self._mock_tips(scope)

        context_text = f"Recipe: {recipe_title}\nIngredients: {', '.join(ingredients)}"
        prompt_scope = "storage and shelf life" if scope == "storage" else "reheating instructions"
        
        prompt = f"""
        You are a food safety expert. Provide 3 specific {prompt_scope} tips for this recipe.
        Also provide 1 important food safety warning if applicable.
        
        {context_text}
        
        Return JSON format:
        {{
            "tips": ["tip1", "tip2", "tip3"],
            "food_safety": ["warning1"],
            "confidence": "high"
        }}
        """
        
        try:
            response = ai_client.generate_json(prompt, response_model=RecipeTipsResponse)
            if response:
                return response
            raise Exception("Empty AI response")
        except Exception as e:
            logger.error(f"AI Tips failed: {e}")
            return self._heuristic_tips(scope)

    def _mock_tips(self, scope: str) -> RecipeTipsResponse:
        return self._heuristic_tips(scope, source="mock")

    def _heuristic_tips(self, scope: str, source: str = "heuristic") -> RecipeTipsResponse:
        if scope == "storage":
            return RecipeTipsResponse(
                tips=[
                    "Store in an airtight container in the refrigerator.",
                    "Consume within 3-4 days.",
                    "Label with datestamp."
                ],
                food_safety=["Do not leave at room temperature for > 2 hours."],
                confidence="medium",
                source=source
            )
        else: # reheat
            return RecipeTipsResponse(
                tips=[
                    "Reheat until internal temperature reaches 165°F (74°C).",
                    "Add a splash of water or broth to restore moisture.",
                    "Cover while reheating to prevent drying out."
                ],
                food_safety=["Ensure food is steaming hot throughout."],
                confidence="medium",
                source=source
            )

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
