"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    gemini_api_key: str = ""
    groq_api_key: str = ""
    newsapi_key: str = ""

    random_seed: int = 42
    log_level: str = "INFO"


def get_settings() -> Settings:
    """Return a cached or newly initialized application Settings instance."""
    return Settings()
