import os
from pathlib import Path
from pydantic import BaseModel

class Settings(BaseModel):
    """
    Application configuration settings.
    Provides type safety and centralized values for backend services.
    """
    APP_NAME: str = "Smart Resume Screener"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "A backend API foundation for the Smart Resume Screener application."
    DATABASE_URL: str = "sqlite:///./smart_resume_screener.db"
    UPLOAD_DIR: Path = Path("uploads")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Create a single settings instance to be imported across the application
settings = Settings()
