"""
ResumeRecord model representing an uploaded document's state and processing pipeline progress.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.schemas.candidate import CandidateProfile
from app.schemas.match import MatchResult


class ProcessingStatus(str, Enum):
    """
    Represents the current stage of the resume in the screening pipeline.
    """
    UPLOADED = "UPLOADED"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    PROFILE_PARSED = "PROFILE_PARSED"
    MATCHED = "MATCHED"
    FAILED = "FAILED"


class ResumeRecord(Base):
    """
    SQLAlchemy model representing a resume's processing state, plain text,
    and extracted candidate profile schema.
    """
    __tablename__ = "resume_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # Primary key
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # Original filename from the client
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # UUID filename saved on disk
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Extracted plain text content
    candidate_profile_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # CandidateProfile Pydantic schema stored as JSON
    latest_match_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Latest MatchResult schema serialized as JSON
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
    )  # Current status of the pipeline processing
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )  # UTC creation timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )  # UTC update timestamp

    def to_candidate_profile(self) -> Optional[CandidateProfile]:
        """
        Deserialize candidate_profile_json from the database into a validated CandidateProfile schema.
        Returns None if profile has not yet been extracted.
        """
        if not self.candidate_profile_json:
            return None
        return CandidateProfile.model_validate(self.candidate_profile_json)

    def from_candidate_profile(self, profile: CandidateProfile) -> None:
        """
        Serialize a CandidateProfile schema into candidate_profile_json dictionary format.
        """
        self.candidate_profile_json = profile.model_dump(mode='json')

    def to_match_result(self) -> Optional[MatchResult]:
        """
        Deserialize latest_match_result from the database into a validated MatchResult schema.
        Returns None if match has not yet been processed.
        """
        if not self.latest_match_result:
            return None
        return MatchResult.model_validate(self.latest_match_result)

    def from_match_result(self, match_result: MatchResult) -> None:
        """
        Serialize a MatchResult schema into latest_match_result dictionary format.
        """
        self.latest_match_result = match_result.model_dump(mode='json')

    def __repr__(self) -> str:
        return f"<ResumeRecord(id={self.id}, status={self.processing_status}, original_filename='{self.original_filename}')>"
