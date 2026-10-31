"""Dependency injection providers for database drivers and clients."""

from collections.abc import Generator

from neo4j import Auth, Driver, GraphDatabase

from api.config import Settings, get_settings


def create_neo4j_driver(uri: str, auth: Auth | tuple[str, str]) -> Driver:
    """Create and return a configured Neo4j driver instance."""
    return GraphDatabase.driver(uri, auth=auth)


def get_neo4j_driver_from_settings(settings: Settings | None = None) -> Driver:
    """Instantiate a Neo4j driver configured from application settings."""
    cfg = settings or get_settings()
    return create_neo4j_driver(cfg.neo4j_uri, (cfg.neo4j_user, cfg.neo4j_password))


def get_driver_session(driver: Driver) -> Generator[Driver, None, None]:
    """Yield Neo4j driver instance for FastAPI dependency injection."""
    yield driver
