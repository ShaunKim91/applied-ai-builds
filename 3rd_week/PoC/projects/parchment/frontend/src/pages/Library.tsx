import React, { useEffect, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface LibraryEntry {
  id: string;
  doc_type: "receipt" | "pdf";
  label: string;
  is_duplicate: boolean;
  duplicate_of: string | null;
  similarity: number | null;
  created_at: string;
}
interface LibraryResponse {
  entries: LibraryEntry[];
  total: number;
  duplicate_count: number;
}

const TYPE_ICON: Record<string, string> = { receipt: "🧾", pdf: "📄" };

export default function Library() {
  const { t } = useI18n();
  const [data, setData] = useState<LibraryResponse | null>(null);

  useEffect(() => {
    api.get<LibraryResponse>("/api/library").then(setData).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-display-md">{t("library.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[65ch]">{t("library.subtitle")}</p>
      </div>

      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="card p-6">
            <div className="text-sm text-ink-secondary">{t("library.totalDocuments")}</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums">{data.total}</div>
          </div>
          <div className="card p-6">
            <div className="text-sm text-ink-secondary">{t("library.duplicatesFlagged")}</div>
            <div className={`mt-2 text-3xl font-semibold tabular-nums ${data.duplicate_count > 0 ? "text-warning" : "text-good"}`}>
              {data.duplicate_count}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {data?.entries.map((e) => (
          <div key={e.id} className="card p-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-lg">{TYPE_ICON[e.doc_type]}</span>
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{e.label}</div>
                <div className="text-[11px] text-ink-muted">{new Date(e.created_at).toLocaleString()}</div>
              </div>
            </div>
            {e.is_duplicate ? (
              <span className="text-xs px-2.5 py-1 rounded-full bg-warning/10 text-warning border border-warning/30 whitespace-nowrap">
                ⚠ {((e.similarity ?? 0) * 100).toFixed(0)}% {t("library.similarTo")} {e.duplicate_of}
              </span>
            ) : (
              <span className="text-xs px-2.5 py-1 rounded-full bg-good/10 text-good border border-good/30 whitespace-nowrap">
                {t("library.unique")}
              </span>
            )}
          </div>
        ))}
        {data && data.entries.length === 0 && <p className="text-sm text-ink-muted">{t("library.empty")}</p>}
      </div>
    </div>
  );
}
