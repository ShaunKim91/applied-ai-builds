import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface Meeting {
  id: number;
  filename: string;
  transcript: string;
  source: string;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [searchBackend, setSearchBackend] = useState<string>("…");
  const [sandboxRunCount, setSandboxRunCount] = useState<number | null>(null);
  const [searchCount, setSearchCount] = useState<number | null>(null);

  useEffect(() => {
    api.get<Meeting[]>("/api/meetings").then(setMeetings).catch(() => {});
    api.get<{ backend: string }>("/api/search/status").then((s) => setSearchBackend(s.backend)).catch(() => {});
    api.get<unknown[]>("/api/sandbox/runs").then((r) => setSandboxRunCount(r.length)).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t("dashboard.meetings")} value={meetings.length} />
        <StatCard label={t("dashboard.sandboxRuns")} value={sandboxRunCount ?? "…"} />
        <StatCard label={t("dashboard.vectorBackend")} value={searchBackend} />
        <StatCard label="FOMC + audio corpus" value="7 minutes · 6 clips" />
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("dashboard.quickActions")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { to: "/meetings", icon: "🎙️", label: "nav.meetings" },
            { to: "/search", icon: "🔎", label: "nav.search" },
            { to: "/sandbox", icon: "🧮", label: "nav.sandbox" },
            { to: "/tokenizer", icon: "🔤", label: "nav.tokenizer" },
          ].map((a) => (
            <Link key={a.to} to={a.to} className="card p-5 hover:border-accent transition-colors text-center">
              <div className="text-2xl mb-2">{a.icon}</div>
              <div className="text-sm font-medium">{t(a.label)}</div>
            </Link>
          ))}
        </div>
      </div>

      {meetings.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("meetings.recent")}</h2>
          <div className="space-y-2">
            {meetings.slice(0, 5).map((m) => (
              <div key={m.id} className="card p-4">
                <div className="text-xs font-medium text-ink-muted mb-1">{m.filename}</div>
                <div className="text-sm truncate">{m.transcript || "(empty transcript)"}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
