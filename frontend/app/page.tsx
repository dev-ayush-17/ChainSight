"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Compass,
  Cpu,
  DollarSign,
  GitGraph,
  Globe2,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { fetchKPIs, KpiResponse } from "../lib/api";

export default function HomePage() {
  const [kpis, setKpis] = useState<KpiResponse | null>(null);

  useEffect(() => {
    fetchKPIs().then(setKpis).catch(() => null);
  }, []);

  const totalRevM = kpis ? (kpis.total_revenue_at_risk / 1_000_000).toFixed(1) : "154.2";
  const soleCount = kpis ? kpis.sole_sourced_components : 15;
  const highRiskSup = kpis ? kpis.high_risk_suppliers : 18;
  const activeEvents = kpis ? kpis.active_disruption_events : 4;

  const scenarios = [
    {
      title: "🌊 Port of Shanghai Labor Action",
      desc: "Simulate a 14-day container terminal halt cascading through Tier-1 East Asian suppliers to bill-of-materials and product lines.",
      impact: "Critical • $108.0M Exposure",
      query: "Port of Shanghai is disrupted: which products are exposed and what is the revenue risk?",
      tag: "Multi-Hop Traversal",
    },
    {
      title: "🏭 Taiwan Fab Seismic Downtime",
      desc: "Inspect geographic concentration risk, identify sole-sourced power management ICs, and locate pre-qualified backup suppliers.",
      impact: "High • 4 Exposed SKUs",
      query: "Analyze country concentration risk and total revenue at risk in Taiwan",
      tag: "Concentration Risk",
    },
    {
      title: "🔄 Component Shortage & Substitution",
      desc: "Rapidly identify qualified secondary suppliers for component CMP-0005 with verified lead times and reliability scores.",
      impact: "Sourcing Alternative",
      query: "Find alternative suppliers for component CMP-0005 due to shortage",
      tag: "Alternative Finder",
    },
  ];

  return (
    <div className="space-y-10 py-2">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl glass border border-white/10 p-8 sm:p-12 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Next-Generation Graph RAG Architecture</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            Stop Guessing Multi-Hop Risk. <br />
            <span className="text-gradient">Reason Over the Graph.</span>
          </h1>

          <p className="text-slate-300 text-base sm:text-lg leading-relaxed">
            Standard vector RAG fails multi-hop supply chain queries because embeddings cannot traverse
            complex connections. <strong>ChainSight</strong> links 40+ suppliers, bill of materials,
            maritime ports, and live news intelligence in a unified <strong>Neo4j knowledge graph</strong>,
            delivering verifiable answers with interactive reasoning subgraphs.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/copilot"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 text-white font-semibold text-sm hover:from-sky-400 hover:to-blue-500 transition-all shadow-glow hover:scale-[1.02]"
            >
              <Bot className="w-4 h-4" />
              <span>Launch Risk Copilot</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>

            <Link
              href="/benchmark"
              className="flex items-center gap-2 px-6 py-3 rounded-xl glass border border-sky-500/30 text-sky-300 font-semibold text-sm hover:bg-surface-hover/80 hover:border-sky-400 transition-all"
            >
              <GitGraph className="w-4 h-4 text-emerald-400" />
              <span>Graph RAG vs Normal RAG (+50pp Delta)</span>
            </Link>
          </div>
        </div>
      </section>

      {/* KPI Counters */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass rounded-2xl border border-border p-5 relative overflow-hidden group hover:border-sky-500/40 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Revenue At Risk</span>
            <DollarSign className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-3xl font-extrabold text-white tracking-tight">${totalRevM}M</div>
          <p className="text-xs text-slate-400 mt-1">Across 9 product families</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-sky-500 to-blue-500 opacity-80" />
        </div>

        <div className="glass rounded-2xl border border-border p-5 relative overflow-hidden group hover:border-rose-500/40 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Sole-Sourced Bottlenecks</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-extrabold text-rose-400 tracking-tight">{soleCount}</div>
          <p className="text-xs text-slate-400 mt-1">Single-point-of-failure components</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-rose-500 opacity-80" />
        </div>

        <div className="glass rounded-2xl border border-border p-5 relative overflow-hidden group hover:border-amber-500/40 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">High-Risk Tier Suppliers</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-amber-400 tracking-tight">{highRiskSup}</div>
          <p className="text-xs text-slate-400 mt-1">Located in risk index &gt; 0.60 zones</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-amber-500 opacity-80" />
        </div>

        <div className="glass rounded-2xl border border-border p-5 relative overflow-hidden group hover:border-emerald-500/40 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-semibold tracking-wider">Active Disruption Events</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">{activeEvents}</div>
          <p className="text-xs text-slate-400 mt-1">Extracted from live news corpus</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-500 opacity-80" />
        </div>
      </section>

      {/* Primary Navigation Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/copilot"
          className="group glass rounded-2xl border border-border p-6 hover:border-sky-500/50 hover:bg-surface-hover/70 transition-all shadow-lg flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 mb-4 group-hover:scale-110 transition-transform">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-sky-300 transition-colors">
              AI Risk Copilot & Canvas
            </h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Ask natural language impact questions. ChainSight automatically classifies your intent,
              retrieves multi-hop Cypher paths, generates citations, and renders the visual reasoning subgraph.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-sky-400 mt-6 group-hover:translate-x-1 transition-transform">
            <span>Open Copilot</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </div>
        </Link>

        <Link
          href="/benchmark"
          className="group glass rounded-2xl border border-emerald-500/30 p-6 hover:border-emerald-500/60 hover:bg-surface-hover/70 transition-all shadow-glow-green flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-110 transition-transform">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">
                Graph vs. Vector Benchmark
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300">
                +50pp Win
              </span>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed">
              Explore empirical proof why Graph RAG is superior. View side-by-side comparison charts,
              token efficiency breakdowns (78% savings), hallucination reduction, and question logs.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-emerald-400 mt-6 group-hover:translate-x-1 transition-transform">
            <span>View Benchmark & Statistics</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </div>
        </Link>

        <Link
          href="/analytics"
          className="group glass rounded-2xl border border-border p-6 hover:border-purple-500/50 hover:bg-surface-hover/70 transition-all shadow-lg flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-4 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
              Risk Intelligence Dashboard
            </h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Inspect geographic risk heatmaps, component vulnerability matrices, supplier reliability
              scores, and run real-time &ldquo;What-If&rdquo; disruption simulations.
            </p>
          </div>
          <div className="flex items-center text-xs font-semibold text-purple-400 mt-6 group-hover:translate-x-1 transition-transform">
            <span>Explore Analytics</span>
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </div>
        </Link>
      </section>

      {/* Disruption Scenarios Showcase */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-sky-400" />
              <span>Interactive Multi-Hop Disruption Scenarios</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select any pre-configured scenario to see ChainSight trace multi-tier supply chain dependencies:
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {scenarios.map((sc, idx) => (
            <div
              key={idx}
              className="glass rounded-xl border border-border p-5 flex flex-col justify-between hover:border-sky-500/40 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-surface-card border border-border text-slate-300">
                    {sc.tag}
                  </span>
                  <span className="text-[11px] font-bold text-amber-400">{sc.impact}</span>
                </div>
                <h4 className="font-bold text-white text-base mb-1.5">{sc.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{sc.desc}</p>
              </div>

              <Link
                href={`/copilot?q=${encodeURIComponent(sc.query)}`}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-surface-card hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs font-semibold transition-colors"
              >
                <span>Run in Copilot</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
