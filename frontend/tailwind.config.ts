import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#080c14",
        surface: "#0e1526",
        "surface-card": "#131c31",
        "surface-hover": "#1a2540",
        border: "#1f2d4a",
        accent: {
          blue: "#38bdf8",
          emerald: "#10b981",
          amber: "#f59e0b",
          purple: "#a855f7",
          rose: "#f43f5e",
        },
        graph: {
          supplier: "#4A90D9",
          port: "#E67E22",
          component: "#27AE60",
          product: "#8E44AD",
          country: "#C0392B",
          event: "#E74C3C",
          article: "#95A5A6",
          customer: "#F39C12",
          facility: "#16A085",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 25px -5px rgba(56, 189, 248, 0.25)",
        "glow-green": "0 0 25px -5px rgba(16, 185, 129, 0.25)",
        "glow-red": "0 0 25px -5px rgba(244, 63, 94, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;

