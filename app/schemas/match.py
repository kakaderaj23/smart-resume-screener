"""
AI matching schemas and typing contracts for the Smart Resume Screener application.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """
    Strongly typed confidence indicators for matching evaluation.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class JobRequirements(BaseModel):
    """
    Structured job requirements parsed from job description or specified directly.
    """
    required_skills: List[str] = Field(
        default_factory=list,
        description="List of mandatory technical and professional skills."
    )
    preferred_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional nice-to-have technical skills."
    )
    minimum_experience: Optional[int] = Field(
        default=None,
        description="Minimum years of professional experience required."
    )
    education: Optional[str] = Field(
        default=None,
        description="Minimum educational level or degree required."
    )
    domain: Optional[str] = Field(
        default=None,
        description="Specific industry domain (e.g. Finance, Healthcare)."
    )


class RuleEvidence(BaseModel):
    """
    Deterministic skill overlap statistics computed by RuleEvidenceBuilder.
    Contains facts only, no subjective or AI-generated scoring.
    """
    matched_skills: List[str] = Field(
        default_factory=list,
        description="Required skills present in the candidate profile."
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Required skills missing from the candidate profile."
    )
    skill_overlap_percentage: float = Field(
        default=0.0,
        description="Percentage of required skills matched (matched_skill_count / required_skill_count)."
    )
    required_skill_count: int = Field(
        default=0,
        description="Total count of required skills."
    )
    matched_skill_count: int = Field(
        default=0,
        description="Total count of matched skills."
    )


class EvidenceItem(BaseModel):
    """
    Factual evidence item pairing a job requirement to corresponding candidate details.
    """
    category: str = Field(
        ...,
        description="Category of evaluation (e.g. Experience, Education, Specific Skill)."
    )
    resume_excerpt: str = Field(
        ...,
        description="Direct excerpt or citation from the candidate's resume."
    )
    job_requirement: str = Field(
        ...,
        description="The corresponding requirement specified in the job description."
    )


class PromptPackage(BaseModel):
    """
    Structured prompt packaging holding separated prompts.
    Enables different LLM providers to consume prompt components in their own format.
    """
    system_prompt: str = Field(
        ...,
        description="Role parameters, rules, and constraints for the LLM system prompt."
    )
    user_prompt: str = Field(
        ...,
        description="Contextual runtime data and formatting instruction for the LLM user prompt."
    )
    full_prompt: str = Field(
        ...,
        description="Consolidated prompt string for engines accepting a single string input."
    )


class MatchResult(BaseModel):
    """
    Assessment object representing the semantic fit of a candidate profile against requirements.
    Does NOT contain recruiter recommendation fields, which are handled at the business rules layer.
    """
    semantic_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Subjective matching score between 1 (poor fit) and 10 (perfect fit)."
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level of the LLM assessment based on input evidence quality."
    )
    matched_skills: List[str] = Field(
        default_factory=list,
        description="Semantic overlap of matching technical and soft skills."
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Skills explicitly or semantically missing in the candidate profile."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Core technical or architectural strengths aligned to the role."
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Identified candidate gaps, missing qualifications, or risks."
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Structured citations linking resume excerpts directly to requirements."
    )
    justification: str = Field(
        ...,
        description="Comprehensive textual justification detailing the matching score."
    )
