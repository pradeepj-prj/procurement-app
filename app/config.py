from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    For local development, place a `.env` file in the project root.
    On Cloud Foundry, set env vars via `cf set-env`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Graph backend: "hana" (production) or "networkx" (local dev with CSV)
    graph_backend: str = "hana"

    # NetworkX backend (local CSV mode)
    csv_dir: str = "../procurement-data-generator/output/csv"

    # HANA Cloud
    hana_host: str = ""
    hana_port: int = 443
    hana_user: str = "DBADMIN"
    hana_password: str = ""
    hana_schema: str = "PROCUREMENT"

    # SAP GenAI Hub (AI Core)
    aicore_auth_url: str = ""
    aicore_client_id: str = ""
    aicore_client_secret: str = ""
    aicore_resource_group: str = "default"
    aicore_base_url: str = ""
    genai_model_name: str = "anthropic--claude-4.6-opus"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
