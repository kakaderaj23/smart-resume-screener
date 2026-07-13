"""
Base provider interface for abstracting LLM interactions.
"""

from abc import ABC, abstractmethod
from app.schemas.match import PromptPackage


class BaseLLMProvider(ABC):
    """
    Abstract Base Class defining the contract for all LLM providers.
    Ensures provider independence across Gemini, OpenAI, Claude, and others.
    """

    @abstractmethod
    def generate(self, prompt: PromptPackage) -> str:
        """
        Generate a text response from the LLM provider based on a structured PromptPackage.

        Args:
            prompt (PromptPackage): Structured package holding system, user, and full prompt contents.

        Returns:
            str: Raw generated string response from the provider, expected to be structured JSON.
        """
        pass
