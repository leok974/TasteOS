import re
import logging

logger = logging.getLogger(__name__)

def estimate_recipe_time(recipe) -> tuple[int, str]:
    """
    Estimate total cook time for a recipe.
    Returns (total_minutes, source).
    source is "explicit" if derived from step times, "estimated" if parsed/heuristic.
    """
    
    # 1. explicit sum from steps
    # Prefer recipe.steps, but handle if it's a dict or object
    # The caller passes a Recipe ORM object usually
    steps = recipe.steps or []
    
    explicit_minutes = 0
    has_explicit = False
    
    # Check if steps have minutes_est
    for step in steps:
        if hasattr(step, 'minutes_est') and step.minutes_est and step.minutes_est > 0:
            explicit_minutes += step.minutes_est
            has_explicit = True
            
    if has_explicit:
        # If we have explicit minutes, trust them, but maybe add minimal margin?
        # Requirement: "If total derived from explicit step.minutes only -> source='explicit'"
        total = explicit_minutes
        
        # Clamp
        total = max(5, min(total, 1440)) # 24h max? requirement said 240
        total = min(total, 240)
        return total, "explicit"

    # 2. Parse time from text
    parsed_minutes = 0
    has_parsed = False
    
    # Regex for time ranges: 10-15 mins, 20 minutes
    # Use upper bound
    time_regex = re.compile(r'(\d+)(?:\s*(?:-|to|–)\s*(\d+))?\s*(?:min|mins|minutes)', re.IGNORECASE)
    
    for step in steps:
        # Check title
        text_to_scan = [step.title]
        if hasattr(step, 'bullets') and step.bullets:
            text_to_scan.extend(step.bullets)
            
        step_val = 0
        step_found = False
        
        for text in text_to_scan:
            matches = time_regex.findall(text)
            for m in matches:
                # m is ('10', '15') or ('20', '')
                low = int(m[0])
                high = int(m[1]) if m[1] else low
                val = high
                step_val += val
                step_found = True
        
        if step_found:
             parsed_minutes += step_val
             has_parsed = True
        else:
            # Fallback per step if nothing found? 
            # Not in requirements, but maybe useful. 
            # "Add a prep overhead based on recipe size" -> this applies always
            pass

    # 3. Heuristic / Prep overhead
    # prep = clamp(5, 25, round(ingredients_count * 1.5))
    ingredients_count = len(recipe.ingredients) if recipe.ingredients else 0
    
    if ingredients_count > 0:
        prep = max(5, min(25, round(ingredients_count * 1.5)))
    else:
        # fallback: prep = clamp(5, 20, steps_count * 2)
        steps_count = len(steps)
        prep = max(5, min(20, steps_count * 2))
        
    total = parsed_minutes + prep
    
    # Round to nearest 5
    total = round(total / 5) * 5
    
    # Clamp
    total = max(5, min(total, 240))
    
    source = "estimated" # Since we added heuristic prep or parsed text
    
    # If we parsed explicit text, it is "estimated" per requirement: 
    # "If derived from parsed text or heuristic -> source='estimated'"
    
    return total, source
