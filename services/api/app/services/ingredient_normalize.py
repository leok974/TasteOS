import re

def normalize_ingredient_key(name: str) -> str:
    """
    Normalize an ingredient name to a consistent key for density lookups.
    
    Strategies:
    1. Lowercase
    2. Remove common noisy modifiers (fresh, chopped, diced, etc) - though 'chopped' can affect density, 
       for broad matching usually we want 'Onion' to match 'Onion, chopped'.
    3. Remove punctuation
    4. Collapse whitespace
    """
    if not name:
        return ""
        
    normalized = name.lower()
    
    # 1. Remove parenthetical info e.g. "flour (all purpose)" -> "flour "
    normalized = re.sub(r'\(.*?\)', '', normalized)
    
    # 2. Cleanup punctuation
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # 3. Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # 4. Remove modifiers (Basic list, can be expanded)
    # Note: Pluralization (onions -> onion) is hard without NLP lib, keeping simple for now.
    modifiers = [
        "fresh", "chopped", "diced", "minced", "sliced", "grated", "shredded",
        "optional", "to taste", "large", "small", "medium", "whole", 
        "can", "jar", "frozen", "dried", "dry", "raw", "cooked"
    ]
    
    words = normalized.split()
    filtered = [w for w in words if w not in modifiers]
    
    # If we stripped everything (e.g. input was just "fresh"), revert to normalized
    if not filtered:
        return normalized
        
    return " ".join(filtered)

