"""
Pantry agent for TasteOS API.

This agent helps parse and interpret pantry items from various sources.
"""

import os
from typing import Optional, Dict, Any
import json

# OpenAI import for LLM parsing
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


async def parse_item(
    barcode: Optional[str] = None,
    raw_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse pantry item from barcode or raw text input.

    Uses LLM to interpret natural language descriptions like:
    - "half an onion"
    - "2 lbs chicken breast"
    - "3 eggs"

    Or in the future, barcode data to identify products.

    Args:
        barcode: Optional barcode string
        raw_text: Optional natural language description

    Returns:
        Dict shaped like PantryItemCreate with:
        - name: str
        - quantity: float | None
        - unit: str | None
        - expires_at: datetime | None
        - tags: list[str]
    """

    if not raw_text and not barcode:
        return {
            "name": "Unknown Item",
            "quantity": None,
            "unit": None,
            "tags": []
        }

    # If we have a barcode, for now just return a placeholder
    # In production, this would lookup a product database
    if barcode:
        return {
            "name": f"Product {barcode}",
            "quantity": 1,
            "unit": "item",
            "tags": ["scanned"]
        }

    # Parse raw text using LLM if available
    if HAS_OPENAI and raw_text:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                client = openai.OpenAI(api_key=api_key)

                prompt = f"""Parse this pantry item description into structured data.
Input: "{raw_text}"

Return ONLY valid JSON with these fields:
- name (string): ingredient name
- quantity (number or null): how much
- unit (string or null): unit of measurement (e.g., "g", "lb", "cups", "pcs")
- tags (array): relevant categorization tags (e.g., ["vegetable"], ["protein"], ["dairy"])

Examples:
Input: "half an onion"
Output: {{"name": "onion", "quantity": 0.5, "unit": "whole", "tags": ["vegetable"]}}

Input: "2 lbs chicken breast"
Output: {{"name": "chicken breast", "quantity": 2, "unit": "lb", "tags": ["protein", "poultry"]}}

Input: "3 eggs"
Output: {{"name": "eggs", "quantity": 3, "unit": "pcs", "tags": ["protein", "dairy"]}}

Now parse: "{raw_text}"
"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that parses food items into structured data. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )

                content = response.choices[0].message.content
                if content:
                    # Extract JSON from response
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                    parsed = json.loads(content)
                    return {
                        "name": parsed.get("name", "Unknown"),
                        "quantity": parsed.get("quantity"),
                        "unit": parsed.get("unit"),
                        "tags": parsed.get("tags", [])
                    }

            except Exception as e:
                print(f"LLM parsing error: {e}")
                # Fall through to simple parsing

    # Fallback: simple heuristic parsing
    if raw_text:
        return _simple_parse(raw_text)

    return {
        "name": "Unknown Item",
        "quantity": None,
        "unit": None,
        "tags": []
    }


def _simple_parse(text: str) -> Dict[str, Any]:
    """Simple heuristic parser for pantry items."""

    text = text.strip().lower()
    words = text.split()

    # Try to extract quantity (first number)
    quantity = None
    unit = None
    name_words = []

    for i, word in enumerate(words):
        # Check if it's a number
        try:
            # Handle fractions like "1/2"
            if "/" in word:
                parts = word.split("/")
                quantity = float(parts[0]) / float(parts[1])
                continue
            # Handle decimals
            quantity = float(word)
            # Next word might be a unit
            if i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in ["lb", "lbs", "oz", "g", "kg", "ml", "l", "cup", "cups", "tbsp", "tsp", "pcs", "piece", "pieces"]:
                    unit = next_word
                    continue
            continue
        except ValueError:
            # Not a number, part of name
            if word not in ["lb", "lbs", "oz", "g", "kg", "ml", "l", "cup", "cups", "tbsp", "tsp", "pcs", "piece", "pieces"]:
                name_words.append(word)

    name = " ".join(name_words) if name_words else text

    # Guess tags based on common keywords
    tags = []
    if any(veg in name for veg in ["onion", "tomato", "carrot", "lettuce", "spinach", "broccoli", "pepper"]):
        tags.append("vegetable")
    if any(protein in name for protein in ["chicken", "beef", "pork", "fish", "salmon", "turkey", "egg"]):
        tags.append("protein")
    if any(dairy in name for dairy in ["milk", "cheese", "butter", "yogurt", "cream"]):
        tags.append("dairy")
    if any(grain in name for grain in ["rice", "pasta", "bread", "flour", "oats"]):
        tags.append("grain")

    return {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "tags": tags
    }
