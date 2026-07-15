from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.
    Uses pydantic-settings BaseSettings to automatically load values
    from environment variables and .env files.
    """
    APP_NAME: str = "Smart Resume Screener"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered resume screening system for evaluating candidates against job descriptions."
    DATABASE_URL: str = "sqlite:///./smart_resume_screener.db"
    UPLOAD_DIR: Path = Path("uploads")
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-4.5"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Create a single settings instance to be imported across the application
settings = Settings()
