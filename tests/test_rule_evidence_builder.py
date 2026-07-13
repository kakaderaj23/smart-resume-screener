"""
Unit tests for RuleEvidenceBuilder.
"""

import pytest
from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata
from app.schemas.match import JobRequirements, RuleEvidence
from app.services.rule_evidence_builder import RuleEvidenceBuilder


@pytest.fixture
def builder() -> RuleEvidenceBuilder:
    """Fixture providing a clean RuleEvidenceBuilder instance."""
    return RuleEvidenceBuilder()


@pytest.fixture
def dummy_profile() -> CandidateProfile:
    """Fixture providing a dummy candidate profile for validation."""
    return CandidateProfile(
        personal_info=PersonalInfo(full_name="Jane Doe"),
        professional_info=ProfessionalInfo(
            skills=["Python", "FastAPI", "Docker", "PostgreSQL"]
        ),
        metadata=Metadata(parser_version="test")
    )


def test_compare_skills_full_match(builder: RuleEvidenceBuilder, dummy_profile: CandidateProfile):
    """Test full matching of required skills case-insensitively."""
    requirements = JobRequirements(required_skills=["python", "fastapi"])
    evidence = builder.compare_skills(dummy_profile, requirements)

    assert isinstance(evidence, RuleEvidence)
    assert evidence.matched_skills == ["python", "fastapi"]
    assert evidence.missing_skills == []
    assert evidence.skill_overlap_percentage == 100.0
    assert evidence.required_skill_count == 2
    assert evidence.matched_skill_count == 2


def test_compare_skills_partial_match(builder: RuleEvidenceBuilder, dummy_profile: CandidateProfile):
    """Test partial matching of required skills."""
    requirements = JobRequirements(required_skills=["Python", "Kubernetes", "docker"])
    evidence = builder.compare_skills(dummy_profile, requirements)

    assert evidence.matched_skills == ["Python", "docker"]
    assert evidence.missing_skills == ["Kubernetes"]
    assert evidence.skill_overlap_percentage == 66.67
    assert evidence.required_skill_count == 3
    assert evidence.matched_skill_count == 2


def test_compare_skills_no_match(builder: RuleEvidenceBuilder, dummy_profile: CandidateProfile):
    """Test when none of the required skills match."""
    requirements = JobRequirements(required_skills=["AWS", "React"])
    evidence = builder.compare_skills(dummy_profile, requirements)

    assert evidence.matched_skills == []
    assert evidence.missing_skills == ["AWS", "React"]
    assert evidence.skill_overlap_percentage == 0.0
    assert evidence.required_skill_count == 2
    assert evidence.matched_skill_count == 0


def test_compare_skills_empty_requirements(builder: RuleEvidenceBuilder, dummy_profile: CandidateProfile):
    """Test behavior when required skills is empty."""
    requirements = JobRequirements(required_skills=[])
    evidence = builder.compare_skills(dummy_profile, requirements)

    assert evidence.matched_skills == []
    assert evidence.missing_skills == []
    assert evidence.skill_overlap_percentage == 0.0
    assert evidence.required_skill_count == 0
    assert evidence.matched_skill_count == 0
