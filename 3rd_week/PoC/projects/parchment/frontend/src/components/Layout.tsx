import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

// Top tab bar instead of a left sidebar — a deliberate departure from the
// Week1/2 PoCs' sidebar+card dashboard shape (see architecture.md's UI
// differentiation section). Mirrors, and visually elevates, a simple
// 3-tab structure (🧾/📄/🌐), plus this project's two additional pages
// (Dashboard, Library).
const NAV = [
  { to: "/", key: "nav.dashboard", icon: "📊" },
  { to: "/receipts", key: "nav.receipts", icon: "🧾" },
  { to: "/pdfs", key: "nav.pdfs", icon: "📄" },
  { to: "/tables", key: "nav.tables", icon: "🌐" },
  { to: "/library", key: "nav.library", icon: "🗂️" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-page text-ink">
      <header className="border-b border-edge bg-surface">
        <div className="max-w-6xl mx-auto px-4 md:px-8 pt-5 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl">📜</span>
            <span className="font-serif text-display-sm text-ink">{t("app.name")}</span>
            <span className="hidden sm:inline text-xs text-ink-muted ml-1">{t("app.tagline")}</span>
          </div>
          <div className="flex items-center gap-2 pb-2">
            <button
              onClick={() => setLang(lang === "en" ? "ko" : "en")}
              className="text-sm px-3 py-1.5 rounded-full border border-edge hover:bg-accent-soft transition-colors"
              aria-label="Toggle language"
            >
              {t("common.language")}
            </button>
            <button
              onClick={toggle}
              className="text-sm px-3 py-1.5 rounded-full border border-edge hover:bg-accent-soft transition-colors"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            {user && (
              <div className="flex items-center gap-2 pl-2 ml-1 border-l border-edge">
                <span className="text-sm text-ink-secondary hidden sm:inline">{user.display_name}</span>
                <button
                  onClick={async () => {
                    await logout();
                    navigate("/login");
                  }}
                  className="text-sm px-3 py-1.5 rounded-full border border-edge hover:bg-accent-soft transition-colors"
                >
                  {t("nav.logout")}
                </button>
              </div>
            )}
          </div>
        </div>

        <nav className="max-w-6xl mx-auto px-4 md:px-8 flex gap-1 overflow-x-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-accent text-accent"
                    : "border-transparent text-ink-secondary hover:text-ink hover:border-edge"
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {t(item.key)}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-accent text-accent"
                    : "border-transparent text-ink-secondary hover:text-ink hover:border-edge"
                }`
              }
            >
              <span aria-hidden>🛠️</span>
              {t("nav.admin")}
            </NavLink>
          )}
        </nav>
      </header>

      <main className="max-w-6xl mx-auto w-full p-4 md:p-8">{children}</main>

      <footer className="max-w-6xl mx-auto px-4 md:px-8 pb-6 text-xs text-ink-muted">
        Parchment v1.0.0 · Week3 PoC
      </footer>
    </div>
  );
}
