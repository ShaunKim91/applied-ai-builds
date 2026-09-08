/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens mapped to CSS custom properties in src/index.css.
        // The fifth distinct palette family in this series (Week10/11 blue
        // -> Week12 terracotta -> Week13 indigo/cyan glass -> Week14_1 navy/
        // brass/teal -> now high-lightness, low-saturation pastel lilac +
        // sage, executed as claymorphism rather than flat/glass) — see
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
        display: ['"Quicksand"', "system-ui", "-apple-system", "sans-serif"],
        sans: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"Space Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backgroundImage: {
        "accent-gradient": "linear-gradient(135deg, var(--accent), var(--accent-2))",
        cloud: "var(--cloud-background)",
      },
      borderRadius: {
        clay: "1.5rem",
        "clay-sm": "1rem",
      },
      boxShadow: {
        // The claymorphism recipe: a bright highlight from the light
        // source (top-left) plus a soft, hue-tinted shadow opposite it —
        // real spatial depth from shadow direction, not decoration.
        clay: "var(--clay-shadow)",
        "clay-sm": "var(--clay-shadow-sm)",
        "clay-inset": "var(--clay-shadow-inset)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        "pop-in": {
          "0%": { transform: "scale(0.94) translateY(6px)", opacity: "0" },
          "100%": { transform: "scale(1) translateY(0)", opacity: "1" },
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        "pop-in": "pop-in 260ms cubic-bezier(0.2, 0, 0, 1) both",
      },
    },
  },
  plugins: [],
};
