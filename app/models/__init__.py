"""
Models package for the Smart Resume Screener application.
Defines SQLAlchemy ORM entities for database persistence.
"""

from app.models.resume_record import ResumeRecord, ProcessingStatus

__all__ = ["ResumeRecord", "ProcessingStatus"]
