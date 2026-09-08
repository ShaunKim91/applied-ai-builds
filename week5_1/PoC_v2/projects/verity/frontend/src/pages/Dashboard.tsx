import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Skeleton from "../components/Skeleton";
import StatCard from "../components/StatCard";
import { useLang } from "../i18n";

interface Stats {
  total_reports: number;
  by_mode: Record<string, number>;
  ghost_citation_failures: number;
  cat_events: number;
}

export default function Dashboard() {
  const { t } = useLang();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.get<Stats>("/api/research/stats").then(setStats).catch(() => setStats(null));
  }, []);

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("dashboard.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("dashboard.subtitle")}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {stats ? (
          <>
            <StatCard label={t("dashboard.totalReports")} value={stats.total_reports} />
            <StatCard label={t("research.modeBrief")} value={stats.by_mode.precedent_brief ?? 0} />
            <StatCard label={t("dashboard.ghostFailures")} value={stats.ghost_citation_failures} />
            <StatCard label={t("dashboard.catEvents")} value={stats.cat_events} />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height="5.5rem" />)
        )}
      </div>

      <h2 className="font-display font-bold text-lg mt-8 mb-3">{t("dashboard.quickStart")}</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/research" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">🔍</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.research")}
          </div>
        </Link>
        <Link to="/archive" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">📚</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.archive")}
          </div>
        </Link>
        <Link to="/radar" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">📡</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.radar")}
          </div>
        </Link>
      </div>
    </div>
  );
}
