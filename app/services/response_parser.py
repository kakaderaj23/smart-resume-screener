"""
LLM Response Parser service for extracting, parsing, and validating JSON match results.
"""

import json
import logging
from pydantic import ValidationError

from app.schemas.match import MatchResult

logger = logging.getLogger("smart-resume-screener.services.response_parser")


class LLMResponseError(Exception):
    """Base exception class for all response parsing and validation errors."""
    pass


class MalformedJSONError(LLMResponseError):
    """Raised when the LLM response cannot be parsed as valid JSON."""
    pass


class InvalidLLMResponseError(LLMResponseError):
    """Raised when the parsed JSON fails validation against the MatchResult Pydantic schema."""
    pass


class LLMResponseParser:
    """
    Parser responsible for cleaning raw LLM strings, extracting JSON structures,
    and validating them against Pydantic schema contracts.
    """

    def parse_match_result(self, raw_response: str) -> MatchResult:
        """
        Clean, parse, and validate the raw text response from the LLM into a MatchResult.

        Workflow:
        1. Remove markdown code fences if present (e.g. ```json ... ```).
        2. Attempt standard JSON parsing.
        3. If standard parsing fails, fallback to extracting characters between first '{' and last '}'.
        4. Validate the resulting dict against Pydantic MatchResult contracts.
        5. Raise domain exceptions with clear, descriptive error details upon failure.

        Args:
            raw_response (str): The raw string output from the LLM.

        Returns:
            MatchResult: Validated assessment domain object.

        Raises:
            MalformedJSONError: If the string contains invalid or unparseable JSON.
            InvalidLLMResponseError: If the JSON is valid but does not match the Pydantic schema.
        """
        if not raw_response or not raw_response.strip():
            logger.error("Received empty response from LLM provider.")
            raise MalformedJSONError("LLM response is empty or contains only whitespace.")

        cleaned = raw_response.strip()

        # 1. Clean markdown code fences if they wrap the response
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline:].strip()
            else:
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        # Remove any lingering fence keywords
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # 2. Parse JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # 3. Bracket extraction fallback if conversational text wraps the JSON
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    data = json.loads(cleaned[start_idx:end_idx + 1])
                except json.JSONDecodeError as inner_exc:
                    logger.error(f"Malformed JSON after bracket isolation fallback: {inner_exc}")
                    raise MalformedJSONError(
                        f"LLM response contains malformed or unparseable JSON: {inner_exc}"
                    ) from inner_exc
            else:
                logger.error(f"Malformed JSON: {exc}")
                raise MalformedJSONError(
                    f"LLM response contains malformed or unparseable JSON: {exc}"
                ) from exc

        # 4. Validate against Pydantic model contracts
        try:
            return MatchResult.model_validate(data)
        except ValidationError as exc:
            logger.error(f"Pydantic validation of MatchResult failed: {exc}")
            # Format and aggregate specific validation errors for domain-level debugging
            error_details = []
            for err in exc.errors():
                loc_path = " -> ".join(str(loc_item) for loc_item in err["loc"])
                error_details.append(f"[{loc_path}]: {err['msg']} (input_value={err.get('input')})")
            
            detail_str = "; ".join(error_details)
            raise InvalidLLMResponseError(
                f"LLM response JSON is valid but does not conform to MatchResult schema: {detail_str}"
            ) from exc
