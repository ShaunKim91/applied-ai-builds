import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface PdfSummary {
  id: number;
  filename: string;
  source: string;
  extracted_chars: number;
  used_scanned_fallback: boolean;
  chunk_count: number;
  chunks_summarized: number;
  summary_text: string;
  provider: string;
  numeric_check_passed: boolean;
  numeric_check_detail: string;
  duplicate_of_id: number | null;
  duplicate_similarity: number | null;
  latency_ms: number;
  created_at: string;
}

export default function Pdfs() {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [useOpenRouter, setUseOpenRouter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PdfSummary | null>(null);
  const [recent, setRecent] = useState<PdfSummary[]>([]);
  const [sampleAvailable, setSampleAvailable] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => api.get<PdfSummary[]>("/api/pdfs").then(setRecent).catch(() => {});

  useEffect(() => {
    api.get<{ available: boolean }>("/api/pdfs/sample").then((r) => setSampleAvailable(r.available)).catch(() => {});
    refresh();
  }, []);

  const summarizeUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.postForm<PdfSummary>(`/api/pdfs/summarize?use_openrouter=${useOpenRouter}`, form);
      setResult(res);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const summarizeSample = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<PdfSummary>("/api/pdfs/summarize-sample", { use_openrouter: useOpenRouter });
      setResult(res);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-display-md">{t("pdfs.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[65ch]">{t("pdfs.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept="application/pdf" className="text-sm" />
          <button
            onClick={summarizeUpload}
            disabled={busy}
            className="px-4 py-2 rounded-full bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("pdfs.upload")}
          </button>
          {sampleAvailable && (
            <button
              onClick={summarizeSample}
              disabled={busy}
              className="px-3 py-1.5 rounded-full border border-edge hover:border-accent transition-colors disabled:opacity-60 text-xs"
            >
              {t("pdfs.orSample")}
            </button>
          )}
          {busy && <span className="text-sm text-ink-muted">{t("pdfs.summarizing")}</span>}
        </div>

        <label className="flex items-center gap-2 text-sm text-ink-secondary">
          <input type="checkbox" checked={useOpenRouter} onChange={(e) => setUseOpenRouter(e.target.checked)} />
          {t("pdfs.useOpenRouter")}
        </label>

        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="pt-4 border-t border-edge space-y-3">
            {result.used_scanned_fallback && (
              <div className="text-xs px-3 py-2 rounded-lg bg-accent-soft text-accent border border-accent/30">
                {t("pdfs.scannedFallbackUsed")}
              </div>
            )}
            {result.chunk_count > result.chunks_summarized && (
              <div className="text-xs px-3 py-2 rounded-lg bg-accent-soft text-accent border border-accent/30">
                {t("pdfs.chunksTruncated")
                  .replace("{summarized}", String(result.chunks_summarized))
                  .replace("{total}", String(result.chunk_count))}
              </div>
            )}
            {result.duplicate_of_id && (
              <div className="text-sm px-3 py-2 rounded-lg bg-warning/10 text-warning border border-warning/30">
                {t("pdfs.duplicateWarning")
                  .replace("{id}", String(result.duplicate_of_id))
                  .replace("{pct}", ((result.duplicate_similarity ?? 0) * 100).toFixed(0))}
              </div>
            )}
            <div>
              <div className="text-xs font-medium text-ink-muted mb-1">
                {t("pdfs.summary")} ({result.provider}, {result.extracted_chars.toLocaleString()} chars extracted)
              </div>
              <p className="text-sm leading-relaxed bg-page rounded-lg p-3 border border-edge">{result.summary_text}</p>
            </div>
            <div
              className={`text-xs px-3 py-2 rounded-lg border ${
                result.numeric_check_passed
                  ? "bg-good/10 text-good border-good/30"
                  : "bg-critical/10 text-critical border-critical/30"
              }`}
            >
              {result.numeric_check_passed
                ? t("pdfs.numericCheckPassed")
                : `${t("pdfs.numericCheckFailed")}: ${result.numeric_check_detail}`}
            </div>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("pdfs.recent")}</h2>
        <div className="space-y-2">
          {recent.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-ink-muted">{r.filename}</span>
                <span className="text-[11px] text-ink-muted">{r.provider}</span>
              </div>
              <div className="text-sm truncate">{r.summary_text || "(no summary)"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
