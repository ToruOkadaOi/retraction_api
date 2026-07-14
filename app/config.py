from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/retraction_watch.db"
    csv_path: Path = Path("data/retraction_watch.csv")
    debug: bool = False
    api_title: str = "Retraction Watch API"
    api_version: str = "0.1.0"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding="utf-8",
    )

settings = Settings()
