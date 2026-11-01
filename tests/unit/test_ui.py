"""Unit tests for Streamlit UI helpers and graph visualization rendering."""

from ui.graph_renderer import COLOR_PALETTE, generate_subgraph_html


def test_color_palette_labels() -> None:
    """Verify color palette includes all core schema node labels."""
    expected_labels = [
        "Supplier",
        "Port",
        "Component",
        "Product",
        "Country",
        "Event",
        "Article",
        "Customer",
        "Facility",
    ]
    for lbl in expected_labels:
        assert lbl in COLOR_PALETTE
        assert COLOR_PALETTE[lbl].startswith("#")


def test_generate_subgraph_html_contains_vis_network() -> None:
    """Verify generate_subgraph_html produces complete HTML with dataset and container."""
    nodes = [
        {
            "id": "sup_001",
            "label": "Supplier",
            "name": "Apex Microelectronics",
            "properties": {"tier": 1, "country": "Taiwan"},
        },
        {
            "id": "port_SHA",
            "label": "Port",
            "name": "Port of Shanghai",
            "properties": {"locode": "CNSHA"},
        },
    ]
    edges = [
        {
            "id": "sup_001-SHIPS_VIA->port_SHA",
            "source": "sup_001",
            "target": "port_SHA",
            "type": "SHIPS_VIA",
            "properties": {},
        }
    ]

    html = generate_subgraph_html(nodes, edges, height=450)
    assert "<!DOCTYPE html>" in html
    assert "vis-network" in html
    assert 'id="network"' in html
    assert "Apex Microelectronics" in html
    assert "Port of Shanghai" in html
    assert "SHIPS_VIA" in html
    assert COLOR_PALETTE["Supplier"] in html
    assert COLOR_PALETTE["Port"] in html


def test_generate_subgraph_html_empty() -> None:
    """Verify generate_subgraph_html gracefully handles empty nodes and edges."""
    html = generate_subgraph_html([], [])
    assert '<div id="network"></div>' in html
    assert "vis.DataSet([])" in html
