/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens mapped to CSS custom properties in src/index.css.
        // A third, deliberately distinct palette family from the Week10-12
        // PoCs (cool blue -> warm terracotta -> now indigo/cyan on glass) —
        // see architecture.md's UI differentiation section.
        surface: "var(--surface-1)",
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
        sans: ['"Manrope"', "system-ui", "-apple-system", "sans-serif"],
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, var(--accent), var(--accent-2))",
        mesh: "var(--mesh-background)",
      },
      borderRadius: {
        glass: "1.25rem",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(31, 20, 90, 0.12)",
        "glass-lg": "0 16px 48px rgba(31, 20, 90, 0.18)",
      },
      backdropBlur: {
        glass: "20px",
      },
    },
  },
  plugins: [],
};
