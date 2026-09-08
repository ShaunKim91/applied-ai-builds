import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface HistoryHit {
  run_id: number;
  question: string;
  final_answer_excerpt: string;
  similarity: number;
  created_at: string;
}

export default function History() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<HistoryHit[] | null>(null);
  const [busy, setBusy] = useState(false);

  const search = async () => {
    if (!query.trim() || busy) return;
    setBusy(true);
    try {
      setResults(await api.post<HistoryHit[]>("/api/history/search", { query, top_k: 8 }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">{t("history.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("history.subtitle")}</p>
      </div>

      <div className="clay p-6">
        <div className="flex gap-3">
          <input
            className="flex-1 px-4 py-2.5 rounded-full clay-inset bg-transparent text-sm outline-none"
            placeholder={t("history.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button onClick={search} disabled={busy} className="px-5 py-2.5 rounded-full bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-clay-sm">
            {t("history.search")}
          </button>
        </div>
      </div>

      {results && (
        <div className="space-y-3">
          {results.length === 0 && <p className="text-sm text-ink-muted">{t("history.noResults")}</p>}
          {results.map((r) => (
            <button
              key={r.run_id}
              onClick={() => navigate("/console")}
              className="clay-sm p-4 w-full text-left hover:shadow-clay transition-shadow"
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-sm font-medium truncate">{r.question}</span>
                <span className="text-[11px] text-ink-muted font-mono shrink-0">{(r.similarity * 100).toFixed(1)}%</span>
              </div>
              <p className="text-xs text-ink-secondary line-clamp-2">{r.final_answer_excerpt}</p>
              <div className="text-[10px] text-ink-muted mt-1 font-mono">{new Date(r.created_at).toLocaleString()}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
