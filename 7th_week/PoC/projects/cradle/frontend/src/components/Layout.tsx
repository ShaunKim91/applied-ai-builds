import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

// A floating, centered, pill-shaped top nav bar — the fifth distinct
// navigation pattern in this series (after Week1/2's flush sidebar,
// Week3's top tabs, Week4's floating glass sidebar, Week6's command
// console + icon rail). The full-pill shape reads as one soft, rounded
// object floating above the page — consistent with claymorphism's rounded
// vocabulary, distinct from every prior pattern's rectangular chrome.
const NAV = [
  { to: "/", key: "nav.dashboard", icon: "◆" },
  { to: "/console", key: "nav.console", icon: "◈" },
  { to: "/approvals", key: "nav.approvals", icon: "✓" },
  { to: "/history", key: "nav.history", icon: "▤" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-ink">
      <header className="sticky top-4 z-30 mx-auto max-w-4xl px-4">
        <div className="clay flex items-center gap-1 px-3 py-2 !rounded-full">
          <div className="flex items-center gap-2 pl-2 pr-3 shrink-0">
            <span className="text-xl">🧸</span>
            <span className="font-display font-bold text-base tracking-tight hidden sm:inline">{t("app.name")}</span>
          </div>
          <nav className="flex-1 flex items-center gap-1 overflow-x-auto">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap ${
                    isActive ? "bg-accent-gradient text-white shadow-clay-sm" : "text-ink-secondary hover:bg-accent-soft"
                  }`
                }
              >
                <span aria-hidden className="text-sm leading-none">{item.icon}</span>
                {t(item.key)}
              </NavLink>
            ))}
            {user?.role === "admin" && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap ${
                    isActive ? "bg-accent-gradient text-white shadow-clay-sm" : "text-ink-secondary hover:bg-accent-soft"
                  }`
                }
              >
                <span aria-hidden className="text-sm leading-none">⚙</span>
                {t("nav.admin")}
              </NavLink>
            )}
          </nav>
          <div className="flex items-center gap-1 shrink-0 pl-2">
            <button onClick={() => setLang(lang === "en" ? "ko" : "en")} className="text-xs px-2.5 py-1.5 rounded-full clay-inset hover:bg-accent-soft">
              {t("common.language")}
            </button>
            <button onClick={toggle} className="text-xs px-2.5 py-1.5 rounded-full clay-inset hover:bg-accent-soft">
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            {user && (
              <button
                onClick={async () => {
                  await logout();
                  navigate("/login");
                }}
                className="hidden md:inline text-xs px-2.5 py-1.5 rounded-full clay-inset hover:bg-accent-soft whitespace-nowrap"
              >
                {t("nav.logout")}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="pt-8 pb-16 px-4">
        <div className="max-w-6xl mx-auto w-full">{children}</div>
      </main>
    </div>
  );
}
