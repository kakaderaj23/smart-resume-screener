"""
ResumeScreeningService for orchestrating candidate screening pipelines.
"""

from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.models.resume_record import ResumeRecord, ProcessingStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.candidate import CandidateProfile
from app.schemas.match import JobRequirements, RuleEvidence, MatchResult
from app.schemas.screening import ScreeningResult
from app.services.rule_evidence_builder import RuleEvidenceBuilder
from app.services.prompt_builder import PromptRenderer
from app.services.llm_execution_service import LLMExecutionService
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger("smart-resume-screener.services.screening")


class ResumeScreeningService:
    """
    Orchestrator coordinating components of the candidate screening pipeline.
    Maintains clean boundaries between repositories, builders, execution engines,
    and business rule mapping services.
    """

    def __init__(
        self,
        repository: ResumeRepository,
        evidence_builder: RuleEvidenceBuilder,
        prompt_renderer: PromptRenderer,
        execution_service: LLMExecutionService,
        recommendation_engine: RecommendationEngine
    ) -> None:
        """
        Inject pipeline dependencies.
        """
        self.repository = repository
        self.evidence_builder = evidence_builder
        self.prompt_renderer = prompt_renderer
        self.execution_service = execution_service
        self.recommendation_engine = recommendation_engine

    def screen_candidate(
        self,
        db: Session,
        resume_id: int,
        job_requirements: JobRequirements
    ) -> ScreeningResult:
        """
        Orchestrate the end-to-end evaluation pipeline for an uploaded resume.

        Workflow:
        1. Load target ResumeRecord by ID.
        2. Deserialize CandidateProfile from stored JSON context.
        3. Deterministically compare skills using RuleEvidenceBuilder.
        4. Render structured PromptPackage using PromptRenderer (PromptBuilder).
        5. Submit prompt and parse response using LLMExecutionService.
        6. Apply deterministic business rules using RecommendationEngine.
        7. Persist latest match result JSON and transition state to MATCHED.
        8. Return final ScreeningResult envelope.

        Args:
            db (Session): Database transaction session.
            resume_id (int): Primary key ID of the target ResumeRecord.
            job_requirements (JobRequirements): Expectations to evaluate candidate against.

        Returns:
            ScreeningResult: Integrated candidate assessment envelope.
        """
        logger.info(f"Initiating screening pipeline for resume ID {resume_id}...")

        # 1. Load ResumeRecord
        record = self.repository.get(db, resume_id)
        if not record:
            logger.error(f"Screening failed: Resume ID {resume_id} not found in database.")
            raise ValueError(f"Resume record with ID {resume_id} not found.")

        # 2. Deserialize CandidateProfile
        profile = record.to_candidate_profile()
        if not profile:
            logger.error(f"Screening failed: Resume ID {resume_id} contains no parsed candidate profile.")
            raise ValueError(
                f"Resume ID {resume_id} does not have a parsed candidate profile. "
                "Ensure candidate profile extraction has completed successfully first."
            )

        # 3. Build RuleEvidence (deterministic comparison)
        rule_evidence = self.evidence_builder.compare_skills(profile, job_requirements)

        # 4. Render PromptPackage
        prompt_package = self.prompt_renderer.build_matching_prompt(
            candidate_profile=profile,
            job_requirements=job_requirements,
            rule_evidence=rule_evidence,
            raw_text=record.raw_text
        )

        # 5. Execute LLM via LLMExecutionService (includes provider generate & parser validation)
        match_result = self.execution_service.execute(prompt_package)

        # 6. Generate Recommendation using RecommendationEngine
        recommendation = self.recommendation_engine.generate_recommendation(match_result.semantic_score)

        # 7. Persist results and update processing status to MATCHED
        record.from_match_result(match_result)
        record.processing_status = ProcessingStatus.MATCHED
        self.repository.update(db, record)

        # 8. Build and return integrated ScreeningResult
        screening_result = ScreeningResult(
            candidate_profile=profile,
            job_requirements=job_requirements,
            rule_evidence=rule_evidence,
            match_result=match_result,
            recommendation=recommendation,
            screened_at=datetime.now(timezone.utc)
        )

        logger.info(f"Screening pipeline completed successfully for resume ID {resume_id}.")
        return screening_result
