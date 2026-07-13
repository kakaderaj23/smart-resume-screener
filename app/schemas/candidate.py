"""
Candidate Profile domain schema definitions (`CandidateProfile`).

Architectural Rationale:
`CandidateProfile` serves as the central canonical domain object across all application tiers.
By establishing a unified, strongly-typed Pydantic schema early in the ingestion pipeline,
we decouple document parsing (regex, heuristics, OCR, or LLMs) from downstream consumers
(such as database persistence layers, search indices, scoring algorithms, and API responses).
Every extraction tier (deterministic regex or semantic LLM) outputs or mutates this single
canonical contract, ensuring data consistency and type safety across the entire platform.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class PersonalInfo(BaseModel):
    """
    Candidate contact and personal identification details.
    
    Fields that cannot be extracted with high confidence or are not present in the document
    default to `None` to prevent hallucinations or misleading data.
    """
    full_name: Optional[str] = Field(
        default=None,
        description="Candidate's full name, inferred only when high confidence exists."
    )
    email: Optional[str] = Field(
        default=None,
        description="Primary email address extracted via deterministic regex."
    )
    phone: Optional[str] = Field(
        default=None,
        description="Primary contact phone number extracted and cleaned via heuristics."
    )
    linkedin: Optional[str] = Field(
        default=None,
        description="Optional LinkedIn profile URL."
    )
    github: Optional[str] = Field(
        default=None,
        description="Optional GitHub profile URL."
    )
    location: Optional[str] = Field(
        default=None,
        description="Optional geographical location or city/state of residence."
    )


class ProfessionalInfo(BaseModel):
    """
    Candidate professional qualifications, skills, experience, and education.
    
    In deterministic/regex extraction stages, these lists remain empty.
    They are populated later by semantic LLM extraction pipelines.
    """
    skills: List[str] = Field(
        default_factory=list,
        description="List of professional skills, tools, and technical competencies."
    )
    education: List[str] = Field(
        default_factory=list,
        description="List of educational qualifications, degrees, and institutions."
    )
    experience: List[str] = Field(
        default_factory=list,
        description="List of work experiences, job titles, companies, and roles."
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="List of professional certifications and licenses."
    )


class Metadata(BaseModel):
    """
    Extraction metadata tracking parser versions and processing timestamps.
    """
    parser_version: str = Field(
        default="0.1.0-deterministic",
        description="Version and identifier of the extraction engine that generated this profile."
    )
    extraction_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp indicating when the profile extraction occurred."
    )


class CandidateProfile(BaseModel):
    """
    Root canonical domain model representing a candidate's complete profile.
    
    Combines personal contact information, structured professional background,
    and provenance metadata into a single validated object.
    """
    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo,
        description="Personal contact and identification details."
    )
    professional_info: ProfessionalInfo = Field(
        default_factory=ProfessionalInfo,
        description="Structured professional skills, education, and career experience."
    )
    metadata: Metadata = Field(
        default_factory=Metadata,
        description="System provenance and extraction metadata."
    )
