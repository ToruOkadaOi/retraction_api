import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    api_url: str = "https://retraction-api.onrender.com"
    api_timeout: float = Field(default=10.0, gt=0)
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    mcp_allowed_hosts: str = ""
    mcp_allowed_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RETRACTION_",
        extra="ignore",
        env_file_encoding="utf-8",
    )

    @property
    def base_url(self) -> str:
        return self.api_url.rstrip("/")

    @property
    def server_port(self) -> int:
        port = int(os.environ.get("PORT", self.mcp_port))
        if not 1 <= port <= 65535:
            raise ValueError("MCP server port must be between 1 and 65535")
        return port

    @property
    def allowed_hosts(self) -> list[str]:
        return self._split(self.mcp_allowed_hosts)

    @property
    def allowed_origins(self) -> list[str]:
        return self._split(self.mcp_allowed_origins)

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]


settings = MCPSettings()
