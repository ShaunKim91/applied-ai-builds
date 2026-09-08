import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

const NAV = [
  { to: "/", key: "nav.dashboard", icon: "📊" },
  { to: "/vision", key: "nav.vision", icon: "🖼️" },
  { to: "/generate", key: "nav.generate", icon: "🎨" },
  { to: "/forecast", key: "nav.forecast", icon: "📈" },
  { to: "/search", key: "nav.search", icon: "🔎" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-page text-ink">
      <aside className="w-64 shrink-0 border-r border-edge bg-surface hidden md:flex md:flex-col">
        <div className="px-6 py-5 border-b border-edge">
          <div className="text-lg font-semibold">🛒 {t("app.name")}</div>
          <div className="text-xs text-ink-muted mt-0.5">{t("app.tagline")}</div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary hover:bg-accent-soft/60"
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
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary hover:bg-accent-soft/60"
                }`
              }
            >
              <span aria-hidden>🛠️</span>
              {t("nav.admin")}
            </NavLink>
          )}
        </nav>
        <div className="px-3 py-4 border-t border-edge text-xs text-ink-muted">
          CommerceIQ v1.0.0 · PoC
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-edge bg-surface flex items-center justify-between px-4 md:px-8">
          <div className="md:hidden font-semibold">🛒 {t("app.name")}</div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLang(lang === "en" ? "ko" : "en")}
              className="text-sm px-3 py-1.5 rounded-lg border border-edge hover:bg-accent-soft/60 transition-colors"
              aria-label="Toggle language"
            >
              {t("common.language")}
            </button>
            <button
              onClick={toggle}
              className="text-sm px-3 py-1.5 rounded-lg border border-edge hover:bg-accent-soft/60 transition-colors"
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
                  className="text-sm px-3 py-1.5 rounded-lg border border-edge hover:bg-accent-soft/60 transition-colors"
                >
                  {t("nav.logout")}
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8 max-w-6xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
