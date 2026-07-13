"""
Unit tests for ExtractorService (`app/services/extractor_service.py`).
Covers deterministic extraction of emails, multiple phone formats, LinkedIn/GitHub URLs,
high-confidence name inference, missing values, and malformed resume handling.
"""

import pytest
from app.services.extractor_service import ExtractorService
from app.schemas.candidate import CandidateProfile


@pytest.fixture
def extractor() -> ExtractorService:
    """Fixture providing a fresh instance of ExtractorService."""
    return ExtractorService()


def test_extract_valid_email(extractor: ExtractorService):
    """Test deterministic extraction of valid email addresses."""
    text = """
    John Doe
    Contact: john.doe+work@domain.co.uk | +1 (555) 123-4567
    Experience in Python Backend Systems.
    """
    profile = extractor.extract(text)
    assert profile.personal_info.email == "john.doe+work@domain.co.uk"


def test_extract_multiple_phone_formats(extractor: ExtractorService):
    """
    Test extraction across multiple valid national and international phone formats,
    verifying that year ranges (2018-2022) and IP addresses are ignored.
    """
    # Format 1: US with country code and parens
    text1 = "Jane Smith\nPhone: +1 (415) 555-2671\nWorked from 2018-2022."
    profile1 = extractor.extract(text1)
    assert profile1.personal_info.phone == "+1 (415) 555-2671"

    # Format 2: Standard dashes without country code
    text2 = "Contact Info: 123-456-7890 | email@test.com"
    profile2 = extractor.extract(text2)
    assert profile2.personal_info.phone == "123-456-7890"

    # Format 3: UK / International format with spaces
    text3 = "Call me at +44 20 7946 0958 or visit my profile."
    profile3 = extractor.extract(text3)
    assert profile3.personal_info.phone == "+44 20 7946 0958"

    # Format 4: UK local format
    text4 = "Alex Jones\nTel: 07911 123456\nServer IP: 192.168.1.100"
    profile4 = extractor.extract(text4)
    assert profile4.personal_info.phone == "07911 123456"


def test_extract_linkedin_detection(extractor: ExtractorService):
    """Test detection and canonicalization of LinkedIn profile URLs."""
    # Without https scheme
    text1 = "Connect: linkedin.com/in/john-doe-12345 / github.com/johndoe"
    profile1 = extractor.extract(text1)
    assert profile1.personal_info.linkedin == "https://linkedin.com/in/john-doe-12345"

    # With full scheme and trailing slash
    text2 = "Check out https://www.linkedin.com/in/jane_smith/ for more info."
    profile2 = extractor.extract(text2)
    assert profile2.personal_info.linkedin == "https://www.linkedin.com/in/jane_smith"


def test_extract_github_detection(extractor: ExtractorService):
    """Test detection and canonicalization of GitHub profile URLs."""
    text = "Code samples available at github.com/alex-dev-python/ or email me."
    profile = extractor.extract(text)
    assert profile.personal_info.github == "https://github.com/alex-dev-python"


def test_infer_full_name_high_confidence(extractor: ExtractorService):
    """
    Test that high-confidence names at the top of the resume are inferred correctly,
    while uncertain/header-heavy tops return None without hallucinating.
    """
    # High confidence top line
    text_valid = "Alexander Marie Smith\nSenior Backend Engineer\nEmail: alex@smith.com"
    profile_valid = extractor.extract(text_valid)
    assert profile_valid.personal_info.full_name == "Alexander Marie Smith"

    # Uncertain header top line (should NOT hallucinate or return "Curriculum Vitae")
    text_header = "CURRICULUM VITAE\nSenior Python Developer\nContact: 123-456-7890"
    profile_header = extractor.extract(text_header)
    assert profile_header.personal_info.full_name is None


def test_missing_values_and_empty_text(extractor: ExtractorService):
    """Test that empty text or missing contact fields cleanly default to None/empty lists without errors."""
    profile_empty = extractor.extract("")
    assert isinstance(profile_empty, CandidateProfile)
    assert profile_empty.personal_info.full_name is None
    assert profile_empty.personal_info.email is None
    assert profile_empty.personal_info.phone is None
    assert profile_empty.personal_info.linkedin is None
    assert profile_empty.personal_info.github is None
    assert profile_empty.professional_info.skills == []
    assert profile_empty.professional_info.education == []
    assert profile_empty.professional_info.experience == []
    assert profile_empty.professional_info.certifications == []
    assert profile_empty.metadata.parser_version == "0.1.0-deterministic"


def test_malformed_resume_text(extractor: ExtractorService):
    """
    Test that scrambled, noisy, or malformed text does not cause unhandled exceptions
    and extracts only valid deterministic patterns when present.
    """
    noisy_text = """
    !@#$%^&*()_+ NO REAL NAME FOUND 12345
    Date of Birth: 1990-05-12 | Years: 2015-2021
    Random text snippet: contact-me-via email: valid.candidate@test.org right away!!
    IP check: 10.0.0.1 / no phone number here.
    """
    profile = extractor.extract(noisy_text)
    assert profile.personal_info.full_name is None
    assert profile.personal_info.phone is None
    assert profile.personal_info.email == "valid.candidate@test.org"
