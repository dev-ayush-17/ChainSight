"""Unit tests for synthetic data models and generation."""

from pathlib import Path

from data.generate_synthetic import (
    generate_bom,
    generate_components,
    generate_facilities,
    generate_products,
    generate_suppliers,
    get_country_definitions,
    load_reference_ports,
)


def test_country_definitions_count_and_risk() -> None:
    """Verify that exactly 20 countries are returned with 8 high-risk."""
    countries = get_country_definitions()
    assert len(countries) == 20
    high_risk = [c for c in countries if c.risk_index >= 0.60]
    assert len(high_risk) == 8


def test_reference_ports_loading() -> None:
    """Verify that reference ports CSV is properly parsed into 12 ports."""
    ref_csv = Path("data/reference/ports_unlocode.csv")
    ports = load_reference_ports(ref_csv)
    assert len(ports) == 12
    un_locodes = {p.un_locode for p in ports}
    assert "CNSHA" in un_locodes
    assert "NLRTM" in un_locodes


def test_suppliers_and_tier_distribution() -> None:
    """Verify supplier count and tier distribution."""
    countries = get_country_definitions()
    suppliers = generate_suppliers(countries)
    assert len(suppliers) == 40
    tier1 = [s for s in suppliers if s.tier == 1]
    tier2 = [s for s in suppliers if s.tier == 2]
    tier3 = [s for s in suppliers if s.tier == 3]
    assert len(tier1) == 10
    assert len(tier2) == 20
    assert len(tier3) == 10


def test_components_sole_sourced_ratio() -> None:
    """Verify component count and that exactly 15 are sole-sourced."""
    components = generate_components()
    assert len(components) == 60
    sole_sourced = [c for c in components if c.is_sole_sourced]
    assert len(sole_sourced) == 15


def test_bom_links_components_to_all_products() -> None:
    """Verify that BOM connects components to every product."""
    components = generate_components()
    products = generate_products()
    bom = generate_bom(components, products)
    assert len(bom) > 0
    covered_product_ids = {b.product_id for b in bom}
    assert len(covered_product_ids) == len(products)


def test_facilities_generation() -> None:
    """Verify that 55 facilities are created for 40 suppliers."""
    countries = get_country_definitions()
    suppliers = generate_suppliers(countries)
    facilities, operates = generate_facilities(suppliers)
    assert len(facilities) == 55
    assert len(operates) == 55
