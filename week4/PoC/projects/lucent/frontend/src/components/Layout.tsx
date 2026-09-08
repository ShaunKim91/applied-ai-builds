import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

// A floating, rounded glass sidebar with margin on every side — a third
// navigation pattern distinct from the Week1/11 PoCs' flush left sidebar
// and the Week3 PoC's top tab bar (see architecture.md's UI section).
const NAV = [
  { to: "/", key: "nav.dashboard", icon: "◆" },
  { to: "/chat", key: "nav.chat", icon: "◈" },
  { to: "/documents", key: "nav.documents", icon: "▤" },
  { to: "/retrieval-lab", key: "nav.retrievalLab", icon: "⬡" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex text-ink">
      <aside className="card m-4 mr-0 w-60 shrink-0 hidden md:flex md:flex-col p-5">
        <div className="flex items-center gap-2 mb-8 px-1">
          <span className="text-2xl">💎</span>
          <span className="font-extrabold text-lg tracking-tight">{t("app.name")}</span>
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent-gradient text-white shadow-glass"
                    : "text-ink-secondary hover:bg-accent-soft"
                }`
              }
            >
              <span aria-hidden className="text-base leading-none">{item.icon}</span>
              {t(item.key)}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent-gradient text-white shadow-glass"
                    : "text-ink-secondary hover:bg-accent-soft"
                }`
              }
            >
              <span aria-hidden className="text-base leading-none">⚙</span>
              {t("nav.admin")}
            </NavLink>
          )}
        </nav>
        <div className="pt-4 mt-4 border-t border-edge space-y-3">
          <div className="flex gap-2">
            <button
              onClick={() => setLang(lang === "en" ? "ko" : "en")}
              className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-edge hover:bg-accent-soft transition-colors"
            >
              {t("common.language")}
            </button>
            <button
              onClick={toggle}
              className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-edge hover:bg-accent-soft transition-colors"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
          </div>
          {user && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-ink-secondary truncate">{user.display_name}</span>
              <button
                onClick={async () => {
                  await logout();
                  navigate("/login");
                }}
                className="text-xs px-2 py-1 rounded-lg border border-edge hover:bg-accent-soft transition-colors whitespace-nowrap"
              >
                {t("nav.logout")}
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="flex-1 min-w-0 p-4 md:p-6 max-w-6xl mx-auto w-full">{children}</main>
    </div>
  );
}
