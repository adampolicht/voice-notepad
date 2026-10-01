"""Application configuration loaded from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Language = Literal["auto", "pl", "en"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    whisper_model: str = "small"
    whisper_device: Literal["auto", "cpu", "cuda"] = "auto"
    whisper_compute_type: Literal["auto", "int8", "float16", "float32"] = "auto"
    host: str = "127.0.0.1"
    port: int = 8000
    default_language: Language = "auto"
    notes_dir: str = "~/.voice-notepad/notes"


settings = Settings()
