import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface CaseRow {
  id: number;
  title: string;
  status: string;
  case_summary: string;
  created_at: string;
  updated_at: string;
}

export default function Cases() {
  const { t } = useLang();
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [query, setQuery] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const load = (q = "") => {
    setLoading(true);
    api
      .get<CaseRow[]>(`/api/cases${q ? `?q=${encodeURIComponent(q)}` : ""}`)
      .then(setCases)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const search = (e: React.FormEvent) => {
    e.preventDefault();
    load(query);
  };

  const createCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const created = await api.post<CaseRow>("/api/cases", { title: newTitle });
      navigate(`/cases/${created.id}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("cases.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("cases.subtitle")}</p>

      <form onSubmit={createCase} className="card p-4 mt-5 flex gap-2 items-end flex-wrap">
        <div className="flex-1 min-w-[220px]">
          <label className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
            {t("cases.newCaseLabel")}
          </label>
          <input
            className="w-full mt-1 px-3 py-2 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            placeholder={t("cases.newCasePlaceholder")}
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
        </div>
        <button type="submit" disabled={creating} className="btn-primary px-5 py-2">
          {t("cases.newCaseSubmit")}
        </button>
      </form>

      <form onSubmit={search} className="flex gap-2 mt-4">
        <input
          className="flex-1 px-3 py-2 rounded-ledger-sm border"
          style={{ borderColor: "var(--border-color)", background: "var(--surface-1)" }}
          placeholder={t("cases.searchPlaceholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="btn-secondary px-4 py-2">
          {t("cases.search")}
        </button>
        {query && (
          <button
            type="button"
            className="btn-secondary px-4 py-2"
            onClick={() => {
              setQuery("");
              load();
            }}
          >
            {t("cases.clear")}
          </button>
        )}
      </form>

      <div className="mt-5 grid grid-cols-1 gap-3">
        {loading && <p style={{ color: "var(--text-muted)" }}>{t("cases.loading")}</p>}
        {!loading && cases.length === 0 && <EmptyState>{t("cases.empty")}</EmptyState>}
        {cases.map((c) => (
          <button key={c.id} onClick={() => navigate(`/cases/${c.id}`)} className="card p-4 text-left hover:shadow-ledger-lift transition-shadow">
            <div className="flex items-center justify-between">
              <div className="font-display font-bold" style={{ color: "var(--text-primary)" }}>
                {c.title}
              </div>
              <span className={`badge ${c.status === "open" ? "badge-good" : ""}`}>{c.status}</span>
            </div>
            {c.case_summary && (
              <p className="text-sm mt-1 line-clamp-2" style={{ color: "var(--text-secondary)" }}>
                {c.case_summary}
              </p>
            )}
            <div className="text-xs mt-2 font-mono-num" style={{ color: "var(--text-muted)" }}>
              {new Date(c.updated_at).toLocaleString()}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
