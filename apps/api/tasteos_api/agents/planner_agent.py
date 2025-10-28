"""
Meal planner agent for TasteOS API.

This agent generates multi-day meal plans based on pantry inventory,
nutritional goals, and dietary preferences.
"""

import os
from typing import List, Dict, Any
from datetime import date, timedelta
import json

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


async def generate_week_plan(
    pantry_items: List[Dict[str, Any]],
    goals: Dict[str, Any],
    prefs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate a multi-day meal plan using AI.

    Args:
        pantry_items: List of available ingredients from pantry
        goals: Nutrition goals like {"calories": 2200, "protein_g": 150}
        prefs: Preferences like {
            "dietary_preferences": ["high-protein", "no-dairy"],
            "budget": "normal",
            "days": 7
        }

    Returns:
        List of daily meal plans, each with structure:
        {
            "date": "2025-10-28",
            "breakfast": [{"recipe_id": "...", "title": "..."}],
            "lunch": [...],
            "dinner": [...],
            "snacks": [...],
            "total_calories": 2150,
            "total_protein_g": 145,
            "total_carbs_g": 180,
            "total_fat_g": 65,
            "notes": "High protein day for training"
        }
    """

    days = prefs.get("days", 7)
    dietary_prefs = prefs.get("dietary_preferences", [])
    budget = prefs.get("budget", "normal")

    target_calories = goals.get("calories", 2000)
    target_protein = goals.get("protein_g", 100)

    # Generate plan starting today
    start_date = date.today()

    # If OpenAI available, use LLM for intelligent planning
    if HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
        return await _llm_generate_plan(
            pantry_items, days, target_calories, target_protein,
            dietary_prefs, budget, start_date
        )

    # Fallback: Generate stub plan
    return _generate_stub_plan(
        days, target_calories, target_protein, dietary_prefs, start_date
    )


async def _llm_generate_plan(
    pantry_items: List[Dict],
    days: int,
    target_calories: int,
    target_protein: float,
    dietary_prefs: List[str],
    budget: str,
    start_date: date
) -> List[Dict]:
    """Use LLM to generate intelligent meal plan."""

    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Build pantry list for context
        pantry_text = "\n".join([
            f"- {item.get('name', 'Unknown')}: {item.get('quantity', 'some')} {item.get('unit', '')}"
            for item in pantry_items[:20]  # Limit to avoid token overflow
        ])

        prefs_text = ", ".join(dietary_prefs) if dietary_prefs else "no specific restrictions"

        prompt = f"""Create a {days}-day meal plan with these constraints:

PANTRY INVENTORY:
{pantry_text if pantry_text else "No pantry items specified"}

GOALS:
- Daily calories: ~{target_calories} kcal
- Daily protein: ~{target_protein}g
- Dietary preferences: {prefs_text}
- Budget: {budget}

REQUIREMENTS:
- Prioritize using ingredients from pantry
- Each day needs breakfast, lunch, dinner, and optional snacks
- Provide recipe titles (use common recipe names)
- Estimate nutrition for each day
- Add helpful notes for each day

Return valid JSON array with {days} objects, each with this structure:
{{
  "date": "YYYY-MM-DD",
  "breakfast": [{{"recipe_id": "generated-id", "title": "Recipe Name"}}],
  "lunch": [{{"recipe_id": "generated-id", "title": "Recipe Name"}}],
  "dinner": [{{"recipe_id": "generated-id", "title": "Recipe Name"}}],
  "snacks": [],
  "total_calories": 2100,
  "total_protein_g": 145,
  "total_carbs_g": 180,
  "total_fat_g": 65,
  "notes": "Brief note about the day"
}}

Start with date: {start_date.isoformat()}
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a meal planning expert. Create balanced, delicious meal plans that use available ingredients efficiently. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        if content:
            # Clean up markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            plan = json.loads(content)

            # Validate and ensure dates are sequential
            for i, day in enumerate(plan):
                day_date = start_date + timedelta(days=i)
                day["date"] = day_date.isoformat()

                # Ensure all required fields
                day.setdefault("breakfast", [])
                day.setdefault("lunch", [])
                day.setdefault("dinner", [])
                day.setdefault("snacks", [])
                day.setdefault("total_calories", target_calories)
                day.setdefault("total_protein_g", target_protein)
                day.setdefault("notes", "")

            return plan[:days]  # Return only requested number of days

    except Exception as e:
        print(f"LLM plan generation error: {e}")
        # Fall back to stub

    return _generate_stub_plan(days, target_calories, target_protein, dietary_prefs, start_date)


def _generate_stub_plan(
    days: int,
    target_calories: int,
    target_protein: float,
    dietary_prefs: List[str],
    start_date: date
) -> List[Dict]:
    """Generate a simple stub meal plan."""

    # Sample meal templates
    breakfast_options = [
        {"recipe_id": "stub-breakfast-1", "title": "Greek Yogurt with Berries"},
        {"recipe_id": "stub-breakfast-2", "title": "Scrambled Eggs and Toast"},
        {"recipe_id": "stub-breakfast-3", "title": "Oatmeal with Banana"},
    ]

    lunch_options = [
        {"recipe_id": "stub-lunch-1", "title": "Grilled Chicken Salad"},
        {"recipe_id": "stub-lunch-2", "title": "Turkey Sandwich"},
        {"recipe_id": "stub-lunch-3", "title": "Quinoa Bowl"},
    ]

    dinner_options = [
        {"recipe_id": "stub-dinner-1", "title": "Baked Salmon with Vegetables"},
        {"recipe_id": "stub-dinner-2", "title": "Chicken Stir-Fry"},
        {"recipe_id": "stub-dinner-3", "title": "Spaghetti with Marinara"},
    ]

    plan = []

    for i in range(days):
        day_date = start_date + timedelta(days=i)

        # Rotate through meal options
        breakfast = [breakfast_options[i % len(breakfast_options)]]
        lunch = [lunch_options[i % len(lunch_options)]]
        dinner = [dinner_options[i % len(dinner_options)]]

        # Add variation note based on dietary prefs
        notes = "Balanced day"
        if "high-protein" in dietary_prefs:
            notes = "High protein day 💪"
        elif "low-carb" in dietary_prefs:
            notes = "Lower carb focus"

        plan.append({
            "date": day_date.isoformat(),
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "snacks": [],
            "total_calories": target_calories,
            "total_protein_g": target_protein,
            "total_carbs_g": target_calories * 0.45 / 4,  # ~45% carbs
            "total_fat_g": target_calories * 0.30 / 9,    # ~30% fat
            "notes": notes
        })

    return plan
