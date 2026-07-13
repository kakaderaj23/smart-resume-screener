"""
Unit and integration tests for Application Metadata endpoints (`GET /` and `GET /about`).
"""

from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_read_root_endpoint():
    """
    Verify `GET /` returns status 200 OK and basic application metadata structure.
    """
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == {
        "application": f"{settings.APP_NAME} API",
        "version": settings.VERSION,
        "status": "running",
        "documentation": "/docs"
    }


def test_read_about_endpoint():
    """
    Verify `GET /about` returns status 200 OK and complete system/architecture metadata,
    including dynamic verification of the configured Gemini model.
    """
    response = client.get("/about")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == {
        "application": settings.APP_NAME,
        "version": settings.VERSION,
        "description": "AI-powered resume screening system",
        "llm_provider": "Groq",
        "model": settings.GROQ_MODEL,
        "backend": "FastAPI",
        "database": "SQLite",
        "frontend": "React + Vite",
        "api_docs": "/docs",
        "health_endpoint": "/health"
    }
