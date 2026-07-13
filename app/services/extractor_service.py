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
from typing import List, Optional, Dict, Tuple, Set

from app.schemas.candidate import CandidateProfile, PersonalInfo, ProfessionalInfo, Metadata

logger = logging.getLogger("smart-resume-screener.services.extractor")

# Centralized technical skill dictionary with case-insensitive aliases
TECHNICAL_SKILL_DICTIONARY: Dict[str, List[str]] = {
    "Python": ["python"],
    "React": ["react", "react.js", "reactjs"],
    "Machine Learning": ["machine learning", "ml", "artificial intelligence", "deep learning"],
    "Git": ["git", "github"],
    "Docker": ["docker", "containerization"],
    "AWS": ["aws", "amazon web services"],
    "PostgreSQL": ["postgresql", "postgres"],
    "SQLAlchemy": ["sqlalchemy"],
    "FastAPI": ["fastapi"],
    "NumPy": ["numpy"],
    "Pandas": ["pandas"],
}


def _build_whole_word_regex(alias: str) -> re.Pattern:
    """Build a case-insensitive whole-word regex pattern for a skill alias."""
    escaped = re.escape(alias.lower())
    start_bound = r'\b' if alias[0].isalnum() or alias[0] == '_' else r'(?:^|\W)'
    end_bound = r'\b' if alias[-1].isalnum() or alias[-1] == '_' else r'(?:$|\W)'
    return re.compile(f"{start_bound}{escaped}{end_bound}", re.IGNORECASE)


# Precompile regex patterns for each canonical skill and its aliases for fast lookup
_TECHNICAL_SKILL_PATTERNS: List[Tuple[str, List[re.Pattern]]] = [
    (canonical, [_build_whole_word_regex(alias) for alias in aliases])
    for canonical, aliases in TECHNICAL_SKILL_DICTIONARY.items()
]

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
    TECHNICAL_SKILL_DICTIONARY = TECHNICAL_SKILL_DICTIONARY

    def extract_skills(self, text: str, explicit_items: Optional[List[str]] = None) -> List[str]:
        """
        Extract technical skills deterministically using centralized dictionary aliases
        and case-insensitive whole-word matching.

        Requirements:
        - Whole-word matching (e.g. 'ML' matches 'ML' but not 'HTML')
        - Alias mapping to canonical names (e.g. 'react.js' -> 'React')
        - Deduplication across matches and explicit section items
        - Alphabetical sorting of the output list
        """
        matched_canonical = set()

        # 1. Match dictionary aliases against the text using whole-word regex
        if text and text.strip():
            for canonical, patterns in _TECHNICAL_SKILL_PATTERNS:
                for pattern in patterns:
                    if pattern.search(text):
                        matched_canonical.add(canonical)
                        break

        # 2. Process explicit section items (from SKILLS section) and map them if they match an alias
        final_skills = set(matched_canonical)
        if explicit_items:
            for item in explicit_items:
                clean_item = re.sub(r'^[-\s]+|[-\s]+$', '', item.strip())
                if not clean_item or len(clean_item) < 2:
                    continue

                # Check if this item matches any alias in our dictionary
                mapped = False
                for canonical, patterns in _TECHNICAL_SKILL_PATTERNS:
                    if canonical in final_skills:
                        for pattern in patterns:
                            if pattern.search(clean_item):
                                mapped = True
                                break
                        if mapped:
                            break
                    else:
                        for pattern in patterns:
                            if pattern.search(clean_item):
                                final_skills.add(canonical)
                                mapped = True
                                break
                        if mapped:
                            break

                # If the item wasn't in the dictionary (e.g. Kubernetes, GraphQL), add its clean form
                if not mapped:
                    if not any(clean_item.lower() == existing.lower() for existing in final_skills):
                        final_skills.add(clean_item)

        # 3. Sort output alphabetically
        return sorted(list(final_skills), key=lambda x: x.lower())

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

        # Populate deterministic section-based professional lists
        professional_info = self._extract_professional_info(raw_text)

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

        return None

    def _extract_professional_info(self, text: str) -> ProfessionalInfo:
        """
        Perform deterministic section-based extraction of professional information from raw resume text.
        Detects common headings ("Skills", "Technical Skills", "Education", "Experience", "Projects", "Certifications")
        and populates the corresponding lists inside `ProfessionalInfo`.
        """
        skills: List[str] = []
        education: List[str] = []
        experience: List[str] = []
        certifications: List[str] = []

        seen_skills = set()
        current_section: Optional[str] = None

        skills_headers = {
            "skills", "technical skills", "core competencies", "key skills",
            "professional skills", "skills & expertise", "technologies",
            "technical competencies", "summary of skills", "competencies",
            "technical expertise"
        }
        education_headers = {
            "education", "academic background", "academic qualifications",
            "qualifications", "education & credentials", "academic history",
            "degrees", "educational background"
        }
        experience_headers = {
            "experience", "work experience", "professional experience",
            "employment history", "work history", "career history",
            "projects", "key projects", "professional projects",
            "relevant experience", "employment", "professional background",
            "selected projects", "technical projects"
        }
        certifications_headers = {
            "certifications", "licenses", "certificates", "certifications & licenses",
            "professional certifications", "licenses & certifications",
            "accreditations", "courses & certifications"
        }
        non_target_headers = {
            "summary", "objective", "profile", "professional summary",
            "contact", "contact info", "contact information", "personal info",
            "personal details", "references", "awards", "honors", "languages",
            "interests", "hobbies", "publications", "affiliations",
            "executive summary", "career objective"
        }

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            cleaned_for_check = re.sub(r'^[#*\-=_~:\s\d\.\>\+\[\(]+|[#*\-=_~:\s\.\+\]\)]+$', '', line).strip()
            normalized = " ".join(cleaned_for_check.lower().split())

            words = normalized.split()
            word_count = len(words)
            is_header_candidate = False

            if 1 <= word_count <= 5 and 2 <= len(normalized) <= 45:
                if (
                    normalized in skills_headers
                    or normalized in education_headers
                    or normalized in experience_headers
                    or normalized in certifications_headers
                    or normalized in non_target_headers
                ):
                    is_header_candidate = True
                else:
                    clean_alpha = re.sub(r'[^a-zA-Z]', '', line)
                    is_all_caps = len(clean_alpha) >= 3 and clean_alpha.isupper()
                    ends_with_colon = line.strip().endswith(":") and not any(
                        word.lower() in ("http:", "https:", "email:", "phone:", "tel:", "mobile:")
                        for word in line.split()
                    )
                    has_markdown_or_sep = bool(
                        re.match(r'^[#=~]{1,6}\s+\w+', line)
                        or re.match(r'^[=-]{3,}\s*\w+.*[=-]{3,}$', line)
                        or re.match(r'^\d+[\.\)]\s+[A-Z]\w+', line)
                    )

                    if is_all_caps or ends_with_colon or has_markdown_or_sep:
                        if any(k in normalized for k in ("skill", "competenc", "technolog")):
                            normalized = "skills"
                            is_header_candidate = True
                        elif any(k in normalized for k in ("education", "academic", "degree", "qualification")):
                            normalized = "education"
                            is_header_candidate = True
                        elif any(k in normalized for k in ("experience", "employment", "work history", "career history", "project")):
                            normalized = "experience"
                            is_header_candidate = True
                        elif any(k in normalized for k in ("certification", "certificate", "license", "licensure")):
                            normalized = "certifications"
                            is_header_candidate = True
                        elif any(k in normalized for k in ("summary", "objective", "profile", "reference", "contact", "award", "honor", "language", "interest")):
                            normalized = "summary"
                            is_header_candidate = True

            if is_header_candidate:
                if normalized in skills_headers or normalized == "skills":
                    current_section = "skills"
                elif normalized in education_headers or normalized == "education":
                    current_section = "education"
                elif normalized in experience_headers or normalized == "experience":
                    current_section = "experience"
                elif normalized in certifications_headers or normalized == "certifications":
                    current_section = "certifications"
                else:
                    current_section = None
                continue

            if current_section is not None:
                content_line = re.sub(r'^[•\*\-\+\d\.\>\s]+', '', line).strip()
                if not content_line or len(content_line) < 2:
                    continue

                if current_section == "skills":
                    if any(sep in content_line for sep in ("|", ",", ";", "•", "*")):
                        if ":" in content_line and not content_line.lower().startswith("http"):
                            parts_after_colon = content_line.split(":", 1)[1]
                            raw_items = re.split(r'[,|;•\*\+]', parts_after_colon)
                        else:
                            raw_items = re.split(r'[,|;•\*\+]', content_line)
                    else:
                        if ":" in content_line and not content_line.lower().startswith("http"):
                            raw_items = [content_line.split(":", 1)[1]]
                        else:
                            raw_items = [content_line]

                    for item in raw_items:
                        cleaned_item = re.sub(r'^[-\s]+|[-\s]+$', '', item.strip())
                        if len(cleaned_item) >= 2 and cleaned_item.lower() not in seen_skills:
                            seen_skills.add(cleaned_item.lower())
                            skills.append(cleaned_item)

                elif current_section == "education":
                    education.append(content_line)

                elif current_section == "experience":
                    experience.append(content_line)

                elif current_section == "certifications":
                    certifications.append(content_line)

        # Extract dictionary-matched skills across text, map explicit section items, deduplicate, and sort
        skills = self.extract_skills(text, explicit_items=skills)

        return ProfessionalInfo(
            skills=skills,
            education=education,
            experience=experience,
            certifications=certifications
        )

    def merge_profiles(
        self,
        deterministic_profile: Optional[CandidateProfile] = None,
        llm_profile: Optional[CandidateProfile] = None,
        db_profile: Optional[CandidateProfile] = None,
    ) -> CandidateProfile:
        """
        Merge multiple CandidateProfile instances across pipeline stages while enforcing strict hierarchy rules.
        Delegates to `CandidateProfile.merge_profiles`.
        """
        return CandidateProfile.merge_profiles(
            deterministic_profile=deterministic_profile,
            llm_profile=llm_profile,
            db_profile=db_profile
        )
