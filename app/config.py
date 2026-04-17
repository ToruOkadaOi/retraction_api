from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings): # need to look more into pydant-settings

    database_url: str = "sqlite:///./data/retraction_watch.db"
    csv_path: Path = Path("data/retraction_watch.csv")
    debug: bool = False
    api_title: str = "Retraction Watch API"
    api_version: str = "0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore", 
        env_file_encoding="utf-8",
    )

settings = Settings()