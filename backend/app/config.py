from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CineBook API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "development-only-change-this-secret"
    access_token_expire_minutes: int = 60

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "cinebook_db"
    db_user: str = "root"
    db_password: str = ""
    db_echo: bool = False
    demo_mode: bool = True
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower() in {"production", "prod"}:
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false outside local development.")
            if len(self.secret_key) < 32 or self.secret_key.startswith("development-only"):
                raise ValueError("Set a unique SECRET_KEY with at least 32 characters in production.")
            if not self.cors_allowed_origins.strip():
                raise ValueError("Set CORS_ALLOWED_ORIGINS to the deployed frontend origin.")
            if "*" in [origin.strip() for origin in self.cors_allowed_origins.split(",")]:
                raise ValueError("Wildcard CORS origins are not allowed in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
