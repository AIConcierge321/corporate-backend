from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Corporate Travel Platform"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5435/corporate_travel"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6385/0"

    # Security
    SECRET_KEY: str = "changethis-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AirportTransfer API (Ground Transport)
    # Get API key from: emine@airporttransfer.com or hasan@airporttransfer.com
    AIRPORT_TRANSFER_API_KEY: Optional[str] = None
    AIRPORT_TRANSFER_BASE_URL: str = "https://api.airporttransfer.com"
    AIRPORT_TRANSFER_USE_MOCK: bool = True  # Set to False when you have API key
    
    # All Aboard Train API (Rail)
    # Docs: https://docs.allaboard.eu/
    ALLABOARD_API_KEY: Optional[str] = None
    ALLABOARD_BASE_URL: str = "https://api-gateway.allaboard.eu"
    ALLABOARD_USE_TEST: bool = False  # Use production environment
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()

