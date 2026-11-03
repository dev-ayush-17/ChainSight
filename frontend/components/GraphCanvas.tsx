"use client";

import React, { useEffect, useRef, useState } from "react";
import { GraphNode, GraphEdge } from "../lib/api";
import { Maximize2, Minimize2, RotateCcw, ZoomIn, ZoomOut, X } from "lucide-react";

export const COLOR_MAP: Record<string, string> = {
  Supplier: "#4A90D9",
  Port: "#E67E22",
  Component: "#27AE60",
  Product: "#8E44AD",
  Country: "#C0392B",
  Event: "#E74C3C",
  Article: "#95A5A6",
  Customer: "#F39C12",
  Facility: "#16A085",
  Entity: "#64748b",
};

interface SimulationNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  highlightedIds?: string[];
  onNodeSelect?: (node: GraphNode | null) => void;
}

export default function GraphCanvas({
  nodes,
  edges,
  height = 500,
  highlightedIds = [],
  onNodeSelect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimulationNode | null>(null);

  // Transform states
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const isDraggingCanvas = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const draggedNode = useRef<SimulationNode | null>(null);

  // Simulation node map
  const simNodesRef = useRef<Map<string, SimulationNode>>(new Map());

  // Initialize nodes positions
  useEffect(() => {
    const map = new Map<string, SimulationNode>();
    const count = nodes.length;
    const center = { x: 350, y: height / 2 };
    const radiusDist = Math.min(220, 80 + count * 8);

    nodes.forEach((n, idx) => {
      const angle = (idx / Math.max(1, count)) * 2 * Math.PI;
      const existing = simNodesRef.current.get(n.id);
      const isPortOrProduct = n.label === "Port" || n.label === "Product";

      map.set(n.id, {
        ...n,
        x: existing ? existing.x : center.x + Math.cos(angle) * (radiusDist + (idx % 2) * 40),
        y: existing ? existing.y : center.y + Math.sin(angle) * (radiusDist + (idx % 2) * 40),
        vx: 0,
        vy: 0,
        radius: isPortOrProduct ? 18 : 13,
        color: COLOR_MAP[n.label] || COLOR_MAP.Entity,
      });
    });

    simNodesRef.current = map;
  }, [nodes, height]);

  // Physics animation loop
  useEffect(() => {
    let animationFrameId: number;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function render() {
      if (!canvas || !ctx) return;
      const simNodes = Array.from(simNodesRef.current.values());

      // 1. Simple repulsive and attractive physics step
      for (let i = 0; i < simNodes.length; i++) {
        const n1 = simNodes[i];
        if (n1 === draggedNode.current) continue;

        // Repel from center gently
        n1.vx += (canvas.width / 2 - n1.x) * 0.0005;
        n1.vy += (canvas.height / 2 - n1.y) * 0.0005;

        // Repel from each other
        for (let j = i + 1; j < simNodes.length; j++) {
          const n2 = simNodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const dist = Math.sqrt(dx * dy + dy * dy) || 1;
          const minDist = n1.radius + n2.radius + 60;
          if (dist < minDist) {
            const force = (minDist - dist) / dist * 0.04;
            n1.vx -= dx * force;
            n1.vy -= dy * force;
            n2.vx += dx * force;
            n2.vy += dy * force;
          }
        }
      }

      // Attract along edges
      edges.forEach((edge) => {
        const s = simNodesRef.current.get(edge.source);
        const t = simNodesRef.current.get(edge.target);
        if (s && t) {
          const dx = t.x - s.x;
          const dy = t.y - s.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const targetDist = 90;
          const force = (dist - targetDist) * 0.005;
          if (s !== draggedNode.current) {
            s.vx += dx * force;
            s.vy += dy * force;
          }
          if (t !== draggedNode.current) {
            t.vx -= dx * force;
            t.vy -= dy * force;
          }
        }
      });

      // Update positions with friction damping
      simNodes.forEach((n) => {
        if (n !== draggedNode.current) {
          n.vx *= 0.88;
          n.vy *= 0.88;
          n.x += n.vx;
          n.y += n.vy;
        }
      });

      // 2. Draw canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.translate(offset.x, offset.y);
      ctx.scale(zoom, zoom);

      // Draw Edges
      edges.forEach((edge) => {
        const s = simNodesRef.current.get(edge.source);
        const t = simNodesRef.current.get(edge.target);
        if (!s || !t) return;

        const isHighlighted =
          hoveredNode && (hoveredNode.id === s.id || hoveredNode.id === t.id);

        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = isHighlighted ? "#38bdf8" : "rgba(100, 116, 139, 0.35)";
        ctx.lineWidth = isHighlighted ? 2.5 : 1.2;
        ctx.stroke();

        // Edge label
        const midX = (s.x + t.x) / 2;
        const midY = (s.y + t.y) / 2;
        ctx.fillStyle = isHighlighted ? "#38bdf8" : "rgba(148, 163, 184, 0.7)";
        ctx.font = "9px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(edge.type, midX, midY - 4);
      });

      // Draw Nodes
      simNodes.forEach((n) => {
        const isHovered = hoveredNode?.id === n.id;
        const isSelected = selectedNode?.id === n.id;
        const isHighlighted = highlightedIds.includes(n.id);

        // Halo / Glow
        if (isHovered || isSelected || isHighlighted) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + 6, 0, 2 * Math.PI);
          ctx.fillStyle = isSelected
            ? "rgba(245, 158, 11, 0.3)"
            : "rgba(56, 189, 248, 0.25)";
          ctx.fill();
        }

        // Node Body
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, 2 * Math.PI);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.lineWidth = isSelected ? 3 : 1.5;
        ctx.strokeStyle = isSelected ? "#f59e0b" : "#ffffff";
        ctx.stroke();

        // Label Text
        ctx.fillStyle = "#ffffff";
        ctx.font = "11px Inter, sans-serif";
        ctx.textAlign = "center";
        const displayName = n.name.length > 18 ? n.name.slice(0, 16) + "…" : n.name;
        ctx.fillText(displayName, n.x, n.y + n.radius + 14);

        // Small type pill
        ctx.fillStyle = "rgba(148, 163, 184, 0.85)";
        ctx.font = "9px Inter, sans-serif";
        ctx.fillText(`(${n.label})`, n.x, n.y + n.radius + 25);
      });

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    }

    animationFrameId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationFrameId);
  }, [edges, zoom, offset, hoveredNode, selectedNode, highlightedIds]);

  // Mouse interaction handlers
  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    return {
      x: (clientX - offset.x) / zoom,
      y: (clientY - offset.y) / zoom,
    };
  };

  const findNodeAt = (x: number, y: number): SimulationNode | null => {
    for (const node of Array.from(simNodesRef.current.values())) {
      const dx = node.x - x;
      const dy = node.y - y;
      if (Math.sqrt(dx * dx + dy * dy) <= node.radius + 4) {
        return node;
      }
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getCanvasCoords(e);
    const clickedNode = findNodeAt(coords.x, coords.y);

    if (clickedNode) {
      draggedNode.current = clickedNode;
      setSelectedNode(clickedNode);
      onNodeSelect?.(clickedNode);
    } else {
      isDraggingCanvas.current = true;
      dragStart.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getCanvasCoords(e);

    if (draggedNode.current) {
      draggedNode.current.x = coords.x;
      draggedNode.current.y = coords.y;
      draggedNode.current.vx = 0;
      draggedNode.current.vy = 0;
    } else if (isDraggingCanvas.current) {
      setOffset({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      });
    } else {
      const hovered = findNodeAt(coords.x, coords.y);
      setHoveredNode(hovered);
    }
  };

  const handleMouseUp = () => {
    draggedNode.current = null;
    isDraggingCanvas.current = false;
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.min(2.5, Math.max(0.4, prev * factor)));
  };

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-border bg-[#080d1a] shadow-inner">
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={900}
        height={height}
        className="w-full cursor-grab active:cursor-grabbing block"
        style={{ height: `${height}px` }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      />

      {/* Control Buttons */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 p-1 rounded-xl glass border border-white/10 text-slate-300">
        <button
          onClick={() => setZoom((z) => Math.min(2.5, z * 1.2))}
          className="p-1.5 hover:bg-surface-hover rounded-lg transition-colors text-slate-300 hover:text-white"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.4, z / 1.2))}
          className="p-1.5 hover:bg-surface-hover rounded-lg transition-colors text-slate-300 hover:text-white"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setOffset({ x: 0, y: 0 });
          }}
          className="p-1.5 hover:bg-surface-hover rounded-lg transition-colors text-slate-300 hover:text-white"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Legend Bar */}
      <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center gap-2 px-3 py-2 rounded-xl glass border border-white/10 text-xs">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
          Graph Entities:
        </span>
        {Object.entries(COLOR_MAP)
          .filter(([label]) => label !== "Entity")
          .map(([label, color]) => (
            <div key={label} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-slate-300 text-[11px]">{label}</span>
            </div>
          ))}
      </div>

      {/* Selected Node Properties Drawer */}
      {selectedNode && (
        <div className="absolute top-3 left-3 max-w-sm w-80 glass rounded-xl border border-sky-500/30 p-4 shadow-2xl animate-in fade-in duration-150">
          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: COLOR_MAP[selectedNode.label] }}
                />
                <span className="font-bold text-white text-sm">
                  {selectedNode.name}
                </span>
              </div>
              <span className="text-[10px] font-mono text-sky-400">
                {selectedNode.id} • {selectedNode.label}
              </span>
            </div>
            <button
              onClick={() => {
                setSelectedNode(null);
                onNodeSelect?.(null);
              }}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-surface-hover"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1.5 max-h-56 overflow-y-auto text-xs mt-3 pr-1">
            {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
              <div
                key={key}
                className="flex items-start justify-between py-1 border-b border-border/40"
              >
                <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}:</span>
                <span className="text-slate-200 font-mono text-right max-w-[160px] truncate">
                  {String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
