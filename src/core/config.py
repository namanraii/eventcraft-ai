"""Environment-backed settings.

Secrets stay in the process environment or a git-ignored ``.env`` file.
Nothing in this module has a default API key.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EventCraft AI"
    app_version: str = "1.0.0"

    xai_api_key: str = ""
    xai_model: str = "grok-4.7"
    xai_base_url: str = "https://api.x.ai/v1"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"

    rate_limit_per_minute: int = Field(default=60, ge=1, le=600)
    cache_ttl_seconds: int = Field(default=3600, ge=1, le=86_400)
    cache_max_entries: int = Field(default=128, ge=1, le=10_000)
    max_body_bytes: int = Field(default=32_768, ge=1_024, le=1_048_576)

    def active_provider_name(self) -> str | None:
        """Return the first configured model provider, if any.

        SpaceXAI (the xAI API) is preferred. Groq and Gemini are optional
        fallbacks. An empty string means the deterministic engines run alone.
        """
        if self.xai_api_key.strip():
            return "spacexai"
        if self.groq_api_key.strip():
            return "groq"
        if self.gemini_api_key.strip():
            return "gemini"
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide settings object.

    Tests should call :func:`get_settings.cache_clear` if they mutate the
    environment, or pass a ``Settings`` instance into ``create_app`` instead.
    """
    return Settings()
