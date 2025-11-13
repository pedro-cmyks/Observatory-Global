"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    # API
    API_BASE_URL: str = "http://localhost:8000"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # PostgreSQL (for future use)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "observatory"
    POSTGRES_USER: str = "observatory"
    POSTGRES_PASSWORD: str = "changeme"

    # External Services
    GDELT_BASE: str = "http://data.gdeltproject.org/gdeltv2"
    MAPBOX_TOKEN: Optional[str] = None

    # Cache settings
    CACHE_TTL: int = 300  # 5 minutes
    USE_CACHE: bool = True

    # Flow detection settings
    HEAT_HALFLIFE_HOURS: float = 6.0  # Time decay half-life
    FLOW_THRESHOLD: float = 0.5  # Minimum heat score for flows
    DRY_RUN_APIS: bool = False  # Mock external API calls for testing

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
