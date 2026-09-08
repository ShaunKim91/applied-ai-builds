import { useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface Match {
  id: number;
  question: string;
  final_answer: string;
  status: string;
  similarity: number;
  created_at: string;
}

export default function History() {
  const { t } = useLang();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Match[] | null>(null);
  const [busy, setBusy] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setBusy(true);
    try {
      setResults(await api.post<Match[]>("/api/history/search", { query }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("history.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("history.subtitle")}</p>

      <div className="flex gap-2 mt-4">
        <input
          className="flex-1 px-3 py-2 rounded-ledger-sm border"
          style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
          placeholder={t("history.placeholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn-primary px-5" disabled={busy} onClick={search}>
          {t("history.search")}
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {(results === null || results.length === 0) && <EmptyState>{t("history.empty")}</EmptyState>}
        {results?.map((m) => (
          <div key={m.id} className="card p-4">
            <div className="flex justify-between items-start">
              <div className="font-medium">{m.question}</div>
              <span className="badge font-mono-num">{m.similarity}%</span>
            </div>
            <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
              {m.final_answer}
            </p>
            <div className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
              {m.status} · {new Date(m.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
