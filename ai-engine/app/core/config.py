"""Environment-based settings for the local API."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "LawSphere"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: Path = _PROJECT_ROOT / "local-data" / "database" / "lawsphere.db"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 1.5

    model_config = SettingsConfigDict(
        env_prefix="LAWSPHERE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
