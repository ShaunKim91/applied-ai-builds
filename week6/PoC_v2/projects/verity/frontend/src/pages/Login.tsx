import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useLang } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

export default function Login() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { login, signup } = useAuth();
  const { t, lang, setLang } = useLang();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, password, displayName);
      }
      navigate("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "error";
      setError(message.toLowerCase().includes("locked") ? t("auth.locked") : message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4" style={{ background: "var(--page-plane)" }}>
      <div className="absolute top-4 right-4 flex gap-2">
        <button className="btn-secondary text-xs px-3 py-1.5" onClick={() => setLang(lang === "en" ? "ko" : "en")}>
          {lang === "en" ? "한국어" : "EN"}
        </button>
        <button className="btn-secondary text-xs px-3 py-1.5" onClick={toggle}>
          {theme === "light" ? "🌙" : "☀️"}
        </button>
      </div>
      <Link to="/" className="mb-6 font-display font-bold text-2xl no-underline" style={{ color: "var(--text-primary)" }}>
        📗 Verity
      </Link>
      <form onSubmit={submit} className="card p-8 w-full max-w-sm">
        <h1 className="font-display font-bold text-xl mb-4">{mode === "login" ? t("auth.login") : t("auth.signup")}</h1>
        {mode === "signup" && (
          <div className="mb-3">
            <label className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
              {t("auth.displayName")}
            </label>
            <input
              className="w-full mt-1 px-3 py-2 rounded-ledger-sm border"
              style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
        )}
        <div className="mb-3">
          <label className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
            {t("auth.email")}
          </label>
          <input
            type="email"
            required
            className="w-full mt-1 px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="mb-4">
          <label className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
            {t("auth.password")}
          </label>
          <input
            type="password"
            required
            minLength={8}
            className="w-full mt-1 px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && (
          <div className="mb-3 text-sm" style={{ color: "var(--critical)" }}>
            {error}
          </div>
        )}
        <button type="submit" disabled={busy} className="btn-primary w-full py-2.5">
          {t("auth.submit")}
        </button>
        <button
          type="button"
          className="w-full mt-3 text-sm underline"
          style={{ color: "var(--accent-2)" }}
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? t("auth.switchToSignup") : t("auth.switchToLogin")}
        </button>
        <p className="mt-4 text-xs text-center" style={{ color: "var(--text-muted)" }}>
          {t("auth.demoNote")}
        </p>
      </form>
    </div>
  );
}
