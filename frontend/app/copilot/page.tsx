"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  BookOpen,
  Bot,
  ExternalLink,
  Flame,
  GitBranch,
  Layers,
  RotateCcw,
  Send,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  ChatResponse,
  GraphNode,
  GraphEdge,
  fetchSubgraph,
  sendChatQuestion,
} from "../../lib/api";
import GraphCanvas, { COLOR_MAP } from "../../components/GraphCanvas";

interface Message {
  role: "user" | "assistant";
  content: string;
  strategy?: "lookup" | "impact_traversal" | "semantic" | "refused";
  confidence?: "high" | "medium" | "low" | "none";
  latency_ms?: number;
  citations?: Array<{
    source_id: string;
    title: string;
    source: string;
    url: string;
    date: string;
  }>;
  subgraph_node_ids?: string[];
}

const PRESET_QUESTIONS = [
  "Port of Shanghai is disrupted: which products are exposed and what is the revenue risk?",
  "Which country is supplier SUP-007 located in?",
  "Find alternative suppliers for component CMP-0005 due to shortage",
  "Analyze country concentration risk and total revenue at risk in Taiwan",
  "What recent shipping disruptions and container delays have occurred in Asia?",
  "What is the CEO's annual salary and bonus package?",
];

function CopilotContent() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [subgraphNodes, setSubgraphNodes] = useState<GraphNode[]>([]);
  const [subgraphEdges, setSubgraphEdges] = useState<GraphEdge[]>([]);
  const [activeNodeIds, setActiveNodeIds] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Handle URL query parameter pre-population
  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setInput(q);
      handleSend(q);
    }
  }, [searchParams]);

  const handleSend = async (questionToSend?: string) => {
    const query = (questionToSend || input).trim();
    if (!query || loading) return;

    setInput("");
    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChatQuestion(query);

      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
        strategy: res.retrieval_strategy,
        confidence: res.confidence,
        latency_ms: res.latency_ms,
        citations: res.citations,
        subgraph_node_ids: res.subgraph_node_ids,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Fetch Subgraph for visual rendering if node IDs were returned
      if (res.subgraph_node_ids && res.subgraph_node_ids.length > 0) {
        setActiveNodeIds(res.subgraph_node_ids);
        const graphData = await fetchSubgraph(res.subgraph_node_ids);
        setSubgraphNodes(graphData.nodes);
        setSubgraphEdges(graphData.edges);
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to execute copilot query";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ **Error connecting to backend**: ${errorMessage}. Ensure FastAPI is running at \`http://localhost:8000\`.`,
          strategy: "refused",
          confidence: "none",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getStrategyBadge = (strategy?: string) => {
    switch (strategy) {
      case "impact_traversal":
        return {
          label: "Graph Traversal",
          bg: "bg-purple-500/20 text-purple-300 border-purple-500/40",
          icon: GitBranch,
        };
      case "lookup":
        return {
          label: "Exact Lookup",
          bg: "bg-sky-500/20 text-sky-300 border-sky-500/40",
          icon: Zap,
        };
      case "semantic":
        return {
          label: "Semantic Vector Search",
          bg: "bg-amber-500/20 text-amber-300 border-amber-500/40",
          icon: Layers,
        };
      case "refused":
        return {
          label: "Guardrail Refusal",
          bg: "bg-slate-500/20 text-slate-300 border-slate-500/40",
          icon: AlertCircle,
        };
      default:
        return {
          label: "Graph RAG",
          bg: "bg-sky-500/20 text-sky-300 border-sky-500/40",
          icon: Bot,
        };
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border/60">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="w-6 h-6 text-sky-400" />
            <span>AI Supply Chain Risk Copilot</span>
          </h1>
          <p className="text-xs text-slate-400">
            Multi-hop reasoning over Neo4j knowledge graphs with live source verification.
          </p>
        </div>

        <button
          onClick={() => {
            setMessages([]);
            setSubgraphNodes([]);
            setSubgraphEdges([]);
            setActiveNodeIds([]);
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg glass border border-border text-slate-400 hover:text-white hover:bg-surface-hover text-xs transition-colors self-start sm:self-auto"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Session</span>
        </button>
      </div>

      {/* Main 2-Column Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[720px]">
        {/* Left Column: Chat Stream (7 cols) */}
        <div className="lg:col-span-7 flex flex-col glass rounded-2xl border border-border overflow-hidden h-full">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {messages.length === 0 && (
              <div className="h-full flex flex-col justify-center items-center text-center max-w-md mx-auto py-8">
                <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 mb-4 shadow-glow">
                  <Bot className="w-7 h-7" />
                </div>
                <h3 className="text-lg font-bold text-white mb-1">
                  How can ChainSight assist your supply chain today?
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  Ask multi-hop impact questions, locate single-source component risks, or find alternative supplier routes.
                </p>

                {/* Preset Chips */}
                <div className="w-full space-y-2 text-left">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Recommended Questions:
                  </p>
                  {PRESET_QUESTIONS.slice(0, 3).map((preset, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(preset)}
                      className="w-full text-left p-2.5 rounded-xl bg-surface-card hover:bg-surface-hover border border-border/80 text-xs text-slate-300 hover:text-white transition-all flex items-center justify-between group"
                    >
                      <span className="truncate pr-2">{preset}</span>
                      <Sparkles className="w-3.5 h-3.5 text-sky-400 opacity-60 group-hover:opacity-100 flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, idx) => {
              const isUser = msg.role === "user";
              const badge = !isUser ? getStrategyBadge(msg.strategy) : null;
              const BadgeIcon = badge?.icon;

              return (
                <div
                  key={idx}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[90%] sm:max-w-[85%] rounded-2xl p-4 sm:p-5 text-sm leading-relaxed ${
                      isUser
                        ? "bg-gradient-to-r from-sky-600 to-blue-600 text-white rounded-br-none shadow-md"
                        : "bg-surface-card border border-border/80 text-slate-200 rounded-bl-none shadow-lg"
                    }`}
                  >
                    {/* Render message content with markdown formatting */}
                    <div className="whitespace-pre-wrap space-y-2 prose prose-invert prose-sm max-w-none">
                      {msg.content}
                    </div>

                    {/* Metadata bar for assistant answers */}
                    {!isUser && (
                      <div className="mt-4 pt-3 border-t border-border/50 flex flex-wrap items-center gap-2">
                        {badge && BadgeIcon && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${badge.bg}`}
                          >
                            <BadgeIcon className="w-3 h-3" />
                            {badge.label}
                          </span>
                        )}

                        {msg.confidence && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-surface border border-border text-slate-300">
                            Confidence:{" "}
                            <strong
                              className={
                                msg.confidence === "high"
                                  ? "text-emerald-400"
                                  : msg.confidence === "medium"
                                  ? "text-amber-400"
                                  : "text-rose-400"
                              }
                            >
                              {msg.confidence.toUpperCase()}
                            </strong>
                          </span>
                        )}

                        {msg.latency_ms !== undefined && (
                          <span className="text-[11px] font-mono text-slate-400">
                            ⏱️ {msg.latency_ms}ms
                          </span>
                        )}
                      </div>
                    )}

                    {/* Citations accordion */}
                    {!isUser && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2">
                        <details className="text-xs group">
                          <summary className="cursor-pointer text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1.5 list-none select-none">
                            <BookOpen className="w-3.5 h-3.5" />
                            <span>Verified Source Citations ({msg.citations.length})</span>
                          </summary>
                          <div className="mt-2 space-y-1.5 pl-2 border-l border-sky-500/30">
                            {msg.citations.map((cite, cIdx) => (
                              <div
                                key={cIdx}
                                className="p-2 rounded bg-surface border border-border text-slate-300 text-xs flex items-center justify-between"
                              >
                                <div>
                                  <span className="font-semibold text-white">
                                    [{cite.source_id}]
                                  </span>{" "}
                                  <span>{cite.title}</span>
                                  <div className="text-[10px] text-slate-400">
                                    Source: {cite.source} • {cite.date}
                                  </div>
                                </div>
                                {cite.url && (
                                  <a
                                    href={cite.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-sky-400 hover:text-sky-300 p-1"
                                  >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-surface-card border border-border/80 max-w-sm">
                <div className="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-slate-300">
                  Traversing knowledge graph & citing evidence...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-3 sm:p-4 bg-surface-card/90 border-t border-border">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about port strikes, supplier dependencies, single-source BOM risk..."
                disabled={loading}
                className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-all"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-4 py-3 rounded-xl bg-sky-500 text-white font-medium text-sm hover:bg-sky-400 disabled:opacity-40 disabled:hover:bg-sky-500 transition-colors flex items-center justify-center shadow-glow"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Reasoning Subgraph Canvas (5 cols) */}
        <div className="lg:col-span-5 flex flex-col glass rounded-2xl border border-border overflow-hidden h-full">
          <div className="p-3.5 border-b border-border/80 flex items-center justify-between bg-surface-card">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-sky-400" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Live Reasoning Subgraph
              </span>
            </div>
            {subgraphNodes.length > 0 && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface border border-border text-slate-300">
                {subgraphNodes.length} nodes • {subgraphEdges.length} edges
              </span>
            )}
          </div>

          <div className="flex-1 p-3 flex flex-col justify-between bg-[#080d1a]">
            {subgraphNodes.length > 0 ? (
              <GraphCanvas
                nodes={subgraphNodes}
                edges={subgraphEdges}
                height={620}
                highlightedIds={activeNodeIds}
              />
            ) : (
              <div className="h-full flex flex-col justify-center items-center text-center p-6 text-slate-500">
                <div className="w-16 h-16 rounded-full border border-dashed border-border/80 flex items-center justify-center mb-3">
                  <GitBranch className="w-8 h-8 opacity-40 text-slate-400" />
                </div>
                <h4 className="font-semibold text-slate-300 text-sm mb-1">
                  Reasoning Subgraph Inactive
                </h4>
                <p className="text-xs max-w-xs text-slate-500">
                  Ask a multi-hop disruption question on the left to see the graph traversal path rendered with physics in real-time.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CopilotPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center text-slate-400">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>Loading Copilot...</span>
          </div>
        </div>
      }
    >
      <CopilotContent />
    </Suspense>
  );
}
