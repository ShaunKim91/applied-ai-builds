import { Link } from "react-router-dom";
import { useLang } from "../i18n";
import { useTheme } from "../theme/ThemeContext";

const FEATURES = ["feature1", "feature2", "feature3", "feature4"];

export default function Landing() {
  const { t, lang, setLang } = useLang();
  const { theme, toggle } = useTheme();

  return (
    <div style={{ background: "var(--page-plane)", minHeight: "100vh" }}>
      <header className="flex items-center justify-between px-6 py-4 max-w-5xl mx-auto">
        <div className="font-display font-bold text-lg">📗 Verity</div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary text-xs px-3 py-1.5" onClick={() => setLang(lang === "en" ? "ko" : "en")}>
            {lang === "en" ? "한국어" : "EN"}
          </button>
          <button className="btn-secondary text-xs px-3 py-1.5" onClick={toggle}>
            {theme === "light" ? "🌙" : "☀️"}
          </button>
          <Link to="/login" className="btn-secondary text-sm px-4 py-1.5 no-underline">
            {t("landing.cta.login")}
          </Link>
        </div>
      </header>

      <section className="max-w-3xl mx-auto text-center px-6 pt-16 pb-12">
        <p className="text-xs uppercase tracking-widest font-mono" style={{ color: "var(--accent-2)" }}>
          {t("landing.eyebrow")}
        </p>
        <h1 className="font-display font-bold text-5xl md:text-6xl mt-3" style={{ color: "var(--text-primary)" }}>
          {t("landing.title")}
        </h1>
        <p className="text-xl mt-4 font-display" style={{ color: "var(--text-secondary)" }}>
          {t("landing.tagline")}
        </p>
        <p className="mt-6 max-w-xl mx-auto" style={{ color: "var(--text-secondary)" }}>
          {t("landing.persona")}
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/signup" className="btn-primary px-6 py-3 no-underline">
            {t("landing.cta.signup")}
          </Link>
          <Link to="/login" className="btn-secondary px-6 py-3 no-underline">
            {t("landing.cta.login")}
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-16 grid grid-cols-1 md:grid-cols-2 gap-5">
        {FEATURES.map((f) => (
          <div key={f} className="card p-6">
            <h3 className="font-display font-bold text-lg mb-1">{t(`landing.${f}.title`)}</h3>
            <p style={{ color: "var(--text-secondary)" }}>{t(`landing.${f}.body`)}</p>
          </div>
        ))}
      </section>

      <footer className="max-w-3xl mx-auto px-6 pb-16 text-center text-xs" style={{ color: "var(--text-muted)" }}>
        {t("landing.disclaimer")}
      </footer>
    </div>
  );
}
