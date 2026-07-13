"""
Matching user prompt templates for candidate evaluation.
"""


def get_matching_prompt_template() -> str:
    """
    Return the user matching prompt template with placeholders.
    """
    return (
        "Please assess the following candidate against the job requirements and deterministic rule evidence.\n"
        "Evaluate using BOTH:\n"
        "1. Structured CandidateProfile\n"
        "AND\n"
        "2. Original Resume Text\n"
        "If structured extraction misses information but the raw resume clearly contains the evidence, use the raw resume. Never ignore explicit evidence in the resume.\n\n"
        "### STRUCTURED CANDIDATE PROFILE\n"
        "{candidate_profile}\n\n"
        "### ORIGINAL RESUME TEXT\n"
        "{raw_text}\n\n"
        "### JOB REQUIREMENTS\n"
        "{job_requirements}\n\n"
        "### DETERMINISTIC RULE EVIDENCE\n"
        "{rule_evidence}\n\n"
        "### FEW-SHOT EXAMPLE\n"
        "{few_shot_example}\n\n"
        "### OUTPUT JSON SCHEMA\n"
        "Provide your assessment conforming exactly to this JSON schema:\n"
        "{json_schema}\n\n"
        "Remember, your output must be a single, valid JSON object matching the schema. Begin output now:"
    )
