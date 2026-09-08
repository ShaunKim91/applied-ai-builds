import React, { useEffect, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface TableResult {
  headers: string[];
  rows: (string | number)[][];
  row_count: number;
  csv: string;
}
interface ParseResponse {
  id: number;
  url: string;
  table_count: number;
  tables: TableResult[];
  latency_ms: number;
}
interface ScrapeHistory {
  id: number;
  source_url: string;
  table_count: number;
  row_count: number;
  latency_ms: number;
  created_at: string;
}

function downloadCsv(csv: string, filename: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Tables() {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  const [sample, setSample] = useState<{ url: string; label: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ParseResponse | null>(null);
  const [recent, setRecent] = useState<ScrapeHistory[]>([]);
  const [error, setError] = useState("");

  const refresh = () => api.get<ScrapeHistory[]>("/api/tables").then(setRecent).catch(() => {});

  useEffect(() => {
    api.get<{ url: string; label: string }>("/api/tables/sample").then(setSample).catch(() => {});
    refresh();
  }, []);

  const parse = async (targetUrl: string) => {
    if (!targetUrl.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.post<ParseResponse>("/api/tables/parse", { url: targetUrl });
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
        <h1 className="text-display-md">{t("tables.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[65ch]">{t("tables.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap gap-3">
          <input
            className="flex-1 min-w-[240px] px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm"
            placeholder={t("tables.urlPlaceholder")}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && parse(url)}
          />
          <button
            onClick={() => parse(url)}
            disabled={busy}
            className="px-4 py-2 rounded-full bg-accent text-white text-sm font-medium disabled:opacity-60"
          >
            {t("tables.parse")}
          </button>
          {sample && (
            <button
              onClick={() => {
                setUrl(sample.url);
                parse(sample.url);
              }}
              disabled={busy}
              className="px-3 py-1.5 rounded-full border border-edge hover:border-accent transition-colors disabled:opacity-60 text-xs"
            >
              {t("tables.orSample")}
            </button>
          )}
        </div>

        {error && <div className="text-sm text-critical">{error}</div>}

        {result && (
          <div className="pt-4 border-t border-edge space-y-4">
            <div className="text-xs text-ink-muted">
              {t("tables.tableCount").replace("{count}", String(result.table_count))} · {result.latency_ms.toFixed(0)}ms
            </div>
            {result.tables.map((tbl, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-ink-muted">
                    Table {i + 1} · {tbl.row_count} rows
                  </span>
                  <button
                    onClick={() => downloadCsv(tbl.csv, `parchment_table_${i + 1}.csv`)}
                    className="text-xs px-2 py-1 rounded-full border border-edge hover:border-accent"
                  >
                    {t("tables.downloadCsv")}
                  </button>
                </div>
                <div className="overflow-x-auto border border-edge rounded-lg">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-ink-muted bg-page">
                        {tbl.headers.map((h, j) => (
                          <th key={j} className="p-2 whitespace-nowrap">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tbl.rows.slice(0, 15).map((row, r) => (
                        <tr key={r} className="border-t border-edge">
                          {row.map((cell, c) => (
                            <td key={c} className="p-2 whitespace-nowrap">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("tables.recent")}</h2>
        <div className="space-y-2">
          {recent.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-ink-muted truncate max-w-[70%]">{r.source_url}</span>
                <span className="text-[11px] text-ink-muted">
                  {r.table_count} tables · {r.row_count} rows
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
