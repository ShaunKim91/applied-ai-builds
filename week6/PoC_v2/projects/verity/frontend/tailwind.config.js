/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "var(--text-primary)",
      },
      borderRadius: {
        ledger: "10px",
        "ledger-sm": "6px",
      },
      boxShadow: {
        ledger: "0 1px 2px rgba(36,31,24,0.06), 0 8px 24px rgba(36,31,24,0.08)",
        "ledger-lift": "0 4px 10px rgba(36,31,24,0.10), 0 16px 32px rgba(36,31,24,0.12)",
      },
    },
  },
  plugins: [],
};
