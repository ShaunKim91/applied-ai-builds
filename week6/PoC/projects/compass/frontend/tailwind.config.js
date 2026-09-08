/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens mapped to CSS custom properties in src/index.css.
        // The fourth distinct palette family in this series (Week10/11 blue
        // -> Week12 terracotta -> Week13 indigo/cyan glass -> now a navy
        // "chart room at night" with brass/teal, and the first of these
        // apps to default to dark rather than light) — see
        // docs/guide.html's UI Differentiation section.
        surface: "var(--surface-1)",
        surface2: "var(--surface-2)",
        page: "var(--page-plane)",
        ink: "var(--text-primary)",
        "ink-secondary": "var(--text-secondary)",
        "ink-muted": "var(--text-muted)",
        edge: "var(--border-color)",
        accent: "var(--accent)",
        "accent-2": "var(--accent-2)",
        "accent-soft": "var(--accent-soft)",
        good: "var(--status-good)",
        warning: "var(--status-warning)",
        serious: "var(--status-serious)",
        critical: "var(--status-critical)",
      },
      fontFamily: {
        serif: ['"Newsreader"', "Georgia", "serif"],
        sans: ['"Space Grotesk"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, var(--accent), var(--accent-2))",
        chart: "var(--chart-background)",
      },
      borderRadius: {
        card: "0.875rem",
      },
      boxShadow: {
        card: "0 8px 28px rgba(4, 8, 20, 0.28)",
        "card-lg": "0 20px 56px rgba(4, 8, 20, 0.36)",
      },
      keyframes: {
        "radar-sweep": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0 50%" },
        },
      },
      animation: {
        "radar-sweep": "radar-sweep 1.8s linear infinite",
        shimmer: "shimmer 1.4s ease infinite",
      },
    },
  },
  plugins: [],
};
