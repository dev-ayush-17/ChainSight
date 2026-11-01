"""FastAPI dependency injection providers for Neo4j driver and application settings."""

from collections.abc import Generator

from fastapi import Depends
from neo4j import Driver, GraphDatabase

from api.config import Settings, get_settings


def create_neo4j_driver(uri: str, auth: tuple[str, str]) -> Driver:
    """Create and return a Neo4j Bolt driver instance."""
    return GraphDatabase.driver(uri, auth=auth)


def get_neo4j_driver_from_settings(settings: Settings | None = None) -> Driver:
    """Instantiate a Neo4j driver from application Settings."""
    cfg = settings or get_settings()
    return create_neo4j_driver(cfg.neo4j_uri, (cfg.neo4j_user, cfg.neo4j_password))


def get_app_settings() -> Settings:
    """Provide application settings singleton for dependency injection."""
    return get_settings()


def get_driver(settings: Settings = Depends(get_app_settings)) -> Generator[Driver, None, None]:
    """Provide managed Neo4j Bolt driver instance with dependency injection."""
    driver = get_neo4j_driver_from_settings(settings)
    try:
        yield driver
    finally:
        pass
