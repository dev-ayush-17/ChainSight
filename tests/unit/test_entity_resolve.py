"""Unit tests for the three-stage entity resolution module."""

from extraction.entity_resolve import (
    normalize_entity_string,
    resolve_country_entity,
    resolve_entity,
    resolve_port_entity,
)
from extraction.schemas import ExtractedEntity


def test_normalize_entity_string() -> None:
    """Verify normalize_entity_string cleans casing, punctuation, and extra whitespace."""
    assert normalize_entity_string("  Port of Shanghai!!  ") == "port of shanghai"
    assert normalize_entity_string("U.S.A.") == "usa"


def test_resolve_port_entity_exact_and_alias() -> None:
    """Verify resolve_port_entity matches canonical ports from variations."""
    res1 = resolve_port_entity("Port of Shanghai")
    assert res1 is not None
    assert res1.target_id == "PORT-SHA"
    assert res1.target_name == "Port of Shanghai"
    assert res1.resolution_method == "exact"

    res2 = resolve_port_entity("Port of LA")
    assert res2 is not None
    assert res2.target_id == "PORT-LAX"
    assert res2.target_name == "Port of Los Angeles"

    res3 = resolve_port_entity("Rotterdam")
    assert res3 is not None
    assert res3.target_id == "PORT-RTM"


def test_resolve_country_entity_variations() -> None:
    """Verify resolve_country_entity matches codes and country names."""
    res_cn = resolve_country_entity("PRC")
    assert res_cn is not None
    assert res_cn.target_id == "CN"
    assert res_cn.target_name == "China"

    res_tw = resolve_country_entity("Taiwan")
    assert res_tw is not None
    assert res_tw.target_id == "TW"

    res_us = resolve_country_entity("United States")
    assert res_us is not None
    assert res_us.target_id == "US"


def test_resolve_entity_with_registries() -> None:
    """Verify resolve_entity utilizes supplier and component registries."""
    supp_reg = {"Acme Semiconductor": "SUP-001", "Global Precision": "SUP-002"}
    comp_reg = {"DDR5 DRAM 16GB (v1)": "CMP-0001"}

    entity_supp = ExtractedEntity(label="Supplier", name="Acme Semiconductor", properties={})
    res_supp = resolve_entity(entity_supp, supplier_registry=supp_reg)
    assert res_supp.target_id == "SUP-001"
    assert res_supp.resolution_method == "exact"

    entity_comp = ExtractedEntity(label="Component", name="DDR5 DRAM 16GB", properties={})
    res_comp = resolve_entity(entity_comp, component_registry=comp_reg)
    assert res_comp.target_id == "CMP-0001"
    assert res_comp.resolution_method == "fuzzy"

    entity_unknown = ExtractedEntity(label="Supplier", name="Unknown Vendor Corp", properties={})
    res_unknown = resolve_entity(entity_unknown, supplier_registry=supp_reg)
    assert res_unknown.resolution_method == "new"
    assert res_unknown.target_id.startswith("ext_supplier_")
