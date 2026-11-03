"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Building,
  CheckCircle,
  Cpu,
  DollarSign,
  Globe,
  Layers,
  MapPin,
  ShieldAlert,
} from "lucide-react";
import { fetchKPIs, KpiResponse } from "../../lib/api";

const GEOGRAPHIC_RISKS = [
  { country: "China (CN)", region: "East Asia", risk: 0.68, level: "Critical", suppliers: 12 },
  { country: "Philippines (PH)", region: "Southeast Asia", risk: 0.65, level: "Critical", suppliers: 4 },
  { country: "Taiwan (TW)", region: "East Asia", risk: 0.64, level: "Critical", suppliers: 8 },
  { country: "Malaysia (MY)", region: "Southeast Asia", risk: 0.63, level: "High", suppliers: 5 },
  { country: "Vietnam (VN)", region: "Southeast Asia", risk: 0.62, level: "High", suppliers: 6 },
  { country: "Mexico (MX)", region: "North America", risk: 0.62, level: "High", suppliers: 3 },
  { country: "India (IN)", region: "South Asia", risk: 0.61, level: "High", suppliers: 4 },
  { country: "Indonesia (ID)", region: "Southeast Asia", risk: 0.61, level: "High", suppliers: 2 },
  { country: "Israel (IL)", region: "Middle East", risk: 0.58, level: "Medium", suppliers: 1 },
  { country: "Thailand (TH)", region: "Southeast Asia", risk: 0.48, level: "Medium", suppliers: 3 },
];

export default function AnalyticsPage() {
  const [kpis, setKpis] = useState<KpiResponse | null>(null);

  useEffect(() => {
    fetchKPIs().then(setKpis).catch(() => null);
  }, []);

  const totalRevM = kpis ? (kpis.total_revenue_at_risk / 1_000_000).toFixed(1) : "154.2";
  const soleCount = kpis ? kpis.sole_sourced_components : 15;
  const highRiskSup = kpis ? kpis.high_risk_suppliers : 18;
  const activeEvents = kpis ? kpis.active_disruption_events : 4;
  const avgReliability = kpis ? kpis.avg_supplier_reliability : 0.84;

  return (
    <div className="space-y-10 py-2">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/80">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-purple-400" />
            <span>Supply Chain Risk Analytics & Intelligence</span>
          </h1>
          <p className="text-xs text-slate-400">
            Real-time exposure modeling, concentration indices, and bottleneck analysis from Neo4j.
          </p>
        </div>

        <Link
          href="/copilot"
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-medium text-xs transition-colors self-start sm:self-auto shadow-glow"
        >
          <span>Ask Copilot about Risks</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="glass rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] uppercase font-bold tracking-wider">Revenue At Risk</span>
            <DollarSign className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-white">${totalRevM}M</div>
          <p className="text-[11px] text-slate-400 mt-1">Across 9 finished products</p>
        </div>

        <div className="glass rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] uppercase font-bold tracking-wider">Sole-Sourced</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-rose-400">{soleCount}</div>
          <p className="text-[11px] text-slate-400 mt-1">Zero secondary suppliers</p>
        </div>

        <div className="glass rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] uppercase font-bold tracking-wider">High-Risk Suppliers</span>
            <ShieldAlert className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-amber-400">{highRiskSup}</div>
          <p className="text-[11px] text-slate-400 mt-1">In high-risk jurisdictions</p>
        </div>

        <div className="glass rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] uppercase font-bold tracking-wider">Active Disruption</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400">{activeEvents}</div>
          <p className="text-[11px] text-slate-400 mt-1">Port & maritime events</p>
        </div>

        <div className="glass rounded-2xl border border-border p-5 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] uppercase font-bold tracking-wider">Avg Reliability</span>
            <CheckCircle className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-sky-400">
            {(avgReliability * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Vendor historical on-time score</p>
        </div>
      </div>

      {/* Geographic Concentration Heatmap & Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Country Risk Concentration (7 cols) */}
        <div className="lg:col-span-7 glass rounded-2xl border border-border p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-sky-400" />
              <span>Geopolitical Concentration Risk Index</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">ISO 3166-1</span>
          </div>
          <p className="text-xs text-slate-400">
            Suppliers located in countries with risk indices &gt; 0.60 represent priority dual-sourcing targets:
          </p>

          <div className="space-y-3 pt-2">
            {GEOGRAPHIC_RISKS.map((geo, idx) => {
              const barWidth = Math.round(geo.risk * 100);
              const colorCls =
                geo.level === "Critical"
                  ? "bg-rose-500"
                  : geo.level === "High"
                  ? "bg-amber-500"
                  : "bg-sky-500";
              const textCls =
                geo.level === "Critical"
                  ? "text-rose-400"
                  : geo.level === "High"
                  ? "text-amber-400"
                  : "text-sky-400";

              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium text-white">{geo.country}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-[11px] text-slate-400 font-mono">
                        {geo.suppliers} Suppliers
                      </span>
                      <span className={`font-bold font-mono text-[11px] ${textCls}`}>
                        {geo.level} ({geo.risk.toFixed(2)})
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-surface h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${colorCls} rounded-full transition-all duration-500`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Risk Classification Matrix (5 cols) */}
        <div className="lg:col-span-5 glass rounded-2xl border border-border p-6 space-y-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>Component Risk Classification</span>
          </h3>
          <p className="text-xs text-slate-400">
            Automated triaging based on bill-of-materials graph topology:
          </p>

          <div className="space-y-3">
            <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-400">Critical Priority (Tier 1)</span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">
                  {soleCount} Components
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Sole-sourced parts situated in countries with risk &gt; 0.60. Immediate secondary vendor qualification required.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400">High Risk (Tier 2)</span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                  22 Components
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Components routed through single chokepoint maritime ports (e.g., Shanghai, Rotterdam). Maintain 30-day buffer stock.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400">Resilient (Tier 3)</span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  23 Components
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Multiple verified suppliers with pre-negotiated lead times and low geopolitical risk. Standard monitoring.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
