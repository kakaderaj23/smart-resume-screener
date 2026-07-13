"""
Unit tests for GroqProvider, mocking the official Groq Client and response values for openai/gpt-oss-120b.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.providers.groq_provider import GroqProvider, GroqProviderError
from app.schemas.match import PromptPackage


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch):
    """Fixture to ensure a mock API key is set for provider initialization."""
    monkeypatch.setattr("app.config.settings.GROQ_API_KEY", "test_mock_groq_key_12345")


@patch("app.providers.groq_provider.Groq")
def test_groq_provider_initialization_success(mock_client_class):
    """Test that the provider client initializes successfully when key is present."""
    mock_client_class.return_value = MagicMock()
    provider = GroqProvider()
    assert provider.model_name == "openai/gpt-oss-120b"
    mock_client_class.assert_called_once_with(api_key="test_mock_groq_key_12345")


def test_groq_provider_initialization_failure(monkeypatch):
    """Test that GroqProviderError is raised if no API key is configured."""
    monkeypatch.setattr("app.config.settings.GROQ_API_KEY", "")
    monkeypatch.setattr("app.config.settings.XAI_API_KEY", "")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with pytest.raises(GroqProviderError) as exc_info:
        GroqProvider()

    assert "API key is not configured" in str(exc_info.value)


@patch("app.providers.groq_provider.Groq")
def test_groq_provider_generate_success(mock_client_class):
    """
    Test successful generation of content using official parameters (temperature=1, max_completion_tokens=8192, top_p=1).
    """
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_choice = MagicMock()
    mock_choice.message.content = '{"semantic_score": 92, "confidence": "HIGH"}'
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion

    provider = GroqProvider()
    prompt = PromptPackage(
        system_prompt="Test system instruction",
        user_prompt="Test user query",
        full_prompt="Full concatenated prompt"
    )

    result = provider.generate(prompt)

    assert result == '{"semantic_score": 92, "confidence": "HIGH"}'
    mock_client.chat.completions.create.assert_called_once_with(
        messages=[
            {"role": "system", "content": "Test system instruction"},
            {"role": "user", "content": "Test user query"}
        ],
        model="openai/gpt-oss-120b",
        temperature=1,
        max_completion_tokens=3500,
        top_p=1,
        reasoning_effort="medium",
        response_format={"type": "json_object"}
    )


@patch("app.providers.groq_provider.Groq")
def test_groq_provider_generate_empty_choices(mock_client_class):
    """Test exception raising when model returns no choices."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = []
    mock_client.chat.completions.create.return_value = mock_completion

    provider = GroqProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(GroqProviderError) as exc_info:
        provider.generate(prompt)

    assert "returned no choices" in str(exc_info.value)


@patch("app.providers.groq_provider.Groq")
def test_groq_provider_generate_empty_response_content(mock_client_class):
    """Test exception raising when model returns empty message content."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion

    provider = GroqProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(GroqProviderError) as exc_info:
        provider.generate(prompt)

    assert "empty response" in str(exc_info.value)


@patch("app.providers.groq_provider.Groq")
def test_groq_provider_generate_api_error(mock_client_class):
    """Test that API generation connection or SDK errors are captured and re-raised as GroqProviderError."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = RuntimeError("API rate limit exceeded")

    provider = GroqProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(GroqProviderError) as exc_info:
        provider.generate(prompt)

    assert "Groq content generation failed: API rate limit" in str(exc_info.value)
