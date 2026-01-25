import uuid
from typing import Optional, List, Dict
from ..schemas import CookAdjustment

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
        # Fallback or unknown
        title = f"Fix: {kind}"
        bullets.append("Check seasoning and adjust carefully.")
        confidence = 0.5
        source = "generic"

    # 3. Method refinements
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
