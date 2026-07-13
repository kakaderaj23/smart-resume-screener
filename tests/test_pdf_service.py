"""
Unit tests for the PDF Text Extraction Service (PDFService).
Covers successful extraction, missing file handling, corrupted PDF handling,
and empty/non-text PDF behavior without touching databases, LLMs, or HTTP endpoints.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.services.pdf_service import (
    PDFService,
    PDFNotFoundError,
    InvalidPDFError,
    NoExtractableTextError,
)


@pytest.fixture
def pdf_service() -> PDFService:
    """Fixture providing a clean instance of PDFService."""
    return PDFService()


def test_successful_extraction_with_skipped_empty_pages(pdf_service: PDFService, tmp_path: Path):
    """
    Test successful text extraction across multiple pages, verifying that:
    - Text from valid pages is stripped and joined cleanly with newlines.
    - Pages with None or empty/whitespace-only text are skipped.
    """
    dummy_pdf_path = tmp_path / "sample_resume.pdf"
    dummy_pdf_path.write_bytes(b"%PDF-1.4 dummy valid bytes")

    # Mock pdfplumber to simulate a multi-page PDF document
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = "   John Doe\nSoftware Engineer   "
    
    mock_page_2_empty = MagicMock()
    mock_page_2_empty.extract_text.return_value = "   \n   "  # Blank/spacer page to skip
    
    mock_page_3 = MagicMock()
    mock_page_3.extract_text.return_value = "Experience:\n- Backend Development with Python & FastAPI"

    mock_pdf.pages = [mock_page_1, mock_page_2_empty, mock_page_3]

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf

        extracted_text = pdf_service.extract_text(dummy_pdf_path)

        assert "John Doe\nSoftware Engineer" in extracted_text
        assert "Experience:\n- Backend Development with Python & FastAPI" in extracted_text
        assert extracted_text == (
            "John Doe\nSoftware Engineer\n\n"
            "Experience:\n- Backend Development with Python & FastAPI"
        )
        mock_open.assert_called_once_with(dummy_pdf_path)


def test_missing_file_raises_pdf_not_found_error(pdf_service: PDFService, tmp_path: Path):
    """
    Test that calling extract_text on a non-existent filesystem path immediately
    raises PDFNotFoundError without attempting to open pdfplumber.
    """
    non_existent_path = tmp_path / "does_not_exist.pdf"

    with pytest.raises(PDFNotFoundError) as exc_info:
        pdf_service.extract_text(non_existent_path)

    assert "does not exist" in str(exc_info.value)


def test_corrupted_pdf_raises_invalid_pdf_error(pdf_service: PDFService, tmp_path: Path):
    """
    Test that if a PDF file is unreadable, corrupted, or structurally invalid,
    the service catches the parser error and raises InvalidPDFError.
    Uses real file creation with invalid binary data to verify actual parser/service behavior.
    """
    corrupted_path = tmp_path / "corrupt.pdf"
    corrupted_path.write_bytes(b"Not a real PDF file structure - just random garbage data")

    with pytest.raises(InvalidPDFError) as exc_info:
        pdf_service.extract_text(corrupted_path)

    assert "invalid or unreadable" in str(exc_info.value)


def test_empty_or_non_text_pdf_raises_no_extractable_text_error(pdf_service: PDFService, tmp_path: Path):
    """
    Test that when a validly opened PDF contains pages with zero extractable text
    (such as scanned images without OCR or completely blank pages), NoExtractableTextError is raised.
    """
    scanned_pdf_path = tmp_path / "scanned_resume.pdf"
    scanned_pdf_path.write_bytes(b"%PDF-1.4 dummy bytes")

    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = None  # Simulates scanned image page where extract_text() returns None
    mock_page_2 = MagicMock()
    mock_page_2.extract_text.return_value = "   "  # Simulates whitespace-only page

    mock_pdf.pages = [mock_page_1, mock_page_2]

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf

        with pytest.raises(NoExtractableTextError) as exc_info:
            pdf_service.extract_text(scanned_pdf_path)

        assert "No extractable text could be found" in str(exc_info.value)


def test_zero_page_pdf_raises_no_extractable_text_error(pdf_service: PDFService, tmp_path: Path):
    """
    Test that a PDF containing 0 pages raises NoExtractableTextError right away upon opening.
    """
    zero_page_path = tmp_path / "empty_pages.pdf"
    zero_page_path.write_bytes(b"%PDF-1.4 dummy bytes")

    mock_pdf = MagicMock()
    mock_pdf.pages = []

    with patch("pdfplumber.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_pdf

        with pytest.raises(NoExtractableTextError) as exc_info:
            pdf_service.extract_text(zero_page_path)

        assert "contains zero pages" in str(exc_info.value)
