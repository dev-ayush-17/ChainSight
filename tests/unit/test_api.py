"""Unit and integration tests for FastAPI REST endpoints (/health, /schema, /chat, /graph)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_driver
from api.main import app


@pytest.fixture
def mock_driver() -> MagicMock:
    """Provide mock Neo4j driver for FastAPI endpoint testing."""
    driver = MagicMock()
    driver.verify_connectivity.return_value = None
    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock
    session_mock.__exit__.return_value = None
    session_mock.run.return_value = []
    driver.session.return_value = session_mock
    return driver


@pytest.fixture
def client(mock_driver: MagicMock) -> TestClient:
    """Provide FastAPI test client with mocked database driver dependency."""
    app.dependency_overrides[get_driver] = lambda: mock_driver
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_endpoint(client: TestClient) -> None:
    """Test /health endpoint returns expected status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "neo4j" in data
    assert data["neo4j"] == "connected"


def test_schema_endpoint(client: TestClient) -> None:
    """Test /schema endpoint returns labels, relationships, and colors."""
    resp = client.get("/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert "Supplier" in data["node_labels"]
    assert "Port" in data["node_labels"]
    assert "SHIPS_VIA" in data["relationship_types"]
    assert data["label_colors"]["Supplier"] == "#4A90D9"


def test_chat_endpoint_unanswerable(client: TestClient) -> None:
    """Test /chat endpoint handles unanswerable out-of-scope query."""
    resp = client.post("/chat", json={"question": "What is the CEO salary?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["retrieval_strategy"] == "refused"
    assert data["confidence"] == "none"
    assert len(data["subgraph_node_ids"]) == 0


def test_chat_endpoint_empty_question(client: TestClient) -> None:
    """Test /chat endpoint returns 422 on empty question string."""
    resp = client.post("/chat", json={"question": "   "})
    assert resp.status_code == 422


def test_graph_endpoint_empty(client: TestClient) -> None:
    """Test /graph endpoint returns empty nodes when no IDs provided."""
    resp = client.get("/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_graph_endpoint_with_mocked_nodes(client: TestClient, mock_driver: MagicMock) -> None:
    """Test /graph endpoint processes records into GraphNode and GraphEdge models."""
    session = mock_driver.session.return_value
    session.run.return_value = [
        {
            "source_id": "sup_001",
            "source_labels": ["Supplier"],
            "source_name": "Apex Micro",
            "source_props": {"tier": 1},
            "rel_type": "LOCATED_IN",
            "rel_props": {},
            "target_id": "c_TWN",
            "target_labels": ["Country"],
            "target_name": "Taiwan",
            "target_props": {"code": "TW"},
        }
    ]

    resp = client.get("/graph?node_ids=sup_001,c_TWN")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0]["type"] == "LOCATED_IN"


def test_metrics_kpis_endpoint(client: TestClient, mock_driver: MagicMock) -> None:
    """Test /metrics/kpis endpoint returns formatted KPI metrics."""
    session = mock_driver.session.return_value
    mock_result = MagicMock()
    mock_result.data.side_effect = [
        [{"total_revenue": 150000000.0}],
        [{"cnt": 12}],
        [{"cnt": 8}],
        [{"label": "Supplier", "cnt": 40}, {"label": "Product", "cnt": 9}],
        [{"cnt": 3}],
        [{"avg_rel": 0.85}],
    ]
    session.run.return_value = mock_result

    resp = client.get("/metrics/kpis")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue_at_risk" in data
    assert "sole_sourced_components" in data
    assert "high_risk_suppliers" in data
    assert "node_counts" in data
