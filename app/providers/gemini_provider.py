"""
Gemini LLM Provider implementation using the official Google GenAI SDK.
"""

import os
import logging
from google import genai
from google.genai import types

from app.config import settings
from app.providers.base_provider import BaseLLMProvider
from app.schemas.match import PromptPackage

logger = logging.getLogger("smart-resume-screener.providers.gemini")


class ProviderError(Exception):
    """Base exception class for all LLM provider errors."""
    pass


class GeminiProviderError(ProviderError):
    """Raised when an error occurs during generation with the Gemini provider."""
    pass


class GeminiProvider(BaseLLMProvider):
    """
    Adapter for Google's Gemini models using the official google-genai SDK.
    """

    def __init__(self) -> None:
        """
        Initialize the Gemini Client using configured settings.
        Raises GeminiProviderError if no API key is available.
        """
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("Gemini API initialization failed: API key not found in settings or environment.")
            raise GeminiProviderError(
                "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable."
            )

        self.model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        try:
            # Initialize official Client from google-genai SDK
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Gemini Client initialized successfully using model: {self.model_name}")
        except Exception as exc:
            logger.error(f"Failed to initialize Gemini Client: {exc}", exc_info=True)
            raise GeminiProviderError(f"Failed to initialize Gemini Client: {exc}") from exc

    def generate(self, prompt: PromptPackage) -> str:
        """
        Send a PromptPackage context to Gemini models and return the raw response text.

        Args:
            prompt (PromptPackage): Structured package holding system, user, and full prompts.

        Returns:
            str: Raw text payload returned by the model.

        Raises:
            GeminiProviderError: If the API call fails or the model returns an empty payload.
        """
        try:
            logger.info(f"Sending generation request to Gemini model '{self.model_name}'...")
            
            # Configure generation using native system_instruction support
            config = types.GenerateContentConfig(
                system_instruction=prompt.system_prompt,
                response_mime_type="application/json"  # Guide model to return JSON structure
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt.user_prompt,
                config=config
            )

            if not response or not response.text:
                logger.error("Gemini returned an empty response.")
                raise GeminiProviderError("Gemini API call succeeded but returned an empty response.")

            logger.info("Successfully received text response from Gemini.")
            return response.text

        except GeminiProviderError:
            raise
        except Exception as exc:
            logger.error(f"Error during Gemini text generation: {exc}", exc_info=True)
            raise GeminiProviderError(f"Gemini content generation failed: {exc}") from exc
