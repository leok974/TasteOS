"""
Unit Conversion Service for TasteOS v14.

Handles mass, volume, and count based conversions with intelligent density lookups.
"""

import re
from typing import Optional, Tuple, Literal

# --- Types ---

UnitType = Literal["mass", "volume", "count", "unknown"]
RoundingMode = Literal["cook", "decimal"]

class ConversionResult:
    def __init__(
        self, 
        qty: float, 
        unit: str, 
        confidence: str = "high", # high, medium, low
        note: Optional[str] = None,
        is_approx: bool = False
    ):
        self.qty = qty
        self.unit = unit
        self.confidence = confidence
        self.note = note
        self.is_approx = is_approx
    
    def to_dict(self):
        return {
            "qty": self.qty,
            "unit": self.unit,
            "confidence": self.confidence,
            "note": self.note,
            "is_approx": self.is_approx
        }

# --- Data Tables ---

# Normalized unit -> (type, factor_to_base)
# Base units: g (mass), ml (volume), each (count)
UNITS_DB = {
    # Mass (base: g)
    "g": ("mass", 1.0),
    "gram": ("mass", 1.0),
    "grams": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "kilogram": ("mass", 1000.0),
    "kilograms": ("mass", 1000.0),
    "mg": ("mass", 0.001),
    "oz": ("mass", 28.3495),
    "ounce": ("mass", 28.3495),
    "ounces": ("mass", 28.3495),
    "lb": ("mass", 453.592),
    "pound": ("mass", 453.592),
    "pounds": ("mass", 453.592),
    
    # Volume (base: ml)
    "ml": ("volume", 1.0),
    "milliliter": ("volume", 1.0),
    "milliliters": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "liter": ("volume", 1000.0),
    "liters": ("volume", 1000.0),
    "tsp": ("volume", 4.92892),
    "teaspoon": ("volume", 4.92892),
    "teaspoons": ("volume", 4.92892),
    "tbsp": ("volume", 14.7868),
    "tablespoon": ("volume", 14.7868),
    "tablespoons": ("volume", 14.7868),
    "fl oz": ("volume", 29.5735),
    "fluid ounce": ("volume", 29.5735),
    "c": ("volume", 236.588), # US Cup
    "cup": ("volume", 236.588),
    "cups": ("volume", 236.588),
    "pt": ("volume", 473.176),
    "pint": ("volume", 473.176),
    "qt": ("volume", 946.353),
    "quart": ("volume", 946.353),
    "gal": ("volume", 3785.41),
    "gallon": ("volume", 3785.41),
    
    # Count (base: each)
    "each": ("count", 1.0),
    "pc": ("count", 1.0),
    "pcs": ("count", 1.0),
    "clove": ("count", 1.0), # often treated as count but variable size
    "cloves": ("count", 1.0),
    "slice": ("count", 1.0),
    "slices": ("count", 1.0),
    "can": ("count", 1.0), # ambiguous, but usually count in inventories
}

# Density Table: g/ml (approximate)
# Derived from common cooking defaults (g/cup / 240.0)
DENSITY_DB = {
    # Water-like (240-245g/cup)
    "water": 1.0,
    "milk": 1.02, # whole
    "whole milk": 1.02,
    "broth": 1.0,
    "stock": 1.0,
    "chicken broth": 1.0,
    "beef broth": 1.0,
    "vegetable broth": 1.0,

    # Oils & Fats (218-227g/cup)
    "oil": 0.91,
    "vegetable oil": 0.91,
    "olive oil": 0.91,
    "canola oil": 0.91,
    "butter": 0.95, # melted
    "melted butter": 0.95,

    # Sweeteners
    "honey": 1.42,
    "maple syrup": 1.30,
    "sugar": 0.83, # granulated (200g/cup)
    "white sugar": 0.83,
    "granulated sugar": 0.83,
    "brown sugar": 0.92, # packed (220g/cup)
    "packed brown sugar": 0.92,
    "powdered sugar": 0.50, # (120g/cup)
    "confectioners sugar": 0.50,

    # Flours & Dry Goods (120-130g/cup typical)
    "flour": 0.50, # all-purpose (120g/cup)
    "all-purpose flour": 0.50,
    "all purpose flour": 0.50,
    "ap flour": 0.50,
    "bread flour": 0.54, # (130g/cup)
    "whole wheat flour": 0.50, # (120g/cup)
    "cornstarch": 0.50, # (120g/cup)
    "corn starch": 0.50,
    "cocoa": 0.35, # (85g/cup)
    "cocoa powder": 0.35,
    "oats": 0.375, # rolled (90g/cup)
    "rolled oats": 0.375,
    "rice": 0.77, # uncooked white (185g/cup)
    "white rice": 0.77,
    "uncooked rice": 0.77,

    # Pantry Staples
    "salt": 1.20, # table salt/fine (288g/cup)
    "table salt": 1.20,
    "fine salt": 1.20,
    "kosher salt": 0.56, # Defauting to Diamond Crystal (135g/cup) - safer than Morton
    "diamond crystal kosher salt": 0.56,
    "diamond crystal salt": 0.56,
    "morton kosher salt": 0.96, # (230g/cup)
    "morton salt": 0.96,
}

# Synonyms map for input normalization
SYNONYMS = {
    "t": "tsp",
    "T": "tbsp",
    "tbl": "tbsp",
    "oz": "oz",
}

# --- Core Functions ---

def normalize_unit(unit: str) -> Optional[str]:
    """Normalize unit string to key in UNITS_DB."""
    if not unit:
        return None
    
    # 1. Check strict case synonyms (e.g. 'T' vs 't')
    raw_clean = unit.strip().rstrip('.')
    if raw_clean in SYNONYMS:
        return SYNONYMS[raw_clean]
        
    u = raw_clean.lower()
    
    # Check direct
    if u in UNITS_DB:
        return u
        
    # Check synonyms
    if u in SYNONYMS:
        return SYNONYMS[u]
        
    # Check plural s removal
    if u.endswith('s') and u[:-1] in UNITS_DB:
        return u[:-1]
        
    return None

def get_unit_info(unit: str) -> Tuple[UnitType, float]:
    """Get type and factor for a normalized unit."""
    return UNITS_DB.get(unit, ("unknown", 1.0))

def calculate_density_factor(
    mass_val: float, mass_unit: str,
    vol_val: float, vol_unit: str
) -> Optional[float]:
    """Calculate g/ml density from arbitrary mass and volume measurements."""
    norm_m = normalize_unit(mass_unit)
    norm_v = normalize_unit(vol_unit)
    
    if not norm_m or not norm_v:
        return None
        
    type_m, factor_m = get_unit_info(norm_m)
    type_v, factor_v = get_unit_info(norm_v)
    
    if type_m != "mass" or type_v != "volume":
        return None
        
    # Convert to base units (g and ml)
    g_val = mass_val * factor_m
    ml_val = vol_val * factor_v
    
    if ml_val == 0:
        return None
        
    return g_val / ml_val


def estimate_density(ingredient_name: str) -> Tuple[float, str]:
    """
    Start simple density lookup.
    Returns (density_g_per_ml, confidence).
    """
    name = ingredient_name.lower()
    
    # Direct match
    if name in DENSITY_DB:
        return DENSITY_DB[name], "medium"
        
    # Substring / Suffix match
    for k, v in DENSITY_DB.items():
        if k in name:  # e.g. "whole milk" -> "milk"
            return v, "low" # Generic match
            
    # Default: Water density with very low confidence
    return 1.0, "none"

def format_qty_cook(qty: float) -> Tuple[float, Optional[str]]:
    """
    Round to friendly fractions for cooking.
    Returns (rounded_qty, formatted_string_or_none).
    """
    # Thresholds for friendly output
    # TODO: Implement full fraction string logic (e.g. "1 1/2") if needed for UI string.
    # For now, we return decimal optimized for display.
    
    # Small numbers: 2 significant digits
    if qty < 10:
        return round(qty, 2), None
    # Medium numbers: 1 decimal
    if qty < 100:
        return round(qty, 1), None
    # Large numbers: integer
    return round(qty), None


def convert_unit(
    qty: float,
    from_unit: str,
    to_unit: str,
    ingredient_name: str = "",
    allow_cross_type: bool = False,
    override_density: Optional[float] = None
) -> ConversionResult:
    """
    Convert quantity between units.
    """
    norm_from = normalize_unit(from_unit)
    norm_to = normalize_unit(to_unit)
    
    if not norm_from or not norm_to:
        return ConversionResult(qty, to_unit, "low", "Unknown unit", is_approx=True)

    type_from, factor_from = get_unit_info(norm_from)
    type_to, factor_to = get_unit_info(norm_to)
    
    # Case 1: Same type (Mass->Mass, Vol->Vol)
    if type_from == type_to and type_from != "unknown":
        # Base conversion: 
        # base_qty = qty * factor_from
        # target_qty = base_qty / factor_to
        base_qty = qty * factor_from
        result_qty = base_qty / factor_to
        return ConversionResult(result_qty, norm_to, "high")
        
    # Case 2: Cross type (Mass <-> Vol)
    if {type_from, type_to} == {"mass", "volume"}:
        density = 1.0
        confidence = "none"
        is_override = False

        if override_density:
            density = override_density
            confidence = "high"
            is_override = True
        else:
            density, confidence = estimate_density(ingredient_name)
        
        if confidence == "none" and not allow_cross_type:
             return ConversionResult(qty, norm_to, "low", "Cannot convert mass to volume without density", is_approx=True)
             
        # Conversion logic:
        # Mass (g) = Volume (ml) * Density (g/ml)
        # Volume (ml) = Mass (g) / Density (g/ml)
        
        base_qty_from = qty * factor_from # g or ml
        
        result_base_to = 0.0
        
        if type_from == "mass": # g -> ml
            # V = M / D
            result_base_to = base_qty_from / density # ml
        else: # ml -> g
            # M = V * D
            result_base_to = base_qty_from * density # g
            
        result_qty = result_base_to / factor_to
        
        if is_override:
            note_text = f"Using density override: {density:.3g} g/ml"
            is_approx = False
            confidence = "high"
        else:
            note_text = "Uses common cooking density defaults — set an override for precision."
            is_approx = True
            # If estimate_density gave us 'medium' (exact match), stick with it. 
            # If 'low' (substring), also stick with it but maybe warn?
            # User request: "For anything from this list, mark conversions as: confidence: medium"
            if confidence == "medium":
                confidence = "medium"
            # If it was low/none, it remains so
        
        return ConversionResult(
            result_qty, 
            norm_to, 
            confidence, 
            note=note_text,
            is_approx=is_approx
        )

    # Case 3: Incompatible (Count <-> Mass/Vol)
    # Cannot do without "avg weight per item" database which is huge.
    return ConversionResult(qty, to_unit, "low", "Cannot convert count to measurement", is_approx=True)

def auto_select_unit(qty: float, current_unit: str, target_system: str = "metric") -> str:
    """
    Select best unit for readability based on target system.
    target_system: "metric" or "us_customary"
    """
    norm_u = normalize_unit(current_unit)
    if not norm_u: 
        return current_unit
        
    u_type, factor = get_unit_info(norm_u)
    
    # 1. Metric Logic
    if target_system == "metric":
        if u_type == "volume":
            base_ml = qty * factor
            if base_ml >= 1000: return "l"
            return "ml"
        elif u_type == "mass":
            base_g = qty * factor
            if base_g >= 1000: return "kg"
            return "g"
            
    # 2. US Customary Logic
    elif target_system == "us_customary":
        if u_type == "volume":
            base_ml = qty * factor
            # 1 tsp ~ 5ml
            # 1 tbsp ~ 15ml
            # 1 cup ~ 240ml
            # 1 qt ~ 950ml
            # 1 gal ~ 3800ml
            
            if base_ml < 15: return "tsp" # < 1 tbsp
            if base_ml < 60: return "tbsp" # < 1/4 cup
            if base_ml < 950: return "cup" # < 1 qt
            if base_ml < 3800: return "qt" # < 1 gal
            return "gal"
            
        elif u_type == "mass":
            base_g = qty * factor
            base_oz = base_g / 28.3495
            
            if base_oz >= 16: return "lb"
            return "oz"

    return current_unit
