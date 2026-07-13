"""
Resume upload endpoint and router for the Smart Resume Screener application.

Architectural Decisions & Module Design:
1. Separation of Concerns: This module strictly handles file reception, validation, and secure disk storage.
   Parsing PDFs, text extraction, and LLM integration are intentionally isolated from this ingestion step
   to maintain single-responsibility endpoints, prevent long-running blocking operations during upload, and
   allow independent scaling or asynchronous worker queueing for resume processing.
2. FastAPI UploadFile over `bytes`: UploadFile is preferred over `bytes` because `bytes` loads the entire payload
   into RAM right at request time, causing memory spikes under heavy concurrent uploads. UploadFile uses a
   `SpooledTemporaryFile` that stores data in memory up to a limit (default 1MB) and rolls over to disk,
   enabling streaming I/O with minimal memory consumption.
3. UUID Filenames: UUID v4 filenames are used for storage to prevent filename collisions, mitigate path traversal
   attacks (`../../etc/passwd`), and eliminate filesystem issues with special characters or unicode names.
   The original filename is preserved separately to maintain user intent and context for subsequent processing steps.
4. Chunked Streaming Write: When saving to `uploads/`, we read/write in 1 MB chunks to keep peak memory footprint
   low even for multi-megabyte PDFs.
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

logger = logging.getLogger("smart-resume-screener.api.resume")

# Router definition with clear prefix and tags
router = APIRouter(
    prefix="/resume",
    tags=["Resume"],
    responses={
        400: {"description": "Bad Request - Invalid file extension, empty file, or malformed PDF"},
        500: {"description": "Internal Server Error - Failure writing file to storage"}
    }
)

# Constants for file validation and efficient streaming
CHUNK_SIZE = 1024 * 1024  # 1 MB chunk size for memory-efficient streaming
PDF_MAGIC_BYTES = b"%PDF-"


class ResumeUploadResponse(BaseModel):
    """
    Response schema for a successful resume upload.
    
    Attributes:
        message: Success notification message.
        filename: Unique UUID-based storage filename on the server.
        original_filename: Preserved original filename provided by the client.
        size_bytes: Total size of the uploaded file in bytes.
    """
    message: str = Field(..., description="Status confirmation message")
    filename: str = Field(..., description="Unique UUID-based filename saved on disk")
    original_filename: str = Field(..., description="Original client-side filename")
    size_bytes: int = Field(..., description="Total size of the saved file in bytes")


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Securely upload a resume PDF file",
    description="Accepts a single PDF file via multipart/form-data, validates its structure and extension, "
                "saves it with a unique UUID filename, extracts its text and profile metadata, "
                "and persists it in SQLite."
)
async def upload_resume(
    resume: UploadFile = File(..., description="The PDF resume file to upload"),
    db: Session = Depends(get_db)
) -> ResumeUploadResponse:
    """
    Handle secure resume uploading, parsing, and database persistence.

    Validations & Workflow:
    1. Check presence of original filename and verify `.pdf` extension.
    2. Inspect MIME content type if provided by the client header.
    3. Verify file header magic bytes (`%PDF-`) to ensure the file is structurally a PDF.
    4. Generate a collision-resistant UUID v4 filename.
    5. Stream the file in 1 MB chunks from SpooledTemporaryFile to disk in `uploads/` directory.
    6. Extract plain text from PDF and extract contact info into CandidateProfile.
    7. Persist resume details and parsed profile to the SQLite database.
    8. Ensure atomic cleanup of local files if parsing or database insertion fails.

    Args:
        resume (UploadFile): The uploaded resume file object from multipart/form-data.
        db (Session): Database session dependency.

    Returns:
        ResumeUploadResponse: Structured JSON containing success message, storage filename,
                               original filename, and size in bytes.

    Raises:
        HTTPException (400): If the file is not a valid `.pdf` or parsing fails.
        HTTPException (500): If server filesystem or database errors occur.
    """
    # 1. Validate filename presence and extension (.pdf only)
    if not resume.filename or not resume.filename.strip():
        logger.warning("Upload attempt rejected: No filename provided.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in the uploaded file."
        )

    # Sanitize and extract original filename
    original_filename = Path(resume.filename).name
    if not original_filename.lower().endswith(".pdf"):
        logger.warning(f"Upload attempt rejected: Invalid extension for file '{original_filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .pdf files are accepted."
        )

    # 2. Validate content type if supplied by client
    if resume.content_type and resume.content_type not in ["application/pdf", "application/x-pdf", "application/octet-stream"]:
        logger.warning(f"Upload attempt rejected: Unexpected content type '{resume.content_type}' for file '{original_filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{resume.content_type}'. Only 'application/pdf' is accepted."
        )

    # 3. Validate magic bytes to ensure true PDF content and reject empty files
    try:
        header = await resume.read(len(PDF_MAGIC_BYTES))
        if not header:
            logger.warning(f"Upload attempt rejected: Empty file '{original_filename}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty."
            )
        if not header.startswith(PDF_MAGIC_BYTES):
            logger.warning(f"Upload attempt rejected: Missing PDF magic bytes in file '{original_filename}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. File does not appear to be a valid PDF."
            )
    finally:
        # Reset file cursor back to the beginning after reading the header bytes
        await resume.seek(0)

    # 4. Prepare target storage directory and generate unique UUID filename
    try:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error(f"Failed to create or access upload directory '{settings.UPLOAD_DIR}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Unable to access upload storage."
        )

    file_id = str(uuid.uuid4())
    unique_filename = f"{file_id}.pdf"
    file_path = settings.UPLOAD_DIR / unique_filename

    # 5. Stream the file in memory-efficient chunks to storage
    size_bytes = 0
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await resume.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
                size_bytes += len(chunk)
    except Exception as exc:
        # If writing fails halfway through, clean up partial file to avoid corrupted orphans
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        logger.error(f"Error saving uploaded resume '{original_filename}' to '{file_path}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the uploaded resume file."
        )
    finally:
        # Ensure temporary resources allocated by UploadFile are released
        await resume.close()

    # Double check that we didn't end up with a 0-byte file
    if size_bytes == 0:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        logger.warning(f"Upload attempt rejected after streaming: 0-byte file '{original_filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    logger.info(f"Successfully uploaded '{original_filename}' ({size_bytes} bytes) -> stored as '{unique_filename}'.")

    # 6. Pipeline processing: Extract text, parse profile, and persist to SQLite
    from app.services.pdf_service import PDFService, PDFExtractionError
    from app.services.extractor_service import ExtractorService
    from app.models.resume_record import ResumeRecord, ProcessingStatus
    from app.repositories.resume_repository import ResumeRepository

    repo = ResumeRepository()
    
    # 6.1 Create and persist initial record in UPLOADED state
    record = ResumeRecord(
        original_filename=original_filename,
        stored_filename=unique_filename,
        processing_status=ProcessingStatus.UPLOADED
    )
    try:
        repo.save(db, record)
    except Exception as exc:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        logger.error(f"Failed to persist initial resume record for '{original_filename}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while initializing the resume record in the database."
        )

    # 6.2 Run PDF Text Extraction and transition to TEXT_EXTRACTED
    pdf_service = PDFService()
    try:
        raw_text = pdf_service.extract_text(file_path)
        record.raw_text = raw_text
        record.processing_status = ProcessingStatus.TEXT_EXTRACTED
        repo.update(db, record)
    except PDFExtractionError as exc:
        record.processing_status = ProcessingStatus.FAILED
        try:
            repo.update(db, record)
        except Exception:
            pass
        # Cleanup saved file on disk if text extraction fails
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        logger.warning(f"Failed to extract text from uploaded PDF '{original_filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

    # 6.3 Run Deterministic Profile Parsing and transition to PROFILE_PARSED
    extractor = ExtractorService()
    try:
        profile = extractor.extract(raw_text)
        record.from_candidate_profile(profile)
        record.processing_status = ProcessingStatus.PROFILE_PARSED
        repo.update(db, record)
    except Exception as exc:
        record.processing_status = ProcessingStatus.FAILED
        try:
            repo.update(db, record)
        except Exception:
            pass
        # Cleanup saved file on disk if database updates fail
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        logger.error(f"Failed to process and update candidate profile for '{original_filename}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while parsing and saving the candidate profile."
        )

    # 7. Return structured response JSON matching exact milestone specification
    return ResumeUploadResponse(
        message="Resume uploaded successfully",
        filename=unique_filename,
        original_filename=original_filename,
        size_bytes=size_bytes
    )
