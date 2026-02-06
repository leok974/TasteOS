import re
import hashlib
from typing import List, Tuple, Optional
from ..schemas import TimerSuggestion

# Regex to match durations like "10 min", "5 minutes", "1 hour", "1 hr 30 mins"
# Simplification: we'll look for simple "X min" or "X hour" patterns first.
# "(\d+)\s*(min|mins|minute|minutes)"
DURATION_REGEX = re.compile(r'(\d+)\s*(min|mins|minute|minutes|hr|hrs|hour|hours)', re.IGNORECASE)

# Keywords to attempt to label the timer
LABEL_KEYWORDS = ["bake", "simmer", "rest", "marinate", "broil", "boil", "roast", "cool", "chill"]

def extract_suggestions_from_text(text: str, step_index: int, existing_suggestions: List[TimerSuggestion]) -> List[TimerSuggestion]:
    """
    Parse text for time durations and return suggestions.
    Deduplicates against existing list.
    """
    suggestions = []
    
    # Process line by line to keep context local
    lines = text.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
            
        # Iterate over all matches in the line
        for match in DURATION_REGEX.finditer(line):
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            # Normalize to seconds
            duration_s = 0
            if "hr" in unit or "hour" in unit:
                duration_s = amount * 3600
            else:
                duration_s = amount * 60
                
            if duration_s == 0:
                continue
                
            # Infer Label from this LINE only
            label = "Timer"
            line_lower = line.lower()
            for kw in LABEL_KEYWORDS:
                if kw in line_lower:
                    label = kw.title() # Capitalize first letter
                    break
            
            # Create client_id
            clean_label = label.lower().replace(" ", "-")
            client_id = f"step-{step_index}-{clean_label}-{duration_s}"
            
            # Check uniqueness
            if any(s.client_id == client_id for s in existing_suggestions + suggestions):
                continue
                
            suggestions.append(TimerSuggestion(
                client_id=client_id,
                label=label,
                step_index=step_index,
                duration_s=duration_s,
                reason="text_regex"
            ))
        
    return suggestions

def generate_suggestions_for_step(step, step_index: int) -> List[TimerSuggestion]:
    suggestions = []
    
    # 1. minutes_est
    if step.minutes_est and step.minutes_est > 0:
        duration_s = step.minutes_est * 60
        client_id = f"step-{step_index}-est-{duration_s}"
        label = step.title or "Timer"
        
        suggestions.append(TimerSuggestion(
            client_id=client_id,
            label=label,
            step_index=step_index,
            duration_s=duration_s,
            reason="minutes_est"
        ))
        
    # 2. Text regex (Title + Bullets)
    full_text = (step.title or "") + "\n" + "\n".join(step.bullets or [])
    text_suggestions = extract_suggestions_from_text(full_text, step_index, suggestions)
    suggestions.extend(text_suggestions)
    
    return suggestions
