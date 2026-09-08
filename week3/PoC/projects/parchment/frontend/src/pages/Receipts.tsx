import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Sample {
  filename: string;
  label: string;
}
interface StructuredItem {
  name: string;
  price: number;
}
interface Structured {
  vendor?: string | null;
  items?: StructuredItem[];
  total?: number | null;
}
interface Receipt {
  id: number;
  filename: string;
  source: string;
  is_synthetic: boolean;
  image_url: string;
  ocr_text: string;
  ocr_structured: Structured | null;
  ocr_latency_ms: number;
  vlm_answer: string;
  vlm_latency_ms: number;
  duplicate_of_id: number | null;
  duplicate_similarity: number | null;
  created_at: string;
}

export default function Receipts() {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Receipt | null>(null);
  const [recent, setRecent] = useState<Receipt[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.get<Receipt[]>("/api/receipts").then(setRecent).catch(() => {});

  useEffect(() => {
    api.get<{ samples: Sample[] }>("/api/receipts/samples").then((r) => setSamples(r.samples)).catch(() => {});
    refresh();
  }, []);

  const extractUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.postForm<Receipt>("/api/receipts/extract", form);
      setResult(res);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const extractSample = async (filename: string) => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<Receipt>(`/api/receipts/extract-sample/${filename}`);
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
        <h1 className="text-display-md">{t("receipts.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[65ch]">{t("receipts.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept="image/*" className="text-sm" />
          <button
            onClick={extractUpload}
            disabled={busy}
            className="px-4 py-2 rounded-full bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("receipts.upload")}
          </button>
          {busy && <span className="text-sm text-ink-muted">{t("receipts.processing")}</span>}
        </div>

        <div>
          <div className="text-sm text-ink-secondary mb-2">{t("receipts.orSamples")}</div>
          <div className="flex flex-wrap gap-2">
            {samples.map((s) => (
              <button
                key={s.filename}
                onClick={() => extractSample(s.filename)}
                disabled={busy}
                className="px-3 py-1.5 rounded-full border border-edge hover:border-accent transition-colors disabled:opacity-60 text-xs"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="pt-4 border-t border-edge space-y-4">
            {result.duplicate_of_id && (
              <div className="text-sm px-3 py-2 rounded-lg bg-warning/10 text-warning border border-warning/30">
                {t("receipts.duplicateWarning")
                  .replace("{id}", String(result.duplicate_of_id))
                  .replace("{pct}", ((result.duplicate_similarity ?? 0) * 100).toFixed(0))}
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium text-ink-secondary mb-2">
                  {t("receipts.ocrPath")} · {result.ocr_latency_ms.toFixed(0)}ms
                </h3>
                <div className="space-y-2">
                  <pre className="text-xs bg-page rounded-lg p-3 overflow-x-auto border border-edge whitespace-pre-wrap">
                    {result.ocr_text || "(no text found)"}
                  </pre>
                  {result.ocr_structured && (
                    <pre className="text-xs bg-page rounded-lg p-3 overflow-x-auto border border-edge">
                      {JSON.stringify(result.ocr_structured, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-ink-secondary mb-2">
                  {t("receipts.vlmPath")} · {result.vlm_latency_ms.toFixed(0)}ms
                </h3>
                <p className="text-sm leading-relaxed bg-page rounded-lg p-3 border border-edge">{result.vlm_answer}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("receipts.recent")}</h2>
        <div className="space-y-2">
          {recent.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-ink-muted">{r.filename}</span>
                <span className="text-[11px] text-ink-muted">
                  {r.duplicate_of_id ? `⚠ ${t("receipts.duplicateShort")}` : ""}
                </span>
              </div>
              <div className="text-sm truncate">{r.ocr_text || "(no text found)"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
