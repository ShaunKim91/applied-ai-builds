import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Result {
  id: string;
  text: string;
  metadata: { label?: string; item_id?: number };
  similarity: number;
}

export default function Search() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[] | null>(null);
  const [backend, setBackend] = useState("");
  const [busy, setBusy] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await api.post<{ results: Result[]; backend: string }>("/api/search", { query, top_k: 8 });
      setResults(res.results);
      setBackend(res.backend);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("search.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("search.subtitle")}</p>
      </div>

      <div className="card p-6">
        <div className="flex gap-3">
          <input
            className="flex-1 px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm"
            placeholder={t("search.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button
            onClick={search}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("search.button")}
          </button>
        </div>
        {backend && <div className="text-xs text-ink-muted mt-2">backend: {backend}</div>}
      </div>

      {results && (
        <div className="space-y-2">
          {results.length === 0 && <div className="text-sm text-ink-muted">{t("search.noResults")}</div>}
          {results.map((r) => (
            <div key={r.id} className="card p-4 flex items-center justify-between">
              <div className="text-sm">{r.text}</div>
              <div className="text-xs text-ink-muted tabular-nums shrink-0 ml-4">
                {(r.similarity * 100).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
