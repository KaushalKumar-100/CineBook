from functools import lru_cache
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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
