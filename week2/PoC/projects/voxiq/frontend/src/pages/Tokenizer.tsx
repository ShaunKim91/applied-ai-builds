import React, { useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface ExploreResult {
  tokens: string[];
  token_ids: number[];
  token_count: number;
  attention: number[][];
  attention_tokens: string[];
  layer: number;
  num_layers: number;
  truncated: boolean;
}

const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];

export default function Tokenizer() {
  const { t } = useI18n();
  const [text, setText] = useState("Self-attention connects every token to every other token.");
  const [result, setResult] = useState<ExploreResult | null>(null);
  const [busy, setBusy] = useState(false);

  const explore = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const res = await api.post<ExploreResult>("/api/tokenizer/explore", { text });
      setResult(res);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("tokenizer.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("tokenizer.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <textarea
          className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm min-h-[64px]"
          placeholder={t("tokenizer.placeholder")}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          onClick={explore}
          disabled={busy}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
        >
          {t("tokenizer.button")}
        </button>
      </div>

      {result && (
        <>
          <div className="card p-6">
            <h2 className="text-sm font-medium text-ink-secondary mb-3">
              {result.token_count} {t("tokenizer.tokenCount")}
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {result.tokens.map((tok, i) => (
                <span
                  key={i}
                  className="px-2 py-1 rounded-md text-xs font-mono border"
                  style={{
                    backgroundColor: `${PALETTE[i % PALETTE.length]}22`,
                    borderColor: `${PALETTE[i % PALETTE.length]}66`,
                  }}
                  title={`id ${result.token_ids[i]}`}
                >
                  {tok.replace(/ /g, "·") || "∅"}
                </span>
              ))}
            </div>
          </div>

          <div className="card p-6">
            <h2 className="text-sm font-medium text-ink-secondary mb-4">
              {t("tokenizer.attentionHeatmap").replace("{layer}", String(result.layer + 1)).replace("{total}", String(result.num_layers))}
            </h2>
            {result.truncated && (
              <p className="text-xs text-warning mb-3">Input truncated to the first 40 tokens for the heatmap.</p>
            )}
            <div className="overflow-x-auto">
              <div
                className="inline-grid gap-[1px] bg-edge"
                style={{ gridTemplateColumns: `100px repeat(${result.attention_tokens.length}, 28px)` }}
              >
                <div />
                {result.attention_tokens.map((tok, j) => (
                  <div key={`h-${j}`} className="w-7 h-7 flex items-center justify-center text-[9px] bg-surface text-ink-muted overflow-hidden">
                    {tok.trim().slice(0, 3)}
                  </div>
                ))}
                {result.attention.map((row, i) => (
                  <React.Fragment key={`row-${i}`}>
                    <div className="text-[10px] px-1.5 flex items-center bg-surface text-ink-secondary truncate">
                      {result.attention_tokens[i].trim() || "∅"}
                    </div>
                    {row.map((val, j) => (
                      <div
                        key={`cell-${i}-${j}`}
                        className="w-7 h-7"
                        title={`${result.attention_tokens[i]} → ${result.attention_tokens[j]}: ${val.toFixed(3)}`}
                        style={{ backgroundColor: `var(--accent)`, opacity: Math.max(val, 0.04) }}
                      />
                    ))}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
