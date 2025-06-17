# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: config.py
# author: dunamismax
# version: 1.0.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: Pydantic-based settings management from environment variables.
# -----------------------------------------------------------------------------
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings to load configuration from a .env file or the
    environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "HTMX FastAPI Demo"
    LOG_LEVEL: str = Field("INFO", description="Logging level for the application.")


settings = AppSettings()
