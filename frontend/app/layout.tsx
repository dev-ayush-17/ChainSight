import type { Metadata } from "next";
import Navbar from "../components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChainSight — Graph RAG Supply Chain Risk Copilot",
  description:
    "Grounded multi-hop reasoning over Neo4j knowledge graphs and real-time maritime disruption intelligence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 min-h-screen flex flex-col font-sans antialiased selection:bg-sky-500/30 selection:text-sky-200">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
        <footer className="border-t border-border/60 py-6 text-center text-xs text-slate-500 glass mt-12">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p>
              ChainSight v2.0 • Enterprise Graph RAG Architecture • Built with Neo4j,
              FastAPI & Next.js
            </p>
            <div className="flex items-center gap-4 text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Zero Framework Abstractions (No LangChain/LlamaIndex)
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
