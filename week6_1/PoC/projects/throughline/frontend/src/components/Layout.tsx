import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useLang } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

const NAV_ITEMS = [
  { to: "/", key: "nav.dashboard", icon: "◆" },
  { to: "/cases", key: "nav.cases", icon: "🗂" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useLang();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col md:flex-row" style={{ background: "var(--page-plane)" }}>
      <aside className="md:w-64 shrink-0 p-4 md:p-6">
        <div className="mb-6">
          <div className="font-display font-bold text-lg" style={{ color: "var(--text-primary)" }}>
            🧵 Throughline
          </div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            Fenwick Mutual
          </div>
        </div>
        <nav className="tab-binder" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => `tab-binder-item ${isActive ? "active" : ""}`}>
              <span className="mr-2">{item.icon}</span>
              {t(item.key)}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/admin" className={({ isActive }) => `tab-binder-item ${isActive ? "active" : ""}`}>
              <span className="mr-2">⚙</span>
              {t("nav.admin")}
            </NavLink>
          )}
        </nav>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="flex items-center justify-between px-4 md:px-6 py-3 border-b" style={{ borderColor: "var(--border-color)", background: "var(--surface-1)" }}>
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {user?.display_name}
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-secondary text-xs px-3 py-1.5" onClick={() => setLang(lang === "en" ? "ko" : "en")} aria-label="Toggle language">
              {lang === "en" ? "한국어" : "EN"}
            </button>
            <button className="btn-secondary text-xs px-3 py-1.5" onClick={toggle} aria-label="Toggle theme">
              {theme === "light" ? "🌙" : "☀️"}
            </button>
            <a href="/api/status" target="_blank" rel="noreferrer" className="btn-secondary text-xs px-3 py-1.5 no-underline">
              {t("nav.status")}
            </a>
            <button
              className="btn-secondary text-xs px-3 py-1.5"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              {t("nav.logout")}
            </button>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-8 max-w-5xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
