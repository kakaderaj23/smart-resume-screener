"""
Application metadata endpoints (`GET /` and `GET /about`) for the Smart Resume Screener API.

Architectural Decisions & Module Design:
1. Read-Only Operations: These endpoints perform no database queries, file I/O, or LLM calls.
   They are guaranteed to be fast and non-blocking, making them ideal for container orchestration probes,
   load balancer monitoring, and developer introspection.
2. Configuration-Driven: Dynamic metadata such as version, application name, and configured LLM models
   are read directly from `app.config.settings`. This prevents drift between code and deployed configuration.
3. Production Observability: Providing structured system metadata (`version`, `llm_provider`, `database`, `frontend`)
   simplifies runtime verification and health checking across environments (local, staging, production).
"""

from typing import Dict
from fastapi import APIRouter, status
from app.config import settings

# APIRouter without prefix so root paths map directly (`/` and `/about`)
router = APIRouter(
    tags=["Metadata"]
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root Application Information",
    description="Returns basic application status, runtime version, and API documentation URL."
)
async def read_root() -> Dict[str, str]:
    """
    Root endpoint returning concise API application info and status.

    Returns:
        Dict[str, str]: Structured dictionary containing application name, version, status, and docs path.
    """
    return {
        "application": f"{settings.APP_NAME} API",
        "version": settings.VERSION,
        "status": "running",
        "documentation": "/docs"
    }


@router.get(
    "/about",
    status_code=status.HTTP_200_OK,
    summary="Detailed Application Metadata",
    description="Returns comprehensive system metadata including backend framework, database engine, "
                "configured LLM provider/model, frontend stack, and relevant API links."
)
async def read_about() -> Dict[str, str]:
    """
    Detailed metadata endpoint exposing runtime infrastructure and model configuration.

    Returns:
        Dict[str, str]: Comprehensive system summary including backend, database, LLM provider,
                        model name read from config, and documentation links.
    """
    return {
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
