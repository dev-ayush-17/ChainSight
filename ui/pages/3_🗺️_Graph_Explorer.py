"""ChainSight — Interactive Graph Explorer for browsing the knowledge graph."""

import os
import sys
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

_ROOT_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

try:
    from ui.graph_renderer import COLOR_PALETTE, generate_subgraph_html
except ImportError:
    from graph_renderer import COLOR_PALETTE, generate_subgraph_html  # type: ignore[no-redef]

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="ChainSight | Graph Explorer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .explorer-header {
        font-size: 1.9rem; font-weight: 800;
        background: linear-gradient(90deg, #E67E22 0%, #8E44AD 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .node-chip {
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600; color: white; margin: 2px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=120)
def fetch_entity_list(entity_type: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch a list of entities of a given type from the graph via the chat endpoint."""
    query_map = {
        "Supplier": "list all suppliers with their country and reliability score",
        "Port": "show details for all ports in the graph",
        "Component": "list all components with their category",
        "Product": "list all products with their annual revenue",
        "Customer": "list all customers and their segments",
        "Country": "list all countries with their risk index",
    }
    query = query_map.get(entity_type, f"list all {entity_type} entities")
    try:
        resp = httpx.post(f"{API_BASE_URL}/chat", json={"question": query}, timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("subgraph_node_ids", [])
    except Exception:
        pass
    return []


def fetch_subgraph(node_ids: list[str]) -> dict[str, Any]:
    """Fetch subgraph data for a list of node IDs."""
    if not node_ids:
        return {"nodes": [], "edges": []}
    try:
        joined = ",".join(node_ids[:40])
        resp = httpx.get(f"{API_BASE_URL}/graph", params={"node_ids": joined}, timeout=10.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"nodes": [], "edges": []}


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗺️ Graph Explorer Controls")

    entity_type = st.selectbox(
        "Browse entity type:",
        ["Supplier", "Port", "Component", "Product", "Customer", "Country"],
        key="explorer_entity_type",
    )

    st.markdown("### 🔎 Manual Node Search")
    manual_ids = st.text_area(
        "Enter node IDs (comma-separated):",
        placeholder="SUP-001, port-SHA, CMP-0001",
        height=80,
        key="manual_node_ids",
    )

    st.markdown("---")
    st.markdown("### 🎨 Legend")
    for lbl, color in COLOR_PALETTE.items():
        if lbl != "Entity":
            st.markdown(
                f"<span style='display:inline-block;background:{color};width:12px;height:12px;"
                f"border-radius:2px;margin-right:5px;'></span><small>{lbl}</small>",
                unsafe_allow_html=True,
            )


# ── Main Content ────────────────────────────────────────────────────────────────
st.markdown("<div class='explorer-header'>🗺️ Graph Explorer</div>", unsafe_allow_html=True)
st.caption(
    "Browse the ChainSight Neo4j knowledge graph. Search by entity type or enter node IDs directly."
)

# Predefined entity presets
PRESET_QUERIES = {
    "🌊 Port Disruption Path (Shanghai)": [
        "port-SHA",
        "port-CNSHA",
        "CNSHA",
    ],
    "🏭 Taiwan Supplier Cluster": ["TW"],
    "📦 Full Supply Chain (Random Product)": ["PRD-001", "PRD-002", "PRD-003"],
    "🔴 High-Risk Sole-Sourced Components": [],
    "🔗 Alternative Supplier Network": [],
}

st.markdown("### ⚡ Quick Presets")
preset_cols = st.columns(len(PRESET_QUERIES))
for col, (preset_name, preset_ids) in zip(preset_cols, PRESET_QUERIES.items(), strict=False):
    with col:
        if st.button(preset_name, use_container_width=True, key=f"preset_{preset_name}"):
            if preset_ids:
                st.session_state["explorer_node_ids"] = preset_ids
            else:
                # Run a chat query for complex presets
                with st.spinner("Loading preset..."):
                    if "Sole-Sourced" in preset_name:
                        ids = fetch_entity_list("Component")
                        st.session_state["explorer_node_ids"] = ids[:20]
                    elif "Alternative" in preset_name:
                        ids = fetch_entity_list("Supplier")
                        st.session_state["explorer_node_ids"] = ids[:20]

st.markdown("---")

# Determine which node IDs to visualize
active_ids: list[str] = []

if manual_ids and manual_ids.strip():
    active_ids = [nid.strip() for nid in manual_ids.split(",") if nid.strip()]
elif "explorer_node_ids" in st.session_state:
    active_ids = st.session_state.get("explorer_node_ids", [])
else:
    # Default: show a selection of ports
    active_ids = ["port-SHA", "port-RTM", "port-SIN", "port-LAX", "port-BSN"]

if active_ids:
    with st.spinner(f"Fetching graph for {len(active_ids)} nodes..."):
        subgraph = fetch_subgraph(active_ids)

    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    if nodes:
        col_graph, col_info = st.columns([3, 2])

        with col_graph:
            st.markdown(f"#### Knowledge Graph ({len(nodes)} nodes, {len(edges)} edges)")
            graph_html = generate_subgraph_html(nodes, edges, height=520)
            st.components.v1.html(graph_html, height=540, scrolling=False)

        with col_info:
            st.markdown("#### 📋 Entity Details")

            # Group nodes by label
            by_label: dict[str, list[dict]] = {}
            for node in nodes:
                lbl = node.get("label", "Entity")
                by_label.setdefault(lbl, []).append(node)

            for label, label_nodes in sorted(by_label.items()):
                color = COLOR_PALETTE.get(label, "#34495E")
                with st.expander(
                    f"**{label}** ({len(label_nodes)} nodes)", expanded=len(label_nodes) <= 5
                ):
                    for node in label_nodes[:15]:
                        name = node.get("name", node.get("id", ""))
                        node_id = node.get("id", "")
                        props = node.get("properties", {})

                        st.markdown(
                            f"<span style='background:{color};color:white;padding:2px 8px;"
                            f"border-radius:8px;font-size:0.8rem;'>{label}</span> "
                            f"**{name}** `{node_id}`",
                            unsafe_allow_html=True,
                        )

                        # Show key properties
                        key_props = {
                            k: v
                            for k, v in props.items()
                            if k not in ["embedding", "description_embedding", "text"]
                            and not isinstance(v, list)
                        }
                        if key_props:
                            prop_str = " | ".join(
                                f"`{k}`: {v}" for k, v in list(key_props.items())[:4]
                            )
                            st.caption(prop_str)
                        st.markdown("---")

                    if len(label_nodes) > 15:
                        st.caption(f"...and {len(label_nodes) - 15} more")
    else:
        st.warning(
            f"No graph nodes found for IDs: `{', '.join(active_ids[:5])}`\n\n"
            "This may mean:\n"
            "- The database is not seeded yet (run `python -m scripts.seed_database`)\n"
            "- The node IDs don't exist in the graph\n"
            "- Neo4j is not connected"
        )
else:
    st.info("Select a preset or enter node IDs in the sidebar to explore the graph.")

# ── Schema Reference ───────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📐 Graph Schema Reference"):
    st.markdown(
        """
        ### Node Labels & Key Properties

        | Label | Key Properties |
        |---|---|
        | **Supplier** | `id`, `name`, `country_code`, `tier`, `reliability_score`, `lead_time_days` |
        | **Component** | `id`, `name`, `category`, `is_sole_sourced`, `unit_cost_usd` |
        | **Product** | `id`, `name`, `sku`, `revenue_usd_annual`, `margin_pct` |
        | **Port** | `id`, `name`, `un_locode`, `country_code`, `throughput_teu_annual` |
        | **Country** | `code`, `name`, `region`, `risk_index` |
        | **Facility** | `id`, `name`, `type`, `capacity_units` |
        | **Customer** | `id`, `name`, `country_code`, `segment` |
        | **Event** | `id`, `type`, `description`, `severity`, `start_date` |
        | **Article** | `id`, `title`, `source`, `published_date`, `text` |

        ### Relationship Types

        | Relationship | Direction | Meaning |
        |---|---|---|
        | `SHIPS_VIA` | Supplier → Port | Supplier uses this port |
        | `PRODUCES` | Supplier → Component | Supplier manufactures component |
        | `PART_OF` | Component → Product | Component is in product BOM |
        | `LOCATED_IN` | Supplier/Port → Country | Geographic location |
        | `ALTERNATIVE_FOR` | Supplier ↔ Supplier | Can substitute for same component |
        | `AFFECTS` | Event → Port/Supplier | Disruption event impacts entity |
        | `MENTIONS` | Article → Entity | News article mentions entity |
        | `OPERATES` | Supplier → Facility | Supplier runs this facility |
        """
    )
