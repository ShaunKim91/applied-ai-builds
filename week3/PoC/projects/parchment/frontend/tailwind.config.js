/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens mapped to CSS custom properties defined in
        // src/index.css (light "parchment" values in :root, dark values
        // under .dark). Deliberately a different palette family from the
        // Week10/11 PoCs' cool-gray/blue tokens — see architecture.md's UI
        // differentiation section.
        surface: "var(--surface-1)",
        page: "var(--page-plane)",
        ink: "var(--text-primary)",
        "ink-secondary": "var(--text-secondary)",
        "ink-muted": "var(--text-muted)",
        edge: "var(--border-color)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        good: "var(--status-good)",
        warning: "var(--status-warning)",
        serious: "var(--status-serious)",
        critical: "var(--status-critical)",
      },
      fontFamily: {
        // Sans stays the UI/body-text workhorse; serif is reserved for
        // headings and other "reading" moments (interface-craft pairing rule).
        sans: ["system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        serif: ['"Newsreader"', "Georgia", '"Times New Roman"', "serif"],
      },
      fontSize: {
        // Perfect Fourth (1.333) scale for headings — more dramatic than
        // Week10/11's tighter dashboard ratio, fitting an editorial feel.
        "display-lg": ["2.83rem", { lineHeight: "1.1", fontWeight: "600" }],
        "display-md": ["2.13rem", { lineHeight: "1.15", fontWeight: "600" }],
        "display-sm": ["1.6rem", { lineHeight: "1.25", fontWeight: "600" }],
      },
      borderRadius: {
        card: "0.5rem", // 8px — modestly rounded, more "paper corner" than "app bubble"
      },
      boxShadow: {
        // Soft, layered "paper stack" shadows instead of Week10/11's flat
        // 1px-border cards.
        paper: "0 1px 2px rgba(43,32,22,0.07), 0 2px 8px rgba(43,32,22,0.08)",
        "paper-lg": "0 2px 4px rgba(43,32,22,0.08), 0 8px 20px rgba(43,32,22,0.12)",
      },
    },
  },
  plugins: [],
};
