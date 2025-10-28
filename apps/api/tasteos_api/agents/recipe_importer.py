"""
Recipe importer agent for TasteOS.

This module provides functionality to import recipes from URLs and images,
converting them to structured recipe format using LLM assistance.
"""

import json
import re
from typing import Dict, Any

import httpx
from bs4 import BeautifulSoup


async def import_from_url(url: str) -> Dict[str, Any]:
    """
    Fetches recipe from a URL and extracts structured data.

    Args:
        url: The URL of the recipe page to import

    Returns:
        A dict shaped like RecipeCreate with title, ingredients, instructions, etc.

    Example output:
        {
            "title": "Classic Chocolate Chip Cookies",
            "description": "Crispy edges, chewy center...",
            "servings": 24,
            "prep_time": 15,
            "cook_time": 12,
            "difficulty": "easy",
            "cuisine": "american",
            "tags": ["dessert", "cookies"],
            "ingredients": [
                {"item": "flour", "amount": "2 1/4 cups", "notes": "all-purpose"},
                {"item": "butter", "amount": "1 cup", "notes": "softened"}
            ],
            "instructions": [
                {"step": 1, "text": "Preheat oven to 375°F"},
                {"step": 2, "text": "Mix butter and sugars until creamy"}
            ]
        }
    """
    # TODO: Integrate with LLM for better extraction
    # For now, we'll do basic web scraping with BeautifulSoup

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try to extract recipe data using common patterns
        recipe_data = _extract_recipe_from_html(soup, url)

        # TODO: Pass extracted text to LLM for better normalization
        # For Phase 2, we'll use rule-based extraction

        return recipe_data


async def import_from_image(image_bytes: bytes, filename: str = "recipe.jpg") -> Dict[str, Any]:
    """
    Extracts recipe from an image using OCR + LLM.

    Args:
        image_bytes: Raw image data
        filename: Original filename (optional, for context)

    Returns:
        A dict shaped like RecipeCreate
    """
    # TODO: Integrate with OpenAI Vision API or similar
    # For Phase 2, we'll return a stub that shows the structure

    # Placeholder implementation
    return {
        "title": f"Recipe from {filename}",
        "description": "Imported from image - OCR parsing coming soon",
        "servings": 4,
        "prep_time": 15,
        "cook_time": 30,
        "difficulty": "medium",
        "cuisine": "general",
        "tags": ["imported"],
        "ingredients": [
            {"item": "TBD", "amount": "TBD", "notes": "OCR extraction pending"}
        ],
        "instructions": [
            {"step": 1, "text": "Full OCR and LLM parsing will be implemented with OpenAI Vision API"}
        ]
    }


def _extract_recipe_from_html(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    Extract recipe data from HTML using common patterns.

    This is a basic implementation that looks for schema.org markup
    and common CSS selectors. A production version would use LLM
    to parse arbitrary recipe pages.
    """
    recipe_data = {
        "title": "Imported Recipe",
        "description": "",
        "servings": 4,
        "prep_time": 30,
        "cook_time": 30,
        "difficulty": "medium",
        "cuisine": "general",
        "tags": [],
        "ingredients": [],
        "instructions": [],
    }

    # Try to find JSON-LD schema.org Recipe markup
    script_tags = soup.find_all('script', type='application/ld+json')
    for script in script_tags:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'Recipe':
                recipe_data = _parse_schema_org_recipe(data)
                return recipe_data
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') == 'Recipe':
                        recipe_data = _parse_schema_org_recipe(item)
                        return recipe_data
        except (json.JSONDecodeError, AttributeError):
            continue

    # Fallback: Try common selectors
    title = soup.find('h1')
    if title:
        recipe_data['title'] = title.get_text(strip=True)

    # Look for ingredients list
    ingredients_section = soup.find(['ul', 'ol'], class_=re.compile(r'ingredient', re.I))
    if ingredients_section:
        ingredients = []
        for idx, li in enumerate(ingredients_section.find_all('li'), 1):
            text = li.get_text(strip=True)
            if text:
                # Simple parsing: try to split amount from item
                ingredients.append({
                    "item": text,
                    "amount": "",
                    "notes": None
                })
        recipe_data['ingredients'] = ingredients

    # Look for instructions
    instructions_section = soup.find(['ol', 'div'], class_=re.compile(r'instruction|direction|step', re.I))
    if instructions_section:
        instructions = []
        step_elements = instructions_section.find_all(['li', 'p'])
        for idx, elem in enumerate(step_elements, 1):
            text = elem.get_text(strip=True)
            if text and len(text) > 10:  # Filter out short non-instruction text
                instructions.append({
                    "step": idx,
                    "text": text
                })
        recipe_data['instructions'] = instructions

    # Add source URL
    recipe_data['source'] = {"url": url}

    return recipe_data


def _parse_schema_org_recipe(data: dict) -> Dict[str, Any]:
    """
    Parse schema.org Recipe JSON-LD data into our recipe format.
    """
    recipe = {
        "title": data.get('name', 'Imported Recipe'),
        "description": data.get('description', ''),
        "servings": _parse_servings(data.get('recipeYield')),
        "prep_time": _parse_duration(data.get('prepTime')),
        "cook_time": _parse_duration(data.get('cookTime')),
        "difficulty": "medium",
        "cuisine": data.get('recipeCuisine', 'general'),
        "tags": _parse_tags(data),
        "ingredients": _parse_ingredients(data.get('recipeIngredient', [])),
        "instructions": _parse_instructions(data.get('recipeInstructions', [])),
    }

    return recipe


def _parse_servings(yield_val) -> int:
    """Parse recipeYield into servings count."""
    if not yield_val:
        return 4

    if isinstance(yield_val, int):
        return yield_val

    if isinstance(yield_val, str):
        # Try to extract number from strings like "4 servings" or "Makes 6"
        match = re.search(r'\d+', yield_val)
        if match:
            return int(match.group())

    return 4


def _parse_duration(duration_str) -> int:
    """Parse ISO 8601 duration (PT30M) into minutes."""
    if not duration_str:
        return 30

    if isinstance(duration_str, int):
        return duration_str

    # Parse ISO 8601 duration format like PT1H30M
    hours = 0
    minutes = 0

    hour_match = re.search(r'(\d+)H', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))

    min_match = re.search(r'(\d+)M', duration_str)
    if min_match:
        minutes = int(min_match.group(1))

    total = hours * 60 + minutes
    return total if total > 0 else 30


def _parse_tags(data: dict) -> list[str]:
    """Extract tags from recipe data."""
    tags = []

    if 'recipeCategory' in data:
        category = data['recipeCategory']
        if isinstance(category, list):
            tags.extend(category)
        elif isinstance(category, str):
            tags.append(category)

    if 'keywords' in data:
        keywords = data['keywords']
        if isinstance(keywords, str):
            # Keywords might be comma-separated
            tags.extend([k.strip() for k in keywords.split(',') if k.strip()])
        elif isinstance(keywords, list):
            tags.extend(keywords)

    return tags


def _parse_ingredients(ingredients_data) -> list[dict]:
    """Parse ingredients into our format."""
    if not ingredients_data:
        return []

    ingredients = []
    for item in ingredients_data:
        if isinstance(item, str):
            # Simple string format
            ingredients.append({
                "item": item,
                "amount": "",
                "notes": None
            })
        elif isinstance(item, dict):
            # Structured format
            ingredients.append({
                "item": item.get('name', item.get('item', 'Unknown')),
                "amount": item.get('amount', ''),
                "notes": item.get('notes')
            })

    return ingredients


def _parse_instructions(instructions_data) -> list[dict]:
    """Parse instructions into our format."""
    if not instructions_data:
        return []

    instructions = []

    # Handle various formats
    if isinstance(instructions_data, str):
        # Single string - split by periods or newlines
        steps = [s.strip() for s in re.split(r'[.\n]', instructions_data) if s.strip()]
        for idx, step in enumerate(steps, 1):
            instructions.append({"step": idx, "text": step})

    elif isinstance(instructions_data, list):
        for idx, item in enumerate(instructions_data, 1):
            if isinstance(item, str):
                instructions.append({"step": idx, "text": item})
            elif isinstance(item, dict):
                text = item.get('text', item.get('description', ''))
                if text:
                    instructions.append({"step": idx, "text": text})

    return instructions
