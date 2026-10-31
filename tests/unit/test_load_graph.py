"""Unit tests for Neo4j ingestion script with mock drivers."""

from pathlib import Path
from unittest.mock import MagicMock

from ingestion.load_graph import (
    create_constraints_and_indexes,
    load_components,
    load_countries,
    load_customers,
    load_facilities,
    load_ports,
    load_products,
    load_relationships,
    load_suppliers,
)


def test_create_constraints_and_indexes_executes() -> None:
    """Verify that constraints and indexes statements are executed."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    create_constraints_and_indexes(mock_driver)

    # 9 constraints + 3 indexes = 12 statements
    assert mock_session.run.call_count == 12


def test_load_entities_with_mock_driver() -> None:
    """Verify that loading functions parse CSVs and call session.run with batches."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    data_dir = Path("data/raw/synthetic")

    c_count = load_countries(mock_driver, data_dir)
    assert c_count == 20
    assert mock_session.run.called

    p_count = load_ports(mock_driver, data_dir)
    assert p_count == 12

    s_count = load_suppliers(mock_driver, data_dir)
    assert s_count == 40

    f_count = load_facilities(mock_driver, data_dir)
    assert f_count == 55

    cmp_count = load_components(mock_driver, data_dir)
    assert cmp_count == 60

    prd_count = load_products(mock_driver, data_dir)
    assert prd_count == 9

    cust_count = load_customers(mock_driver, data_dir)
    assert cust_count == 15

    rel_counts = load_relationships(mock_driver, data_dir)
    assert "OPERATES" in rel_counts
    assert "PRODUCES" in rel_counts
    assert "PART_OF" in rel_counts
    assert "SHIPS_VIA" in rel_counts
    assert "ALTERNATIVE_FOR" in rel_counts
    assert "SHIPS_TO" in rel_counts
