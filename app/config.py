from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://shortener:shortener_secret@localhost:5432/shortener"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "super-secret-key-change-me-in-production"
    access_token_expire_minutes: int = 60
    cleanup_unused_days: int = 30
    base_url: str = "http://localhost:8000"

    cache_ttl: int = 300


settings = Settings()
