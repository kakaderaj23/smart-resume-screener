"""
API endpoints for candidate screening operations.
"""

from datetime import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resume_record import ResumeRecord, ProcessingStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.match import JobRequirements, MatchResult
from app.schemas.screening import ScreeningResult
from app.services.job_parser import JobDescriptionParser
from app.services.recommendation_engine import RecommendationEngine, Recommendation
from app.services.rule_evidence_builder import RuleEvidenceBuilder
from app.services.resume_screening_service import ResumeScreeningService

logger = logging.getLogger("smart-resume-screener.api.screening")

router = APIRouter(
    prefix="",
    tags=["Screening"]
)


class ScreenRequest(BaseModel):
    """
    HTTP POST request payload for initiating candidate screening.
    """
    resume_id: int = Field(..., description="Database primary key ID of the candidate's resume.")
    job_description: str = Field(..., description="Raw text of the job description to screen against.")


class ScreeningSummary(BaseModel):
    """
    HTTP GET response model summarizing completed resume evaluations.
    """
    resume_id: int = Field(..., description="Database primary key ID of the resume.")
    candidate_name: Optional[str] = Field(None, description="Candidate's full name.")
    semantic_score: Optional[int] = Field(None, description="Model semantic matching score (1-10).")
    recommendation: Optional[Recommendation] = Field(None, description="Deterministic recommendation status.")
    screened_at: Optional[datetime] = Field(None, description="Timestamp of the screening execution.")


def get_screening_service(db: Session = Depends(get_db)) -> ResumeScreeningService:
    """
    FastAPI dependency injecting the instantiated ResumeScreeningService orchestrator.
    """
    from app.services.prompt_builder import PromptRenderer
    from app.services.llm_execution_service import LLMExecutionService
    from app.providers.gemini_provider import GeminiProvider
    from app.services.response_parser import LLMResponseParser

    repository = ResumeRepository()
    evidence_builder = RuleEvidenceBuilder()
    prompt_renderer = PromptRenderer()
    
    # Instantiate LLM provider and parser adapters dynamically
    provider = GeminiProvider()
    parser = LLMResponseParser()
    execution_service = LLMExecutionService(provider, parser)
    
    recommendation_engine = RecommendationEngine()

    return ResumeScreeningService(
        repository=repository,
        evidence_builder=evidence_builder,
        prompt_renderer=prompt_renderer,
        execution_service=execution_service,
        recommendation_engine=recommendation_engine
    )


@router.post(
    "/screen",
    response_model=ScreeningResult,
    status_code=status.HTTP_200_OK,
    summary="Screen a candidate resume against a job description",
    description="Loads the resume by ID, extracts required skills deterministically from the job description, "
                "runs LLM-based semantic matching, and returns the integrated evaluation result."
)
async def screen_candidate(
    request: ScreenRequest,
    db: Session = Depends(get_db),
    screening_service: ResumeScreeningService = Depends(get_screening_service)
) -> ScreeningResult:
    """
    HTTP endpoint to trigger the end-to-end resume screening pipeline.
    """
    if not request.job_description or not request.job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text cannot be empty."
        )

    # 1. Deterministically parse required skills from job description
    parser = JobDescriptionParser()
    job_requirements = parser.parse(request.job_description)

    # 2. Invoke ResumeScreeningService orchestrator
    try:
        result = screening_service.screen_candidate(
            db=db,
            resume_id=request.resume_id,
            job_requirements=job_requirements
        )
        return result
    except ValueError as exc:
        # Business logic errors (e.g. resume not found, or profile not parsed yet)
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.error(f"Unexpected error during API candidate screening: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during candidate screening: {exc}"
        )


@router.get(
    "/screenings",
    response_model=List[ScreeningSummary],
    status_code=status.HTTP_200_OK,
    summary="List all processed screening summaries",
    description="Returns a list of all resume records that have completed evaluation and reached MATCHED status."
)
async def list_screenings(
    db: Session = Depends(get_db)
) -> List[ScreeningSummary]:
    """
    HTTP endpoint to list processed candidate evaluations.
    """
    repository = ResumeRepository()
    rec_engine = RecommendationEngine()

    try:
        # Load all records from database
        records = repository.list(db)
        summaries: List[ScreeningSummary] = []

        for record in records:
            # Exclude records that haven't reached the MATCHED stage yet
            if record.processing_status != ProcessingStatus.MATCHED:
                continue

            profile = record.to_candidate_profile()
            match_result = record.to_match_result()

            candidate_name = profile.personal_info.full_name if (profile and profile.personal_info) else "Unknown"
            score = match_result.semantic_score if match_result else None
            
            recommendation = None
            if score is not None:
                try:
                    recommendation = rec_engine.generate_recommendation(score)
                except ValueError:
                    pass

            summaries.append(ScreeningSummary(
                resume_id=record.id,
                candidate_name=candidate_name,
                semantic_score=score,
                recommendation=recommendation,
                screened_at=record.updated_at
            ))

        return summaries
    except Exception as exc:
        logger.error(f"Failed to query screenings: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while loading screening records."
        )


@router.get(
    "/screenings/{resume_id}",
    response_model=ScreeningResult,
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete screening result for a resume",
    description="Loads a candidate's evaluation, reconstructs requirements and rules evidence, "
                "and returns the integrated ScreeningResult contract."
)
async def get_screening(
    resume_id: int,
    db: Session = Depends(get_db)
) -> ScreeningResult:
    """
    HTTP endpoint to retrieve detailed screening evaluation details.
    """
    repository = ResumeRepository()
    record = repository.get(db, resume_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume record with ID {resume_id} not found."
        )

    profile = record.to_candidate_profile()
    match_result = record.to_match_result()

    if not profile or not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screening evaluation results have not been generated for resume ID {resume_id}."
        )

    # 1. Reconstruct JobRequirements from match evaluation skills categories
    all_req_skills = list(set(match_result.matched_skills + match_result.missing_skills))
    job_requirements = JobRequirements(required_skills=all_req_skills)

    # 2. Reconstruct RuleEvidence deterministically
    evidence_builder = RuleEvidenceBuilder()
    rule_evidence = evidence_builder.compare_skills(profile, job_requirements)

    # 3. Apply Recommendation rules
    rec_engine = RecommendationEngine()
    recommendation = rec_engine.generate_recommendation(match_result.semantic_score)

    return ScreeningResult(
        candidate_profile=profile,
        job_requirements=job_requirements,
        rule_evidence=rule_evidence,
        match_result=match_result,
        recommendation=recommendation,
        screened_at=record.updated_at
    )
