"""
RuleEvidenceBuilder service for deterministic evaluation of candidates against job requirements.
"""

import logging
from app.schemas.candidate import CandidateProfile
from app.schemas.match import JobRequirements, RuleEvidence

logger = logging.getLogger("smart-resume-screener.services.rule_evidence_builder")


class RuleEvidenceBuilder:
    """
    Builder responsible for comparing a CandidateProfile against JobRequirements deterministically.
    Performs case-insensitive matching without AI heuristics.
    """

    def compare_skills(
        self,
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements
    ) -> RuleEvidence:
        """
        Compare the candidate's skills against required job skills case-insensitively
        and return a strongly-typed RuleEvidence object.
        """
        candidate_skills = candidate_profile.professional_info.skills or []
        required_skills = job_requirements.required_skills or []

        if not required_skills:
            logger.info("No required skills specified in job requirements. Returning empty RuleEvidence.")
            return RuleEvidence(
                matched_skills=[],
                missing_skills=[],
                skill_overlap_percentage=0.0,
                required_skill_count=0,
                matched_skill_count=0
            )

        # Normalize candidate skills for case-insensitive matching
        candidate_skills_normalized = {skill.strip().lower() for skill in candidate_skills if skill.strip()}

        matched_skills = []
        missing_skills = []

        # Compare required skills against normalized candidate skills
        for req_skill in required_skills:
            req_skill_clean = req_skill.strip()
            if not req_skill_clean:
                continue
            if req_skill_clean.lower() in candidate_skills_normalized:
                matched_skills.append(req_skill_clean)
            else:
                missing_skills.append(req_skill_clean)

        required_count = len(required_skills)
        matched_count = len(matched_skills)
        overlap_percentage = round((matched_count / required_count) * 100.0, 2) if required_count > 0 else 0.0

        evidence = RuleEvidence(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            skill_overlap_percentage=overlap_percentage,
            required_skill_count=required_count,
            matched_skill_count=matched_count
        )

        logger.info(
            f"Skill match complete -> Required: {required_count}, Matched: {matched_count}, "
            f"Overlap: {overlap_percentage}%"
        )
        return evidence
