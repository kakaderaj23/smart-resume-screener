"""
Matching user prompt templates for candidate evaluation.
"""


def get_matching_prompt_template() -> str:
    """
    Return the user matching prompt template with placeholders.
    """
    return (
        "Please assess the following candidate against the job requirements and deterministic rule evidence.\n\n"
        "### CANDIDATE PROFILE\n"
        "{candidate_profile}\n\n"
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
