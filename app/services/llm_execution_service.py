"""
LLMExecutionService orchestrating base providers and validation parsers.
"""

import logging
from app.providers.base_provider import BaseLLMProvider
from app.services.response_parser import LLMResponseParser
from app.schemas.match import PromptPackage, MatchResult

logger = logging.getLogger("smart-resume-screener.services.llm_execution")


class LLMExecutionService:
    """
    Execution service coordinating provider calls and output response parsing.
    Maintains clean separation between provider communication and syntax validation.
    """

    def __init__(self, provider: BaseLLMProvider, parser: LLMResponseParser) -> None:
        """
        Inject provider and parser dependencies.
        """
        self.provider = provider
        self.parser = parser

    def execute(self, prompt: PromptPackage) -> MatchResult:
        """
        Submit a PromptPackage to the configured LLM provider and parse the result.

        Args:
            prompt (PromptPackage): The structured prompt package to be generated.

        Returns:
            MatchResult: Parsed and schema-validated match result assessment object.
        """
        logger.info("Initiating LLM generation request...")
        raw_response = self.provider.generate(prompt)
        
        logger.info("LLM generation response received. Initiating parse and validation...")
        return self.parser.parse_match_result(raw_response)
