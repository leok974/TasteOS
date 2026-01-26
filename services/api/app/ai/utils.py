import re

def normalize_model_id(model_string: str) -> str:
    """
    Sanitizes a model string to be SDK-compatible.
    
    Examples:
    - 'model="gemini-3-flash-preview"' -> 'gemini-3-flash-preview'
    - '"gemini-3-flash-preview"' -> 'gemini-3-flash-preview'
    
    """
    if not model_string:
        return model_string
        
    # Trim whitespace
    s = model_string.strip()
    
    # Strip optional 'model=' prefix (case insensitive)
    if s.lower().startswith("model="):
        s = s[6:]
        
    # Strip quotes
    s = s.strip('"\'')
    
    return s.strip()
