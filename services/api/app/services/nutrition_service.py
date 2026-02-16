def calculate_macros_for_log(recipe_macros: dict, servings: float) -> dict:
    """
    Calculates total macros for a specific log entry.
    Ensures rounding so we don't get floating point artifacts (e.g., 14.000000002).
    """
    keys = ["calories", "protein_g", "carbs_g", "fat_g"]
    return {
        key: round(float(recipe_macros.get(key, 0)) * servings, 1)
        for key in keys
    }
