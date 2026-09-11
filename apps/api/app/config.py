"""
ArogyaRakshak API — Configuration.

Reads environment variables for the application. All config is centralised here
so that no module ever hardcodes credentials or model names.

GROQ_MODEL defaults to "openai/gpt-oss-120b".  Never use deprecated model
names (llama3-70b, llama-3.3-70b-versatile) — see AGENTS.md.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # --- Groq -----------------------------------------------------------------
    groq_model: str = "openai/gpt-oss-120b"
    groq_api_key: str = ""

    # --- Database -------------------------------------------------------------
    database_url: str = "postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak"

    # --- Security -------------------------------------------------------------
    cors_origins: str = "*"

    # --- Upload limits --------------------------------------------------------
    # Documents are read fully into RAM for transient parsing, so an unbounded upload is
    # a denial-of-service vector. 10 MB comfortably covers a scanned multi-page bill.
    max_upload_bytes: int = 10 * 1024 * 1024

    # --- Streaming ------------------------------------------------------------
    # The SSE generator polls until the case completes; without a ceiling a request for
    # an unknown case holds a connection open forever.
    sse_timeout_seconds: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
