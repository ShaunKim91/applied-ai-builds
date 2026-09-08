import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface ResultItem {
  id: string;
  text: string;
  metadata: { source?: string; date?: string; filename?: string };
  similarity?: number;
  rerank_score?: number;
}
interface SearchResponse {
  bi_encoder_results: ResultItem[];
  cross_encoder_results: ResultItem[];
  top1_changed: boolean;
  backend: string;
  latency_ms: number;
}

function sourceLabel(meta: ResultItem["metadata"]): string {
  if (meta?.source === "fomc") return `FOMC minutes (${meta.date})`;
  if (meta?.source === "meeting") return `Meeting: ${meta.filename}`;
  return "document";
}

export default function Search() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await api.post<SearchResponse>("/api/search", { query, top_k: 5 });
      setResult(res);
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
        {result && (
          <div className="text-xs text-ink-muted mt-2 flex items-center gap-2">
            <span>backend: {result.backend}</span>
            <span>·</span>
            <span>{result.latency_ms.toFixed(0)} ms</span>
            <span>·</span>
            <span className={result.top1_changed ? "text-warning font-medium" : "text-good"}>
              {result.top1_changed ? t("search.top1Changed") : t("search.top1Same")}
            </span>
          </div>
        )}
      </div>

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-medium text-ink-secondary mb-2">{t("search.biEncoder")}</h3>
            <div className="space-y-2">
              {result.bi_encoder_results.map((r, i) => (
                <div key={r.id} className={`card p-3 ${i === 0 ? "border-accent" : ""}`}>
                  <div className="text-[11px] text-ink-muted mb-1">{sourceLabel(r.metadata)}</div>
                  <div className="text-sm line-clamp-3">{r.text}</div>
                  <div className="text-[11px] text-ink-muted mt-1 tabular-nums">
                    similarity {((r.similarity ?? 0) * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium text-ink-secondary mb-2">{t("search.crossEncoder")}</h3>
            <div className="space-y-2">
              {result.cross_encoder_results.map((r, i) => (
                <div key={r.id} className={`card p-3 ${i === 0 ? "border-accent" : ""}`}>
                  <div className="text-[11px] text-ink-muted mb-1">{sourceLabel(r.metadata)}</div>
                  <div className="text-sm line-clamp-3">{r.text}</div>
                  <div className="text-[11px] text-ink-muted mt-1 tabular-nums">
                    rerank score {(r.rerank_score ?? 0).toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
