"""
xAI (Grok) LLM Provider implementation using the official OpenAI-compatible Python SDK.
"""

import os
import logging
from openai import OpenAI, OpenAIError

from app.config import settings
from app.providers.base_provider import BaseLLMProvider
from app.schemas.match import PromptPackage

logger = logging.getLogger("smart-resume-screener.providers.xai")


class ProviderError(Exception):
    """Base exception class for all LLM provider errors."""
    pass


class XAIProviderError(ProviderError):
    """Raised when an error occurs during generation with the xAI provider."""
    pass


class XAIProvider(BaseLLMProvider):
    """
    Adapter for xAI (Grok) models via the OpenAI-compatible REST API (`https://api.x.ai/v1`).
    """

    def __init__(self) -> None:
        """
        Initialize the xAI Client using configured settings.
        Raises XAIProviderError if no API key is available.
        """
        api_key = settings.XAI_API_KEY or os.environ.get("XAI_API_KEY")
        if not api_key:
            logger.error("xAI API initialization failed: API key not found in settings or environment.")
            raise XAIProviderError(
                "xAI API key is not configured. Please set the XAI_API_KEY environment variable."
            )

        self.model_name = settings.XAI_MODEL or "grok-2-latest"
        try:
            # Initialize official OpenAI SDK client pointed at xAI base URL
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )
            logger.info(f"xAI Client initialized successfully using model: {self.model_name}")
        except Exception as exc:
            logger.error(f"Failed to initialize xAI Client: {exc}", exc_info=True)
            raise XAIProviderError(f"Failed to initialize xAI Client: {exc}") from exc

    def generate(self, prompt: PromptPackage) -> str:
        """
        Send a PromptPackage context to xAI models and return the raw response text.

        Args:
            prompt (PromptPackage): Structured package holding system, user, and full prompts.

        Returns:
            str: Raw text payload returned by the model, expected to be structured JSON.

        Raises:
            XAIProviderError: If the API call fails or the model returns an empty payload.
        """
        try:
            logger.info(f"Sending generation request to xAI model '{self.model_name}'...")
            
            # Configure generation using messages list and response_format for JSON mode
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
                response_format={"type": "json_object"}
            )

            if not chat_completion or not chat_completion.choices:
                logger.error("xAI returned no choices.")
                raise XAIProviderError("xAI API call succeeded but returned no choices.")

            choice = chat_completion.choices[0]
            if not choice.message or not choice.message.content:
                logger.error("xAI returned an empty response content.")
                raise XAIProviderError("xAI API call succeeded but returned an empty response.")

            logger.info("Successfully received text response from xAI.")
            return choice.message.content

        except XAIProviderError:
            raise
        except OpenAIError as exc:
            logger.error(f"OpenAI/xAI SDK error during text generation: {exc}", exc_info=True)
            raise XAIProviderError(f"xAI content generation failed: {exc}") from exc
        except Exception as exc:
            logger.error(f"Error during xAI text generation: {exc}", exc_info=True)
            raise XAIProviderError(f"xAI content generation failed: {exc}") from exc
