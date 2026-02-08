import os
import json
import logging
from typing import Optional, Any, Type, TypeVar
from datetime import datetime, timezone
from pydantic import BaseModel
from google import genai
from google.genai import types

from ..settings import settings

logger = logging.getLogger("tasteos.ai")

T = TypeVar("T", bound=BaseModel)

class AIClient:
    _instance = None

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.mode = settings.ai_mode  # "mock" or "gemini"
        self._client: Optional[genai.Client] = None
        self.last_error: Optional[str] = None
        self.last_error_at: Optional[datetime] = None
        self.image_quota_exceeded: bool = False
        
        if self.mode == "gemini" and self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self) -> bool:
        return self.mode == "gemini" and self._client is not None

    def generate_image(
        self,
        prompt: str,
        number_of_images: int = 1,
        model: Optional[str] = None
    ) -> Optional[list[bytes]]:
        """
        Generate images using Imagen.
        Returns list of image bytes (JPEG).
        """
        if not self.is_available():
            logger.warning("AI is not available, skipping image generation")
            return None
        
        target_model = model or settings.ai_image_model

        try:
            logger.info(f"Generating image with model={target_model} prompt='{prompt[:50]}...'")
            
            # Gemini models (2.0+) use generate_content for images
            if "gemini" in target_model.lower():
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        safety_settings=[types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_ONLY_HIGH"
                        )]
                    )
                )
                
                images_bytes = []
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            import base64
                            # inline_data.data is bytes in most SDK versions, or base64 string
                            data = part.inline_data.data
                            if isinstance(data, str):
                                data = base64.b64decode(data)
                            images_bytes.append(data)
                
                if not images_bytes:
                     logger.warning("Gemini returned no images")
                
                return images_bytes

            else:
                # Imagen models use generate_images
                response = self._client.models.generate_images(
                    model=target_model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=number_of_images,
                        output_mime_type="image/jpeg"
                    )
                )
                
                images_bytes = []
                for item in response.generated_images:
                    # The SDK might return a PIL Image or bytes wrapped object.
                    # In modern 0.x/1.x SDK, item.image is a PIL.Image.
                    if hasattr(item, "image"):
                        import io
                        buf = io.BytesIO()
                        item.image.save(buf, format="JPEG")
                        images_bytes.append(buf.getvalue())
                    elif hasattr(item, "image_bytes"):
                        images_bytes.append(item.image_bytes)
                
                return images_bytes

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            self.last_error = str(e)
            self.last_error_at = datetime.now(timezone.utc)

            # Check for quota limits / 429
            if "429" in str(e) or "quota" in str(e).lower() or "limit" in str(e).lower():
                 self.image_quota_exceeded = True

            raise e

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> Optional[T]:
        """
        Generate structured JSON output using Gemini (Async).
        Returns None if AI is disabled/unavailable or fails.
        """
        if not self.is_available():
            logger.warning("AI is not available (mode=%s), skipping generation", self.mode)
            return None

        model_id = model or settings.gemini_text_model
        
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_model,
                system_instruction=system_instruction
            )
            
            # Use Async Client (aio)
            response = await self._client.aio.models.generate_content(
                model=model_id,
                contents=prompt,
                config=config
            )

            if not response.text:
                logger.warning("Gemini returned empty response")
                return None
            
            # V2 SDK automagically parses if response_schema is provided and matches
            return response.parsed
            
        except Exception as e:
            self.last_error = f"{e.__class__.__name__}: {str(e)}"
            self.last_error_at = datetime.now(timezone.utc)
            logger.error(f"Gemini generation failed: {e}")
            return None

    def generate_content_sync(
        self,
        prompt: str,
        response_model: Optional[Type[T]] = None,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None
    ) -> Any:
        # Synchronous version if needed
        if not self.is_available():
            return None
            
        model_id = model or settings.gemini_text_model
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if response_model else "text/plain",
            response_schema=response_model if response_model else None,
            system_instruction=system_instruction
        )
        
        try:
            response = self._client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=config
            )
            return response.parsed if response_model else response.text
        except Exception as e:
            self.last_error = f"{e.__class__.__name__}: {str(e)}"
            self.last_error_at = datetime.now(timezone.utc)
            logger.error(f"Gemini Sync generation failed: {e}")
            return None

# Singleton instance access
ai_client = AIClient.get_instance()
