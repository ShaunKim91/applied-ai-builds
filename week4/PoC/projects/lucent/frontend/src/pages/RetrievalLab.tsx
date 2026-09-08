import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface ResultItem {
  id: string;
  text: string;
  metadata: { title?: string; language?: string };
  similarity?: number;
  rerank_score?: number;
}
interface CompareResponse {
  bi_results: ResultItem[];
  cross_results: ResultItem[];
  top1_changed: boolean;
  latency_ms: number;
}

export default function RetrievalLab() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const compare = async () => {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await api.post<CompareResponse>("/api/retrieval/compare", { query });
      setResult(res);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">{t("retrievalLab.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("retrievalLab.subtitle")}</p>
      </div>

      <div className="card p-6">
        <div className="flex gap-3">
          <input
            className="flex-1 px-3.5 py-2.5 rounded-xl border border-edge bg-transparent text-sm"
            placeholder={t("retrievalLab.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && compare()}
          />
          <button
            onClick={compare}
            disabled={busy}
            className="px-4 py-2.5 rounded-xl bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-glass"
          >
            {t("retrievalLab.compare")}
          </button>
        </div>
        {result && (
          <div className="text-xs text-ink-muted mt-2 flex items-center gap-2">
            <span>{result.latency_ms.toFixed(0)} ms</span>
            <span>·</span>
            <span className={result.top1_changed ? "text-warning font-medium" : "text-good"}>
              {result.top1_changed ? t("retrievalLab.top1Changed") : t("retrievalLab.top1Same")}
            </span>
          </div>
        )}
      </div>

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-semibold text-ink-secondary mb-2">{t("retrievalLab.biEncoder")}</h3>
            <div className="space-y-2">
              {result.bi_results.map((r, i) => (
                <div key={r.id} className={`card p-3 ${i === 0 ? "border-accent" : ""}`}>
                  <div className="text-[11px] text-ink-muted mb-1">{r.metadata.title}</div>
                  <div className="text-sm line-clamp-3">{r.text}</div>
                  <div className="text-[11px] text-ink-muted mt-1 tabular-nums">
                    similarity {((r.similarity ?? 0) * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink-secondary mb-2">{t("retrievalLab.crossEncoder")}</h3>
            <div className="space-y-2">
              {result.cross_results.map((r, i) => (
                <div key={r.id} className={`card p-3 ${i === 0 ? "border-accent" : ""}`}>
                  <div className="text-[11px] text-ink-muted mb-1">{r.metadata.title}</div>
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
