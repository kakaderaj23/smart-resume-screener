"""
Unit tests for ResumeScreeningService verifying complete pipeline orchestration.
"""

from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from app.models.resume_record import ResumeRecord, ProcessingStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata
from app.schemas.match import JobRequirements, RuleEvidence, PromptPackage, MatchResult, ConfidenceLevel
from app.schemas.screening import ScreeningResult
from app.services.rule_evidence_builder import RuleEvidenceBuilder
from app.services.prompt_builder import PromptRenderer
from app.services.llm_execution_service import LLMExecutionService
from app.services.recommendation_engine import RecommendationEngine, Recommendation
from app.services.resume_screening_service import ResumeScreeningService


@pytest.fixture
def mock_dependencies():
    """Fixture providing mocks for all orchestrated service components."""
    repository = MagicMock(spec=ResumeRepository)
    evidence_builder = MagicMock(spec=RuleEvidenceBuilder)
    prompt_renderer = MagicMock(spec=PromptRenderer)
    execution_service = MagicMock(spec=LLMExecutionService)
    recommendation_engine = MagicMock(spec=RecommendationEngine)
    
    return repository, evidence_builder, prompt_renderer, execution_service, recommendation_engine


@pytest.fixture
def screening_service(mock_dependencies) -> ResumeScreeningService:
    """Fixture providing a ResumeScreeningService instance with mock dependencies."""
    repository, evidence_builder, prompt_renderer, execution_service, recommendation_engine = mock_dependencies
    return ResumeScreeningService(
        repository=repository,
        evidence_builder=evidence_builder,
        prompt_renderer=prompt_renderer,
        execution_service=execution_service,
        recommendation_engine=recommendation_engine
    )


@pytest.fixture
def dummy_profile() -> CandidateProfile:
    """Fixture providing a clean candidate profile."""
    return CandidateProfile(
        personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com"),
        professional_info=ProfessionalInfo(skills=["Python", "FastAPI"]),
        metadata=Metadata(parser_version="test")
    )


@pytest.fixture
def dummy_requirements() -> JobRequirements:
    """Fixture providing clean job requirements."""
    return JobRequirements(required_skills=["Python", "FastAPI", "Kubernetes"])


def test_screen_candidate_orchestration_flow_success(
    screening_service: ResumeScreeningService,
    mock_dependencies,
    dummy_profile: CandidateProfile,
    dummy_requirements: JobRequirements
):
    """
    Test successful candidate screening to verify that:
    - ResumeRecord is loaded and deserialized.
    - Skills are compared deterministically.
    - Prompts are built and sent to LLMExecutionService.
    - Hiring recommendations are determined via RecommendationEngine.
    - ResumeRecord is updated with the latest MatchResult and MATCHED status.
    - Correctly populated ScreeningResult is returned.
    """
    repository, evidence_builder, prompt_renderer, execution_service, recommendation_engine = mock_dependencies
    db = MagicMock(spec=Session)

    # 1. Setup mock ResumeRecord behavior
    mock_record = MagicMock(spec=ResumeRecord)
    mock_record.id = 42
    mock_record.original_filename = "Jane_Doe_CV.pdf"
    mock_record.raw_text = "Jane Doe Resume Raw Text"
    mock_record.to_candidate_profile.return_value = dummy_profile
    repository.get.return_value = mock_record

    # 2. Setup mock RuleEvidenceBuilder behavior
    dummy_evidence = RuleEvidence(
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Kubernetes"],
        skill_overlap_percentage=66.67,
        required_skill_count=3,
        matched_skill_count=2
    )
    evidence_builder.compare_skills.return_value = dummy_evidence

    # 3. Setup mock PromptRenderer behavior
    dummy_prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")
    prompt_renderer.build_matching_prompt.return_value = dummy_prompt

    # 4. Setup mock LLMExecutionService behavior
    dummy_match = MatchResult(
        semantic_score=8,
        confidence=ConfidenceLevel.HIGH,
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Kubernetes"],
        strengths=["FastAPI expert"],
        weaknesses=["Kubernetes gap"],
        evidence=[],
        justification="Strong technical match."
    )
    execution_service.execute.return_value = dummy_match

    # 5. Setup mock RecommendationEngine behavior
    recommendation_engine.generate_recommendation.return_value = Recommendation.SHORTLIST

    # Execute orchestrator method
    result = screening_service.screen_candidate(db, resume_id=42, job_requirements=dummy_requirements)

    # Verify return types and payload integration
    assert isinstance(result, ScreeningResult)
    assert result.candidate_profile == dummy_profile
    assert result.job_requirements == dummy_requirements
    assert result.rule_evidence == dummy_evidence
    assert result.match_result == dummy_match
    assert result.recommendation == Recommendation.SHORTLIST
    assert result.screened_at is not None

    # Verify execution flow sequences and parameters passed
    repository.get.assert_called_once_with(db, 42)
    mock_record.to_candidate_profile.assert_called_once()
    
    evidence_builder.compare_skills.assert_called_once_with(dummy_profile, dummy_requirements)
    
    prompt_renderer.build_matching_prompt.assert_called_once_with(
        candidate_profile=dummy_profile,
        job_requirements=dummy_requirements,
        rule_evidence=dummy_evidence,
        raw_text="Jane Doe Resume Raw Text"
    )
    
    execution_service.execute.assert_called_once_with(dummy_prompt)
    
    recommendation_engine.generate_recommendation.assert_called_once_with(8)

    # Verify database updates and state transitions
    mock_record.from_match_result.assert_called_once_with(dummy_match)
    assert mock_record.processing_status == ProcessingStatus.MATCHED
    repository.update.assert_called_once_with(db, mock_record)


def test_screen_candidate_record_not_found(
    screening_service: ResumeScreeningService,
    mock_dependencies,
    dummy_requirements: JobRequirements
):
    """
    Test that screen_candidate raises ValueError if the resume record is not found in database.
    """
    repository, _, _, _, _ = mock_dependencies
    db = MagicMock(spec=Session)
    repository.get.return_value = None

    with pytest.raises(ValueError) as exc_info:
        screening_service.screen_candidate(db, resume_id=99, job_requirements=dummy_requirements)

    assert "not found" in str(exc_info.value)


def test_screen_candidate_profile_not_parsed(
    screening_service: ResumeScreeningService,
    mock_dependencies,
    dummy_requirements: JobRequirements
):
    """
    Test that screen_candidate raises ValueError if the candidate profile has not been parsed yet (None).
    """
    repository, _, _, _, _ = mock_dependencies
    db = MagicMock(spec=Session)

    mock_record = MagicMock(spec=ResumeRecord)
    mock_record.to_candidate_profile.return_value = None
    repository.get.return_value = mock_record

    with pytest.raises(ValueError) as exc_info:
        screening_service.screen_candidate(db, resume_id=42, job_requirements=dummy_requirements)

    assert "does not have a parsed candidate profile" in str(exc_info.value)
