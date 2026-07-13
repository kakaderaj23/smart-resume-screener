"""
Unit tests for GeminiProvider, mocking the google-genai SDK Client and response values.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.providers.gemini_provider import GeminiProvider, GeminiProviderError
from app.schemas.match import PromptPackage


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch):
    """Fixture to ensure a mock API key is set for provider initialization."""
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "test_mock_api_key_12345")


@patch("app.providers.gemini_provider.genai.Client")
def test_gemini_provider_initialization_success(mock_client_class):
    """Test that the provider client initializes successfully when key is present."""
    mock_client_class.return_value = MagicMock()
    provider = GeminiProvider()
    assert provider.model_name == "gemini-2.5-flash"
    mock_client_class.assert_called_once_with(api_key="test_mock_api_key_12345")


def test_gemini_provider_initialization_failure(monkeypatch):
    """Test that GeminiProviderError is raised if no API key is configured."""
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(GeminiProviderError) as exc_info:
        GeminiProvider()

    assert "API key is not configured" in str(exc_info.value)


@patch("app.providers.gemini_provider.genai.Client")
def test_gemini_provider_generate_success(mock_client_class):
    """
    Test successful generation of content. Verifies that:
    - generate_content is called with correct arguments.
    - system_instruction and response_mime_type are set correctly in the config.
    - Raw text response is returned.
    """
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = '{"semantic_score": 8, "confidence": "HIGH"}'
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider()
    prompt = PromptPackage(
        system_prompt="Test system instruction",
        user_prompt="Test user query",
        full_prompt="Full concatenated prompt"
    )

    result = provider.generate(prompt)

    assert result == '{"semantic_score": 8, "confidence": "HIGH"}'
    mock_client.models.generate_content.assert_called_once()
    
    # Assert call arguments are formatted correctly
    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["contents"] == "Test user query"
    assert kwargs["config"].system_instruction == "Test system instruction"
    assert kwargs["config"].response_mime_type == "application/json"


@patch("app.providers.gemini_provider.genai.Client")
def test_gemini_provider_generate_empty_response(mock_client_class):
    """Test exception raising when model returns empty text response."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(GeminiProviderError) as exc_info:
        provider.generate(prompt)

    assert "empty response" in str(exc_info.value)


@patch("app.providers.gemini_provider.genai.Client")
def test_gemini_provider_generate_api_error(mock_client_class):
    """Test that API generation connection errors are captured and re-raised as GeminiProviderError."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = RuntimeError("API rate limit exceeded")

    provider = GeminiProvider()
    prompt = PromptPackage(system_prompt="sys", user_prompt="usr", full_prompt="full")

    with pytest.raises(GeminiProviderError) as exc_info:
        provider.generate(prompt)

    assert "generation failed: API rate limit" in str(exc_info.value)
