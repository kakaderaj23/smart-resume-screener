"""
ScreeningResult schema representing the canonical output of candidate screening.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.schemas.candidate import CandidateProfile
from app.schemas.match import JobRequirements, RuleEvidence, MatchResult
from app.services.recommendation_engine import Recommendation


class ScreeningResult(BaseModel):
    """
    Canonical output contract of the resume screening pipeline.
    Combines parsed candidate profile details, specific job expectations,
    rule evidence metrics, LLM match assessments, and final recommendations.
    """
    candidate_profile: CandidateProfile = Field(
        ...,
        description="Structured candidate profile details extracted from resume raw text."
    )
    job_requirements: JobRequirements = Field(
        ...,
        description="Structured job requirements compared against the candidate."
    )
    rule_evidence: RuleEvidence = Field(
        ...,
        description="Deterministic skill matching overlap calculations and metadata."
    )
    match_result: MatchResult = Field(
        ...,
        description="Subjective and semantic fit evaluations from the LLM engine."
    )
    recommendation: Recommendation = Field(
        ...,
        description="Final deterministic hiring recommendation based on semantic score."
    )
    screened_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the screening evaluation was performed."
    )
