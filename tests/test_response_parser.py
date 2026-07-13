"""
Unit tests for LLMResponseParser validating markdown cleaning, JSON formatting, and schema compatibility.
"""

import pytest
from app.schemas.match import MatchResult, ConfidenceLevel
from app.services.response_parser import (
    LLMResponseParser,
    MalformedJSONError,
    InvalidLLMResponseError
)


@pytest.fixture
def parser() -> LLMResponseParser:
    """Fixture providing a clean LLMResponseParser instance."""
    return LLMResponseParser()


def test_parser_valid_json(parser: LLMResponseParser):
    """Test parsing a clean, well-formatted JSON string matching MatchResult schema."""
    raw_json = """
    {
        "semantic_score": 8,
        "confidence": "HIGH",
        "matched_skills": ["Python", "FastAPI"],
        "missing_skills": ["C++"],
        "strengths": ["Excellent API design patterns."],
        "weaknesses": ["No low-level systems programming experience."],
        "evidence": [
            {
                "category": "Experience",
                "resume_excerpt": "Designed REST APIs using Python & FastAPI",
                "job_requirement": "Python backends"
            }
        ],
        "justification": "Candidate has solid experience in relevant technologies."
    }
    """
    result = parser.parse_match_result(raw_json)
    
    assert isinstance(result, MatchResult)
    assert result.semantic_score == 8
    assert result.confidence == ConfidenceLevel.HIGH
    assert len(result.matched_skills) == 2
    assert result.matched_skills[0] == "Python"
    assert result.evidence[0].category == "Experience"


def test_parser_markdown_fenced_json(parser: LLMResponseParser):
    """Test parsing JSON enclosed within markdown code blocks (```json ... ```)."""
    raw_markdown = """
    ```json
    {
        "semantic_score": 5,
        "confidence": "MEDIUM",
        "matched_skills": ["Python"],
        "missing_skills": [],
        "strengths": [],
        "weaknesses": [],
        "evidence": [],
        "justification": "Adequate skills."
    }
    ```
    """
    result = parser.parse_match_result(raw_markdown)
    
    assert isinstance(result, MatchResult)
    assert result.semantic_score == 5
    assert result.confidence == ConfidenceLevel.MEDIUM
    assert result.justification == "Adequate skills."


def test_parser_malformed_json_raises_malformed_json_error(parser: LLMResponseParser):
    """Test that malformed JSON raises MalformedJSONError."""
    malformed_raw = '{"semantic_score": 8, "confidence": "HIGH", "matched_skills": ["Python"'  # Missing brackets/quotes
    
    with pytest.raises(MalformedJSONError) as exc_info:
        parser.parse_match_result(malformed_raw)
        
    assert "malformed or unparseable" in str(exc_info.value)


def test_parser_missing_fields_raises_invalid_llm_response_error(parser: LLMResponseParser):
    """Test that missing required fields (e.g. justification) raises InvalidLLMResponseError."""
    missing_fields_raw = """
    {
        "semantic_score": 8,
        "confidence": "HIGH",
        "matched_skills": [],
        "missing_skills": [],
        "strengths": [],
        "weaknesses": [],
        "evidence": []
        // Missing "justification" field
    }
    """
    with pytest.raises(InvalidLLMResponseError) as exc_info:
        parser.parse_match_result(missing_fields_raw)
        
    assert "justification" in str(exc_info.value)


def test_parser_invalid_schema_score_out_of_range(parser: LLMResponseParser):
    """Test that validation fails (InvalidLLMResponseError) when field values violate constraints (e.g. score=11)."""
    invalid_score_raw = """
    {
        "semantic_score": 11,
        "confidence": "HIGH",
        "matched_skills": [],
        "missing_skills": [],
        "strengths": [],
        "weaknesses": [],
        "evidence": [],
        "justification": "Out of bounds."
    }
    """
    with pytest.raises(InvalidLLMResponseError) as exc_info:
        parser.parse_match_result(invalid_score_raw)
        
    assert "semantic_score" in str(exc_info.value)


def test_parser_invalid_schema_confidence_level_value(parser: LLMResponseParser):
    """Test validation fails when enum value is invalid (e.g., confidence='SUPER_HIGH')."""
    invalid_enum_raw = """
    {
        "semantic_score": 7,
        "confidence": "SUPER_HIGH",
        "matched_skills": [],
        "missing_skills": [],
        "strengths": [],
        "weaknesses": [],
        "evidence": [],
        "justification": "Invalid enum."
    }
    """
    with pytest.raises(InvalidLLMResponseError) as exc_info:
        parser.parse_match_result(invalid_enum_raw)
        
    assert "confidence" in str(exc_info.value)
