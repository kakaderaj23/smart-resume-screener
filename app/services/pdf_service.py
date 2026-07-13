"""
PDF Text Extraction Service for the Smart Resume Screener application.

Architectural Design & Decisions:
1. Pure Domain/Infrastructure Layer: This module is strictly decoupled from FastAPI, HTTP routers,
   and database concerns. By raising domain-specific exceptions (`PDFNotFoundError`, `InvalidPDFError`,
   and `NoExtractableTextError`), callers (such as API endpoints, background queue workers, or CLI scripts)
   can catch and map errors appropriately without this service needing to know about HTTP status codes.
2. Choice of pdfplumber: `pdfplumber` (built on top of `pdfminer.six`) is preferred because it provides
   superior spatial layout analysis, accuracy in extracting character streams, table awareness, and clean
   handling of multi-column resumes compared to PyPDF2 or standard pypdf, while avoiding the heavyweight
   system dependencies of OCR tools or headless browsers.
3. Page-by-Page Extraction & Filtering: Resumes often contain visual headers/footers or blank spacer pages.
   Iterating per page allows us to filter out empty pages, isolate extraction failures to single pages where
   possible, and cleanly join extracted content using standard double-newline boundaries (`\\n\\n`) to preserve
   logical document structure for downstream parsing/LLM ingestion.
"""

import logging
from pathlib import Path
from typing import List

import pdfplumber

logger = logging.getLogger("smart-resume-screener.services.pdf")


class PDFExtractionError(Exception):
    """Base exception for all errors occurring during PDF text extraction."""
    pass


class PDFNotFoundError(PDFExtractionError, FileNotFoundError):
    """Raised when the specified PDF file path does not exist on disk."""
    pass


class InvalidPDFError(PDFExtractionError, ValueError):
    """Raised when the PDF file is corrupted, unreadable, or structurally invalid."""
    pass


class NoExtractableTextError(PDFExtractionError):
    """Raised when the PDF file contains no extractable text across any of its pages."""
    pass


class PDFService:
    """
    Reusable domain service responsible for converting PDF documents into plain text.
    
    Designed to operate independently of HTTP frameworks and database models, making it
    suitable for both synchronous request handling and asynchronous background processing queues.
    """

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract plain text from a PDF file located at `pdf_path`.

        Workflow & Safety:
        1. Verify that `pdf_path` exists and is a regular file.
        2. Safely open the document using `pdfplumber` within a context manager.
        3. Iterate sequentially through every page in the PDF document.
        4. Extract text from each page, stripping leading and trailing whitespace.
        5. Skip pages that yield empty string or `None` (e.g., blank or graphic-only pages).
        6. Join all valid page texts using double newline separators (`\\n\\n`).
        7. Raise meaningful domain exceptions (`PDFNotFoundError`, `InvalidPDFError`, `NoExtractableTextError`)
           if extraction cannot produce text.

        Args:
            pdf_path (Path): Filesystem path to the target PDF document.

        Returns:
            str: Complete extracted plain text joined across all valid pages.

        Raises:
            PDFNotFoundError: If the provided file path does not exist or is not a file.
            InvalidPDFError: If the PDF document is corrupted, password-protected, or structurally unreadable.
            NoExtractableTextError: If the PDF contains zero pages or yields no text across all pages.
        """
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)

        # 1. Check file existence
        if not pdf_path.exists() or not pdf_path.is_file():
            logger.error(f"Extraction failed: PDF file not found at '{pdf_path}'")
            raise PDFNotFoundError(f"PDF file does not exist at path: '{pdf_path}'")

        extracted_pages: List[str] = []

        # 2. Open PDF safely inside a context manager to guarantee file descriptor release
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check whether the document contains any pages
                if not pdf.pages:
                    logger.warning(f"PDF document '{pdf_path.name}' contains zero pages.")
                    raise NoExtractableTextError(f"PDF document '{pdf_path.name}' contains zero pages.")

                # 3. Iterate through every page
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = page.extract_text()
                    except Exception as exc:
                        logger.warning(f"Failed to extract text from page {page_num} of '{pdf_path.name}': {exc}")
                        continue

                    # 4. & 5. Skip pages with no extractable text
                    if page_text and page_text.strip():
                        extracted_pages.append(page_text.strip())

        except (PDFNotFoundError, NoExtractableTextError):
            # Re-raise domain exceptions without wrapping
            raise
        except Exception as exc:
            logger.error(f"Failed to open or parse PDF document '{pdf_path.name}': {exc}", exc_info=True)
            raise InvalidPDFError(f"The PDF file '{pdf_path.name}' is invalid or unreadable: {exc}") from exc

        # 6. Check if any text was collected after iterating through all pages
        if not extracted_pages:
            logger.warning(f"No extractable text found across {len(pdf.pages)} pages in '{pdf_path.name}'.")
            raise NoExtractableTextError(
                f"No extractable text could be found in PDF '{pdf_path.name}'. "
                "The document may be image-only (scanned), empty, or formatted with non-standard fonts without OCR."
            )

        # Join pages using newline separators
        full_text = "\n\n".join(extracted_pages)
        logger.info(
            f"Successfully extracted {len(full_text)} characters across {len(extracted_pages)} "
            f"pages from '{pdf_path.name}'."
        )
        return full_text
