import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Source {
  title: string;
  href: string;
  body: string;
  bi_score?: number;
  rerank_score?: number;
}
interface GhostCheck {
  passed: boolean;
  ghost_citations: string[];
}
interface OwnArm {
  text: string;
  sources: Source[];
  search_mode: string;
  latency_ms: number;
  cost_usd: number;
  ghost_citations: GhostCheck;
}
interface Citation {
  url: string;
  title: string;
}
interface OpenRouterArm {
  text: string;
  citations: Citation[];
  latency_ms: number;
  cost_usd: number;
  ghost_citations: GhostCheck;
}
interface CompareResponse {
  own_pipeline: OwnArm;
  openrouter_web_search: OpenRouterArm | null;
  openrouter_error: string | null;
  budget: { daily_limit_usd: number; spent_today_usd: number };
}

export default function GroundingLab() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const compare = async () => {
    if (!query.trim() || busy) return;
    setBusy(true);
    try {
      setResult(await api.post<CompareResponse>("/api/grounding-lab/compare", { query }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{t("groundingLab.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("groundingLab.subtitle")}</p>
      </div>

      <div className="card p-6">
        <div className="flex gap-3">
          <input
            className="flex-1 px-3.5 py-2.5 rounded-lg border border-edge bg-transparent text-sm"
            placeholder={t("groundingLab.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && compare()}
          />
          <button
            onClick={compare}
            disabled={busy}
            className="px-4 py-2.5 rounded-lg bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-card"
          >
            {busy ? <span className="radar-ring w-4 h-4 inline-block" /> : t("groundingLab.compare")}
          </button>
        </div>
        {result && (
          <div className="text-xs text-ink-muted mt-2 font-mono">
            {t("groundingLab.budgetLine")
              .replace("{spent}", result.budget.spent_today_usd.toFixed(4))
              .replace("{limit}", result.budget.daily_limit_usd.toFixed(2))}
          </div>
        )}
      </div>

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-ink-secondary">{t("groundingLab.ownPipeline")}</h3>
              <span className="text-[11px] text-good font-mono">{t("groundingLab.free")}</span>
            </div>
            <p className="text-sm leading-relaxed font-display">{result.own_pipeline.text}</p>
            <div className="mt-3 pt-3 border-t border-edge text-[11px] text-ink-muted font-mono space-y-1">
              <div>{result.own_pipeline.latency_ms.toFixed(0)} ms · search={result.own_pipeline.search_mode}</div>
              {!result.own_pipeline.ghost_citations.passed && (
                <div className="text-critical">
                  ⚠ {t("groundingLab.ghostCount")} {result.own_pipeline.ghost_citations.ghost_citations.length}
                </div>
              )}
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-ink-secondary">{t("groundingLab.openrouterWeb")}</h3>
              {result.openrouter_web_search && (
                <span className="text-[11px] text-warning font-mono">${result.openrouter_web_search.cost_usd.toFixed(3)}</span>
              )}
            </div>
            {result.openrouter_error && <p className="text-sm text-warning">{result.openrouter_error}</p>}
            {result.openrouter_web_search && (
              <>
                <p className="text-sm leading-relaxed font-display">{result.openrouter_web_search.text}</p>
                <div className="mt-3 pt-3 border-t border-edge text-[11px] text-ink-muted font-mono space-y-1">
                  <div>
                    {result.openrouter_web_search.latency_ms.toFixed(0)} ms · {result.openrouter_web_search.citations.length}{" "}
                    {t("groundingLab.citations")}
                  </div>
                  {!result.openrouter_web_search.ghost_citations.passed && (
                    <div className="text-critical">
                      ⚠ {t("groundingLab.ghostCount")} {result.openrouter_web_search.ghost_citations.ghost_citations.length}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
