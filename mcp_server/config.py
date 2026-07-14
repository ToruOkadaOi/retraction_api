from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    api_url: str = "http://localhost:8000"
    api_timeout: float = Field(default=10.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RETRACTION_",
        extra="ignore",
        env_file_encoding="utf-8",
    )

    @property
    def base_url(self) -> str:
        return self.api_url.rstrip("/")


settings = MCPSettings()
