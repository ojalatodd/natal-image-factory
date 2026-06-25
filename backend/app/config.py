from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 10080
    bootstrap_user_email: str | None = None
    bootstrap_user_password: str | None = None

    # Database
    database_url: str = "sqlite:////data/app.db"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # OpenAI
    openai_api_key: str | None = None

    # Spaces / S3
    spaces_endpoint_url: str = "http://minio:9000"
    spaces_region: str = "us-east-1"
    spaces_bucket: str = "natal-media"
    spaces_key: str = "minioadmin"
    spaces_secret: str = "minioadmin"
    spaces_public_url: str = "http://localhost:9000/natal-media"

    # Source API keys
    pexels_api_key: str | None = None
    pixabay_api_key: str | None = None
    unsplash_access_key: str | None = None
    smithsonian_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
