"""Streamlit web application for ChainSight Graph RAG Supply Chain Risk Copilot."""

import os
import sys
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

# Ensure project root is present in sys.path for top-level module resolution
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

try:
    from ui.graph_renderer import COLOR_PALETTE, generate_subgraph_html
except ImportError:
    from graph_renderer import COLOR_PALETTE, generate_subgraph_html  # type: ignore[no-redef]

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page Configuration
st.set_page_config(
    page_title="ChainSight | Supply Chain Risk Copilot",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Tech Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4A90D9 0%, #27AE60 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #8B949E;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .badge-traversal {
        background-color: #8E44AD;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-lookup {
        background-color: #2980B9;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-semantic {
        background-color: #D35400;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-refused {
        background-color: #7F8C8D;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
    }
    .confidence-pill {
        background-color: #1F2937;
        border: 1px solid #374151;
        color: #E5E7EB;
        padding: 2px 7px;
        border-radius: 8px;
        font-size: 0.75rem;
        margin-left: 6px;
    }
    .source-card {
        background-color: #161B22;
        border-left: 3px solid #4A90D9;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 6px;
        margin-bottom: 6px;
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    """Initialize session state variables for chat history and graph state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_subgraph" not in st.session_state:
        st.session_state.current_subgraph = {"nodes": [], "edges": []}
    if "active_node_ids" not in st.session_state:
        st.session_state.active_node_ids = []
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


init_session_state()


def call_chat_api(question: str) -> dict[str, Any] | None:
    """Submit natural language question to ChainSight FastAPI /chat endpoint."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{API_BASE_URL}/chat", json={"question": question})
            if resp.status_code == 200:
                return resp.json()
            st.error(f"API Error ({resp.status_code}): {resp.text}")
            return None
    except Exception as err:
        st.error(f"Connection to backend failed ({API_BASE_URL}): {err}")
        return None


def call_graph_api(node_ids: list[str]) -> dict[str, Any]:
    """Fetch nodes and edges for subgraph visualization from /graph endpoint."""
    if not node_ids:
        return {"nodes": [], "edges": []}
    try:
        joined = ",".join(node_ids)
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


# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ System Status")
    health = check_health_api()
    if health.get("status") == "ok":
        st.success("🟢 API: Online | Neo4j: Connected")
    elif health.get("status") == "degraded":
        st.warning(f"🟡 API: Online | Neo4j: {health.get('neo4j')}")
    else:
        st.error("🔴 API: Offline (Run: uvicorn api.main:app)")

    st.markdown("---")
    st.markdown("### 💡 Example Scenarios")
    st.caption("Click any scenario to populate and run:")

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
        ("⛔ Guardrail Refusal Check", "What is the CEO's annual salary and bonus package?"),
    ]

    for label, query_text in examples:
        if st.button(label, use_container_width=True):
            st.session_state.pending_query = query_text
            st.rerun()

    st.markdown("---")
    st.markdown("### 🎨 Graph Legend")
    legend_html = "".join(
        f"<span style='display:inline-block;margin:3px 6px;'><span style='background-color:{c};"
        f"width:12px;height:12px;display:inline-block;border-radius:2px;margin-right:4px;'></span>"
        f"<small>{lbl}</small></span>"
        for lbl, c in COLOR_PALETTE.items()
        if lbl != "Entity"
    )
    st.markdown(legend_html, unsafe_allow_html=True)


# --- Header ---
st.markdown("<div class='main-title'>ChainSight 🔗</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Graph RAG Supply Chain Risk Copilot — Multi-hop Impact Analysis & Disruption Intelligence</div>",
    unsafe_allow_html=True,
)

# Layout: 60% Chat Pane / 40% Subgraph Pane
col_chat, col_graph = st.columns([6, 4], gap="medium")


# --- LEFT COLUMN: Chat Pane ---
with col_chat:
    st.markdown("#### 💬 Supply Chain Risk Copilot")

    # Message History Container
    chat_container = st.container(height=520)
    with chat_container:
        if not st.session_state.messages:
            st.info(
                "👋 Welcome to ChainSight! Ask questions about port disruptions, supplier vulnerabilities, "
                "or click an example scenario in the sidebar to begin."
            )

        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                with st.chat_message("user"):
                    st.markdown(content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(content)

                    # Retrieval strategy and metrics badge bar
                    strategy = msg.get("strategy", "lookup")
                    badge_cls = {
                        "impact_traversal": "badge-traversal",
                        "lookup": "badge-lookup",
                        "semantic": "badge-semantic",
                        "refused": "badge-refused",
                    }.get(strategy, "badge-lookup")

                    badge_label = {
                        "impact_traversal": "Graph Traversal",
                        "lookup": "Lookup",
                        "semantic": "Semantic Search",
                        "refused": "Refused",
                    }.get(strategy, strategy.title())

                    conf = msg.get("confidence", "medium").upper()
                    latency = msg.get("latency_ms", 0)

                    badge_html = (
                        f"<div style='margin-top:8px;'>"
                        f"<span class='{badge_cls}'>{badge_label}</span>"
                        f"<span class='confidence-pill'>Confidence: {conf}</span>"
                        f"<span class='confidence-pill'>⏱️ {latency}ms</span>"
                        f"</div>"
                    )
                    st.markdown(badge_html, unsafe_allow_html=True)

                    # Citations Accordion
                    citations = msg.get("citations", [])
                    if citations:
                        with st.expander(f"📚 Verified Sources & Intelligence ({len(citations)})"):
                            for cite in citations:
                                title = cite.get("title", "Untitled Source")
                                src = cite.get("source", "Unknown")
                                dt = cite.get("date", "")
                                url = cite.get("url", "#")
                                st.markdown(
                                    f"""
                                    <div class='source-card'>
                                        <b>[{cite.get("source_id")}]</b> <a href='{url}' target='_blank' style='color:#58A6FF;text-decoration:none;'><b>{title}</b></a><br>
                                        <small style='color:#8B949E;'>Source: {src} | Published: {dt}</small>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

    # User Input Handling
    user_query = st.chat_input("Ask about supplier exposure, port strikes, BOM risks...")

    # Check if a pending example query was triggered from the sidebar
    if st.session_state.pending_query:
        user_query = st.session_state.pending_query
        st.session_state.pending_query = None

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})

        with st.spinner("Analyzing graph topologies and disruption intelligence..."):
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

            # Update Subgraph in Session State
            if node_ids:
                st.session_state.active_node_ids = node_ids
                subgraph_data = call_graph_api(node_ids)
                st.session_state.current_subgraph = subgraph_data

            st.rerun()


# --- RIGHT COLUMN: Subgraph Pane ---
with col_graph:
    st.markdown("#### 🕸️ Reasoning Subgraph")

    current_subgraph = st.session_state.current_subgraph
    nodes = current_subgraph.get("nodes", [])
    edges = current_subgraph.get("edges", [])

    if nodes:
        st.caption(f"Visualizing {len(nodes)} active nodes and {len(edges)} connecting edges:")
        graph_html = generate_subgraph_html(nodes, edges, height=440)
        st.components.v1.html(graph_html, height=460)

        # Node Inspector Table
        with st.expander("🔎 Node Inspector"):
            node_names = [f"[{n.get('label')}] {n.get('name', n.get('id'))}" for n in nodes]
            selected_idx = st.selectbox(
                "Select node to inspect properties:",
                range(len(node_names)),
                format_func=lambda x: node_names[x],
            )
            if selected_idx is not None and selected_idx < len(nodes):
                selected = nodes[selected_idx]
                st.write(f"**ID:** `{selected.get('id')}` | **Label:** `{selected.get('label')}`")
                props = selected.get("properties", {})
                if props:
                    st.json(props)
                else:
                    st.write("No additional properties available.")
    else:
        st.info(
            "🕸️ **No active subgraph to display.**\n\n"
            "Ask a question or select an example query to visualize the multi-hop dependency path."
        )
