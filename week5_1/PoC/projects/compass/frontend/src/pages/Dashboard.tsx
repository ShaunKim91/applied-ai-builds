import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface Session {
  id: number;
}
interface Ready {
  web_search: { mode: "ddgs" | "mock"; ok: boolean } | null;
  all_warm: boolean;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [ready, setReady] = useState<Ready | null>(null);

  useEffect(() => {
    api.get<Session[]>("/api/research/sessions").then(setSessions).catch(() => {});
    fetch("/api/health/ready")
      .then((r) => r.json())
      .then(setReady)
      .catch(() => {});
  }, []);

  const searchMode = ready?.web_search?.mode;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label={t("dashboard.sessions")} value={sessions?.length ?? "…"} />
        <StatCard
          label={t("dashboard.searchMode")}
          value={searchMode ? (searchMode === "ddgs" ? t("dashboard.searchLive") : t("dashboard.searchMock")) : "…"}
          hint={searchMode === "mock" ? t("dashboard.searchMockHint") : t("dashboard.searchModeHint")}
        />
        <StatCard label={t("dashboard.modelsWarm")} value={ready ? (ready.all_warm ? "✓" : "…") : "…"} />
      </div>

      <div>
        <h2 className="text-sm font-semibold text-ink-secondary mb-3 uppercase tracking-wide font-mono">
          {t("dashboard.quickActions")}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { to: "/research", icon: "◈", label: "nav.research" },
            { to: "/archive", icon: "▤", label: "nav.archive" },
            { to: "/grounding-lab", icon: "⬡", label: "nav.groundingLab" },
            { to: "/trend-radar", icon: "◎", label: "nav.trendRadar" },
          ].map((a) => (
            <Link key={a.to} to={a.to} className="card p-6 hover:shadow-card-lg transition-standard text-center">
              <div className="text-2xl mb-2">{a.icon}</div>
              <div className="text-sm font-medium">{t(a.label)}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
