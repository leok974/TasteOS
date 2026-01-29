import uuid
import os
import json
import logging
from typing import Optional, List, Dict
from google import genai
from google.genai import types

from ..schemas import CookAdjustment
from ..settings import settings
from ..ai.utils import normalize_model_id

logger = logging.getLogger("tasteos.ai")

SYSTEM_PROMPT = """Return VALID JSON only. No markdown. No extra keys.

You are an expert chef assistant helping a user fix a cooking problem in real-time.
The user is currently on a specific step of a recipe and has flagged an issue (e.g. "Too Salty", "Burning").

Your goal: Provide a structured adjustment to fix the issue *for this specific step*.

Input:
- Method: {method} (e.g. "standard", "air_fryer")
- Step Context: {step_text}
- Issue: {kind} {user_context}

Output Schema (JSON):
{{
  "title": "Short, Punchy Title (e.g. 'Fix: Add Acid')",
  "bullets": ["Actionable instruction 1", "Actionable instruction 2"],
  "warnings": ["Safety warning or risk (optional)"]
}}

Rules:
1. Be extremely concise. Bullets should be < 10 words.
2. If the issue is dangerous (burning), safety first.
3. Tailor advice to the cooking method if specified (e.g. release pressure for Instant Pot).
4. Max 5 bullets.
"""

def get_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def _generate_ai_adjustment(
    session_method_key: Optional[str],
    step_text: str,
    kind: str,
    context: Optional[dict]
) -> Optional[Dict]:
    """Call Gemini to generate adjustment details."""
    client = get_client()
    if not client:
        return None

    try:
        user_context = ""
        if context:
            user_context = f"({context})"

        formatted_system_prompt = SYSTEM_PROMPT.format(
            method=session_method_key or "standard",
            step_text=step_text,
            kind=kind,
            user_context=user_context
        )

        model_id = normalize_model_id(settings.gemini_text_model)
        
        response = client.models.generate_content(
            model=model_id,
            contents="Generate adjustment JSON.",
            config=types.GenerateContentConfig(
                system_instruction=formatted_system_prompt,
                response_mime_type="application/json",
            )
        )

        if not response.text:
            return None

        return json.loads(response.text)

    except Exception as e:
        logger.error(f"AI adjustment generation failed: {e}")
        return None

def generate_adjustment(
    session_method_key: Optional[str],
    step_index: int,
    original_step: dict,
    kind: str,
    context: Optional[dict] = None
) -> CookAdjustment:
    
    # 1. Defaults
    adjustment_id = f"adj_{uuid.uuid4().hex[:8]}"
    title = f"Fix: {kind.replace('_', ' ').capitalize()}"
    bullets = []
    warnings = []
    confidence = 0.8
    source = "rules"

    # 2. Logic based on kind
    k = kind.lower()
    
    # Pre-defined rules for common issues
    if k == "too_salty":
        title = "Fix: Too Salty"
        bullets.extend([
            "Add a splash of water, unsalted stock, or cream (if appropriate) to dilute.",
            "Add a squeeze of lemon or dash of vinegar to mask saltiness.",
            "Add a customized potato chunk to absorb salt, then remove.",
            "Do NOT add any more salt."
        ])
    
    elif k == "too_spicy":
        title = "Fix: Too Spicy"
        bullets.extend([
            "Add dairy (cream, yogurt, milk) or coconut milk.",
            "Add sweetness (honey, sugar, maple syrup) to balance heat.",
            "Serve with cooling starch (rice, bread) or cucumber salad."
        ])
    
    elif k == "too_thick":
        title = "Fix: Too Thick"
        bullets.extend([
            "Add water or stock in 1 tbsp increments.",
            "Whisk vigorously over low heat.",
        ])
        warnings.append("If dairy-based, do not boil aggressively to avoid splitting.")

    elif k == "too_thin":
        title = "Fix: Too Thin"
        bullets.extend([
            "Simmer uncovered for 5-10 minutes to reduce.",
            "Mix 1 tsp cornstarch with 1 tbsp cold water (slurry), then stir in.",
            "Add a knob of cold butter at the end to mount the sauce."
        ])

    elif k == "burning":
        title = "Emergency: Burning"
        bullets.extend([
            "Remove from heat IMMEDIATELY.",
            "Do NOT scrape the bottom of the pan.",
            "Transfer unburnt contents to a clean pot/pan.",
            "Deglaze original pan only if you want to inspect damage (discard burnt bits)."
        ])

    elif k == "no_browning":
        title = "Fix: No Browning"
        bullets.extend([
            "Pat ingredients completely dry with paper towels.",
            "Increase heat slightly (careful of burning oil).",
            "Don't crowd the pan - cook in batches if needed.",
             "Add a tiny pinch of sugar if appropriate for caramelization."
        ])

    elif k == "undercooked":
        title = "Fix: Undercooked"
        bullets.extend([
            "Continue cooking, checking every 2 minutes.",
            "Cover the pan to trap heat (steaming effect).",
            "Cut into a thick piece to check internal doneness."
        ])
        warnings.append("Ensure poultry reaches 165°F (74°C).")
        
    else:
        # Fallback to AI for unknown or generic kinds
        step_text = f"{original_step.get('title', '')} - {' '.join(original_step.get('bullets', []))}"
        ai_result = _generate_ai_adjustment(session_method_key, step_text, k, context)
        
        if ai_result:
            title = ai_result.get("title", title)
            bullets = ai_result.get("bullets", [])
            warnings = ai_result.get("warnings", [])
            confidence = 0.9
            source = "ai_gemini"
        else:
            # Final fallback
            title = f"Fix: {kind}"
            bullets.append("Check seasoning and adjust carefully.")
            confidence = 0.5
            source = "generic"

    # 3. Method refinements (Rules applied ON TOP of basic rules)
    # We only apply these if source is "rules" to avoid conflicting with AI context
    if source == "rules":
        if session_method_key == "air_fryer":
            if k == "no_browning":
                bullets.insert(0, "Spray generously with oil.")
                bullets.append("Shake the basket to expose new surfaces.")
            if k == "undercooked":
                bullets.append("Lower temp by 20°F and cook longer if outside is browning too fast.")
        
        elif session_method_key == "instant_pot":
            if k == "too_thin":
                bullets.insert(0, "Use 'Sauté' mode with lid off to reduce liquid.")
            if k == "burning":
                warnings.append("Check for 'Burn' error code and scrape bottom well after transferring.")

    return CookAdjustment(
        id=adjustment_id,
        step_index=step_index,
        kind=kind,
        title=title,
        bullets=bullets,
        warnings=warnings,
        confidence=confidence,
        source=source
    )
