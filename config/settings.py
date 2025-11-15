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

    # Redis Configuration (for cache invalidation and real-time monitoring)
    REDIS_URL: str = "redis://:aicallgo_redis_password@aicallgo_redis:6379/0"
    ENTITLEMENT_CACHE_KEY_PREFIX: str = "entitlements"

    # Cold Call Redis (shared database with outcall-agent - database 5)
    COLD_CALL_REDIS_URL: str = "redis://:aicallgo_redis_password@aicallgo_redis:6379/5"

    # Redis Channels (matching web-backend call logging system)
    REDIS_CHANNEL_CALL_LOGS: str = "call_logs"
    REDIS_CHANNEL_HEARTBEAT: str = "call_heartbeat"
    REDIS_CHANNEL_DLQ: str = "call_logs_dlq"

    # Backblaze B2 Configuration (for call recordings)
    B2_APPLICATION_KEY_ID: str
    B2_APPLICATION_KEY: str
    B2_BUCKET_NAME: str = "aicallgo"
    B2_REGION: str = "us-west-004"

    # Kubernetes Configuration (for logs viewer)
    KUBECONFIG_PATH: str = ""  # Empty string means use in-cluster config
    K8S_NAMESPACE: str = "aicallgo-staging"
    K8S_LOGS_ENABLED: bool = True

    # Web Backend API Configuration (for internal API calls)
    WEB_BACKEND_URL: str = "http://aicallgo_app:8000"  # Web backend base URL (Docker service name)
    INTERNAL_API_KEY: str  # Internal API key for service-to-service auth

    # Cold Call Dialer Configuration
    OUTCALL_AGENT_INTERNAL_URL: str = "http://outcall-agent:8000"  # Outcall agent service URL
    ENABLE_COLD_CALL_DIALER: bool = True  # Enable cold call dialer feature
    COLD_CALL_PROVIDER: str = "twilio"  # Cold call telephony provider (twilio or telnyx)
    # Note: Twilio uses conference mode, Telnyx uses direct WebRTC calling

    # Telnyx SIP Configuration (for direct calling)
    TELNYX_SIP_PHONE_NUMBER: str = ""  # Telnyx phone number for outgoing calls (caller ID)

    # Odoo CRM Integration (for Cold Call Dialer)
    ODOO_URL: str = "https://odoo.julya.ai"  # Odoo instance URL (public for local, VPC for prod)
    ODOO_DB: str = "odoo"  # Odoo database name
    ODOO_USERNAME: str = "admin"  # Odoo API username
    ODOO_PASSWORD: str = ""  # Odoo API password (leave empty to disable Odoo integration)

    # Twilio Phone Number Pool Configuration
    PN_ACTIVE_NUMBER_MAX_POOL_SIZE: int = 4  # Maximum active numbers in pool
    PN_PURCHASE_BATCH_SIZE: int = 1  # How many to buy at once
    PN_MAX_UNUSED: int = 2  # Max unassigned available numbers

    @field_validator("COLD_CALL_PROVIDER")
    @classmethod
    def validate_cold_call_provider(cls, v: str) -> str:
        """Validate cold call provider."""
        allowed = ["twilio", "telnyx"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"COLD_CALL_PROVIDER must be one of {allowed}, got '{v}'")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
