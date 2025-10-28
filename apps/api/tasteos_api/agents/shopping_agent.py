"""
Shopping agent for TasteOS API.

This agent generates shopping lists by comparing meal plan requirements
against current pantry inventory.
"""

from typing import List, Dict, Any
import re


async def plan_to_list(
    meal_plan: Dict[str, Any],
    pantry_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate a shopping list from a meal plan.

    Compares required ingredients from the meal plan against
    what's already in the pantry, then returns a deduplicated
    list of missing items.

    Args:
        meal_plan: A meal plan object with breakfast/lunch/dinner/snacks
        pantry_items: List of items currently in pantry

    Returns:
        List of items to buy, each with:
        {
            "name": "chicken breast",
            "quantity": 2.0,
            "unit": "lb"
        }
    """

    # Extract all recipes from the meal plan
    all_recipes = []
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        meals = meal_plan.get(meal_type, [])
        if isinstance(meals, list):
            all_recipes.extend(meals)

    # For now, we'll use stub ingredient lists
    # In production, this would query actual recipe data
    required_ingredients = _get_stub_ingredients(all_recipes)

    # Build pantry inventory map (normalized names)
    pantry_map = {}
    for item in pantry_items:
        name = _normalize_name(item.get("name", ""))
        if name:
            pantry_map[name] = {
                "quantity": item.get("quantity", 0) or 0,
                "unit": item.get("unit", "")
            }

    # Calculate what's missing
    shopping_list = []
    seen_items = {}

    for ingredient in required_ingredients:
        name = _normalize_name(ingredient["name"])
        quantity = ingredient.get("quantity", 1) or 1
        unit = ingredient.get("unit", "")

        # Check if we have this in pantry
        if name in pantry_map:
            pantry_qty = pantry_map[name]["quantity"]
            if pantry_qty >= quantity:
                # We have enough, skip it
                continue
            else:
                # We have some, but need more
                quantity = quantity - pantry_qty

        # Deduplicate by name
        if name in seen_items:
            # Aggregate quantities
            seen_items[name]["quantity"] += quantity
        else:
            seen_items[name] = {
                "name": ingredient["name"],  # Use original casing
                "quantity": quantity,
                "unit": unit
            }

    shopping_list = list(seen_items.values())

    return shopping_list


def _normalize_name(name: str) -> str:
    """Normalize ingredient name for comparison."""
    # Convert to lowercase
    name = name.lower().strip()

    # Remove common qualifiers
    name = re.sub(r'\s+(fresh|frozen|canned|dried|chopped|diced|sliced)\s*', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # Remove plurals (simple approach)
    if name.endswith('es'):
        name = name[:-2]
    elif name.endswith('s') and not name.endswith('ss'):
        name = name[:-1]

    return name


def _get_stub_ingredients(recipes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get stub ingredient list for recipes.

    In production, this would query the recipe database.
    For now, we return plausible ingredients based on recipe titles.
    """

    # Common ingredient patterns by recipe type
    ingredient_patterns = {
        "chicken": [
            {"name": "chicken breast", "quantity": 1.5, "unit": "lb"},
            {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
        ],
        "salmon": [
            {"name": "salmon fillet", "quantity": 1, "unit": "lb"},
            {"name": "lemon", "quantity": 1, "unit": "whole"},
        ],
        "pasta": [
            {"name": "pasta", "quantity": 1, "unit": "lb"},
            {"name": "tomato sauce", "quantity": 2, "unit": "cups"},
        ],
        "salad": [
            {"name": "lettuce", "quantity": 1, "unit": "head"},
            {"name": "tomato", "quantity": 2, "unit": "whole"},
            {"name": "cucumber", "quantity": 1, "unit": "whole"},
        ],
        "egg": [
            {"name": "eggs", "quantity": 4, "unit": "pcs"},
        ],
        "yogurt": [
            {"name": "Greek yogurt", "quantity": 1, "unit": "cup"},
            {"name": "berries", "quantity": 1, "unit": "cup"},
        ],
        "sandwich": [
            {"name": "bread", "quantity": 4, "unit": "slices"},
            {"name": "turkey", "quantity": 0.5, "unit": "lb"},
        ],
        "bowl": [
            {"name": "quinoa", "quantity": 1, "unit": "cup"},
            {"name": "vegetables", "quantity": 2, "unit": "cups"},
        ],
    }

    all_ingredients = []

    for recipe in recipes:
        title = recipe.get("title", "").lower()

        # Match patterns
        for keyword, ingredients in ingredient_patterns.items():
            if keyword in title:
                all_ingredients.extend(ingredients)
                break
        else:
            # Default ingredients
            all_ingredients.append({"name": "misc ingredients", "quantity": 1, "unit": "serving"})

    return all_ingredients
