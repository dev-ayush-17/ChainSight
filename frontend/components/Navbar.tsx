"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  Compass,
  Database,
  GitGraph,
  Layers,
  Sparkles,
} from "lucide-react";
import { fetchHealth, HealthResponse } from "../lib/api";

const navItems = [
  { href: "/", label: "Overview", icon: Layers },
  { href: "/copilot", label: "Risk Copilot", icon: Bot, badge: "AI" },
  { href: "/analytics", label: "Risk Analytics", icon: Activity },
  { href: "/graph-explorer", label: "Graph Explorer", icon: Compass },
  { href: "/benchmark", label: "Graph vs Vector RAG", icon: GitGraph, highlight: true },
];

export default function Navbar() {
  const pathname = usePathname();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => null);
    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(() => null);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = health?.status === "ok" || health?.neo4j === "connected";

  return (
    <header className="sticky top-0 z-50 glass border-b border-border/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 via-emerald-500 to-purple-600 p-[2px] transition-transform group-hover:scale-105 shadow-glow">
              <div className="w-full h-full bg-background rounded-[10px] flex items-center justify-center">
                <GitGraph className="w-5 h-5 text-sky-400 group-hover:rotate-12 transition-transform" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight text-white group-hover:text-sky-400 transition-colors">
                  ChainSight
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-semibold">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-none">
                Graph RAG Supply Chain Risk Copilot
              </p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "text-white bg-surface-card border border-sky-500/30 shadow-glow"
                      : "text-slate-400 hover:text-white hover:bg-surface-hover/60"
                  } ${
                    item.highlight && !isActive
                      ? "text-sky-300 bg-sky-950/20 border border-sky-500/20 hover:border-sky-500/40"
                      : ""
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-sky-400" : ""}`} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      {item.badge}
                    </span>
                  )}
                  {item.highlight && (
                    <Sparkles className="w-3 h-3 text-amber-400 animate-pulse" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Live Status indicator */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface-card border border-border text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline ? "bg-emerald-400 animate-ping" : "bg-amber-400"
                }`}
              />
              <span className="text-slate-300 font-mono text-[11px] hidden sm:inline">
                {isOnline ? "Neo4j Connected" : "Local Standby"}
              </span>
              <Database className="w-3.5 h-3.5 text-slate-400" />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
