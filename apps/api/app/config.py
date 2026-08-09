"""
ArogyaRakshak API — Configuration.

Reads environment variables for the application. All config is centralised here
so that no module ever hardcodes credentials or model names.

GROQ_MODEL defaults to "openai/gpt-oss-120b".  Never use deprecated model
names (llama3-70b, llama-3.3-70b-versatile) — see AGENTS.md.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # --- Groq -----------------------------------------------------------------
    groq_model: str = "openai/gpt-oss-120b"
    groq_api_key: str = ""

    # --- Database -------------------------------------------------------------
    database_url: str = "postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak"

    # --- Security -------------------------------------------------------------
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
