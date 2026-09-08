import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import StatCard from "../components/StatCard";
import { useLang } from "../i18n";

interface Analytics {
  total_runs: number;
  completed: number;
  guardrail_stops: number;
  pending_approvals: number;
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
      .catch(() => setStats({ total_runs: 0, completed: 0, guardrail_stops: 0, pending_approvals: 0 }));
  }, []);

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("dashboard.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("dashboard.subtitle")}</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <StatCard label={t("dashboard.totalRuns")} value={stats?.total_runs ?? "—"} />
        <StatCard label={t("dashboard.completed")} value={stats?.completed ?? "—"} />
        <StatCard label={t("dashboard.guardrailStops")} value={stats?.guardrail_stops ?? "—"} />
        <StatCard label={t("dashboard.pendingApprovals")} value={stats?.pending_approvals ?? "—"} />
      </div>

      <h2 className="font-display font-bold text-lg mt-8 mb-3">{t("dashboard.quickStart")}</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/console" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">🛡️</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.console")}
          </div>
        </Link>
        <Link to="/approvals" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">✓</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.approvals")}
          </div>
        </Link>
        <Link to="/history" className="card p-5 no-underline block hover:shadow-ledger-lift transition-shadow">
          <div className="text-2xl mb-2">📜</div>
          <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {t("nav.history")}
          </div>
        </Link>
      </div>
    </div>
  );
}
