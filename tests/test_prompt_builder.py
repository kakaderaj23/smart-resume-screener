"""
Unit tests for PromptBuilder.
"""

import pytest
from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata
from app.schemas.match import JobRequirements, RuleEvidence, PromptPackage
from app.services.prompt_builder import PromptBuilder


@pytest.fixture
def builder() -> PromptBuilder:
    """Fixture providing a clean PromptBuilder instance."""
    return PromptBuilder()


@pytest.fixture
def dummy_data():
    """Fixture providing structured input arguments for PromptBuilder."""
    profile = CandidateProfile(
        personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com"),
        professional_info=ProfessionalInfo(skills=["Python", "FastAPI"]),
        metadata=Metadata(parser_version="test")
    )
    requirements = JobRequirements(required_skills=["Python", "FastAPI", "Kubernetes"])
    evidence = RuleEvidence(
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Kubernetes"],
        skill_overlap_percentage=66.67,
        required_skill_count=3,
        matched_skill_count=2
    )
    return profile, requirements, evidence


def test_build_matching_prompt(builder: PromptBuilder, dummy_data):
    """
    Test PromptBuilder assembly to ensure:
    - Returns a valid PromptPackage.
    - System, user, and full prompt values are correctly populated.
    - User prompt contains structured JSON schema, profiles, requirements, and evidence strings.
    """
    profile, requirements, evidence = dummy_data
    package = builder.build_matching_prompt(profile, requirements, evidence)

    assert isinstance(package, PromptPackage)
    assert package.system_prompt is not None
    assert package.user_prompt is not None
    assert package.full_prompt is not None

    # Check key placeholders are formatted into the user prompt
    assert "Jane Doe" in package.user_prompt
    assert "jane@example.com" in package.user_prompt
    assert "Kubernetes" in package.user_prompt
    assert "66.67" in package.user_prompt
    assert "json_schema" not in package.user_prompt  # Placeholder should be replaced
    assert "semantic_score" in package.user_prompt  # Part of output schema definition
    assert "No original resume text provided." in package.user_prompt
    assert "Evaluate using BOTH:" in package.user_prompt


def test_build_matching_prompt_with_raw_text(builder: PromptBuilder, dummy_data):
    """
    Test PromptBuilder assembly when raw_text is explicitly passed, verifying that
    both the structured CandidateProfile and the raw resume text are included.
    """
    profile, requirements, evidence = dummy_data
    raw_resume = "Jane Doe Resume\nSkills: Python, FastAPI, Docker (2 years)\nContact: jane@example.com"
    package = builder.build_matching_prompt(profile, requirements, evidence, raw_text=raw_resume)

    assert "Jane Doe Resume" in package.user_prompt
    assert "Docker (2 years)" in package.user_prompt
    assert "Evaluate using BOTH:" in package.user_prompt
