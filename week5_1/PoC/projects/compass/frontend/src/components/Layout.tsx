import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

// A fixed top "command console" bar + a collapsed-by-default, hover-to-expand
// icon rail — the fourth distinct navigation pattern in this series (after
// Week1/11's flush sidebar, Week3's top tabs, Week4's floating glass
// sidebar). The console bar is functional, not decorative: typing a query
// and pressing Enter starts a brand-new research session with that query.
const NAV = [
  { to: "/", key: "nav.dashboard", icon: "◆" },
  { to: "/research", key: "nav.research", icon: "◈" },
  { to: "/archive", key: "nav.archive", icon: "▤" },
  { to: "/grounding-lab", key: "nav.groundingLab", icon: "⬡" },
  { to: "/trend-radar", key: "nav.trendRadar", icon: "◎" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [quickQuery, setQuickQuery] = useState("");
  const [launching, setLaunching] = useState(false);

  const launchQuickResearch = async () => {
    const query = quickQuery.trim();
    if (!query || launching) return;
    setLaunching(true);
    try {
      const s = await api.post<{ id: number }>("/api/research/sessions");
      navigate(`/research?session=${s.id}&q=${encodeURIComponent(query)}`);
      setQuickQuery("");
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="min-h-screen text-ink">
      <header className="fixed top-0 inset-x-0 z-30 h-16 card rounded-none border-x-0 border-t-0 flex items-center gap-4 px-4">
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-2xl">🧭</span>
          <span className="font-display font-semibold text-lg tracking-tight hidden sm:inline">{t("app.name")}</span>
        </div>

        <div className="flex-1 max-w-2xl mx-auto flex items-center gap-2 bg-surface2 rounded-full px-4 py-2 border border-edge">
          <span aria-hidden className="text-ink-muted font-mono text-sm">›</span>
          <input
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && launchQuickResearch()}
            placeholder={t("console.placeholder")}
            className="flex-1 bg-transparent outline-none text-sm font-mono placeholder:text-ink-muted"
          />
          {launching && <span className="radar-ring w-4 h-4 shrink-0" />}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setLang(lang === "en" ? "ko" : "en")}
            className="text-xs px-2.5 py-1.5 rounded-full border border-edge hover:bg-accent-soft"
          >
            {t("common.language")}
          </button>
          <button onClick={toggle} className="text-xs px-2.5 py-1.5 rounded-full border border-edge hover:bg-accent-soft">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          {user && (
            <button
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              className="hidden md:inline text-xs px-2.5 py-1.5 rounded-full border border-edge hover:bg-accent-soft whitespace-nowrap"
            >
              {t("nav.logout")}
            </button>
          )}
        </div>
      </header>

      <aside className="group fixed top-16 bottom-0 left-0 z-20 w-14 hover:w-52 card rounded-none border-y-0 border-l-0 flex flex-col py-4 overflow-hidden transition-standard">
        <nav className="flex-1 space-y-1 px-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap ${
                  isActive ? "bg-accent-gradient text-white" : "text-ink-secondary hover:bg-accent-soft"
                }`
              }
            >
              <span aria-hidden className="text-base leading-none w-5 text-center shrink-0">
                {item.icon}
              </span>
              <span className="opacity-0 group-hover:opacity-100 transition-standard">{t(item.key)}</span>
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap ${
                  isActive ? "bg-accent-gradient text-white" : "text-ink-secondary hover:bg-accent-soft"
                }`
              }
            >
              <span aria-hidden className="text-base leading-none w-5 text-center shrink-0">⚙</span>
              <span className="opacity-0 group-hover:opacity-100 transition-standard">{t("nav.admin")}</span>
            </NavLink>
          )}
        </nav>
        {user && (
          <div className="px-4 pt-3 mt-2 border-t border-edge">
            <span className="text-xs text-ink-muted whitespace-nowrap opacity-0 group-hover:opacity-100 transition-standard">
              {user.display_name}
            </span>
          </div>
        )}
      </aside>

      <main className="pt-16 pl-14 min-h-screen">
        <div className="p-4 md:p-6 max-w-6xl mx-auto w-full">{children}</div>
      </main>
    </div>
  );
}
