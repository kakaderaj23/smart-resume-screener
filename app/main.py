from contextlib import asynccontextmanager
import logging
from typing import Dict
from fastapi import FastAPI
from app.config import settings
from app.api import resume, screening, about

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
    
    # Initialize database tables
    from app.database import Base, engine
    import app.models  # Ensure models are imported so SQLAlchemy registers them
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}", exc_info=True)
        
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
app.include_router(screening.router)
app.include_router(about.router)

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify system availability.
    """
    return {
        "status": "healthy"
    }
