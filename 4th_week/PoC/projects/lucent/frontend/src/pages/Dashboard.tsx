import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface Doc {
  id: number;
  language: string;
}
interface ChatSession {
  id: number;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [documents, setDocuments] = useState<Doc[] | null>(null);
  const [sessions, setSessions] = useState<ChatSession[] | null>(null);

  useEffect(() => {
    api.get<Doc[]>("/api/documents").then(setDocuments).catch(() => {});
    api.get<ChatSession[]>("/api/chat/sessions").then(setSessions).catch(() => {});
  }, []);

  const languages = documents ? new Set(documents.map((d) => d.language)).size : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label={t("dashboard.documents")} value={documents?.length ?? "…"} />
        <StatCard label={t("dashboard.languages")} value={languages ?? "…"} hint={t("dashboard.languagesHint")} />
        <StatCard label={t("dashboard.chatSessions")} value={sessions?.length ?? "…"} />
      </div>

      <div>
        <h2 className="text-sm font-semibold text-ink-secondary mb-3">{t("dashboard.quickActions")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { to: "/chat", icon: "◈", label: "nav.chat" },
            { to: "/documents", icon: "▤", label: "nav.documents" },
            { to: "/retrieval-lab", icon: "⬡", label: "nav.retrievalLab" },
          ].map((a) => (
            <Link key={a.to} to={a.to} className="card p-6 hover:shadow-glass-lg transition-shadow text-center">
              <div className="text-2xl mb-2">{a.icon}</div>
              <div className="text-sm font-medium">{t(a.label)}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
