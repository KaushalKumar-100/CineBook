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

    # Accept the deployed variable name used by the environment template.
    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Optional integrations. Keep secrets exclusively in backend/.env.
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    payment_provider: str = "disabled"
    payment_enabled: bool = False
    seat_hold_minutes: int = 8
    tmdb_read_access_token: str = ""
    tmdb_api_key: str = ""
    ticketmaster_api_key: str = ""
    google_maps_api_key: str = ""
    google_maps_map_id: str = ""
    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "CineBook"
    allevents_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    email_provider: str = "smtp"
    frontend_reset_url: str = "http://localhost:5173/reset-password"
    public_api_url: str = "http://127.0.0.1:8000"
    rate_limit_per_minute: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    # Backward-compatible alias for older deployments.
    @property
    def cors_origins(self) -> str:
        return self.cors_allowed_origins

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower() in {"production", "prod"}:
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false outside local development.")
            if len(self.secret_key) < 32 or self.secret_key.startswith("development-only"):
                raise ValueError(
                    "Set a unique SECRET_KEY with at least 32 characters in production."
                )
            if "*" in self.allowed_origins:
                raise ValueError("Wildcard CORS is not allowed in production.")
            if not self.allowed_origins:
                raise ValueError("Configure at least one explicit frontend CORS origin.")
        if self.seat_hold_minutes < 1 or self.seat_hold_minutes > 30:
            raise ValueError("SEAT_HOLD_MINUTES must be between 1 and 30.")
        if self.rate_limit_per_minute < 1:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be positive.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
