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
    DESCRIPTION: str = "A backend API foundation for the Smart Resume Screener application."
    DATABASE_URL: str = "sqlite:///./smart_resume_screener.db"
    UPLOAD_DIR: Path = Path("uploads")
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-4.5"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Create a single settings instance to be imported across the application
settings = Settings()
