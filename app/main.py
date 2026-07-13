from contextlib import asynccontextmanager
import logging
from typing import Dict
from fastapi import FastAPI
from app.config import settings
from app.api import resume

# Configure simple application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smart-resume-screener")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown routines.
    """
    logger.info("Initializing Smart Resume Screener Backend Foundation...")
    logger.info(f"App Name: {settings.APP_NAME}")
    logger.info(f"Version: {settings.VERSION}")
    yield
    logger.info("Shutting down Smart Resume Screener Backend...")

# Initialize the FastAPI app with metadata from configuration
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc UI
)

# Register API routers
app.include_router(resume.router)

@app.get("/", tags=["Root"])
async def read_root() -> Dict[str, str]:
    """
    Root endpoint returning general API information and status.
    """
    return {
        "message": "Smart Resume Screener API",
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify system availability.
    """
    return {
        "status": "healthy"
    }
