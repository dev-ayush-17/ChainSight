# ChainSight 🔗
> Graph RAG supply chain risk copilot — multi-hop reasoning over a Neo4j knowledge graph.

## Overview
ChainSight enables supply chain managers to answer complex multi-hop risk and disruption questions grounded in a Neo4j knowledge graph and live disruption news, complete with verifiable source citations and interactive reasoning subgraph visualization.

## Architecture
- **Graph Database**: Neo4j (Bolt protocol) with Cypher traversal and native vector indices
- **Data Ingestion**: Synthetic supply chain graph (BOM, facilities, suppliers, ports) + disruption news pipeline
- **Retrieval Engine**: Intent-routed multi-strategy retrieval (Text-to-Cypher, template impact traversal, vector search + graph expansion)
- **Backend**: FastAPI with strict Pydantic data schemas
- **Frontend**: Streamlit interactive copilot UI with graph visualization

## Quickstart (Local Development)

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose (or Neo4j AuraDB instance)

### 2. Setup Environment
```bash
# Copy environment configuration
cp .env.example .env

# Generate synthetic dataset
python -m data.generate_synthetic

# Start Neo4j via Docker
docker compose up -d neo4j

# Ingest data into Neo4j
python -m ingestion.load_graph
```

## License
MIT
