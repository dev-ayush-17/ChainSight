export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  source_id: string;
  title: string;
  source: string;
  url: string;
  date: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  subgraph_node_ids: string[];
  subgraph_edge_ids: string[];
  retrieval_strategy: "lookup" | "impact_traversal" | "semantic" | "refused";
  confidence: "high" | "medium" | "low" | "none";
  latency_ms: number;
}

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  properties: Record<string, string | number | boolean | string[]>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, string | number | boolean>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface KpiResponse {
  total_revenue_at_risk: number;
  sole_sourced_components: number;
  high_risk_suppliers: number;
  active_disruption_events: number;
  avg_supplier_reliability: number;
  node_counts: Record<string, number>;
}

export interface BenchmarkMetricItem {
  name: string;
  target: string;
  graph_rag: string;
  baseline_vector: string;
  delta: string;
  is_positive: boolean;
  description: string;
}

export interface EfficiencyComparison {
  metric: string;
  graph_rag: string;
  baseline_vector: string;
  impact: string;
}

export interface QueryComparison {
  id: string;
  category: string;
  question: string;
  ground_truth: string;
  graph_rag_answer: string;
  graph_rag_hops: number;
  graph_rag_status: string;
  vector_rag_answer: string;
  vector_rag_status: string;
  why_graph_won: string;
}

export interface BenchmarkResponse {
  summary_metrics: BenchmarkMetricItem[];
  efficiencies: EfficiencyComparison[];
  category_scores: Record<string, Record<string, number>>;
  sample_comparisons: QueryComparison[];
}

export interface HealthResponse {
  status: string;
  neo4j: string;
  llm: string;
}

export interface SchemaResponse {
  node_labels: string[];
  relationship_types: string[];
  label_colors: Record<string, string>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch {
    return { status: "degraded", neo4j: "offline", llm: "offline" };
  }
}

export async function fetchKPIs(): Promise<KpiResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/metrics/kpis`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchBenchmarkData(): Promise<BenchmarkResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/metrics/benchmark`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchSubgraph(nodeIds: string[]): Promise<GraphResponse> {
  if (!nodeIds || nodeIds.length === 0) return { nodes: [], edges: [] };
  try {
    const joined = encodeURIComponent(nodeIds.join(","));
    const res = await fetch(`${API_BASE_URL}/graph?node_ids=${joined}`);
    if (!res.ok) return { nodes: [], edges: [] };
    return await res.json();
  } catch {
    return { nodes: [], edges: [] };
  }
}

export async function sendChatQuestion(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || `Server error (${res.status})`);
  }
  return await res.json();
}

