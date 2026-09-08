import React, { useState } from "react";

import { api } from "../api/client";
import { ForecastChart } from "../components/ForecastChart";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface ForecastResult {
  history: { date: string; value: number }[];
  forecast: { date: string; value: number; lower: number; upper: number }[];
  anomalies: { date: string; value: number; residual: number }[];
  metrics: { mae: number | null; mape: number | null; smape: number | null; mape_note: string | null };
  params: { alpha: number; beta: number; gamma: number };
  ai_insight: string;
  insight_provider: string;
}

export default function Forecasting() {
  const { t, lang } = useI18n();
  const [horizon, setHorizon] = useState(14);
  const [useOpenRouter, setUseOpenRouter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<ForecastResult>("/api/forecast/run", {
        horizon_days: horizon,
        use_openrouter: useOpenRouter,
        lang,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("forecast.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("forecast.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <label className="text-sm text-ink-secondary block mb-1.5">
              {t("forecast.horizon")}: {horizon}
            </label>
            <input type="range" min={7} max={60} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} />
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-secondary">
            <input type="checkbox" checked={useOpenRouter} onChange={(e) => setUseOpenRouter(e.target.checked)} />
            {t("forecast.useOpenRouter")}
          </label>
          <button
            onClick={run}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("forecast.run")}
          </button>
        </div>
        {error && <div className="text-sm text-critical">{error}</div>}
      </div>

      {result && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <StatCard label={t("forecast.mae")} value={result.metrics.mae ?? "—"} />
            <StatCard
              label={t("forecast.mape")}
              value={result.metrics.mape !== null ? `${result.metrics.mape}%` : "n/a"}
              hint={result.metrics.mape_note ?? undefined}
            />
            <StatCard
              label="sMAPE"
              value={result.metrics.smape !== null ? `${result.metrics.smape}%` : "—"}
              hint="symmetric, bounded 0-200%"
            />
            <StatCard label={t("forecast.anomalies")} value={result.anomalies.length} />
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium text-ink-secondary mb-4">{t("forecast.chartTitle")}</h2>
            <ForecastChart history={result.history} forecast={result.forecast} anomalies={result.anomalies} />
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium text-ink-secondary mb-2">
              {t("forecast.insight")} <span className="text-ink-muted">({result.insight_provider})</span>
            </h2>
            <p className="text-sm leading-relaxed whitespace-pre-line">{result.ai_insight}</p>
          </div>
        </>
      )}
    </div>
  );
}
