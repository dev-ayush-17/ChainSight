"""Unit tests for parameterized Cypher impact traversal templates."""

from unittest.mock import MagicMock

from retrieval.traversal import (
    run_alternative_supplier_finder,
    run_country_concentration_risk,
    run_port_disruption_impact,
    run_supplier_disruption_impact,
)


def test_run_port_disruption_impact() -> None:
    """Verify run_port_disruption_impact executes query and constructs TraversalImpactResult."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value = [
        {
            "port_id": "PORT-SHA",
            "port_name": "Port of Shanghai",
            "supplier_id": "SUP-001",
            "supplier_name": "Acme Semi",
            "supplier_tier": 1,
            "component_id": "CMP-0001",
            "component_name": "CPU SoC Gen4 (v1)",
            "is_sole_sourced": True,
            "is_critical": True,
            "product_id": "PRD-001",
            "product_name": "UltraBook Pro 14",
            "annual_revenue_usd": 85000000.0,
        }
    ]

    res = run_port_disruption_impact(mock_driver, "Port of Shanghai")
    assert res.template_name == "port_disruption_impact"
    assert len(res.records) == 1
    assert "PORT-SHA" in res.subgraph_node_ids
    assert "PRD-001" in res.subgraph_node_ids


def test_run_supplier_disruption_impact() -> None:
    """Verify run_supplier_disruption_impact handles supplier risk traversals."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value = [
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Precision Optics",
            "reliability_score": 0.88,
            "component_id": "CMP-0020",
            "component_name": "OLED Panel",
            "is_sole_sourced": False,
            "product_id": "PRD-004",
            "product_name": "TabSight Air 11",
            "product_revenue": 52000000.0,
        }
    ]

    res = run_supplier_disruption_impact(mock_driver, "SUP-002")
    assert res.template_name == "supplier_disruption_impact"
    assert len(res.records) == 1
    assert "SUP-002" in res.subgraph_node_ids


def test_run_country_concentration_risk() -> None:
    """Verify run_country_concentration_risk calculates geographic exposure."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value = [
        {
            "country_code": "TW",
            "country_name": "Taiwan",
            "country_risk": 0.64,
            "supplier_count": 8,
            "exposed_product_count": 6,
            "total_revenue_at_risk": 350000000.0,
        }
    ]

    res = run_country_concentration_risk(mock_driver, "Taiwan")
    assert res.template_name == "country_concentration_risk"
    assert len(res.records) == 1
    assert res.records[0]["total_revenue_at_risk"] == 350000000.0


def test_run_alternative_supplier_finder() -> None:
    """Verify run_alternative_supplier_finder locates substitute vendors."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value = [
        {
            "primary_supplier_id": "SUP-001",
            "primary_supplier_name": "Primary Vendor",
            "alt_supplier_id": "SUP-009",
            "alt_supplier_name": "Backup Vendor",
            "alt_country": "KR",
            "alt_reliability": 0.92,
            "component_id": "CMP-0001",
            "component_name": "DDR5 Memory",
            "qualification_status": "Qualified",
        }
    ]

    res = run_alternative_supplier_finder(mock_driver, "CMP-0001")
    assert res.template_name == "alternative_supplier_finder"
    assert len(res.records) == 1
    assert res.records[0]["alt_supplier_name"] == "Backup Vendor"
