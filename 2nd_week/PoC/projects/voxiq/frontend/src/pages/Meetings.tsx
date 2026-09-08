import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Sample {
  filename: string;
  label: string;
  source: string;
}
interface Meeting {
  id: number;
  filename: string;
  source: string;
  transcript: string;
  language: string;
  audio_url: string;
  latency_ms: number;
  created_at: string;
}

export default function Meetings() {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ transcript: string; language: string; latency_ms: number } | null>(null);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.get<Meeting[]>("/api/meetings").then(setMeetings).catch(() => {});

  useEffect(() => {
    api.get<{ samples: Sample[] }>("/api/meetings/samples").then((r) => setSamples(r.samples)).catch(() => {});
    refresh();
  }, []);

  const transcribeUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.postForm<{ transcript: string; language: string; latency_ms: number }>(
        "/api/meetings/transcribe",
        form
      );
      setResult(res);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const transcribeSample = async (filename: string) => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<{ transcript: string; language: string; latency_ms: number }>(
        `/api/meetings/transcribe-sample/${filename}`
      );
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
        <h1 className="text-2xl font-semibold">{t("meetings.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("meetings.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept="audio/*" className="text-sm" />
          <button
            onClick={transcribeUpload}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("meetings.upload")}
          </button>
          {busy && <span className="text-sm text-ink-muted">{t("meetings.transcribing")}</span>}
        </div>

        <div>
          <div className="text-sm text-ink-secondary mb-2">{t("meetings.orSamples")}</div>
          <div className="flex flex-wrap gap-2">
            {samples.map((s) => (
              <button
                key={s.filename}
                onClick={() => transcribeSample(s.filename)}
                disabled={busy}
                title={s.source}
                className="px-3 py-2 rounded-lg border border-edge hover:border-accent transition-colors disabled:opacity-60 text-xs text-left max-w-[180px]"
              >
                <div className="truncate font-medium">{s.label}</div>
              </button>
            ))}
          </div>
        </div>

        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="pt-3 border-t border-edge space-y-1.5">
            <div className="text-xs text-ink-muted">
              language: {result.language || "?"} · {result.latency_ms.toFixed(0)} ms
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-line">{result.transcript || "(empty transcript)"}</p>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("meetings.recent")}</h2>
        <div className="space-y-2">
          {meetings.map((m) => (
            <div key={m.id} className="card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-ink-muted">{m.filename}</span>
                <span className="text-[11px] text-ink-muted">
                  {m.language} · {m.latency_ms.toFixed(0)}ms
                </span>
              </div>
              <div className="text-sm truncate">{m.transcript || "(empty transcript)"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
