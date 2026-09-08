import { useEffect, useRef, useState } from "react";
import { api, streamPost } from "../api/client";
import EmptyState from "../components/EmptyState";
import SourceBadge from "../components/SourceBadge";
import { useLang } from "../i18n";

const JURISDICTIONS = ["Ashford", "Belmont Bay", "Cedermoor", "Dunraven", "Elmsworth", "Fairhaven"];

interface Session {
  id: number;
  title: string;
  claim_number: string;
  jurisdiction: string;
  created_at: string;
}

interface Entry {
  id: number;
  mode: string;
  query: string;
  report_text: string;
  brief: Record<string, string>;
  sources: { title: string; href: string; body: string }[];
  source_trust: { url: string; tier: "primary" | "secondary" | "unverified" }[];
  ghost_citations: { passed: boolean; ghost_urls: string[] };
  fraud_signals: { id: string; label: string }[];
  groundedness_score: number;
  synth_mode: string;
}

export default function Research() {
  const { t } = useLang();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [claimNumber, setClaimNumber] = useState("");
  const [mode, setMode] = useState<"quick" | "precedent_brief">("quick");
  const [useCloud, setUseCloud] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const briefRef = useRef<HTMLDivElement>(null);

  const loadSessions = () => api.get<Session[]>("/api/research/sessions").then(setSessions);

  // Loading a session's entries is triggered ONLY by an explicit user
  // action (opening an existing thread from the sidebar) below — never by
  // a useEffect reacting to activeId changing. That used to also fire
  // whenever startNewThread() called setActiveId(), racing against the
  // in-flight streaming query that immediately follows: this GET is a
  // trivial DB lookup that should resolve in milliseconds, but the local
  // LLM's blocking generate() call holds Python's GIL for most of a
  // multi-second (or 20+ second, in precedent-brief mode) generation,
  // which can delay this "harmless" background fetch until AFTER the
  // stream's own 'done' handler has already appended the real entry —
  // at which point the stale, now-outdated empty-array response silently
  // overwrites it, making a real completed answer vanish from the screen.
  // Confirmed directly via a screenshot showing "No research yet in this
  // thread" immediately after a real 200-OK query response. A brand-new
  // thread has no entries to fetch anyway, so it's set directly and
  // synchronously instead of round-tripping to the server for a fetch
  // whose answer we already know.
  const openSession = (id: number) => {
    setActiveId(id);
    api.get<Entry[]>(`/api/research/sessions/${id}/entries`).then(setEntries);
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const startNewThread = async () => {
    const session = await api.post<Session>("/api/research/sessions", { title: query || claimNumber, claim_number: claimNumber, jurisdiction });
    await loadSessions();
    setActiveId(session.id);
    setEntries([]);
    return session.id;
  };

  const submit = async () => {
    if (!query.trim() || busy) return;
    setBusy(true);
    setErrorMsg("");
    setStreamingText("");
    try {
      const sessionId = activeId ?? (await startNewThread());
      for await (const event of streamPost<{ delta?: string; done?: boolean; entry?: Entry; error?: string }>("/api/research/query", {
        query,
        mode,
        jurisdiction: jurisdiction || null,
        claim_number: claimNumber,
        session_id: sessionId,
        use_openrouter: useCloud,
      })) {
        if (event.error) {
          setErrorMsg(event.error);
        }
        if (event.delta) setStreamingText((prev) => prev + event.delta);
        if (event.done && event.entry) {
          setEntries((prev) => [...prev, event.entry as Entry]);
          setStreamingText("");
          setQuery("");
        }
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] gap-6">
      <div className="no-print">
        <button
          className="btn-secondary w-full py-2 mb-3 text-sm"
          onClick={() => {
            setActiveId(null);
            setEntries([]);
          }}
        >
          + {t("research.newSession")}
        </button>
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s.id)}
              className="w-full text-left text-sm px-3 py-2 rounded-ledger-sm truncate block"
              style={{
                background: activeId === s.id ? "var(--accent-soft)" : "transparent",
                color: activeId === s.id ? "var(--accent)" : "var(--text-secondary)",
              }}
            >
              {s.title || s.claim_number || "Untitled"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h1 className="font-display font-bold text-2xl mb-1">{t("research.title")}</h1>
        <p style={{ color: "var(--text-secondary)" }}>{t("research.subtitle")}</p>

        <div className="card p-4 mt-4 no-print">
          <textarea
            className="w-full px-3 py-2 rounded-ledger-sm border resize-none"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            rows={2}
            placeholder={t("research.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="flex flex-wrap items-center gap-3 mt-3">
            <select
              className="text-sm px-2 py-1.5 rounded-ledger-sm border"
              style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
            >
              <option value="">{t("research.anyJurisdiction")}</option>
              {JURISDICTIONS.map((j) => (
                <option key={j} value={j}>
                  {j}
                </option>
              ))}
            </select>
            <input
              className="text-sm px-2 py-1.5 rounded-ledger-sm border w-40"
              style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
              placeholder={t("research.claimNumber")}
              value={claimNumber}
              onChange={(e) => setClaimNumber(e.target.value)}
            />
            <select
              className="text-sm px-2 py-1.5 rounded-ledger-sm border"
              style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
              value={mode}
              onChange={(e) => setMode(e.target.value as "quick" | "precedent_brief")}
            >
              <option value="quick">{t("research.modeQuick")}</option>
              <option value="precedent_brief">{t("research.modeBrief")}</option>
            </select>
            <label className="flex items-center gap-1.5 text-sm" style={{ color: "var(--text-secondary)" }}>
              <input type="checkbox" checked={useCloud} onChange={(e) => setUseCloud(e.target.checked)} />
              {t("research.useCloud")}
            </label>
            <button className="btn-primary px-5 py-2 ml-auto" disabled={busy || !query.trim()} onClick={submit}>
              {t("research.run")}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-3 text-sm p-3 rounded-ledger-sm" style={{ color: "var(--critical)", background: "var(--surface-1)", border: "1px solid var(--critical)" }}>
            {errorMsg}
          </div>
        )}

        <div className="mt-6 space-y-4" ref={briefRef}>
          {entries.length === 0 && !streamingText && <EmptyState>{t("research.empty")}</EmptyState>}
          {entries.map((entry) => (
            <EntryCard key={entry.id} entry={entry} t={t} />
          ))}
          {streamingText && (
            <div className="card p-5">
              <p className="whitespace-pre-wrap font-mono-num text-sm">{streamingText}</p>
              <span className="inline-block w-2 h-4 ml-1 animate-pulse" style={{ background: "var(--accent)" }} />
            </div>
          )}
        </div>

        <p className="mt-8 text-xs no-print" style={{ color: "var(--text-muted)" }}>
          {t("research.compliance")}
        </p>
      </div>
    </div>
  );
}

function EntryCard({ entry, t }: { entry: Entry; t: (k: string) => string }) {
  const isBrief = entry.mode === "precedent_brief";
  return (
    <div className="card p-5">
      <div className="text-xs font-mono mb-2" style={{ color: "var(--text-muted)" }}>
        {entry.query}
      </div>
      {isBrief ? (
        <div className="space-y-2">
          {(["issue", "governing_authority", "facts_applied", "recommendation"] as const).map((key) => (
            <div key={key}>
              <div className="text-xs font-mono uppercase" style={{ color: "var(--accent-2)" }}>
                {t(`research.brief${key === "issue" ? "Issue" : key === "governing_authority" ? "Authority" : key === "facts_applied" ? "Facts" : "Recommendation"}`)}
              </div>
              <p className="whitespace-pre-wrap">{entry.brief?.[key] || "—"}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="whitespace-pre-wrap">{entry.report_text}</p>
      )}

      <div className="flex flex-wrap items-center gap-2 mt-4">
        <span className="badge">
          {t("research.groundedness")}: {(entry.groundedness_score * 100).toFixed(0)}%
        </span>
        <span className={`badge ${entry.ghost_citations.passed ? "" : "badge-critical"}`}>
          {entry.ghost_citations.passed ? t("research.ghostPassed") : t("research.ghostFailed")}
        </span>
        {entry.synth_mode === "openrouter" && <span className="badge">☁ OpenRouter</span>}
        {isBrief && (
          <button className="btn-secondary text-xs px-3 py-1 ml-auto no-print" onClick={() => window.print()}>
            🖨 {t("research.printBrief")}
          </button>
        )}
      </div>

      {entry.fraud_signals.length > 0 && (
        <div className="mt-3 text-sm p-2 rounded-ledger-sm" style={{ background: "var(--accent-soft)" }}>
          <strong>{t("research.fraudSignals")}:</strong> {entry.fraud_signals.map((f) => f.label).join(", ")}
          <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            {t("research.fraudNote")}
          </div>
        </div>
      )}

      {entry.sources.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-mono uppercase mb-1" style={{ color: "var(--text-muted)" }}>
            {t("research.sources")}
          </div>
          <ul className="space-y-1">
            {entry.sources.map((s, i) => {
              const tier = entry.source_trust.find((tt) => tt.url === s.href)?.tier ?? "unverified";
              return (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="font-mono-num" style={{ color: "var(--text-muted)" }}>
                    [{i + 1}]
                  </span>
                  <span className="flex-1">{s.title}</span>
                  <SourceBadge tier={tier} />
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
