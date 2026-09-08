import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import StatCard from "../components/StatCard";
import { useLang } from "../i18n";

interface Analytics {
  total_cases: number;
  open_cases: number;
  total_turns: number;
  pending_conflicts: number;
}

export default function Dashboard() {
  const { t } = useLang();
  const [stats, setStats] = useState<Analytics | null>(null);

  useEffect(() => {
    // Regular users can't hit /api/admin/analytics — fall back to a zeroed
    // view for non-admins rather than erroring the whole dashboard.
    api
      .get<Analytics>("/api/admin/analytics")
      .then(setStats)
      .catch(() => setStats({ total_cases: 0, open_cases: 0, total_turns: 0, pending_conflicts: 0 }));
  }, []);

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("dashboard.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("dashboard.subtitle")}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <StatCard label={t("dashboard.totalCases")} value={stats?.total_cases ?? "—"} />
        <StatCard label={t("dashboard.openCases")} value={stats?.open_cases ?? "—"} />
        <StatCard label={t("dashboard.totalTurns")} value={stats?.total_turns ?? "—"} />
        <StatCard label={t("dashboard.pendingConflicts")} value={stats?.pending_conflicts ?? "—"} />
      </div>

      <h2 className="font-display font-bold text-lg mt-8 mb-3">{t("dashboard.quickStart")}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link to="/cases" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">🗂</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.cases")}
          </div>
          <div className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {t("dashboard.casesHint")}
          </div>
        </Link>
        <Link to="/cases" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">🧵</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("dashboard.newCase")}
          </div>
          <div className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {t("dashboard.newCaseHint")}
          </div>
        </Link>
      </div>
    </div>
  );
}
