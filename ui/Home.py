"""ChainSight Streamlit multipage app — Home landing page."""

import os
import sys
from pathlib import Path

import httpx
import streamlit as st

# Ensure project root is in sys.path
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="ChainSight | Supply Chain Risk Copilot",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4A90D9 0%, #27AE60 60%, #8E44AD 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        line-height: 1.1;
    }
    .hero-sub {
        font-size: 1.25rem;
        color: #8B949E;
        margin-bottom: 2.5rem;
        font-weight: 300;
    }
    .feature-card {
        background: linear-gradient(135deg, #161B22 0%, #0D1117 100%);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px 22px;
        margin-bottom: 14px;
        transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: #4A90D9; }
    .feature-icon { font-size: 2rem; margin-bottom: 8px; }
    .feature-title { font-size: 1.05rem; font-weight: 700; color: #E6EDF3; margin-bottom: 5px; }
    .feature-desc { font-size: 0.88rem; color: #8B949E; line-height: 1.5; }
    .tech-badge {
        display: inline-block;
        background-color: #21262D;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.82rem;
        color: #79C0FF;
        margin: 3px;
        font-weight: 500;
    }
    .stat-number {
        font-size: 2.4rem;
        font-weight: 800;
        color: #58A6FF;
    }
    .stat-label {
        font-size: 0.78rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def check_health() -> dict:
    """Check backend health status."""
    try:
        resp = httpx.get(f"{API_BASE_URL}/health", timeout=3.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "offline", "neo4j": "offline", "llm": "unknown"}


def get_kpis() -> dict:
    """Fetch KPI metrics from backend."""
    try:
        resp = httpx.get(f"{API_BASE_URL}/metrics/kpis", timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/supply-chain.png",
        width=60,
    )
    st.markdown("## ChainSight 🔗")
    st.markdown("*Graph RAG Supply Chain Risk Copilot*")
    st.markdown("---")

    health = check_health()
    status = health.get("status", "offline")
    neo4j = health.get("neo4j", "offline")
    llm = health.get("llm", "unknown")

    if status == "ok":
        st.success("🟢 All systems operational")
    elif status == "degraded":
        st.warning("🟡 Degraded — Neo4j issue")
    else:
        st.error("🔴 Backend offline")
        st.caption("Start: `uvicorn api.main:app --reload`")

    st.markdown(f"**Neo4j:** `{neo4j}`")
    st.markdown(f"**LLM:** `{llm}`")
    st.markdown("---")
    st.caption("Navigate using the pages above ↑")


# ── Hero Section ─────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hero-title'>ChainSight 🔗</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='hero-sub'>Graph RAG Supply Chain Risk Copilot — Multi-hop Disruption Intelligence</div>",
    unsafe_allow_html=True,
)

# ── Live KPI Stats ────────────────────────────────────────────────────────────
kpis = get_kpis()
if kpis:
    k1, k2, k3, k4 = st.columns(4)
    total_rev = kpis.get("total_revenue_at_risk", 0)
    with k1:
        st.markdown(
            f"<div class='stat-number'>${total_rev / 1e6:.1f}M</div>"
            f"<div class='stat-label'>Total Revenue at Risk</div>",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"<div class='stat-number'>{kpis.get('sole_sourced_components', 0)}</div>"
            f"<div class='stat-label'>Sole-Sourced Components</div>",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"<div class='stat-number'>{kpis.get('high_risk_suppliers', 0)}</div>"
            f"<div class='stat-label'>High-Risk Suppliers</div>",
            unsafe_allow_html=True,
        )
    with k4:
        counts = kpis.get("node_counts", {})
        total_nodes = sum(counts.values())
        st.markdown(
            f"<div class='stat-number'>{total_nodes:,}</div>"
            f"<div class='stat-label'>Knowledge Graph Nodes</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

# ── Feature Cards ─────────────────────────────────────────────────────────────
st.markdown("### 🚀 Navigate the Copilot")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class='feature-card'>
            <div class='feature-icon'>💬</div>
            <div class='feature-title'>Risk Copilot</div>
            <div class='feature-desc'>Ask multi-hop supply chain questions. Get grounded answers with subgraph visualization and source citations.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_💬_Copilot.py", label="Open Copilot →", use_container_width=True)

with col2:
    st.markdown(
        """
        <div class='feature-card'>
            <div class='feature-icon'>📊</div>
            <div class='feature-title'>Analytics Dashboard</div>
            <div class='feature-desc'>KPI metrics, revenue exposure charts, geographic concentration maps, and supply chain risk heatmaps.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_📊_Analytics.py", label="Open Analytics →", use_container_width=True)

with col3:
    st.markdown(
        """
        <div class='feature-card'>
            <div class='feature-icon'>🗺️</div>
            <div class='feature-title'>Graph Explorer</div>
            <div class='feature-desc'>Browse the full Neo4j knowledge graph. Explore suppliers, ports, components, and products interactively.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_🗺️_Graph_Explorer.py", label="Open Explorer →", use_container_width=True)

with col4:
    st.markdown(
        """
        <div class='feature-card'>
            <div class='feature-icon'>🧪</div>
            <div class='feature-title'>Evaluation Benchmark</div>
            <div class='feature-desc'>Graph RAG vs. vector-only baseline comparison. 30-question benchmark with correctness, citation, and hallucination metrics.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_🧪_Evaluation.py", label="Open Evaluation →", use_container_width=True)

st.markdown("---")

# ── Architecture Overview ─────────────────────────────────────────────────────
st.markdown("### 🏗️ System Architecture")
st.markdown(
    """
    ChainSight uses a **3-strategy Graph RAG retrieval layer** to answer supply chain risk questions
    with citations and a live reasoning subgraph:

    | Strategy | When Used | How |
    |---|---|---|
    | **Graph Traversal** | Disruption impact questions | Template Cypher: Port → Supplier → Component → Product |
    | **Text-to-Cypher** | Named entity lookups | LLM generates safe read-only Cypher |
    | **Vector + Graph Expand** | Open-ended semantic questions | Embed query → top-5 articles → 1-hop graph expansion |

    > **LLM Provider:** HuggingFace Inference API (primary) → Gemini (fallback) → Deterministic synthesis
    """
)

# ── Tech Stack ────────────────────────────────────────────────────────────────
st.markdown("### 🛠️ Tech Stack")
tech_html = "".join(
    f"<span class='tech-badge'>{t}</span>"
    for t in [
        "Python 3.11",
        "FastAPI",
        "Streamlit",
        "Neo4j 5.x",
        "HuggingFace Inference API",
        "sentence-transformers",
        "Pydantic v2",
        "Docker Compose",
        "vis-network",
        "tiktoken",
    ]
)
st.markdown(tech_html, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "ChainSight v2.0 · Graph RAG Supply Chain Risk Copilot · "
    "[GitHub](https://github.com) · Built with ❤️ for the AI engineering portfolio"
)
