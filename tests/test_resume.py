"""
Unit tests for the Resume Upload Module (POST /resume/upload).
"""

import io
import shutil
from pathlib import Path
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_cleanup_uploads(tmp_path, monkeypatch):
    """
    Fixture to isolate uploaded files into a temporary directory during tests
    and clean them up automatically afterwards.
    """
    test_upload_dir = tmp_path / "test_uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", test_upload_dir)
    yield
    if test_upload_dir.exists():
        shutil.rmtree(test_upload_dir, ignore_errors=True)


def test_upload_valid_resume_pdf():
    """
    Test successful upload of a valid PDF resume file.
    Verifies response status code, exact JSON structure, and storage on disk.
    """
    pdf_content = b"%PDF-1.4 sample pdf content for resume screener"
    file_obj = io.BytesIO(pdf_content)
    
    response = client.post(
        "/resume/upload",
        files={"resume": ("John_Doe_Resume.pdf", file_obj, "application/pdf")}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Resume uploaded successfully"
    assert data["original_filename"] == "John_Doe_Resume.pdf"
    assert data["filename"].endswith(".pdf")
    assert data["size_bytes"] == len(pdf_content)
    
    # Verify file actually saved on disk with UUID filename and correct content
    saved_file_path = settings.UPLOAD_DIR / data["filename"]
    assert saved_file_path.exists()
    assert saved_file_path.read_bytes() == pdf_content


def test_upload_reject_non_pdf_extension():
    """
    Test rejection of files without .pdf extension (e.g., .docx, .txt).
    """
    txt_content = b"This is a plain text resume."
    file_obj = io.BytesIO(txt_content)
    
    response = client.post(
        "/resume/upload",
        files={"resume": ("Resume.txt", file_obj, "text/plain")}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only .pdf files are accepted" in response.json()["detail"]


def test_upload_reject_invalid_content_type():
    """
    Test rejection of file with .pdf extension when unexpected content type is passed.
    """
    pdf_content = b"%PDF-1.4 valid magic bytes"
    file_obj = io.BytesIO(pdf_content)
    
    response = client.post(
        "/resume/upload",
        files={"resume": ("Fake_Resume.pdf", file_obj, "image/png")}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid content type" in response.json()["detail"]


def test_upload_reject_missing_magic_bytes():
    """
    Test rejection of file with .pdf extension when magic bytes do not start with %PDF-.
    """
    corrupt_content = b"NOT A PDF content string"
    file_obj = io.BytesIO(corrupt_content)
    
    response = client.post(
        "/resume/upload",
        files={"resume": ("Malicious_Resume.pdf", file_obj, "application/pdf")}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid file format" in response.json()["detail"]


def test_upload_reject_empty_pdf_file():
    """
    Test rejection of a 0-byte uploaded file.
    """
    file_obj = io.BytesIO(b"")
    
    response = client.post(
        "/resume/upload",
        files={"resume": ("Empty_Resume.pdf", file_obj, "application/pdf")}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "The uploaded file is empty" in response.json()["detail"]
