"""
Prompts package for the Smart Resume Screener application.
Exposes modular system and matching prompt templates.
"""

from app.prompts.system_prompt import get_system_prompt
from app.prompts.matching_prompt import get_matching_prompt_template

__all__ = ["get_system_prompt", "get_matching_prompt_template"]
