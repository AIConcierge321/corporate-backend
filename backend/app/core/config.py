from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import logging
import sys

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "Corporate Travel Platform"
    API_V1_STR: str = "/api/v1"
    
    # ===========================================
    # REQUIRED - No defaults (must be set in env)
    # ===========================================
    
    # Database - REQUIRED
    DATABASE_URL: str
    
    # Security - REQUIRED (generate with: openssl rand -hex 32)
    SECRET_KEY: str
    
    # ===========================================
    # OPTIONAL - With safe defaults
    # ===========================================
    
    # Redis
    REDIS_URL: str = "redis://localhost:6385/0"

    # Security settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Development Mode - NEVER enable in production!
    # When True: allows mock SSO authentication for local development
    DEV_MODE: bool = False
    
    # CORS - Comma-separated list of allowed origins
    # Example: "https://app.example.com,https://admin.example.com"
    CORS_ORIGINS: str = "*"  # Default allows all for dev, restrict in production!
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute per IP
    
    # AirportTransfer API (Ground Transport)
    AIRPORT_TRANSFER_API_KEY: Optional[str] = None
    AIRPORT_TRANSFER_BASE_URL: str = "https://api.airporttransfer.com"
    AIRPORT_TRANSFER_USE_MOCK: bool = True
    
    # All Aboard Train API (Rail)
    ALLABOARD_API_KEY: Optional[str] = None
    ALLABOARD_BASE_URL: str = "https://api-gateway.allaboard.eu"
    ALLABOARD_USE_TEST: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "changethis-secret-key-in-production":
            raise ValueError(
                "SECRET_KEY must be changed from default! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v


def _validate_settings() -> Settings:
    """Create and validate settings, with helpful error messages."""
    try:
        s = Settings()
        
        # Log warning if DEV_MODE is enabled
        if s.DEV_MODE:
            logger.warning("=" * 60)
            logger.warning("⚠️  DEV_MODE is ENABLED - Mock authentication allowed!")
            logger.warning("⚠️  DO NOT use DEV_MODE=true in production!")
            logger.warning("=" * 60)
        
        return s
        
    except Exception as e:
        print("\n" + "=" * 60, file=sys.stderr)
        print("❌ CONFIGURATION ERROR", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"\n{e}\n", file=sys.stderr)
        print("Required environment variables:", file=sys.stderr)
        print("  - DATABASE_URL: PostgreSQL connection string", file=sys.stderr)
        print("  - SECRET_KEY: JWT signing key (min 32 chars)", file=sys.stderr)
        print("\nExample .env file:", file=sys.stderr)
        print('  DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"', file=sys.stderr)
        print('  SECRET_KEY="your-secure-random-key-at-least-32-chars"', file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        raise


settings = _validate_settings()

