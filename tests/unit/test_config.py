"""Unit tests for configuration and dependencies modules."""

from unittest.mock import patch

from api.config import Settings, get_settings
from api.dependencies import create_neo4j_driver, get_neo4j_driver_from_settings


def test_settings_default_values() -> None:
    """Verify default settings values for local development."""
    settings = Settings()
    assert settings.neo4j_uri == "bolt://localhost:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.neo4j_password == "password123"
    assert settings.random_seed == 42


def test_get_settings_cached_or_fresh() -> None:
    """Verify get_settings returns a valid Settings instance."""
    cfg = get_settings()
    assert isinstance(cfg, Settings)


@patch("api.dependencies.GraphDatabase.driver")
def test_create_neo4j_driver_invokes_driver(mock_driver_func) -> None:
    """Verify create_neo4j_driver calls GraphDatabase.driver with parameters."""
    mock_driver_func.return_value = "mock_driver"
    driver = create_neo4j_driver("bolt://localhost:7687", ("neo4j", "testpass"))
    assert driver == "mock_driver"
    mock_driver_func.assert_called_once_with("bolt://localhost:7687", auth=("neo4j", "testpass"))


@patch("api.dependencies.create_neo4j_driver")
def test_get_neo4j_driver_from_settings(mock_create) -> None:
    """Verify driver creation from custom or default settings."""
    custom_settings = Settings(
        neo4j_uri="bolt://127.0.0.1:7687",
        neo4j_user="admin",
        neo4j_password="secretpassword",
    )
    get_neo4j_driver_from_settings(custom_settings)
    mock_create.assert_called_once_with("bolt://127.0.0.1:7687", ("admin", "secretpassword"))
