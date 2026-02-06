from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone
import json
import logging
import hashlib

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from ..models import CookSession, Recipe, RecipeNoteEntry
from ..core.ai_client import ai_client
from ..settings import settings
from .ai_service import AIService # Reuse heuristic helpers if needed

logger = logging.getLogger("tasteos.cook_assist")

# --- Internal Schemas (sent to AI) ---

class TimerSuggestion(BaseModel):
    label: str
    seconds: int
    rationale: str

class SafetyFlags(BaseModel):
    contains_food_safety: bool
    allergens: List[str]

class CookStepHelpAIResponse(BaseModel):
    """Structured output expected from Gemini"""
    answer_md: str
    bullets: List[str]
    confidence: Literal["high", "medium", "low"]
    safety: SafetyFlags
    timer_suggestions: List[TimerSuggestion]

# --- External Schemas (API IO) ---

class CookHelpContext(BaseModel):
    user_notes: Optional[str] = None
    equipment: List[str] = []
    servings_target: Optional[int] = None

class CookHelpOptions(BaseModel):
    mode: Literal["quick", "detailed"] = "quick"
    temperature_unit: Literal["F", "C"] = "F"

class CookStepHelpRequest(BaseModel):
    step_index: int
    question: str
    context: Optional[CookHelpContext] = None
    options: Optional[CookHelpOptions] = None

class HelpCitation(BaseModel):
    type: Literal["recipe_step", "note", "general"]
    step_index: Optional[int] = None
    note_id: Optional[str] = None
    text: Optional[str] = None

class CookStepHelpResponse(BaseModel):
    answer_md: str
    bullets: List[str]
    confidence: Literal["high", "medium", "low"]
    safety: SafetyFlags
    citations: List[HelpCitation]
    source: Literal["ai", "heuristic"]
    timer_suggestion: Optional[TimerSuggestion] = None
    ai_error: Optional[str] = None

class CookAssistHelpService:
    def __init__(self):
        pass

    async def get_step_help(
        self, 
        db: Session, 
        session_id: str, 
        req: CookStepHelpRequest, 
        workspace_id: str
    ) -> CookStepHelpResponse:
        
        # 1. Fetch Context
        session = db.query(CookSession).filter(CookSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        recipe = db.query(Recipe).filter(Recipe.id == session.recipe_id).first()
        if not recipe:
            raise ValueError("Recipe not found")

        # 2. Check Rate Limit (TODO using Redis, skipping for now per instruction to prioritize logic)
        # self._check_rate_limit(workspace_id)

        # 3. Check Cache (TODO using Redis)
        # cache_key = self._build_cache_key(...)
        # cached = self._get_from_cache(cache_key)
        # if cached: return cached

        # 4. Build AI Context
        prompt = self._build_prompt(recipe, session, req, db)

        # 5. Call AI
        ai_resp = None
        last_error = None
        
        if ai_client.is_available():
            try:
                ai_resp = await ai_client.generate_structured(
                    prompt=prompt,
                    response_model=CookStepHelpAIResponse,
                    system_instruction="You are a helpful, safety-conscious cooking assistant."
                )
            except Exception as e:
                last_error = f"{e.__class__.__name__}: {str(e)}"
                logger.error(f"Cook help AI failed: {e}", exc_info=True)

        # 6. Fallback or Process AI result
        if ai_resp:
            return self._format_ai_response(ai_resp)
        
        return self._generate_heuristic_fallback(req, ai_error=last_error)

    def _build_prompt(self, recipe: Recipe, session: CookSession, req: CookStepHelpRequest, db: Session) -> str:
        # Get current and previous step
        current_step = None
        prev_step = None
        
        steps = recipe.steps if recipe.steps else []
        # sort steps by index just in case
        steps.sort(key=lambda x: x.step_index)
        
        idx = req.step_index
        if 0 <= idx < len(steps):
            current_step = steps[idx]
        
        if idx > 0 and idx - 1 < len(steps):
            prev_step = steps[idx - 1]

        # Recent notes
        recent_notes = db.query(RecipeNoteEntry).filter(
            RecipeNoteEntry.recipe_id == recipe.id,
            # Filter by workspace ideally if notes are workspace scoped, assuming yes logic
        ).order_by(desc(RecipeNoteEntry.created_at)).limit(5).all()
        
        notes_text = "\n".join([f"- {n.content}" for n in recent_notes])

        # Ingredients formatted
        ingredients_text = ""
        if recipe.ingredients:
            lines = []
            for ing in recipe.ingredients[:15]:
                q = f"{ing.qty} " if ing.qty else ""
                u = f"{ing.unit} " if ing.unit else ""
                lines.append(f"- {q}{u}{ing.name}")
            ingredients_text = "\n".join(lines)

        context_str = f"""
        RECIPE: {recipe.title}
        
        CURRENT STEP ({idx}):
        {current_step.title if current_step else 'Unknown'} - {json.dumps(current_step.bullets if current_step and current_step.bullets else [])}
        
        PREVIOUS STEP:
        {prev_step.title if prev_step else 'None'} - {json.dumps(prev_step.bullets if prev_step and prev_step.bullets else [])}
        
        INGREDIENTS (First 15):
        {ingredients_text}
        
        USER NOTES HISTORY:
        {notes_text}
        
        SESSION CONTEXT:
        User Question: {req.question}
        User Context: {req.context.model_dump_json() if req.context else '{}'}
        """
        
        return f"""
        Answer the user's cooking question based on the context above.
        
        Requirements:
        1. Be concise.
        2. If safety issues (undercooked chicken, allergens), flag them.
        3. If a timer is implied ("simmer for 10 mins"), suggest it.
        4. Use {req.options.temperature_unit if req.options else 'F'} for temps.
        
        Context Data:
        {context_str}
        """

    def _format_ai_response(self, ai: CookStepHelpAIResponse) -> CookStepHelpResponse:
        citations = []
        # Basic attribution logic - if referring to step, cite it. 
        # For now, generic citations as we don't have granular attribution from Gemini 2.0 Flash easily without more complex prompting.
        citations.append(HelpCitation(type="general", text="AI generated based on recipe context"))

        # Convert list back to optional single for simple UI
        timer_sugg = ai.timer_suggestions[0] if ai.timer_suggestions else None

        return CookStepHelpResponse(
            answer_md=ai.answer_md,
            bullets=ai.bullets,
            confidence=ai.confidence,
            safety=ai.safety,
            citations=citations,
            source="ai",
            timer_suggestion=timer_sugg
        )

    def _generate_heuristic_fallback(self, req: CookStepHelpRequest, ai_error: Optional[str] = None) -> CookStepHelpResponse:
        return CookStepHelpResponse(
            answer_md="I couldn't reach the AI assistant, but here are some general tips.",
            bullets=[
                "Check for visual doneness cues (golden brown, opacity).",
                "Ensure internal temperature reaches safe levels.",
                "Taste and adjust seasoning carefully."
            ],
            confidence="low",
            safety=SafetyFlags(contains_food_safety=True, allergens=[]),
            citations=[HelpCitation(type="general", text="Heuristic fallback")],
            source="heuristic",
            ai_error=ai_error
        )

cook_assist_help = CookAssistHelpService()
