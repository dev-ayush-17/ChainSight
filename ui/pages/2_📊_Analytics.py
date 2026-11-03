"""ChainSight — Analytics Dashboard with KPI metrics and supply chain risk charts."""

import os
import sys
from pathlib import Path

import httpx
import streamlit as st

_ROOT_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="ChainSight | Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #161B22, #0D1117);
        border: 1px solid #30363D; border-radius: 12px;
        padding: 18px 20px; text-align: center;
    }
    .kpi-value { font-size: 2.3rem; font-weight: 800; }
    .kpi-label { font-size: 0.8rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.07em; margin-top: 4px; }
    .section-header { font-size: 1.2rem; font-weight: 700; color: #E6EDF3; margin: 1.5rem 0 0.8rem 0; }
    .risk-critical { color: #E74C3C; font-weight: 700; }
    .risk-high     { color: #E67E22; font-weight: 700; }
    .risk-medium   { color: #F39C12; font-weight: 600; }
    .risk-low      { color: #27AE60; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def fetch_kpis() -> dict:
    """Fetch KPI data from backend with caching."""
    try:
        resp = httpx.get(f"{API_BASE_URL}/metrics/kpis", timeout=8.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


@st.cache_data(ttl=60)
def fetch_supplier_data() -> list[dict]:
    """Fetch supplier data for risk analysis."""
    try:
        with httpx.Client(timeout=8.0) as client:
            # Use the graph endpoint to get all suppliers
            resp = client.get(
                f"{API_BASE_URL}/graph",
                params={"node_ids": "ALL_SUPPLIERS"},
            )
    except Exception:
        pass

    # Fallback: use a targeted Cypher via the chat endpoint
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/chat",
            json={"question": "list all suppliers with their country and reliability score"},
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json().get("citations", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=60)
def fetch_country_risk_data() -> list[dict]:
    """Fetch country concentration risk analysis."""
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/chat",
            json={
                "question": "Analyze country concentration risk and total revenue at risk for Taiwan"
            },
            timeout=20.0,
        )
        if resp.status_code == 200:
            return resp.json().get("subgraph_node_ids", [])
    except Exception:
        pass
    return []


with st.sidebar:
    st.markdown("### ⚙️ Analytics Controls")
    auto_refresh = st.checkbox("Auto-refresh KPIs (30s)", value=False)
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("KPIs are computed live from the Neo4j knowledge graph.")


st.markdown("## 📊 Supply Chain Risk Analytics Dashboard")
st.caption("Real-time metrics derived from the ChainSight knowledge graph")

kpis = fetch_kpis()

if not kpis:
    st.warning(
        "⚠️ Could not connect to the backend API. "
        "Please ensure the FastAPI server is running: `uvicorn api.main:app --reload`"
    )
    st.stop()

# ── KPI Row ────────────────────────────────────────────────────────────────────
st.markdown("### 🎯 Key Risk Indicators")
c1, c2, c3, c4, c5 = st.columns(5)

total_rev = kpis.get("total_revenue_at_risk", 0)
sole = kpis.get("sole_sourced_components", 0)
high_risk_sup = kpis.get("high_risk_suppliers", 0)
active_events = kpis.get("active_disruption_events", 0)
avg_rel = kpis.get("avg_supplier_reliability", 0.0)

with c1:
    st.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:#58A6FF;'>${total_rev / 1e6:.1f}M</div>"
        f"<div class='kpi-label'>Total Revenue at Risk</div></div>",
        unsafe_allow_html=True,
    )

with c2:
    color = "#E74C3C" if sole > 10 else "#E67E22" if sole > 5 else "#27AE60"
    st.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:{color};'>{sole}</div>"
        f"<div class='kpi-label'>Sole-Sourced Components</div></div>",
        unsafe_allow_html=True,
    )

with c3:
    color = "#E74C3C" if high_risk_sup > 15 else "#E67E22" if high_risk_sup > 8 else "#27AE60"
    st.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:{color};'>{high_risk_sup}</div>"
        f"<div class='kpi-label'>High-Risk Suppliers</div></div>",
        unsafe_allow_html=True,
    )

with c4:
    color = "#E74C3C" if active_events > 3 else "#E67E22" if active_events > 0 else "#27AE60"
    st.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:{color};'>{active_events}</div>"
        f"<div class='kpi-label'>Active Disruption Events</div></div>",
        unsafe_allow_html=True,
    )

with c5:
    color = "#27AE60" if avg_rel > 0.8 else "#E67E22" if avg_rel > 0.6 else "#E74C3C"
    st.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-value' style='color:{color};'>{avg_rel:.2f}</div>"
        f"<div class='kpi-label'>Avg Supplier Reliability</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Node Count Chart ──────────────────────────────────────────────────────────
node_counts = kpis.get("node_counts", {})
if node_counts:
    st.markdown("### 🗂️ Knowledge Graph Node Distribution")
    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        try:
            import altair as alt
            import pandas as pd

            df = pd.DataFrame(
                [
                    {"Entity Type": k, "Count": v}
                    for k, v in sorted(node_counts.items(), key=lambda x: -x[1])
                ]
            )
            COLOR_MAP = {
                "Supplier": "#4A90D9",
                "Port": "#E67E22",
                "Component": "#27AE60",
                "Product": "#8E44AD",
                "Country": "#C0392B",
                "Event": "#E74C3C",
                "Article": "#95A5A6",
                "Customer": "#F39C12",
                "Facility": "#16A085",
            }
            df["Color"] = df["Entity Type"].map(lambda x: COLOR_MAP.get(x, "#34495E"))

            chart = (
                alt.Chart(df)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Entity Type:N", sort="-y", axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("Count:Q"),
                    color=alt.Color(
                        "Entity Type:N",
                        scale=alt.Scale(
                            domain=list(COLOR_MAP.keys()),
                            range=list(COLOR_MAP.values()),
                        ),
                        legend=None,
                    ),
                    tooltip=["Entity Type", "Count"],
                )
                .properties(height=280)
                .configure_view(strokeWidth=0)
                .configure_axis(grid=False, labelColor="#8B949E", titleColor="#8B949E")
            )
            st.altair_chart(chart, use_container_width=True)
        except ImportError:
            # Fallback bar chart with st.bar_chart
            import pandas as pd

            df = pd.DataFrame(node_counts, index=["Count"]).T
            st.bar_chart(df)

    with col_table:
        st.markdown("**Node Counts**")
        for entity, count in sorted(node_counts.items(), key=lambda x: -x[1]):
            st.markdown(f"- **{entity}:** {count:,}")

# ── Risk Matrices ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### ⚠️ Supply Chain Risk Overview")

risk_col1, risk_col2 = st.columns(2)

with risk_col1:
    st.markdown("#### 🌏 Geographic Concentration Risk")
    # Static risk table based on known synthetic data distributions
    risk_data = [
        ("China (CN)", "East Asia", 0.68, "Critical"),
        ("Philippines (PH)", "Southeast Asia", 0.65, "Critical"),
        ("Taiwan (TW)", "East Asia", 0.64, "Critical"),
        ("Malaysia (MY)", "Southeast Asia", 0.63, "High"),
        ("Vietnam (VN)", "Southeast Asia", 0.62, "High"),
        ("Mexico (MX)", "North America", 0.62, "High"),
        ("India (IN)", "South Asia", 0.61, "High"),
        ("Indonesia (ID)", "Southeast Asia", 0.61, "High"),
        ("Israel (IL)", "Middle East", 0.58, "Medium"),
        ("Thailand (TH)", "Southeast Asia", 0.48, "Medium"),
    ]

    for country, _region, risk, level in risk_data:
        level_class = f"risk-{level.lower()}"
        bar_width = int(risk * 100)
        st.markdown(
            f"<div style='margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;'>"
            f"<span style='font-size:0.85rem;'>{country}</span>"
            f"<span class='{level_class}' style='font-size:0.82rem;'>{level} ({risk:.2f})</span>"
            f"</div>"
            f"<div style='background:#21262D;border-radius:4px;height:5px;margin-top:3px;'>"
            f"<div style='background:{'#E74C3C' if risk > 0.62 else '#E67E22' if risk > 0.55 else '#F39C12'};"
            f"width:{bar_width}%;height:100%;border-radius:4px;'></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

with risk_col2:
    st.markdown("#### 📦 Component Risk Classification")
    st.markdown(
        """
        | Risk Level | Criteria | Action Required |
        |---|---|---|
        | 🔴 **Critical** | Sole-sourced + high-risk country | Immediate second-source qualification |
        | 🟠 **High** | Sole-sourced OR high-risk country | 30-day safety stock buffer |
        | 🟡 **Medium** | Single port dependency | Alternate port routing plan |
        | 🟢 **Low** | Multiple suppliers, stable geography | Standard monitoring |
        """
    )

    st.markdown("#### 🔄 Retrieval Strategy Distribution")
    st.markdown(
        """
        The ChainSight copilot automatically routes your questions to the optimal strategy:

        - **🕸️ Graph Traversal** — Multi-hop impact analysis (Port → Supplier → Product)
        - **🔍 Lookup** — Precise entity attribute retrieval via Cypher
        - **🔎 Semantic Search** — Open-ended questions via vector similarity
        - **⛔ Refused** — Out-of-scope queries gracefully declined
        """
    )

# ── Demo Scenarios ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 High-Impact Disruption Scenarios")
st.markdown("Pre-configured scenarios that demonstrate ChainSight's multi-hop reasoning:")

scenarios = [
    {
        "title": "🌊 Shanghai Port Congestion",
        "desc": "14-day vessel delay at Port of Shanghai cascading through 12 Tier-1 suppliers",
        "impact": "Critical",
        "query": "Port of Shanghai is disrupted: which products are exposed and what is the revenue risk?",
    },
    {
        "title": "🏭 Taiwan Semiconductor Disruption",
        "desc": "Seismic event disrupting Taiwan fab capacity affecting semiconductor supply",
        "impact": "Critical",
        "query": "Analyze country concentration risk and total revenue at risk in Taiwan",
    },
    {
        "title": "🚢 Red Sea Maritime Rerouting",
        "desc": "Vessels rerouted around Cape of Good Hope adding 14 transit days",
        "impact": "High",
        "query": "What recent shipping disruptions and container delays have occurred in Asia?",
    },
]

s_cols = st.columns(len(scenarios))
for col, scenario in zip(s_cols, scenarios, strict=False):
    with col:
        impact_color = "#E74C3C" if scenario["impact"] == "Critical" else "#E67E22"
        st.markdown(
            f"<div style='background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;'>"
            f"<div style='font-weight:700;margin-bottom:6px;'>{scenario['title']}</div>"
            f"<div style='font-size:0.82rem;color:#8B949E;margin-bottom:10px;'>{scenario['desc']}</div>"
            f"<span style='background:{impact_color};color:white;padding:2px 8px;border-radius:8px;"
            f"font-size:0.78rem;font-weight:600;'>{scenario['impact']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "▶ Run Scenario", key=f"scenario_{scenario['title']}", use_container_width=True
        ):
            st.session_state["pre_query"] = scenario["query"]
            st.switch_page("pages/1_💬_Copilot.py")
