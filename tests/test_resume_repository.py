"""
Unit tests for ResumeRepository and ResumeRecord models.
Covers save, retrieve, update, delete, and candidate profile serialization.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.resume_record import ResumeRecord, ProcessingStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata

# In-memory SQLite for unit tests
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """
    Setup in-memory SQLite tables, yield session, and drop tables after run.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def repository() -> ResumeRepository:
    """Fixture providing ResumeRepository instance."""
    return ResumeRepository()


@pytest.fixture
def dummy_profile() -> CandidateProfile:
    """Fixture providing a mock CandidateProfile."""
    return CandidateProfile(
        personal_info=PersonalInfo(
            full_name="Jane Doe",
            email="jane.doe@example.com",
            phone="+1 (555) 0199",
            linkedin="https://linkedin.com/in/janedoe",
            github="https://github.com/janedoe",
            location="Chicago, IL"
        ),
        professional_info=ProfessionalInfo(
            skills=["Python", "FastAPI"],
            education=["Degree"],
            experience=["Role"],
            certifications=["Cert"]
        ),
        metadata=Metadata(parser_version="0.1.0-test")
    )


def test_resume_record_serialization(dummy_profile: CandidateProfile):
    """
    Test helper serialization/deserialization methods on the ResumeRecord model.
    Ensures model correctly handles Pydantic CandidateProfile conversion.
    """
    record = ResumeRecord(
        original_filename="test.pdf",
        stored_filename="uuid-test.pdf",
        processing_status=ProcessingStatus.UPLOADED
    )

    # Initially profile should be None
    assert record.to_candidate_profile() is None

    # Load profile into model
    record.from_candidate_profile(dummy_profile)
    assert record.candidate_profile_json is not None
    assert record.candidate_profile_json["personal_info"]["full_name"] == "Jane Doe"

    # Read profile back out of model
    deserialized = record.to_candidate_profile()
    assert isinstance(deserialized, CandidateProfile)
    assert deserialized.personal_info.full_name == "Jane Doe"
    assert deserialized.professional_info.skills == ["Python", "FastAPI"]


def test_save_and_retrieve_resume_record(db_session, repository: ResumeRepository):
    """
    Test saving a ResumeRecord and retrieving it back from SQLite.
    """
    record = ResumeRecord(
        original_filename="resume.pdf",
        stored_filename="uuid-resume.pdf",
        raw_text="Extracted text here",
        processing_status=ProcessingStatus.UPLOADED
    )

    saved = repository.save(db_session, record)
    assert saved.id is not None
    assert saved.processing_status == ProcessingStatus.UPLOADED

    retrieved = repository.get(db_session, saved.id)
    assert retrieved is not None
    assert retrieved.id == saved.id
    assert retrieved.original_filename == "resume.pdf"
    assert retrieved.raw_text == "Extracted text here"


def test_update_status_flow(db_session, repository: ResumeRepository, dummy_profile: CandidateProfile):
    """
    Test transitioning the processing status of a record through the pipeline stages.
    """
    # 1. Start at UPLOADED
    record = ResumeRecord(
        original_filename="cv.pdf",
        stored_filename="uuid-cv.pdf",
        processing_status=ProcessingStatus.UPLOADED
    )
    repository.save(db_session, record)
    assert record.processing_status == ProcessingStatus.UPLOADED

    # 2. Transition to TEXT_EXTRACTED
    record.raw_text = "Extracted Plain Text..."
    record.processing_status = ProcessingStatus.TEXT_EXTRACTED
    repository.update(db_session, record)

    db_session.expire(record)
    retrieved = repository.get(db_session, record.id)
    assert retrieved.processing_status == ProcessingStatus.TEXT_EXTRACTED
    assert retrieved.raw_text == "Extracted Plain Text..."

    # 3. Transition to PROFILE_PARSED
    retrieved.from_candidate_profile(dummy_profile)
    retrieved.processing_status = ProcessingStatus.PROFILE_PARSED
    repository.update(db_session, retrieved)

    db_session.expire(retrieved)
    retrieved_final = repository.get(db_session, record.id)
    assert retrieved_final.processing_status == ProcessingStatus.PROFILE_PARSED
    assert retrieved_final.to_candidate_profile().personal_info.full_name == "Jane Doe"


def test_list_records(db_session, repository: ResumeRepository):
    """
    Test paginated listing of ResumeRecords.
    """
    for i in range(3):
        repository.save(db_session, ResumeRecord(
            original_filename=f"cv_{i}.pdf",
            stored_filename=f"uuid-{i}.pdf",
            processing_status=ProcessingStatus.UPLOADED
        ))

    records = repository.list(db_session)
    assert len(records) == 3

    paginated = repository.list(db_session, skip=1, limit=1)
    assert len(paginated) == 1
    assert paginated[0].original_filename == "cv_1.pdf"


def test_delete_record(db_session, repository: ResumeRepository):
    """
    Test deleting a ResumeRecord.
    """
    record = ResumeRecord(
        original_filename="delete-me.pdf",
        stored_filename="uuid-delete.pdf",
        processing_status=ProcessingStatus.UPLOADED
    )
    repository.save(db_session, record)

    # Delete existing
    deleted = repository.delete(db_session, record.id)
    assert deleted is True

    # Retrieve deleted
    assert repository.get(db_session, record.id) is None

    # Delete non-existent
    assert repository.delete(db_session, 9999) is False
