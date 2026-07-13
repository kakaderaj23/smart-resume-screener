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

    @classmethod
    def merge_profiles(
        cls,
        deterministic_profile: Optional["CandidateProfile"] = None,
        llm_profile: Optional["CandidateProfile"] = None,
        db_profile: Optional["CandidateProfile"] = None,
    ) -> "CandidateProfile":
        """
        Merge multiple CandidateProfile instances across pipeline stages while enforcing strict hierarchy rules.

        Name Resolution Hierarchy (`full_name`):
        1. LLM extracted name (if valid and non-empty string)
        2. Deterministic extracted name (if valid and non-empty string)
        3. Existing database value (if valid and non-empty string)
        An existing non-empty name is never replaced with `None` or an empty string.
        """
        def get_valid_str(val: Optional[str]) -> Optional[str]:
            if val is not None and isinstance(val, str) and val.strip():
                return val.strip()
            return None

        # Resolve full_name according to exact priority: 1. LLM, 2. Deterministic, 3. DB
        llm_name = get_valid_str(llm_profile.personal_info.full_name) if (llm_profile and llm_profile.personal_info) else None
        det_name = get_valid_str(deterministic_profile.personal_info.full_name) if (deterministic_profile and deterministic_profile.personal_info) else None
        db_name = get_valid_str(db_profile.personal_info.full_name) if (db_profile and db_profile.personal_info) else None

        resolved_name = llm_name or det_name or db_name

        # For other personal contact fields, prefer non-empty values from llm -> det -> db
        def resolve_field(field_name: str) -> Optional[str]:
            for prof in (llm_profile, deterministic_profile, db_profile):
                if prof and prof.personal_info:
                    val = get_valid_str(getattr(prof.personal_info, field_name, None))
                    if val is not None:
                        return val
            return None

        email = resolve_field("email")
        phone = resolve_field("phone")
        linkedin = resolve_field("linkedin")
        github = resolve_field("github")
        location = resolve_field("location")

        # For professional info lists, combine across profiles cleanly
        skills: List[str] = []
        education: List[str] = []
        experience: List[str] = []
        certifications: List[str] = []

        seen_skills = set()
        for prof in (llm_profile, deterministic_profile, db_profile):
            if prof and prof.professional_info:
                for skill in prof.professional_info.skills:
                    s_clean = skill.strip()
                    if s_clean and s_clean.lower() not in seen_skills:
                        seen_skills.add(s_clean.lower())
                        skills.append(s_clean)
                for edu in prof.professional_info.education:
                    if edu.strip() and edu.strip() not in education:
                        education.append(edu.strip())
                for exp in prof.professional_info.experience:
                    if exp.strip() and exp.strip() not in experience:
                        experience.append(exp.strip())
                for cert in prof.professional_info.certifications:
                    if cert.strip() and cert.strip() not in certifications:
                        certifications.append(cert.strip())

        personal_info = PersonalInfo(
            full_name=resolved_name,
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            location=location
        )
        professional_info = ProfessionalInfo(
            skills=skills,
            education=education,
            experience=experience,
            certifications=certifications
        )

        parser_ver = "0.1.0-deterministic"
        for prof in (llm_profile, deterministic_profile, db_profile):
            if prof and prof.metadata and prof.metadata.parser_version:
                parser_ver = prof.metadata.parser_version
                break

        metadata = Metadata(parser_version=parser_ver)

        return cls(
            personal_info=personal_info,
            professional_info=professional_info,
            metadata=metadata
        )
