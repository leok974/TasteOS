import base64
from dataclasses import dataclass

from google import genai
from google.genai import types

from ..settings import settings


@dataclass
class GeneratedImage:
    png_bytes: bytes
    model: str
    prompt: str


def build_recipe_prompt(title: str, cuisine: str | None) -> str:
    # tuned for clean “recipe card” vibe
    base = f"A beautiful overhead food photograph of {title}"
    if cuisine:
        base += f", {cuisine} cuisine"
    base += ". Soft natural light, shallow depth of field, clean plating, no text, no logos, no watermark, high detail, appetizing."
    return base


def generate_image_for_recipe(*, title: str, cuisine: str | None) -> GeneratedImage:
    prompt = build_recipe_prompt(title, cuisine)

    if settings.ai_mode.lower() != "gemini":
        # Mock mode: return a 1x1 transparent PNG so pipeline works without paid calls.
        # UI can still show placeholders; recipe retains prompt for later regeneration.
        transparent_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2f8AAAAASUVORK5CYII="
        )
        return GeneratedImage(png_bytes=transparent_png, model="mock", prompt=prompt)

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required when AI_MODE=gemini")

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Gemini returns parts that may include inline image data
    for part in getattr(response, "parts", []) or []:
        if getattr(part, "inline_data", None) is not None:
            img = part.as_image()
            # Save to PNG bytes
            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return GeneratedImage(png_bytes=buf.getvalue(), model=settings.gemini_model, prompt=prompt)

    raise RuntimeError("Gemini returned no image data.")
