"""
Deterministic Resume Extractor Service (`ExtractorService`).

Architectural Rationale:
Contact information (such as email, phone numbers, and portfolio URLs) follows strict,
standardized structural rules and regular patterns. Using deterministic regex and lightweight
heuristics for these fields is vastly preferred over calling semantic Large Language Models (LLMs) because:
1. High Precision & Zero Hallucinations: Regex guarantees exactly what is in the document, avoiding
   LLM hallucinations where digits or URL paths might be altered or fabricated.
2. Speed & Zero Cost: Regex executes in microseconds with zero network calls, token costs, or rate limits.
3. Separation of Concerns: By extracting deterministic contact fields immediately upon file ingestion,
   we populate the canonical `CandidateProfile` early. Downstream LLM extraction pipelines can then
   focus exclusively on semantic, unstructured sections (skills, work experience context, and education),
   reducing prompt complexity and context window requirements.
"""

import logging
import re
from typing import List, Optional

from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata

logger = logging.getLogger("smart-resume-screener.services.extractor")

# Compiled regular expressions for deterministic extraction
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
)

# Comprehensive phone pattern capturing North American & International phone strings
PHONE_PATTERN = re.compile(
    r'(?:'
    r'(?:\+|00)\d{1,3}[\s.-]?(?:\(?\d{1,4}\)?[\s.-]?){2,4}\d{2,4}'  # International +44 20 7946 0958 / +91 98765 43210
    r'|'
    r'(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'           # North American (415) 555-2671 / 123-456-7890
    r'|'
    r'\b0\d{4}[\s.-]?\d{6}\b'                                        # UK / local 07911 123456
    r')'
)

LINKEDIN_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?',
    re.IGNORECASE
)

GITHUB_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?',
    re.IGNORECASE
)

# Common resume headers and professional titles to exclude during top-line name inference
FORBIDDEN_NAME_KEYWORDS = {
    "resume", "curriculum", "vitae", "cv", "summary", "experience", "education",
    "contact", "profile", "skills", "objective", "qualifications", "page",
    "engineer", "developer", "manager", "analyst", "consultant", "specialist",
    "architect", "administrator", "director", "coordinator", "officer"
}


class ExtractorService:
    """
    Service responsible for deterministic extraction of basic candidate contact information
    from raw resume text into the canonical `CandidateProfile` domain schema.

    Strictly avoids LLM calls, semantic parsing, or guessing. If a field is ambiguous or
    cannot be found with high confidence, it is left empty (`None`).
    """

    def extract(self, raw_text: str) -> CandidateProfile:
        """
        Extract deterministic contact details and initialize a canonical `CandidateProfile`.

        Workflow:
        1. Extract email address via regex (`_extract_email`).
        2. Extract and validate phone number via regex and heuristics (`_extract_phone`).
        3. Extract canonicalized LinkedIn and GitHub profile URLs (`_extract_linkedin`, `_extract_github`).
        4. Attempt high-confidence name inference from document header (`_infer_full_name`).
        5. Return structured `CandidateProfile` with personal details and empty professional lists.

        Args:
            raw_text (str): Raw plain text extracted from a resume document.

        Returns:
            CandidateProfile: Validated canonical profile containing deterministic contact info.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("ExtractorService received empty text. Returning empty CandidateProfile.")
            return CandidateProfile()

        email = self._extract_email(raw_text)
        phone = self._extract_phone(raw_text)
        linkedin = self._extract_linkedin(raw_text)
        github = self._extract_github(raw_text)
        full_name = self._infer_full_name(raw_text)

        personal_info = PersonalInfo(
            full_name=full_name,
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            location=None  # Location requires semantic context / NLP, postponed to LLM stage
        )

        # Professional lists explicitly left empty during deterministic extraction
        professional_info = ProfessionalInfo(
            skills=[],
            education=[],
            experience=[],
            certifications=[]
        )

        metadata = Metadata(
            parser_version="0.1.0-deterministic"
        )

        profile = CandidateProfile(
            personal_info=personal_info,
            professional_info=professional_info,
            metadata=metadata
        )

        logger.info(
            f"Extraction complete -> Name: {full_name or 'Uncertain'}, "
            f"Email: {email or 'None'}, Phone: {phone or 'None'}, "
            f"LinkedIn: {'Yes' if linkedin else 'No'}, GitHub: {'Yes' if github else 'No'}"
        )
        return profile

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract the first valid email address found in the text."""
        matches = re.findall(EMAIL_PATTERN, text)
        if matches:
            # Return cleaned match stripped of any trailing artifacts
            return matches[0].strip()
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """
        Extract and validate the primary phone number from text.
        Filters out date ranges, IP addresses, and invalid digit lengths.
        """
        matches = re.findall(PHONE_PATTERN, text)
        for candidate in matches:
            cleaned = candidate.strip()
            # Extract only digits to check length validity according to ITU E.164 (9 to 15 digits)
            digits = re.sub(r'\D', '', cleaned)
            if len(digits) < 9 or len(digits) > 15:
                continue

            # Filter out IP addresses (e.g. 192.168.0.1)
            if cleaned.count('.') >= 3:
                continue

            # Filter out year ranges that might resemble phone strings (e.g. 2018-2022)
            if re.search(r'\b(?:19|20)\d{2}[\s.-]+(?:19|20)\d{2}\b', cleaned):
                continue

            return cleaned
        return None

    def _extract_linkedin(self, text: str) -> Optional[str]:
        """Extract and canonicalize LinkedIn profile URL."""
        match = LINKEDIN_PATTERN.search(text)
        if match:
            url = match.group(0).strip().rstrip('/')
            if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
                url = f"https://{url}"
            return url
        return None

    def _extract_github(self, text: str) -> Optional[str]:
        """Extract and canonicalize GitHub profile URL."""
        match = GITHUB_PATTERN.search(text)
        if match:
            url = match.group(0).strip().rstrip('/')
            if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
                url = f"https://{url}"
            return url
        return None

    def _infer_full_name(self, text: str) -> Optional[str]:
        """
        Attempt to infer candidate full name using strict, high-confidence heuristics.

        Heuristics:
        - Must be located within the first 3 non-empty lines of the document.
        - Must consist of 2 to 4 capitalized words (Title Case or All Caps).
        - Must NOT contain digits, email symbols (`@`), URLs (`http`), or common resume/job titles.
        If any ambiguity or low confidence exists, returns `None`.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:3]:
            # Length and symbol checks
            if len(line) < 3 or len(line) > 50:
                continue
            if any(char in line for char in ['@', 'http', 'www', '.com', '.org']):
                continue
            if any(char.isdigit() for char in line):
                continue

            # Check against forbidden resume section headers and professional titles
            words = line.split()
            if not (2 <= len(words) <= 4):
                continue

            lower_words = {word.lower().strip(",.-") for word in words}
            if lower_words & FORBIDDEN_NAME_KEYWORDS:
                continue

            # Check that every word begins with an uppercase letter and contains only letters/hyphens/apostrophes
            is_capitalized = all(word[0].isupper() for word in words)
            valid_characters = all(
                all(char.isalpha() or char in "-.'" for char in word)
                for word in words
            )

            if is_capitalized and valid_characters:
                return line

        return None
