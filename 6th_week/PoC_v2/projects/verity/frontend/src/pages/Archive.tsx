import { useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface Match {
  id: number;
  query: string;
  report_text: string;
  mode: string;
  claim_number: string;
  jurisdiction: string;
  similarity: number;
  created_at: string;
}

export default function Archive() {
  const { t } = useLang();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Match[] | null>(null);
  const [busy, setBusy] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const matches = await api.post<Match[]>("/api/archive/search", { query });
      setResults(matches);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("archive.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("archive.subtitle")}</p>

      <div className="flex gap-2 mt-4">
        <input
          className="flex-1 px-3 py-2 rounded-ledger-sm border"
          style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
          placeholder={t("archive.placeholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn-primary px-5" disabled={busy} onClick={search}>
          {t("archive.search")}
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {results === null && <EmptyState>{t("archive.empty")}</EmptyState>}
        {results?.length === 0 && <EmptyState>{t("archive.empty")}</EmptyState>}
        {results?.map((m) => (
          <div key={m.id} className="card p-4">
            <div className="flex justify-between items-start">
              <div className="font-medium">{m.query}</div>
              <span className="badge font-mono-num">{m.similarity}%</span>
            </div>
            <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
              {m.report_text}
            </p>
            <div className="flex gap-2 mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
              {m.claim_number && <span className="font-mono-num">{m.claim_number}</span>}
              {m.jurisdiction && <span>{m.jurisdiction}</span>}
              <span>{m.mode}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
