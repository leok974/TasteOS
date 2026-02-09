
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

def normalize_ingredient(name: str, qty: float | None, unit: str | None):
    """
    Normalize ingredient for grocery list aggregation.
    Returns (key, display, qty, unit).
    """
    # 1. Basic cleaning
    clean_name = name.lower()
    
    # Remove parentheticals (e.g. "onions (chopped)")
    clean_name = re.sub(r'\([^)]*\)', '', clean_name)
    
    # Remove adjectives
    words = clean_name.split()
    filtered_words = [w for w in words if w not in ADJECTIVES]
    clean_name = " ".join(filtered_words)
    
    # Remove punctuation
    clean_name = re.sub(r'[^\w\s]', '', clean_name).strip()
    
    # Naive singularization (very basic)
    if clean_name.endswith("s") and not clean_name.endswith("ss"):
        clean_name = clean_name[:-1]
        
    key = clean_name
    display = clean_name.capitalize()
    
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
    # Very naive parser as requested
    # Look for leading number
    match = re.match(r'^([\d\./]+)\s*(.*)', line.strip())
    if not match:
        return None, None, line.strip()
        
    qty_str = match.group(1)
    rest = match.group(2)
    
    try:
        if '/' in qty_str:
            n, d = map(float, qty_str.split('/'))
            qty = n / d
        else:
            qty = float(qty_str)
    except ValueError:
        return None, None, line.strip()
        
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
