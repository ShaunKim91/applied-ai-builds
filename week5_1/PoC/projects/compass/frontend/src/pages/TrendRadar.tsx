import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Lens {
  level: string;
  note: string;
}
interface Radar {
  cost: Lens;
  security: Lens;
  approval: Lens;
}
interface RadarResponse {
  entry_id: number;
  topic: string;
  radar: Radar | null;
  extraction_failed: boolean;
  raw_text: string;
  search_mode: string;
  latency_ms: number;
}

const LEVEL_COLOR: Record<string, string> = {
  Low: "text-good",
  Medium: "text-warning",
  High: "text-critical",
  "Insufficient evidence": "text-ink-muted",
};

export default function TrendRadar() {
  const { t } = useI18n();
  const [topic, setTopic] = useState("");
  const [result, setResult] = useState<RadarResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const evaluate = async () => {
    if (!topic.trim() || busy) return;
    setBusy(true);
    try {
      setResult(await api.post<RadarResponse>("/api/trend-radar/evaluate", { topic }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{t("trendRadar.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("trendRadar.subtitle")}</p>
      </div>

      <div className="card p-6">
        <div className="flex gap-3">
          <input
            className="flex-1 px-3.5 py-2.5 rounded-lg border border-edge bg-transparent text-sm"
            placeholder={t("trendRadar.placeholder")}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && evaluate()}
          />
          <button
            onClick={evaluate}
            disabled={busy}
            className="px-4 py-2.5 rounded-lg bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-card"
          >
            {busy ? <span className="radar-ring w-4 h-4 inline-block" /> : t("trendRadar.evaluate")}
          </button>
        </div>
      </div>

      {result && result.extraction_failed && (
        <div className="card p-5 border-warning">
          <p className="text-sm text-warning">{t("trendRadar.extractionFailed")}</p>
          <p className="text-xs text-ink-muted mt-2 whitespace-pre-wrap font-mono">{result.raw_text}</p>
        </div>
      )}

      {result && result.radar && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(["cost", "security", "approval"] as const).map((lens) => (
            <div key={lens} className="card p-5">
              <h3 className="text-xs font-semibold text-ink-secondary uppercase tracking-wide font-mono mb-2">
                {t(`trendRadar.lens.${lens}`)}
              </h3>
              <div className={`text-2xl font-display font-semibold ${LEVEL_COLOR[result.radar![lens].level] ?? "text-ink"}`}>
                {result.radar![lens].level}
              </div>
              <p className="text-xs text-ink-secondary mt-2">{result.radar![lens].note}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
