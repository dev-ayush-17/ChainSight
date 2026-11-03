"use client";

import { useEffect, useState } from "react";
import {
  Compass,
  Filter,
  Layers,
  RotateCcw,
  Search,
  Sparkles,
} from "lucide-react";
import { GraphNode, GraphEdge, fetchSubgraph } from "../../lib/api";
import GraphCanvas, { COLOR_MAP } from "../../components/GraphCanvas";

const PRESETS = [
  {
    name: "🌊 Shanghai Port Cluster",
    nodes: ["port-SHA", "SUP-007", "SUP-008", "CMP-0001", "PRD-001"],
  },
  {
    name: "🏭 Taiwan Semiconductor Hub",
    nodes: ["TW", "SUP-007", "SUP-012", "CMP-0005", "CMP-0012"],
  },
  {
    name: "📦 Rotterdam European Gateway",
    nodes: ["port-RTM", "SUP-015", "SUP-022", "CMP-0020", "PRD-002"],
  },
  {
    name: "🔴 Critical Sole-Sourced Components",
    nodes: ["CMP-0001", "CMP-0005", "CMP-0015", "SUP-007", "SUP-002"],
  },
];

export default function GraphExplorerPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>(PRESETS[0].name);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const loadNodes = async (nodeIds: string[]) => {
    setLoading(true);
    try {
      const graphData = await fetchSubgraph(nodeIds);
      setNodes(graphData.nodes);
      setEdges(graphData.edges);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNodes(PRESETS[0].nodes);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const splitIds = searchQuery.split(",").map((s) => s.trim());
    loadNodes(splitIds);
  };

  return (
    <div className="space-y-6 py-2">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/80">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Compass className="w-6 h-6 text-emerald-400" />
            <span>Interactive Knowledge Graph Explorer</span>
          </h1>
          <p className="text-xs text-slate-400">
            Browse the complete Neo4j supply chain knowledge graph topology, relationships, and attributes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-surface-card border border-border text-slate-300">
            {nodes.length} Nodes • {edges.length} Relationships
          </span>
        </div>
      </div>

      {/* Filter and Presets Controls */}
      <div className="glass rounded-2xl border border-border p-4 space-y-4">
        {/* Preset Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 flex items-center gap-1 mr-2">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Presets:
          </span>
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => {
                setSelectedPreset(preset.name);
                loadNodes(preset.nodes);
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                selectedPreset === preset.name
                  ? "bg-sky-500/20 text-sky-400 border border-sky-500/40 shadow-glow"
                  : "bg-surface hover:bg-surface-hover text-slate-300 border border-border"
              }`}
            >
              {preset.name}
            </button>
          ))}
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 pt-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Node ID or comma-separated list (e.g., port-SHA, SUP-007, CMP-0005, TitanBook)..."
              className="w-full bg-surface border border-border rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !searchQuery.trim()}
            className="px-4 py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold disabled:opacity-40 transition-colors shadow-glow"
          >
            Load Subgraph
          </button>
        </form>
      </div>

      {/* Main Canvas View with Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 flex flex-col">
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            height={620}
            onNodeSelect={setSelectedNode}
          />
        </div>

        {/* Selected Node Inspector Drawer */}
        <div className="lg:col-span-4 glass rounded-2xl border border-border p-5 space-y-4 flex flex-col">
          <div className="border-b border-border/80 pb-3">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <Filter className="w-4 h-4 text-sky-400" />
              <span>Entity Inspector</span>
            </h3>
            <p className="text-xs text-slate-400">
              {selectedNode
                ? `Properties for ${selectedNode.name}`
                : "Click any node on the canvas to inspect attributes"}
            </p>
          </div>

          {selectedNode ? (
            <div className="space-y-4 flex-1 overflow-y-auto">
              <div className="p-3 rounded-xl bg-surface border border-border space-y-1.5">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLOR_MAP[selectedNode.label] }}
                  />
                  <span className="font-bold text-white text-sm">{selectedNode.name}</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-sky-400">
                  <span>ID: {selectedNode.id}</span>
                  <span>•</span>
                  <span>Label: {selectedNode.label}</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Node Properties:
                </span>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
                    <div
                      key={key}
                      className="p-2.5 rounded-lg bg-surface border border-border flex justify-between items-center"
                    >
                      <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}:</span>
                      <span className="font-mono text-white font-semibold">
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <Compass className="w-10 h-10 opacity-30 mb-2" />
              <p className="text-xs">Select any node on the canvas to view detailed attributes.</p>
            </div>
          )}

          {/* Schema Legend Box */}
          <div className="pt-4 border-t border-border/80 space-y-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Schema Entities:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(COLOR_MAP)
                .filter(([label]) => label !== "Entity")
                .map(([label, color]) => (
                  <span
                    key={label}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-surface border border-border text-slate-300"
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    {label}
                  </span>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
