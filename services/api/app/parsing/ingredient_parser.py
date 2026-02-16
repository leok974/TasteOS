
import re

COMMON_UNITS = {
    "tsp", "teaspoon", "tbsp", "tablespoon", "cup", "oz", "ounce", 
    "lb", "pound", "g", "gram", "kg", "kilogram", "ml", "l", "liter",
    "clove", "can", "package", "bunch", "pinch", "slice", "stick"
}

ADJECTIVES = {
    "large", "medium", "small", "fresh", "dried", "chopped", "sliced", "diced", "minced",
    "grated", "crushed", "whole", "ground", "fine", "coarse", "thinly", "thickly",
    "lean", "boneless", "skinless"
}

GARBAGE_TOKENS = {
    "or", "and", "optional", "to taste", "if needed", "for serving", "plus more", "divided"
}

def sanitize_ingredient_text(text: str) -> str:
    """Strip markdown and normalize whitespace."""
    if not text:
        return ""
        
    s = text
    # Remove markdown bold/italic markers
    s = s.replace("**", "").replace("__", "").replace("*", "")
    
    # Remove leading bullets
    s = re.sub(r'^[\s\-\#]+', '', s)
    
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s

def is_garbage_line(text: str) -> bool:
    """Check if the text is just a connector word or garbage."""
    if not text:
        return True
        
    t = text.lower().strip()
    # Remove punctuation
    t = re.sub(r'[^\w\s]', '', t)
    
    if not t:
        return True

    # Check exact match against tokens
    if t in GARBAGE_TOKENS:
        return True
        
    return False

def normalize_ingredient(name: str, qty: float | None, unit: str | None):
    """
    Normalize ingredient for grocery list aggregation.
    Returns (key, display, qty, unit).
    If the ingredient is detected as garbage/connector, key will be None.
    """
    # 0. Sanitize display name first (handles "Or**" -> "Or")
    clean_display = sanitize_ingredient_text(name)
    
    # 0.5 Check for garbage
    if is_garbage_line(clean_display):
        return None, None, None, None
        
    # 1. Basic cleaning
    clean_name = clean_display.lower()
    
    # Remove parentheticals for KEY generation only (e.g. "onions (chopped)")
    clean_name_key = re.sub(r'\([^)]*\)', '', clean_name)
    
    # Remove adjectives
    words = clean_name_key.split()
    filtered_words = [w for w in words if w not in ADJECTIVES]
    clean_name_key = " ".join(filtered_words)
    
    # Remove punctuation
    clean_name_key = re.sub(r'[^\w\s]', '', clean_name_key).strip()
    
    # Naive singularization (very basic)
    if clean_name_key.endswith("s") and not clean_name_key.endswith("ss"):
        clean_name_key = clean_name_key[:-1]
        
    key = clean_name_key
    
    # Use sanitized name for display to preserve nuances but no markdown
    display = clean_display.capitalize() 
    
    # Unit normalization (basic mapping)
    norm_unit = unit.lower() if unit else None
    if norm_unit:
        if norm_unit in ["teaspoon", "teaspoons"]: norm_unit = "tsp"
        elif norm_unit in ["tablespoon", "tablespoons"]: norm_unit = "tbsp"
        elif norm_unit in ["pound", "pounds"]: norm_unit = "lb"
        elif norm_unit in ["ounce", "ounces"]: norm_unit = "oz"
        elif norm_unit in ["gram", "grams"]: norm_unit = "g"
        
    return key, display, qty, norm_unit

def parse_ingredient_line(line: str):
    """
    Best effort parser for raw strings. 
    Returns (qty, unit, name).
    """
    # 0. Sanitize input line
    clean_line = sanitize_ingredient_text(line)
    if is_garbage_line(clean_line):
        return None, None, ""

    # Very naive parser as requested
    # Look for leading number
    match = re.match(r'^([\d\./]+)\s*(.*)', clean_line)
    if not match:
        return None, None, clean_line
        
    qty_str = match.group(1)
    rest = match.group(2)
    
    try:
        if '/' in qty_str:
            n, d = map(float, qty_str.split('/'))
            qty = n / d
        else:
            qty = float(qty_str)
    except ValueError:
        return None, None, clean_line
        
    # Check for unit in first word of rest
    words = rest.split()
    if not words:
        return qty, None, ""
        
    potential_unit = words[0].lower()
    # Strip plural s for unit check
    check_unit = potential_unit[:-1] if potential_unit.endswith('s') else potential_unit
    
    if check_unit in COMMON_UNITS or potential_unit in COMMON_UNITS:
        name = " ".join(words[1:])
        return qty, check_unit, name
    
    return qty, None, rest
