from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_base_url: str = "http://localhost:1234/v1"
    openai_api_key: str = "lm-studio"
    default_model: str = "google/gemma-4-e2b"
    max_turns: int = 10
    log_level: str = "info"
    app_port: int = 8000
    app_host: str = "127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

