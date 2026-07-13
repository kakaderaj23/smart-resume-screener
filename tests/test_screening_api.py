"""
Unit tests for End-to-End Screening API endpoints.
Mocks the ResumeScreeningService dependency.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.api.screening import get_screening_service
from app.models.resume_record import ResumeRecord, ProcessingStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata
from app.schemas.match import JobRequirements, RuleEvidence, MatchResult, ConfidenceLevel
from app.schemas.screening import ScreeningResult
from app.services.recommendation_engine import Recommendation
from app.services.resume_screening_service import ResumeScreeningService

client = TestClient(app)


@pytest.fixture
def mock_service():
    """Mock the ResumeScreeningService orchestrator."""
    service = MagicMock(spec=ResumeScreeningService)
    app.dependency_overrides[get_screening_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def dummy_profile() -> CandidateProfile:
    """Fixture providing a mock candidate profile."""
    return CandidateProfile(
        personal_info=PersonalInfo(full_name="John Doe", email="john@example.com"),
        professional_info=ProfessionalInfo(skills=["Python", "FastAPI"]),
        metadata=Metadata(parser_version="test")
    )


@pytest.fixture
def dummy_requirements() -> JobRequirements:
    """Fixture providing mock job requirements."""
    return JobRequirements(required_skills=["Python", "FastAPI", "Docker"])


@pytest.fixture
def dummy_result(dummy_profile, dummy_requirements) -> ScreeningResult:
    """Fixture providing mock integrated ScreeningResult."""
    return ScreeningResult(
        candidate_profile=dummy_profile,
        job_requirements=dummy_requirements,
        rule_evidence=RuleEvidence(
            matched_skills=["Python", "FastAPI"],
            missing_skills=["Docker"],
            skill_overlap_percentage=66.67,
            required_skill_count=3,
            matched_skill_count=2
        ),
        match_result=MatchResult(
            semantic_score=8,
            confidence=ConfidenceLevel.HIGH,
            matched_skills=["Python", "FastAPI"],
            missing_skills=["Docker"],
            strengths=["Python backend expert"],
            weaknesses=["Docker gap"],
            evidence=[],
            justification="Good fit."
        ),
        recommendation=Recommendation.SHORTLIST,
        screened_at=datetime.now(timezone.utc)
    )


def test_post_screen_success(mock_service, dummy_result):
    """Test successful POST /screen candidate evaluation request."""
    mock_service.screen_candidate.return_value = dummy_result

    payload = {
        "resume_id": 42,
        "job_description": "We need a Python developer who knows FastAPI and Docker."
    }

    response = client.post("/screen", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["candidate_profile"]["personal_info"]["full_name"] == "John Doe"
    assert data["recommendation"] == "SHORTLIST"
    assert data["match_result"]["semantic_score"] == 8
    
    # Verify mock was called with correctly parsed skills
    mock_service.screen_candidate.assert_called_once()
    _, kwargs = mock_service.screen_candidate.call_args
    assert kwargs["resume_id"] == 42
    assert "Python" in kwargs["job_requirements"].required_skills
    assert "FastAPI" in kwargs["job_requirements"].required_skills
    assert "Docker" in kwargs["job_requirements"].required_skills


def test_post_screen_empty_description_returns_400():
    """Test POST /screen returns 400 Bad Request if job description is empty."""
    payload = {
        "resume_id": 42,
        "job_description": "   "
    }
    response = client.post("/screen", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in response.json()["detail"]


def test_post_screen_resume_not_found_returns_404(mock_service):
    """Test POST /screen returns 404 if the resume record is not found."""
    mock_service.screen_candidate.side_effect = ValueError("Resume record with ID 99 not found.")

    payload = {
        "resume_id": 99,
        "job_description": "Python Developer"
    }

    response = client.post("/screen", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


@patch("app.api.screening.ResumeRepository")
def test_get_screenings_summary_list(mock_repo_class):
    """Test GET /screenings returns processed summaries matching status MATCHED."""
    mock_repo = MagicMock(spec=ResumeRepository)
    mock_repo_class.return_value = mock_repo

    # Set up mock records
    record1 = MagicMock(spec=ResumeRecord)
    record1.id = 1
    record1.processing_status = ProcessingStatus.MATCHED
    record1.to_candidate_profile.return_value = CandidateProfile(
        personal_info=PersonalInfo(full_name="Alice Smith"),
        professional_info=ProfessionalInfo(skills=[]),
        metadata=Metadata()
    )
    record1.to_match_result.return_value = MatchResult(
        semantic_score=9,
        confidence=ConfidenceLevel.HIGH,
        matched_skills=[],
        missing_skills=[],
        strengths=[],
        weaknesses=[],
        evidence=[],
        justification="Superb."
    )
    record1.updated_at = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)

    # Record 2 with different status (should be skipped)
    record2 = MagicMock(spec=ResumeRecord)
    record2.processing_status = ProcessingStatus.UPLOADED

    mock_repo.list.return_value = [record1, record2]

    response = client.get("/screenings")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data) == 1
    assert data[0]["resume_id"] == 1
    assert data[0]["candidate_name"] == "Alice Smith"
    assert data[0]["semantic_score"] == 9
    assert data[0]["recommendation"] == "STRONG_HIRE"


@patch("app.api.screening.ResumeRepository")
def test_get_screening_detail_success(mock_repo_class, dummy_profile):
    """Test GET /screenings/{resume_id} returns reconstructed ScreeningResult for matched records."""
    mock_repo = MagicMock(spec=ResumeRepository)
    mock_repo_class.return_value = mock_repo

    record = MagicMock(spec=ResumeRecord)
    record.id = 42
    record.to_candidate_profile.return_value = dummy_profile
    record.to_match_result.return_value = MatchResult(
        semantic_score=6,
        confidence=ConfidenceLevel.MEDIUM,
        matched_skills=["Python"],
        missing_skills=["Docker"],
        strengths=[],
        weaknesses=[],
        evidence=[],
        justification="Okay."
    )
    record.updated_at = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
    mock_repo.get.return_value = record

    response = client.get("/screenings/42")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["candidate_profile"]["personal_info"]["full_name"] == "John Doe"
    assert data["recommendation"] == "CONSIDER"
    assert data["match_result"]["semantic_score"] == 6
    assert "Python" in data["job_requirements"]["required_skills"]
    assert "Docker" in data["job_requirements"]["required_skills"]


@patch("app.api.screening.ResumeRepository")
def test_get_screening_detail_not_found(mock_repo_class):
    """Test GET /screenings/{resume_id} returns 404 Not Found if record is missing or not processed."""
    mock_repo = MagicMock(spec=ResumeRepository)
    mock_repo_class.return_value = mock_repo
    mock_repo.get.return_value = None

    response = client.get("/screenings/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]
