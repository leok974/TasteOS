import os
import json
import logging
from typing import Optional, Any, Type, TypeVar
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
        
        if self.mode == "gemini" and self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self) -> bool:
        return self.mode == "gemini" and self._client is not None

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
            logger.error(f"Gemini Sync generation failed: {e}")
            return None

# Singleton instance access
ai_client = AIClient.get_instance()
