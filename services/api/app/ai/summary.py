import json
import logging
import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from ..schemas import PolishedSummary
from ..settings import settings
from .utils import normalize_model_id

logger = logging.getLogger("tasteos.ai")

SYSTEM_PROMPT = """Return VALID JSON only. No markdown. No extra keys.

You are a precise kitchen assistant summarizing a cooking session.
Your input is a JSON object of "facts" about the session.
Your output must be a clean, human-readable summary following the schema.

Rules:
1. "tldr" must be one clear sentence, max 140 chars.
2. "bullets" summarize what happened (adjustments, timers, method used). Max count per request.
3. "next_time" offers constructive notes for the next cook based on adjustments/failures. Max 4 items.
4. "warnings" highlight safety or major failure points. Max 3 items.
5. If the user provided a "user_freeform_note", weave it into the summary if relevant, or keep it as a bullet.
6. Tone: {style}

Input Facts Schema:
{{
  "recipe_title": "...",
  "method_key": "...",
  "servings_base": 4,
  "servings_target": 6,
  "adjustments": [...],
  "timers_run": [...],
  "user_freeform_note": "..."
}}
"""

def get_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def polish_summary(
    facts: Dict[str, Any],
    style: str = "concise",
    max_bullets: int = 6
) -> PolishedSummary:
    client = get_client()
    
    # Fallback to rules if no client
    if not client:
        return _fallback_summary(facts)

    try:
        # Construct prompt
        formatted_system_prompt = SYSTEM_PROMPT.format(style=style)
        
        prompt = f"""
        Facts:
        {json.dumps(facts, indent=2)}
        
        Max bullets: {max_bullets}
        """

        model_id = normalize_model_id(settings.gemini_text_model)
        
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=formatted_system_prompt,
                response_mime_type="application/json",
                response_schema=PolishedSummary
            )
        )
        
        if not response.text:
            logger.error(f"Gemini returned empty response from model {model_id}")
            return _fallback_summary(facts)

        # Parse and validate
        data = json.loads(response.text)
        return PolishedSummary(**data)

    except Exception as e:
        logger.error(f"Gemini polish failed with model {model_id if 'model_id' in locals() else 'unknown'}: {e}")
        return _fallback_summary(facts)

def _fallback_summary(facts: Dict[str, Any]) -> PolishedSummary:
    """Simple rule-based fallback when AI fails."""
    bullets = []
    
    if facts.get("method_key"):
        bullets.append(f"Method: {facts['method_key']}")
        
    s_base = facts.get("servings_base")
    s_target = facts.get("servings_target")
    if s_base and s_target and s_base != s_target:
        bullets.append(f"Scaled servings: {s_base} -> {s_target}")
        
    adj_count = len(facts.get("adjustments", []))
    if adj_count:
        bullets.append(f"Adjustments applied: {adj_count}")

    timers = facts.get("timers_run", [])
    if timers:
        bullets.append(f"Timers used: {len(timers)}")
        
    user_note = facts.get("user_freeform_note")
    tldr = "Completed cooking session."
    
    if user_note:
        bullets.append(f"Note: {user_note}")
        tldr = user_note # Promote note to TLDR on fallback
        
    return PolishedSummary(
        title="Cook Session (Auto-Summary)",
        tldr=tldr,
        bullets=bullets,
        next_time=[],
        warnings=[],
        confidence=0.4
    )
