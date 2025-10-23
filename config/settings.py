"""
Application settings using Pydantic Settings.
Matches pattern from web-backend/app/core/config.py
"""
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Configuration
    APP_ENV: str = "development"
    APP_NAME: str = "AICallGO Admin Board"
    DEBUG: bool = True

    # Database Logging
    SQL_ECHO: bool = False  # Enable SQL query logging (independent of DEBUG)

    # Database Configuration (sync format - will be converted to async internally when needed)
    DATABASE_URL_SYNC: PostgresDsn

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL_SYNC to async format for SQLAlchemy async engine."""
        url = str(self.DATABASE_URL_SYNC)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=" in url:
                url = url.replace("sslmode=", "ssl=")
        return url

    @property
    def sync_database_url(self) -> str:
        """
        Convert DATABASE_URL_SYNC to sync format for SQLAlchemy sync engine.
        Uses psycopg2 driver (default for postgresql://)
        """
        url = str(self.DATABASE_URL_SYNC)
        # Remove async driver if present
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        return url

    # Admin Authentication
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str  # bcrypt hash
    SESSION_SECRET_KEY: str  # Secret key for signing session cookies
    SESSION_TIMEOUT_HOURS: int = 8

    # Streamlit Configuration
    STREAMLIT_SERVER_PORT: int = 8501
    STREAMLIT_SERVER_ADDRESS: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
