"""Centralized configuration via Pydantic BaseSettings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ENCOURAGE_GATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        extra="allow",
    )

    socket_path: Path = Field(default=Path("/tmp/encourage-gate.sock"))
    log_level: str = Field(default="INFO")
    model: str = Field(default="anthropic/claude-haiku-4-5")
    rewrite_timeout_seconds: float = Field(default=10.0)
    max_request_bytes: int = Field(default=64 * 1024)
