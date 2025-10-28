"""
Nutrition analyzer agent for TasteOS.

This module provides functionality to analyze recipes and calculate
nutritional information (macros) using external APIs or AI estimation.
"""

import os
from typing import Dict, Any, Optional


async def analyze_recipe_macros(recipe_data: Dict[str, Any], variant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze recipe and calculate nutritional macros.

    Args:
        recipe_data: Recipe dict with ingredients and amounts
        variant_data: Optional variant-specific changes (for comparison)

    Returns:
        Dict with calories, protein_g, carbs_g, fat_g, and notes

    Example output:
        {
            "calories": 520,
            "protein_g": 28,
            "carbs_g": 45,
            "fat_g": 22,
            "notes": "Higher protein, reduced cream vs base"
        }
    """
    # TODO: Integrate with NUTRITION_API_KEY and NUTRITION_PROVIDER from env
    # Providers to consider:
    # - Edamam Nutrition Analysis API
    # - USDA FoodData Central
    # - Nutritionix
    # - OpenAI structured extraction

    nutrition_provider = os.getenv("NUTRITION_PROVIDER", "stub")

    if nutrition_provider == "edamam":
        return await _analyze_with_edamam(recipe_data, variant_data)
    elif nutrition_provider == "usda":
        return await _analyze_with_usda(recipe_data, variant_data)
    else:
        # Stub implementation for Phase 2
        return _generate_stub_nutrition(recipe_data, variant_data)


def _generate_stub_nutrition(recipe_data: Dict[str, Any], variant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate placeholder nutrition data for development.

    This is a temporary implementation that returns reasonable-looking
    macros based on simple heuristics. Replace with real API integration.
    """
    ingredients = recipe_data.get("ingredients", [])
    servings = recipe_data.get("servings", 4)

    # Simple heuristic: estimate based on number of ingredients
    # In reality, this would parse ingredient amounts and look up nutrition data
    num_ingredients = len(ingredients)

    # Base estimates (per serving)
    base_calories = 150 + (num_ingredients * 50)
    base_protein = 10 + (num_ingredients * 2)
    base_carbs = 20 + (num_ingredients * 3)
    base_fat = 8 + (num_ingredients * 1.5)

    # Add variation if this is a variant
    notes = ""
    if variant_data:
        variant_type = variant_data.get("variant_type", "")

        if "high-protein" in variant_type.lower():
            base_protein += 12
            base_fat -= 5
            notes = "Higher protein, lower fat than base"
        elif "low-carb" in variant_type.lower():
            base_carbs -= 15
            base_fat += 8
            notes = "Lower carbs, higher healthy fats"
        elif "vegan" in variant_type.lower():
            base_protein -= 5
            base_fat += 3
            notes = "Plant-based protein sources"
        else:
            notes = "Nutritional profile similar to base recipe"
    else:
        notes = "Calculated from recipe ingredients"

    return {
        "calories": int(base_calories),
        "protein_g": round(base_protein, 1),
        "carbs_g": round(base_carbs, 1),
        "fat_g": round(base_fat, 1),
        "notes": notes
    }


async def _analyze_with_edamam(recipe_data: Dict[str, Any], variant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze recipe using Edamam Nutrition Analysis API.

    TODO: Implement actual API integration
    - API docs: https://developer.edamam.com/edamam-nutrition-api
    - Requires NUTRITION_API_KEY environment variable
    - Endpoint: POST https://api.edamam.com/api/nutrition-details
    """
    # For now, return stub data with a note about pending integration
    stub = _generate_stub_nutrition(recipe_data, variant_data)
    stub["notes"] = f"{stub['notes']} (Edamam integration pending)"
    return stub


async def _analyze_with_usda(recipe_data: Dict[str, Any], variant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze recipe using USDA FoodData Central API.

    TODO: Implement actual API integration
    - API docs: https://fdc.nal.usda.gov/api-guide.html
    - Free API key available
    - Good for detailed nutrient profiles
    """
    # For now, return stub data with a note about pending integration
    stub = _generate_stub_nutrition(recipe_data, variant_data)
    stub["notes"] = f"{stub['notes']} (USDA API integration pending)"
    return stub


def calculate_nutrition_delta(base_nutrition: Dict[str, Any], variant_nutrition: Dict[str, Any]) -> Dict[str, str]:
    """
    Calculate the difference between base recipe and variant nutrition.

    Args:
        base_nutrition: Nutrition data from base recipe
        variant_nutrition: Nutrition data from variant

    Returns:
        Dict with formatted delta strings (e.g., "-110 kcal", "+8g protein")
    """
    deltas = {}

    calories_diff = variant_nutrition["calories"] - base_nutrition["calories"]
    protein_diff = variant_nutrition["protein_g"] - base_nutrition["protein_g"]
    carbs_diff = variant_nutrition["carbs_g"] - base_nutrition["carbs_g"]
    fat_diff = variant_nutrition["fat_g"] - base_nutrition["fat_g"]

    # Format deltas with + or - signs
    deltas["calories"] = f"{calories_diff:+d} kcal" if calories_diff != 0 else "same"
    deltas["protein"] = f"{protein_diff:+.1f}g protein" if abs(protein_diff) >= 0.5 else "same"
    deltas["carbs"] = f"{carbs_diff:+.1f}g carbs" if abs(carbs_diff) >= 0.5 else "same"
    deltas["fat"] = f"{fat_diff:+.1f}g fat" if abs(fat_diff) >= 0.5 else "same"

    # Create a human-readable summary
    significant_changes = []
    if abs(calories_diff) >= 50:
        significant_changes.append(deltas["calories"])
    if abs(protein_diff) >= 3:
        significant_changes.append(deltas["protein"])
    if abs(carbs_diff) >= 5:
        significant_changes.append(deltas["carbs"])
    if abs(fat_diff) >= 3:
        significant_changes.append(deltas["fat"])

    if significant_changes:
        deltas["summary"] = ", ".join(significant_changes)
    else:
        deltas["summary"] = "Similar macros to base recipe"

    return deltas
