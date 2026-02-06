import re

def normalize_ingredient_key(name: str) -> str:
    """
    Normalize ingredient name to a canonical key for density lookup.
    
    Rules:
    - Lowercase
    - Punctuation removal
    - Whitespace collapse
    - Remove common descriptors
    - Basic singularization
    """
    if not name:
        return ""
        
    # 1. Lowercase
    s = name.lower()
    
    # 2. Remove parentheticals (e.g. "Flour (all purpose)") -> "Flour "
    s = re.sub(r'\(.*?\)', '', s)
    
    # 3. Punctuation removal (keep letters, numbers, spaces)
    # Replace with space to avoid merging words (all-purpose -> all purpose)
    s = re.sub(r'[^\w\s]', ' ', s)
    
    # 4. Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    
    # 5. Remove common descriptors
    # Note: Order matters roughly (longer first if overlaps)
    descriptors = [
        "fresh", "chopped", "minced", "diced", "sliced",
        "optional", "to taste", "for garnish",
        "dry", "dried", "ground", "whole",
        "fine", "coarse", "granulated",
        "large", "medium", "small",
        "organic", "raw", "unsalted", "salted"
    ]
    
    # Use word boundary to avoid partial matches
    for desc in descriptors:
        s = re.sub(rf'\b{desc}\b', '', s)
        
    # 6. Collapse whitespace again after removal
    s = re.sub(r'\s+', ' ', s).strip()
    
    # 7. Basic singularization
    # Very naive: if ends in 's', not 'ss', len > 3 -> strip 's'
    words = s.split()
    sing_words = []
    for w in words:
        if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
             sing_words.append(w[:-1])
        else:
             sing_words.append(w)
             
    return " ".join(sing_words)
