"""
PromptBuilder service for dynamic prompt assembly and schema integration.
"""

import json
from typing import Optional
from app.prompts import get_system_prompt, get_matching_prompt_template
from app.schemas.candidate import CandidateProfile
from app.schemas.match import JobRequirements, RuleEvidence, PromptPackage, MatchResult

# Structured, formatting-aligned few-shot demonstration
FEW_SHOT_EXAMPLE = (
    "Input Candidate Profile:\n"
    "Name: John Doe, Email: john@example.com\n"
    "Skills: [Python, FastAPI, Postgres]\n\n"
    "Job Requirements:\n"
    "Required Skills: [Python, FastAPI, Kubernetes]\n\n"
    "Deterministic Rule Evidence:\n"
    "Matched Skills: [Python, FastAPI], Missing Skills: [Kubernetes], Overlap: 66.67%\n\n"
    "Expected Output JSON:\n"
    "{\n"
    '  "semantic_score": 7,\n'
    '  "confidence": "MEDIUM",\n'
    '  "matched_skills": ["Python", "FastAPI"],\n'
    '  "missing_skills": ["Kubernetes"],\n'
    '  "strengths": ["Strong experience with Python backend development using FastAPI."],\n'
    '  "weaknesses": ["Lacks direct experience with Kubernetes specified in required skills."],\n'
    '  "evidence": [\n'
    '    {\n'
    '      "category": "Specific Skill",\n'
    '      "resume_excerpt": "Backend Development with Python & FastAPI",\n'
    '      "job_requirement": "Python, FastAPI"\n'
    '    }\n'
    '  ],\n'
    '  "justification": "The candidate has solid experience in the primary backend stack (Python and FastAPI) representing a good fit, but misses container orchestration (Kubernetes) required for the deployment infrastructure."\n'
    "}"
)


class PromptBuilder:
    """
    Service responsible for dynamic assembly of prompts sent to LLM providers.
    Consumes structured domain models and templates to generate a structured PromptPackage.
    """

    def build_matching_prompt(
        self,
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements,
        rule_evidence: RuleEvidence,
        raw_text: Optional[str] = None
    ) -> PromptPackage:
        """
        Assemble the structured PromptPackage for LLM matching evaluations.

        Loads system instructions, formats user request placeholders using JSON-serialized
        domain inputs and raw resume text, generates model JSON schema definitions, and packages them cleanly.

        Args:
            candidate_profile (CandidateProfile): Candidate contact and experience metadata.
            job_requirements (JobRequirements): Structured job requirements.
            rule_evidence (RuleEvidence): Fact-based deterministic comparison outcomes.
            raw_text (Optional[str]): Original raw text extracted from the candidate's resume.

        Returns:
            PromptPackage: Type-safe package containing system, user, and full prompt views.
        """
        system_prompt = get_system_prompt()
        user_template = get_matching_prompt_template()

        # Serialize Pydantic objects to clean JSON strings for clear prompt structure
        candidate_str = candidate_profile.model_dump_json(indent=2)
        requirements_str = job_requirements.model_dump_json(indent=2)
        evidence_str = rule_evidence.model_dump_json(indent=2)
        raw_text_str = raw_text.strip() if (raw_text and raw_text.strip()) else "No original resume text provided."

        # Generate output JSON schema specification dynamically from the Pydantic schema
        schema_json = json.dumps(MatchResult.model_json_schema(), indent=2)

        # Inject runtime details into user template
        user_prompt = user_template.format(
            candidate_profile=candidate_str,
            raw_text=raw_text_str,
            job_requirements=requirements_str,
            rule_evidence=evidence_str,
            json_schema=schema_json,
            few_shot_example=FEW_SHOT_EXAMPLE
        )

        # Construct single string view for legacy or simpler text endpoints
        full_prompt = f"System Instruction:\n{system_prompt}\n\nUser Request:\n{user_prompt}"

        return PromptPackage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            full_prompt=full_prompt
        )


# Class alias for clean matching orchestration layout matching Part 3 requirements
PromptRenderer = PromptBuilder
