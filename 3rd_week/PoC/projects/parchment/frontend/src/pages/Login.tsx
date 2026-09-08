import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useI18n } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

export default function Login() {
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const { user, login, signup } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("admin@parchment.local");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup(email, password, displayName);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-page text-ink px-4">
      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={() => setLang(lang === "en" ? "ko" : "en")}
          className="text-sm px-3 py-1.5 rounded-full border border-edge hover:bg-accent-soft"
        >
          {t("common.language")}
        </button>
        <button onClick={toggle} className="text-sm px-3 py-1.5 rounded-full border border-edge hover:bg-accent-soft">
          {theme === "dark" ? "☀️" : "🌙"}
        </button>
      </div>

      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">📜</div>
          <h1 className="font-serif text-display-md">{t("app.name")}</h1>
          <p className="text-sm text-ink-secondary mt-1">{t("app.tagline")}</p>
        </div>

        <div className="card p-6">
          <div className="flex mb-6 rounded-full border border-edge overflow-hidden text-sm">
            <button
              className={`flex-1 py-2 ${mode === "login" ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary"}`}
              onClick={() => setMode("login")}
            >
              {t("auth.login")}
            </button>
            <button
              className={`flex-1 py-2 ${mode === "signup" ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary"}`}
              onClick={() => setMode("signup")}
            >
              {t("auth.signup")}
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "signup" && (
              <input
                className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm"
                placeholder={t("auth.displayName")}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            )}
            <input
              type="email"
              required
              className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm"
              placeholder={t("auth.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              type="password"
              required
              minLength={6}
              className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm"
              placeholder={t("auth.password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <div className="text-sm text-critical">{error}</div>}
            <button
              type="submit"
              disabled={busy}
              className="w-full py-2.5 rounded-full bg-accent text-white text-sm font-medium disabled:opacity-60"
            >
              {mode === "login" ? t("auth.login") : t("auth.signup")}
            </button>
          </form>
        </div>
        <p className="text-xs text-ink-muted text-center mt-4">{t("auth.demoHint")}</p>
      </div>
    </div>
  );
}
