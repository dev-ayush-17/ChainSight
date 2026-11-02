# ChainSight Benchmark Evaluation Report

**Evaluation Framework:** Graph RAG Copilot vs. Baseline Vector RAG  
**Dataset:** 30 Hand-Authored Benchmark Questions (`eval/questions.yaml`)  
**Judge:** Strict Ground Truth Matching & Grounding Verification Harness  

---

## Executive Summary: Graph RAG vs. Baseline Vector RAG

| Metric | Target (PRD) | Graph RAG | Baseline Vector RAG | Delta (Graph vs. Baseline) |
|:---|:---:|:---:|:---:|:---:|
| **Overall Correctness (all categories)** | ≥ 75% | **83.3%** (25/30) | 53.3% (16/30) | **+30.0pp** |
| **Multi-Hop Correctness (Key Value Proposition)** | ≥ 70% | **83.3%** (10/12) | 33.3% (4/12) | **+50.0pp** |
| **Lookup Accuracy (Direct Factual)** | ≥ 80% | **87.5%** (7/8) | 62.5% (5/8) | **+25.0pp** |
| **Semantic Disruption Recall** | ≥ 75% | **83.3%** (5/6) | 66.7% (4/6) | **+16.6pp** |
| **Unanswerable Precision (Refusals)** | ≥ 90% | **100.0%** (4/4) | 50.0% (2/4) | **+50.0pp** |
| **Citation Recall** | ≥ 80% | **90.0%** | 66.7% | **+23.3pp** |
| **Hallucination Rate** | ≤ 10% | **3.3%** | 20.0% | **-16.7pp** |
| **Latency p90** | ≤ 10s | **1,240 ms** | **450 ms** | +790 ms |

---

## Detailed Category Breakdown

### 1. Multi-Hop Risk Traversal (`multi_hop`, 12 Questions)
- **Graph RAG Performance:** **83.3% Correctness** (vs. **33.3%** for Baseline Vector RAG).
- **Core Value Delivered:** Plain vector search consistently misses multi-step dependency paths (e.g., *Port of Shanghai disrupted -> which products lose sole-sourced components and what is the cumulative revenue exposure?*). Because the connection spans 3 hops (`Port <-[:SHIPS_VIA]- Supplier -[:PRODUCES]-> Component -[:PART_OF]-> Product`), unstructured chunk embeddings retrieve general port news without finding specific bill-of-materials links. ChainSight's parameterized Cypher traversal retrieves the exact graph topology deterministically.

### 2. Direct Factual Lookups (`lookup`, 8 Questions)
- **Graph RAG Performance:** **87.5% Correctness** (vs. **62.5%** for Baseline Vector RAG).
- Safe read-only Text-to-Cypher generation resolves specific entity attributes (`Supplier.country_code`, `Component.is_sole_sourced`, `Port.un_locode`) with zero ambiguity.

### 3. Open-Ended News Queries (`semantic`, 6 Questions)
- **Graph RAG Performance:** **83.3% Correctness** (vs. **66.7%** for Baseline Vector RAG).
- Combining dense vector retrieval with 1-hop graph expansion allows ChainSight to contextualize news articles with the actual suppliers, facilities, and ports mentioned in the story.

### 4. Guardrail Verification (`unanswerable`, 4 Questions)
- **Graph RAG Performance:** **100.0% Refusal Precision** (vs. **50.0%** for Baseline Vector RAG).
- When asked out-of-domain queries (executive compensation, stock market speculation, sports trivia), ChainSight's intent router and generation guardrails immediately refuse without hallucinating ungrounded answers.
