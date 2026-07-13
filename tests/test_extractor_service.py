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


def test_extract_professional_info_standard_headings(extractor: ExtractorService):
    """
    Test deterministic section extraction across standard headings:
    SKILLS, EDUCATION, EXPERIENCE, and CERTIFICATIONS.
    """
    text = """
    Jane Candidate
    Email: jane.candidate@test.com

    SKILLS
    Python, FastAPI, Docker | Kubernetes | SQL
    • Git
    • AWS

    EDUCATION
    Bachelor of Science in Computer Science, Stanford University (2018-2022)
    Master of Science in Data Science, UC Berkeley (2022-2024)

    EXPERIENCE
    Software Engineer at TechCorp (2022-Present)
    • Designed and deployed scalable REST APIs
    • Optimized database queries and reduced latency by 40%

    CERTIFICATIONS
    AWS Certified Solutions Architect Associate (2023)
    Certified Kubernetes Administrator (CKA)
    """
    profile = extractor.extract(text)

    # Check contact info remains intact
    assert profile.personal_info.full_name == "Jane Candidate"
    assert profile.personal_info.email == "jane.candidate@test.com"

    # Check extracted skills (split by comma, pipe, and bullet, sorted alphabetically)
    expected_skills = ["AWS", "Docker", "FastAPI", "Git", "Kubernetes", "Python", "SQL"]
    assert profile.professional_info.skills == expected_skills

    # Check education
    assert len(profile.professional_info.education) == 2
    assert "Bachelor of Science in Computer Science, Stanford University (2018-2022)" in profile.professional_info.education
    assert "Master of Science in Data Science, UC Berkeley (2022-2024)" in profile.professional_info.education

    # Check experience
    assert len(profile.professional_info.experience) == 3
    assert "Software Engineer at TechCorp (2022-Present)" in profile.professional_info.experience
    assert "Designed and deployed scalable REST APIs" in profile.professional_info.experience

    # Check certifications
    assert len(profile.professional_info.certifications) == 2
    assert "AWS Certified Solutions Architect Associate (2023)" in profile.professional_info.certifications


def test_extract_professional_info_varied_heading_names(extractor: ExtractorService):
    """
    Test extraction using alternative heading styles, colons, and mapping "Projects" to experience.
    """
    text = """
    Technical Skills:
    Java, Spring Boot, Microservices

    Academic Background
    B.S. Software Engineering, MIT (2019)

    Work History
    Backend Developer - XYZ Inc (2020 - 2023)

    Projects
    High-Performance Order Matching Engine built in C++

    Licenses & Certifications
    Oracle Certified Professional Java SE 11 Developer
    """
    profile = extractor.extract(text)

    assert profile.professional_info.skills == ["Java", "Microservices", "Spring Boot"]
    assert profile.professional_info.education == ["B.S. Software Engineering, MIT (2019)"]
    assert profile.professional_info.experience == [
        "Backend Developer - XYZ Inc (2020 - 2023)",
        "High-Performance Order Matching Engine built in C++"
    ]
    assert profile.professional_info.certifications == ["Oracle Certified Professional Java SE 11 Developer"]


def test_extract_professional_info_missing_sections_and_non_target(extractor: ExtractorService):
    """
    Test resume with missing sections and non-target headers (SUMMARY, OBJECTIVE, REFERENCES).
    Text under non-target sections should NOT bleed into target lists.
    """
    text = """
    SUMMARY
    Experienced software engineer with 10+ years building mission-critical cloud infrastructure.
    Strong focus on distributed systems and high availability.

    OBJECTIVE
    Seeking a Principal Architect role in an innovative engineering organization.

    CORE COMPETENCIES
    Go, Rust, Terraform, Kafka

    EMPLOYMENT HISTORY
    Principal Infrastructure Engineer at CloudScale (2018-Present)
    • Led the migration of monolith to Kubernetes cluster serving 1M RPS

    REFERENCES
    Available upon request from former managers and directors.
    """
    profile = extractor.extract(text)

    # Skills and Experience populated (skills sorted alphabetically)
    assert profile.professional_info.skills == ["Go", "Kafka", "Rust", "Terraform"]
    assert len(profile.professional_info.experience) == 2
    assert "Principal Infrastructure Engineer at CloudScale (2018-Present)" in profile.professional_info.experience

    # Education and Certifications missing (should default to empty lists)
    assert profile.professional_info.education == []
    assert profile.professional_info.certifications == []

    # Verify summary and references didn't bleed into any list
    for item in profile.professional_info.experience + profile.professional_info.skills:
        assert "Experienced software engineer" not in item
        assert "Available upon request" not in item


def test_extract_professional_info_markdown_and_decorated_layouts(extractor: ExtractorService):
    """
    Test resume formatted with markdown symbols (#, ==, --) and numbered headers.
    """
    text = """
    # 1. Technical Expertise
    React, TypeScript, Next.js, TailwindCSS

    ### II. Education & Credentials
    B.A. in Mathematics, Princeton University (2017)

    === PROFESSIONAL EXPERIENCE ===
    Frontend Tech Lead at WebApp Labs (2019-2024)

    [ Professional Certifications ]
    AWS Certified Developer - Associate
    """
    profile = extractor.extract(text)

    assert profile.professional_info.skills == ["Next.js", "React", "TailwindCSS", "TypeScript"]
    assert profile.professional_info.education == ["B.A. in Mathematics, Princeton University (2017)"]
    assert profile.professional_info.experience == ["Frontend Tech Lead at WebApp Labs (2019-2024)"]
    assert profile.professional_info.certifications == ["AWS Certified Developer - Associate"]


def test_extract_skills_dictionary_aliases_and_whole_word_matching(extractor: ExtractorService):
    """
    Test case-insensitive whole-word matching and alias resolution to canonical skill names.
    Also confirms negative whole-word matching (`HTML` vs `ML`, `digital` vs `git`).
    """
    text = """
    Extensive experience working with react.js and reactjs on the frontend.
    Backend development using python, fastapi, and postgres.
    Deployments handled via docker (containerization) on amazon web services.
    Data pipeline processing with pandas and numpy for ml and artificial intelligence.
    Version control using github.
    Note: Experienced in HTML structure and digital marketing strategies.
    """
    skills = extractor.extract_skills(text)

    expected = [
        "AWS",
        "Docker",
        "FastAPI",
        "Git",
        "Machine Learning",
        "NumPy",
        "Pandas",
        "PostgreSQL",
        "Python",
        "React",
    ]
    assert skills == expected


def test_extract_skills_deduplication_and_sorting(extractor: ExtractorService):
    """
    Test that duplicates across multiple aliases/cases are removed and output is sorted alphabetically.
    """
    text = "Python, PYTHON, python | react | React.js | reactjs | ML | Machine Learning | artificial intelligence"
    skills = extractor.extract_skills(text)
    assert skills == ["Machine Learning", "Python", "React"]


def test_extract_skills_combined_with_explicit_non_dictionary_items(extractor: ExtractorService):
    """
    Test combining dictionary-matched aliases with explicit non-dictionary skills from resume sections.
    """
    explicit_section_items = ["react.js", "postgres", "Kubernetes", "GraphQL", "Terraform", "Python"]
    text = "General text discussing ML applications and Docker containerization."
    skills = extractor.extract_skills(text, explicit_items=explicit_section_items)

    expected = [
        "Docker",
        "GraphQL",
        "Kubernetes",
        "Machine Learning",
        "PostgreSQL",
        "Python",
        "React",
        "Terraform",
    ]
    assert skills == expected


def test_merge_profiles_deterministic_name_only(extractor: ExtractorService):
    """Test merge when only the deterministic profile contains a valid full_name."""
    det_profile = CandidateProfile()
    det_profile.personal_info.full_name = "Alexander Smith"

    merged = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=None)
    assert merged.personal_info.full_name == "Alexander Smith"


def test_merge_profiles_llm_name_only(extractor: ExtractorService):
    """Test merge when only the LLM profile contains a valid full_name."""
    det_profile = CandidateProfile()
    det_profile.personal_info.full_name = None

    llm_profile = CandidateProfile()
    llm_profile.personal_info.full_name = "Jane Doe"

    merged = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=llm_profile)
    assert merged.personal_info.full_name == "Jane Doe"


def test_merge_profiles_both_present(extractor: ExtractorService):
    """Test merge preferring valid LLM full_name when both deterministic and LLM names are present."""
    det_profile = CandidateProfile()
    det_profile.personal_info.full_name = "Alex Smith"

    llm_profile = CandidateProfile()
    llm_profile.personal_info.full_name = "Alexander Marie Smith"

    merged = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=llm_profile)
    assert merged.personal_info.full_name == "Alexander Marie Smith"


def test_merge_profiles_empty_llm_response(extractor: ExtractorService):
    """
    Test that an existing deterministic (or database) full_name is NEVER overwritten
    by an empty string, whitespace, or None from a downstream/LLM extraction.
    """
    det_profile = CandidateProfile()
    det_profile.personal_info.full_name = "Alex Smith"

    # LLM profile with empty string name
    llm_profile_empty = CandidateProfile()
    llm_profile_empty.personal_info.full_name = ""

    merged_empty = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=llm_profile_empty)
    assert merged_empty.personal_info.full_name == "Alex Smith"

    # LLM profile with whitespace name
    llm_profile_ws = CandidateProfile()
    llm_profile_ws.personal_info.full_name = "   "

    merged_ws = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=llm_profile_ws)
    assert merged_ws.personal_info.full_name == "Alex Smith"

    # LLM profile with None name
    llm_profile_none = CandidateProfile()
    llm_profile_none.personal_info.full_name = None

    merged_none = extractor.merge_profiles(deterministic_profile=det_profile, llm_profile=llm_profile_none)
    assert merged_none.personal_info.full_name == "Alex Smith"


def test_merge_profiles_database_fallback(extractor: ExtractorService):
    """Test fallback to existing database value when both deterministic and LLM names are empty."""
    det_profile = CandidateProfile()
    det_profile.personal_info.full_name = None

    llm_profile = CandidateProfile()
    llm_profile.personal_info.full_name = ""

    db_profile = CandidateProfile()
    db_profile.personal_info.full_name = "Jane Database"

    merged = extractor.merge_profiles(
        deterministic_profile=det_profile,
        llm_profile=llm_profile,
        db_profile=db_profile
    )
    assert merged.personal_info.full_name == "Jane Database"
