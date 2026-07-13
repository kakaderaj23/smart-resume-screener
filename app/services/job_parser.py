"""
Job description parser for deterministic extraction of required skills from text.
"""

import re
from typing import List
from app.schemas.match import JobRequirements

# Predefined dictionary mapping common technical keyphrases to canonical skill representations
COMMON_SKILLS_MAP = {
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sqlalchemy": "SQLAlchemy",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "cloud": "Cloud",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "git": "Git",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "java": "Java",
    "spring": "Spring",
    "c++": "C++",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "rails": "Ruby on Rails",
    "php": "PHP",
    "laravel": "Laravel",
    "machine learning": "Machine Learning",
    "data science": "Data Science",
    "nlp": "NLP",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "rest api": "REST API",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "microservices": "Microservices",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "linux": "Linux",
    "bash": "Bash",
    "agile": "Agile",
    "scrum": "Scrum"
}


class JobDescriptionParser:
    """
    Parser responsible for extracting structured JobRequirements from raw text blocks.
    Keeps extraction isolated to enable clean drop-in replacement by semantic LLMs in the future.
    """

    def parse(self, text: str) -> JobRequirements:
        """
        Scan a raw job description string for known skill keywords case-insensitively.

        Args:
            text (str): Raw text of the job description.

        Returns:
            JobRequirements: Structured requirements with matched canonical skills.
        """
        if not text or not text.strip():
            return JobRequirements(required_skills=[])

        text_lower = text.lower()
        extracted_skills: List[str] = []

        # Compare against keyword list using regex word boundaries to prevent substring collisions
        for kw, canonical_name in COMMON_SKILLS_MAP.items():
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                if canonical_name not in extracted_skills:
                    extracted_skills.append(canonical_name)

        return JobRequirements(
            required_skills=extracted_skills,
            preferred_skills=[],
            minimum_experience=None,
            education=None,
            domain=None
        )
