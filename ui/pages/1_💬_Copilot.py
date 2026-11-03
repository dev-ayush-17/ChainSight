"""ChainSight — Risk Copilot chat page with subgraph visualization."""

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
    page_title="ChainSight | Risk Copilot",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.0rem; font-weight: 800;
        background: linear-gradient(90deg, #4A90D9 0%, #27AE60 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.15rem;
    }
    .sub-title { color: #8B949E; font-size: 0.97rem; margin-bottom: 1rem; }
    .badge { padding: 3px 9px; border-radius: 12px; font-size: 0.78rem;
             font-weight: 600; display: inline-block; color: white; }
    .badge-traversal { background-color: #8E44AD; }
    .badge-lookup    { background-color: #2980B9; }
    .badge-semantic  { background-color: #D35400; }
    .badge-refused   { background-color: #7F8C8D; }
    .confidence-pill {
        background-color: #1F2937; border: 1px solid #374151;
        color: #E5E7EB; padding: 2px 7px; border-radius: 8px;
        font-size: 0.75rem; margin-left: 6px;
    }
    .source-card {
        background-color: #161B22; border-left: 3px solid #4A90D9;
        border-radius: 4px; padding: 8px 12px;
        margin: 5px 0; font-size: 0.87rem;
    }
    .graph-legend-dot {
        display: inline-block; width: 11px; height: 11px;
        border-radius: 50%; margin-right: 5px; vertical-align: middle;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session State ─────────────────────────────────────────────────────────────
def init_session_state() -> None:
    """Initialize session state variables for chat history and graph state."""
    defaults: dict[str, Any] = {
        "messages": [],
        "current_subgraph": {"nodes": [], "edges": []},
        "active_node_ids": [],
        "pending_query": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ── API Helpers ───────────────────────────────────────────────────────────────
def call_chat_api(question: str) -> dict[str, Any] | None:
    """Submit natural language question to ChainSight FastAPI /chat endpoint."""
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{API_BASE_URL}/chat", json={"question": question})
            if resp.status_code == 200:
                return resp.json()
            st.error(f"API Error ({resp.status_code}): {resp.text[:300]}")
    except httpx.ConnectError:
        st.error(f"⚠️ Cannot connect to backend at `{API_BASE_URL}`. Is the API running?")
    except Exception as err:
        st.error(f"Request failed: {err}")
    return None


def call_graph_api(node_ids: list[str]) -> dict[str, Any]:
    """Fetch nodes and edges for subgraph visualization from /graph endpoint."""
    if not node_ids:
        return {"nodes": [], "edges": []}
    try:
        joined = ",".join(node_ids[:50])  # Cap at 50 nodes for performance
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE_URL}/graph", params={"node_ids": joined})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"nodes": [], "edges": []}


def check_health_api() -> dict[str, str]:
    """Check backend API and database connectivity status."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{API_BASE_URL}/health")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"status": "offline", "neo4j": "offline", "llm": "unknown"}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ System Status")
    health = check_health_api()
    if health.get("status") == "ok":
        st.success("🟢 API Online | Neo4j Connected")
    elif health.get("status") == "degraded":
        st.warning(f"🟡 Degraded — Neo4j: {health.get('neo4j')}")
    else:
        st.error("🔴 API Offline")
        st.caption("Run: `uvicorn api.main:app --reload`")

    llm_label = health.get("llm", "unknown")
    if "huggingface" in llm_label:
        st.info(f"🤗 LLM: {llm_label}")
    elif "gemini" in llm_label:
        st.info(f"✨ LLM: {llm_label}")
    else:
        st.caption("📐 LLM: Deterministic synthesis (set HF_API_KEY for AI answers)")

    st.markdown("---")
    st.markdown("### 💡 Example Scenarios")
    st.caption("Click any scenario to run:")

    examples = [
        (
            "🌊 Port Disruption Impact",
            "Port of Shanghai is disrupted: which products are exposed and what is the revenue risk?",
        ),
        ("🔍 Supplier Factual Lookup", "Which country is supplier SUP-007 located in?"),
        (
            "🔄 Alternative Supplier Finder",
            "Find alternative suppliers for component CMP-0005 due to shortage",
        ),
        (
            "📍 Geographic Concentration",
            "Analyze country concentration risk and total revenue at risk in Taiwan",
        ),
        (
            "📰 Maritime Disruption News",
            "What recent shipping disruptions and container delays have occurred in Asia?",
        ),
        (
            "🚢 Port Exposure Chain",
            "Port of Rotterdam is disrupted — which of our suppliers ship via Rotterdam and which products are impacted?",
        ),
        ("⛔ Guardrail Refusal Check", "What is the CEO's annual salary and bonus package?"),
    ]

    for label, query_text in examples:
        if st.button(label, use_container_width=True, key=f"ex_{label}"):
            st.session_state.pending_query = query_text
            st.rerun()

    st.markdown("---")
    st.markdown("### 🎨 Graph Legend")
    for lbl, color in COLOR_PALETTE.items():
        if lbl != "Entity":
            st.markdown(
                f"<span class='graph-legend-dot' style='background:{color}'></span>"
                f"<small>{lbl}</small>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_subgraph = {"nodes": [], "edges": []}
        st.session_state.active_node_ids = []
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<div class='main-title'>💬 Risk Copilot</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Multi-hop Graph RAG • Supply Chain Disruption Intelligence • "
    "Cited Sources</div>",
    unsafe_allow_html=True,
)

# ── Layout ────────────────────────────────────────────────────────────────────
col_chat, col_graph = st.columns([6, 4], gap="medium")


# ── LEFT: Chat Pane ───────────────────────────────────────────────────────────
with col_chat:
    chat_container = st.container(height=540)
    with chat_container:
        if not st.session_state.messages:
            st.info(
                "👋 **Welcome to ChainSight!**\n\n"
                "Ask questions like:\n"
                "- *Port of Shanghai is disrupted — which products are at risk?*\n"
                "- *Who supplies component CMP-0012?*\n"
                "- *What recent news affects Asian shipping lanes?*\n\n"
                "Or click an example in the sidebar."
            )

        for msg in st.session_state.messages:
            role = msg["role"]
            if role == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

                    # Strategy badge + confidence + latency
                    strategy = msg.get("strategy", "lookup")
                    badge_cls = {
                        "impact_traversal": "badge-traversal",
                        "lookup": "badge-lookup",
                        "semantic": "badge-semantic",
                        "refused": "badge-refused",
                    }.get(strategy, "badge-lookup")
                    badge_label = {
                        "impact_traversal": "🕸️ Graph Traversal",
                        "lookup": "🔍 Lookup",
                        "semantic": "🔎 Semantic Search",
                        "refused": "⛔ Refused",
                    }.get(strategy, strategy.title())

                    conf = msg.get("confidence", "medium").upper()
                    latency = msg.get("latency_ms", 0)
                    conf_color = {
                        "HIGH": "#27AE60",
                        "MEDIUM": "#F39C12",
                        "LOW": "#E74C3C",
                        "NONE": "#7F8C8D",
                    }.get(conf, "#7F8C8D")

                    st.markdown(
                        f"<div style='margin-top:8px;'>"
                        f"<span class='badge {badge_cls}'>{badge_label}</span>"
                        f"<span class='confidence-pill' style='border-color:{conf_color};'>"
                        f"Confidence: <b>{conf}</b></span>"
                        f"<span class='confidence-pill'>⏱ {latency}ms</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    # Citations accordion
                    citations = msg.get("citations", [])
                    if citations:
                        with st.expander(f"📚 Sources & Citations ({len(citations)})"):
                            for cite in citations:
                                title = cite.get("title", "Untitled Source")
                                src = cite.get("source", "Unknown")
                                dt = cite.get("date", "")
                                url = cite.get("url", "#")
                                st.markdown(
                                    f"<div class='source-card'>"
                                    f"<b>[{cite.get('source_id')}]</b> "
                                    f"<a href='{url}' target='_blank' "
                                    f"style='color:#58A6FF;text-decoration:none;'>"
                                    f"<b>{title}</b></a><br>"
                                    f"<small style='color:#8B949E;'>"
                                    f"Source: {src} | Published: {dt}</small>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

    # Input bar
    user_query = st.chat_input("Ask about port disruptions, supplier exposure, BOM risks...")

    if st.session_state.pending_query:
        user_query = st.session_state.pending_query
        st.session_state.pending_query = None

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})

        with st.spinner("🔍 Analyzing graph topology and disruption intelligence..."):
            response_data = call_chat_api(user_query)

        if response_data:
            ans = response_data.get("answer", "")
            strategy = response_data.get("retrieval_strategy", "lookup")
            citations = response_data.get("citations", [])
            conf = response_data.get("confidence", "medium")
            latency = response_data.get("latency_ms", 0)
            node_ids = response_data.get("subgraph_node_ids", [])

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": ans,
                    "strategy": strategy,
                    "citations": citations,
                    "confidence": conf,
                    "latency_ms": latency,
                    "subgraph_node_ids": node_ids,
                }
            )

            if node_ids:
                st.session_state.active_node_ids = node_ids
                subgraph_data = call_graph_api(node_ids)
                st.session_state.current_subgraph = subgraph_data

            st.rerun()


# ── RIGHT: Subgraph Pane ──────────────────────────────────────────────────────
with col_graph:
    st.markdown("#### 🕸️ Reasoning Subgraph")

    current_subgraph = st.session_state.current_subgraph
    nodes = current_subgraph.get("nodes", [])
    edges = current_subgraph.get("edges", [])

    if nodes:
        st.caption(f"**{len(nodes)} nodes** · **{len(edges)} edges** in reasoning path")
        graph_html = generate_subgraph_html(nodes, edges, height=460)
        st.components.v1.html(graph_html, height=480, scrolling=False)

        with st.expander("🔎 Node Inspector", expanded=False):
            node_names = [
                f"[{n.get('label', '?')}] {n.get('name', n.get('id', ''))}" for n in nodes
            ]
            selected_idx = st.selectbox(
                "Select node:",
                range(len(node_names)),
                format_func=lambda x: node_names[x],
                key="node_inspector_select",
            )
            if selected_idx is not None and selected_idx < len(nodes):
                selected = nodes[selected_idx]
                st.markdown(
                    f"**ID:** `{selected.get('id')}` | **Label:** `{selected.get('label')}`"
                )
                props = selected.get("properties", {})
                if props:
                    # Filter out large embedding fields
                    clean_props = {
                        k: v
                        for k, v in props.items()
                        if not isinstance(v, list) or len(str(v)) < 200
                    }
                    st.json(clean_props)
                else:
                    st.caption("No additional properties.")
    else:
        st.markdown(
            """
            <div style='text-align:center; padding:60px 20px; color:#4B5563;'>
                <div style='font-size:3rem;'>🕸️</div>
                <div style='font-size:1rem; margin-top:12px; color:#6B7280;'>
                    Ask a question to visualize<br>the reasoning subgraph
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
