"""
Unit tests for prompt template utilities.
"""

from app.prompts import get_system_prompt, get_matching_prompt_template


def test_system_prompt_requirements():
    """Verify system prompt structure and constraints."""
    system_prompt = get_system_prompt()
    assert isinstance(system_prompt, str)
    assert len(system_prompt) > 100
    assert "recruiter" in system_prompt.lower()
    assert "json" in system_prompt.lower()
    assert "hallucinate" in system_prompt.lower()


def test_matching_prompt_template_placeholders():
    """Verify placeholders are defined inside matching prompt template."""
    template = get_matching_prompt_template()
    assert isinstance(template, str)
    assert "{candidate_profile}" in template
    assert "{job_requirements}" in template
    assert "{rule_evidence}" in template
    assert "{json_schema}" in template
    assert "{few_shot_example}" in template
