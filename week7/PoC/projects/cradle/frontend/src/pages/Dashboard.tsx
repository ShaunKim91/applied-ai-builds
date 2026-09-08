import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { TiltCard } from "../components/TiltCard";
import { useI18n } from "../i18n";

interface Run {
  id: number;
  status: string;
}
interface Ready {
  all_warm: boolean;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [ready, setReady] = useState<Ready | null>(null);

  useEffect(() => {
    api.get<Run[]>("/api/agent/runs").then(setRuns).catch(() => {});
    fetch("/api/health/ready")
      .then((r) => r.json())
      .then(setReady)
      .catch(() => {});
  }, []);

  const completed = runs?.filter((r) => r.status === "COMPLETED").length ?? null;
  const guarded = runs?.filter((r) => r.status.startsWith("BLOCKED") || r.status.startsWith("STOPPED")).length ?? null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label={t("dashboard.runs")} value={runs?.length ?? "…"} />
        <StatCard label={t("dashboard.completed")} value={completed ?? "…"} />
        <StatCard label={t("dashboard.guardrailStops")} value={guarded ?? "…"} hint={t("dashboard.guardrailHint")} />
      </div>

      <div>
        <h2 className="text-sm font-semibold text-ink-secondary mb-3 uppercase tracking-wide font-mono">
          {t("dashboard.quickActions")}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { to: "/console", icon: "◈", label: "nav.console" },
            { to: "/history", icon: "▤", label: "nav.history" },
          ].map((a) => (
            <TiltCard key={a.to} maxDeg={5}>
              <Link to={a.to} className="clay p-6 flex flex-col items-center text-center">
                <div className="text-2xl mb-2">{a.icon}</div>
                <div className="text-sm font-medium">{t(a.label)}</div>
              </Link>
            </TiltCard>
          ))}
        </div>
      </div>

      {!ready?.all_warm && (
        <p className="text-xs text-ink-muted">{t("dashboard.warmingUp")}</p>
      )}
    </div>
  );
}
