import React, { useEffect, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface AnalyzeResult {
  generated_code: string;
  stdout: string;
  stderr: string;
  exit_code: number;
  timed_out: boolean;
  provider: string;
}
interface RunHistory {
  id: number;
  request_text: string;
  provider: string;
  status: string;
  generated_code: string;
  stdout: string;
  created_at: string;
}

export default function Sandbox() {
  const { t } = useI18n();
  const [request, setRequest] = useState("How many meetings are there, and what is the average transcript length in words?");
  const [useOpenRouter, setUseOpenRouter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [history, setHistory] = useState<RunHistory[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.get<RunHistory[]>("/api/sandbox/runs").then(setHistory).catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post<AnalyzeResult>("/api/sandbox/analyze", {
        request_text: request,
        use_openrouter: useOpenRouter,
      });
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
        <h1 className="text-2xl font-semibold">{t("sandbox.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("sandbox.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <textarea
          className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm min-h-[72px]"
          placeholder={t("sandbox.placeholder")}
          value={request}
          onChange={(e) => setRequest(e.target.value)}
        />
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink-secondary">
            <input type="checkbox" checked={useOpenRouter} onChange={(e) => setUseOpenRouter(e.target.checked)} />
            {t("sandbox.useOpenRouter")}
          </label>
          <button
            onClick={run}
            disabled={busy}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("sandbox.run")}
          </button>
        </div>
        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="pt-3 border-t border-edge space-y-3">
            <div>
              <div className="text-xs font-medium text-ink-muted mb-1">
                {t("sandbox.generatedCode")} ({result.provider})
              </div>
              <pre className="text-xs bg-page rounded-lg p-3 overflow-x-auto border border-edge">{result.generated_code}</pre>
            </div>
            <div>
              <div className="text-xs font-medium text-ink-muted mb-1">{t("sandbox.output")}</div>
              <pre className="text-xs bg-page rounded-lg p-3 overflow-x-auto border border-edge whitespace-pre-wrap">
                {result.stdout || "(no output)"}
              </pre>
              {result.stderr && (
                <pre className="text-xs text-critical rounded-lg p-3 overflow-x-auto mt-1 whitespace-pre-wrap">
                  {result.stderr}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-ink-secondary mb-3">History</h2>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.id} className="card p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm truncate">{h.request_text}</span>
                  <span className={`text-[11px] ${h.status === "done" ? "text-good" : "text-critical"}`}>{h.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
