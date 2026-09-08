import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface Doc {
  id: number;
  title: string;
  source: string;
  language: string;
  char_count: number;
  chunk_count: number;
  created_at: string;
}

const LANG_LABEL: Record<string, string> = { en: "English", ko: "한국어", auto: "auto-detected" };

export default function Documents() {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = () => api.get<Doc[]>("/api/documents").then(setDocs).catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.postForm("/api/documents/upload", form);
      if (fileRef.current) fileRef.current.value = "";
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const seedCount = docs.filter((d) => d.source === "seed").length;
  const uploadCount = docs.filter((d) => d.source === "upload").length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">{t("documents.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("documents.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept=".txt,.md,.pdf" className="text-sm" />
          <button
            onClick={upload}
            disabled={busy}
            className="px-4 py-2 rounded-xl bg-accent-gradient text-white text-sm font-medium disabled:opacity-60 shadow-glass"
          >
            {t("documents.upload")}
          </button>
          {busy && <span className="text-sm text-ink-muted">{t("documents.uploading")}</span>}
        </div>
        {error && <div className="text-sm text-critical">{error}</div>}
        <p className="text-xs text-ink-muted">
          {t("documents.seedInfo").replace("{seed}", String(seedCount)).replace("{upload}", String(uploadCount))}
        </p>
      </div>

      <div className="space-y-2">
        {docs.map((d) => (
          <div key={d.id} className="card p-4 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">{d.title}</div>
              <div className="text-[11px] text-ink-muted">
                {d.source} · {LANG_LABEL[d.language] ?? d.language} · {d.chunk_count} chunks · {d.char_count.toLocaleString()} chars
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
