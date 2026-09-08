import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Prediction {
  label: string;
  confidence: number;
}
interface Sample {
  filename: string;
  url: string;
}
interface CatalogItem {
  id: number;
  filename: string;
  label: string;
  confidence: number;
  source: string;
  image_url: string;
  top5: Prediction[];
  created_at: string;
}

export default function CatalogVision() {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ image_url: string; predictions: Prediction[]; latency_ms: number } | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [error, setError] = useState("");

  const refreshCatalog = () => api.get<CatalogItem[]>("/api/vision/catalog").then(setCatalog).catch(() => {});

  useEffect(() => {
    api.get<{ samples: Sample[] }>("/api/vision/samples").then((r) => setSamples(r.samples)).catch(() => {});
    refreshCatalog();
  }, []);

  const classifyUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.postForm<{ image_url: string; predictions: Prediction[]; latency_ms: number }>(
        "/api/vision/classify",
        form
      );
      setResult(res);
      refreshCatalog();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const classifySample = async (filename: string) => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ image_url: string; predictions: Prediction[]; latency_ms: number }>(
        `/api/vision/classify-sample/${filename}`
      );
      setResult(res);
      refreshCatalog();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("vision.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("vision.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept="image/*" className="text-sm" />
          <button
            onClick={classifyUpload}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("vision.upload")}
          </button>
          {busy && <span className="text-sm text-ink-muted">{t("vision.classifying")}</span>}
        </div>

        <div>
          <div className="text-sm text-ink-secondary mb-2">{t("vision.orSamples")}</div>
          <div className="flex flex-wrap gap-2">
            {samples.map((s) => (
              <button
                key={s.filename}
                onClick={() => classifySample(s.filename)}
                disabled={busy}
                className="rounded-lg overflow-hidden border border-edge hover:border-accent transition-colors disabled:opacity-60"
                title={s.filename}
              >
                <img src={s.url} alt={s.filename} className="w-16 h-16 object-cover" />
              </button>
            ))}
          </div>
        </div>

        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="flex flex-col sm:flex-row gap-4 pt-2 border-t border-edge">
            <img src={result.image_url} alt="classified" className="w-32 h-32 object-cover rounded-lg" />
            <div className="flex-1 space-y-1.5">
              {result.predictions.map((p, idx) => (
                <div key={p.label} className="flex items-center gap-3">
                  <span className="text-sm w-40 truncate">{p.label}</span>
                  <div className="flex-1 h-2 bg-grid rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full"
                      style={{ width: `${p.confidence * 100}%`, opacity: idx === 0 ? 1 : 0.5 }}
                    />
                  </div>
                  <span className="text-xs text-ink-muted w-12 text-right tabular-nums">
                    {(p.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
              <div className="text-xs text-ink-muted pt-1">{result.latency_ms.toFixed(0)} ms</div>
            </div>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("vision.recent")}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {catalog.map((item) => (
            <div key={item.id} className="card overflow-hidden">
              <img src={item.image_url} alt={item.label} className="w-full h-28 object-cover" />
              <div className="p-2.5">
                <div className="text-xs font-medium truncate">{item.label}</div>
                <div className="text-[11px] text-ink-muted">
                  {(item.confidence * 100).toFixed(0)}% {t("vision.confidence")}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
