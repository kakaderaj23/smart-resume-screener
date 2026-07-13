"""
Groq LLM Provider implementation using the official Groq SDK and models (e.g. openai/gpt-oss-120b).
"""

import os
import logging
from groq import Groq, GroqError

from app.config import settings
from app.providers.base_provider import BaseLLMProvider
from app.schemas.match import PromptPackage

logger = logging.getLogger("smart-resume-screener.providers.groq")


class ProviderError(Exception):
    """Base exception class for all LLM provider errors."""
    pass


class GroqProviderError(ProviderError):
    """Raised when an error occurs during generation with the Groq provider."""
    pass


class GroqProvider(BaseLLMProvider):
    """
    Adapter for Groq models (such as openai/gpt-oss-120b or llama-3.3-70b-versatile) using the official groq SDK.
    """

    def __init__(self) -> None:
        """
        Initialize the Groq Client using configured settings.
        Raises GroqProviderError if no API key is available.
        """
        api_key = (
            settings.GROQ_API_KEY 
            or settings.XAI_API_KEY 
            or os.environ.get("GROQ_API_KEY") 
            or os.environ.get("XAI_API_KEY")
        )
        if not api_key:
            logger.error("Groq API initialization failed: API key not found in settings or environment.")
            raise GroqProviderError(
                "Groq API key is not configured. Please set the GROQ_API_KEY environment variable."
            )

        self.model_name = settings.GROQ_MODEL or "openai/gpt-oss-120b"
        try:
            # Initialize official Client from groq SDK
            self.client = Groq(api_key=api_key)
            logger.info(f"Groq Client initialized successfully using model: {self.model_name}")
        except Exception as exc:
            logger.error(f"Failed to initialize Groq Client: {exc}", exc_info=True)
            raise GroqProviderError(f"Failed to initialize Groq Client: {exc}") from exc

    def generate(self, prompt: PromptPackage) -> str:
        """
        Send a PromptPackage context to Groq models and return the raw response text.

        Args:
            prompt (PromptPackage): Structured package holding system, user, and full prompts.

        Returns:
            str: Raw text payload returned by the model, expected to be structured JSON.

        Raises:
            GroqProviderError: If the API call fails or the model returns an empty payload.
        """
        try:
            logger.info(f"Sending generation request to Groq model '{self.model_name}'...")
            
            # Configure generation using messages list and response_format for strict JSON mode
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": prompt.system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt.user_prompt
                    }
                ],
                model=self.model_name,
                temperature=1,
                max_completion_tokens=3500,
                top_p=1,
                reasoning_effort="medium",
                response_format={"type": "json_object"}
            )

            if not chat_completion or not chat_completion.choices:
                logger.error("Groq returned no choices.")
                raise GroqProviderError("Groq API call succeeded but returned no choices.")

            choice = chat_completion.choices[0]
            if not choice.message or not choice.message.content:
                logger.error("Groq returned an empty response content.")
                raise GroqProviderError("Groq API call succeeded but returned an empty response.")

            logger.info("Successfully received text response from Groq.")
            return choice.message.content

        except GroqProviderError:
            raise
        except GroqError as exc:
            logger.error(f"Groq SDK error during text generation: {exc}", exc_info=True)
            raise GroqProviderError(f"Groq content generation failed: {exc}") from exc
        except Exception as exc:
            logger.error(f"Error during Groq text generation: {exc}", exc_info=True)
            raise GroqProviderError(f"Groq content generation failed: {exc}") from exc
