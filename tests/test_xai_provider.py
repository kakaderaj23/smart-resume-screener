"""
Unit tests for XAIProvider, mocking the official OpenAI Client and response values.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.providers.xai_provider import XAIProvider, XAIProviderError
from app.schemas.match import PromptPackage


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch):
    """Fixture to ensure a mock API key is set for provider initialization."""
    monkeypatch.setattr("app.config.settings.XAI_API_KEY", "test_mock_xai_key_12345")


@patch("app.providers.xai_provider.OpenAI")
def test_xai_provider_initialization_success(mock_client_class):
    """Test that the provider client initializes successfully with base_url=https://api.x.ai/v1 when key is present."""
    mock_client_class.return_value = MagicMock()
    provider = XAIProvider()
    assert provider.model_name == "grok-2-latest"
    mock_client_class.assert_called_once_with(api_key="test_mock_xai_key_12345", base_url="https://api.x.ai/v1")


def test_xai_provider_initialization_failure(monkeypatch):
    """Test that XAIProviderError is raised if no API key is configured."""
    monkeypatch.setattr("app.config.settings.XAI_API_KEY", "")
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    with pytest.raises(XAIProviderError) as exc_info:
        XAIProvider()

    assert "API key is not configured" in str(exc_info.value)


@patch("app.providers.xai_provider.OpenAI")
def test_xai_provider_generate_success(mock_client_class):
    """
    Test successful generation of content. Verifies that:
    - chat.completions.create is called with correct messages.
    - model and response_format (JSON mode) are set correctly.
    - Raw text response is returned.
    """
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_choice = MagicMock()
    mock_choice.message.content = '{"semantic_score": 90, "confidence": "HIGH"}'
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion

    provider = XAIProvider()
    prompt = PromptPackage(
        system_prompt="Test system instruction",
        user_prompt="Test user query",
        full_prompt="Full concatenated prompt"
    )

    result = provider.generate(prompt)

    assert result == '{"semantic_score": 90, "confidence": "HIGH"}'
    mock_client.chat.completions.create.assert_called_once_with(
        messages=[
            {"role": "system", "content": "Test system instruction"},
            {"role": "user", "content": "Test user query"}
        ],
        model="grok-2-latest",
        response_format={"type": "json_object"}
    )


@patch("app.providers.xai_provider.OpenAI")
def test_xai_provider_generate_empty_choices(mock_client_class):
    """Test exception raising when model returns no choices."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = []
    mock_client.chat.completions.create.return_value = mock_completion

    provider = XAIProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(XAIProviderError) as exc_info:
        provider.generate(prompt)

    assert "returned no choices" in str(exc_info.value)


@patch("app.providers.xai_provider.OpenAI")
def test_xai_provider_generate_empty_response_content(mock_client_class):
    """Test exception raising when model returns empty message content."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion

    provider = XAIProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(XAIProviderError) as exc_info:
        provider.generate(prompt)

    assert "empty response" in str(exc_info.value)


@patch("app.providers.xai_provider.OpenAI")
def test_xai_provider_generate_api_error(mock_client_class):
    """Test that API generation connection or SDK errors are captured and re-raised as XAIProviderError."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = RuntimeError("API rate limit exceeded")

    provider = XAIProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(XAIProviderError) as exc_info:
        provider.generate(prompt)

    assert "xAI content generation failed: API rate limit" in str(exc_info.value)
