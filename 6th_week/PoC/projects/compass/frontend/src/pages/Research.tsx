import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, streamPost } from "../api/client";
import { useI18n } from "../i18n";

interface Source {
  title: string;
  href: string;
  body: string;
  source: "ddgs" | "mock";
  bi_score?: number;
  rerank_score?: number;
}
interface Groundedness {
  passed: boolean;
  content_check: { score: number };
}
interface GhostCheck {
  passed: boolean;
  cited_count: number;
  real_citations: string[];
  ghost_citations: string[];
}
interface Turn {
  id?: number;
  query: string;
  report: string;
  streaming?: boolean;
  sources?: Source[];
  search_mode?: "ddgs" | "mock";
  ghost_citations?: GhostCheck;
  groundedness?: Groundedness;
  synth_mode?: string;
}
interface Session {
  id: number;
  title: string;
}

const CITATION_RE = /\[(\d+)\]/g;

function renderWithCitations(text: string, onJump: (n: number) => void) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;
  while ((match = CITATION_RE.exec(text))) {
    parts.push(text.slice(last, match.index));
    const n = Number(match[1]);
    parts.push(
      <button
        key={match.index}
        onClick={() => onJump(n)}
        className="inline-flex items-center justify-center align-super text-[10px] font-bold w-4 h-4 rounded-full bg-accent-gradient text-white mx-0.5 leading-none font-mono"
      >
        {n}
      </button>
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

export default function Research() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [useRerank, setUseRerank] = useState(true);
  const [useOpenRouter, setUseOpenRouter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const autoSentRef = useRef(false);

  const loadSessions = () => api.get<Session[]>("/api/research/sessions").then(setSessions).catch(() => {});

  useEffect(() => {
    loadSessions();
  }, []);

  const openSession = async (id: number) => {
    setSessionId(id);
    const entries = await api.get<any[]>(`/api/research/sessions/${id}/entries`);
    const mapped: Turn[] = entries.map((e) => ({
      id: e.id,
      query: e.query,
      report: e.report_text,
      sources: e.sources,
      search_mode: e.search_mode,
      ghost_citations: e.ghost_citations,
      groundedness: e.groundedness,
      synth_mode: e.synth_mode,
    }));
    setTurns(mapped);
    setActiveSources(mapped[mapped.length - 1]?.sources ?? []);
  };

  const newSession = async () => {
    const s = await api.post<Session>("/api/research/sessions");
    setSessions((prev) => [s, ...prev]);
    setSessionId(s.id);
    setTurns([]);
    setActiveSources([]);
    return s.id;
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const send = async (queryOverride?: string) => {
    const query = (queryOverride ?? input).trim();
    if (!query || busy) return;
    let sid = sessionId;
    if (!sid) sid = await newSession();
    setInput("");
    setBusy(true);
    setTurns((prev) => [...prev, { query, report: "", streaming: true }]);

    try {
      for await (const event of streamPost<{
        delta?: string;
        error?: string;
        done?: boolean;
        entry_id?: number;
        sources?: Source[];
        search_mode?: "ddgs" | "mock";
        ghost_citations?: GhostCheck;
        groundedness?: Groundedness;
      }>(`/api/research/sessions/${sid}/entries`, { query, use_rerank: useRerank, use_openrouter: useOpenRouter })) {
        if (event.error) {
          setTurns((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], report: `⚠ ${event.error}`, streaming: false };
            return next;
          });
          break;
        }
        if (event.delta) {
          setTurns((prev) => {
            const next = [...prev];
            const i = next.length - 1;
            next[i] = { ...next[i], report: next[i].report + event.delta };
            return next;
          });
        }
        if (event.done) {
          setTurns((prev) => {
            const next = [...prev];
            const i = next.length - 1;
            next[i] = {
              ...next[i],
              streaming: false,
              id: event.entry_id,
              sources: event.sources,
              search_mode: event.search_mode,
              ghost_citations: event.ghost_citations,
              groundedness: event.groundedness,
              synth_mode: useOpenRouter ? "openrouter" : "local",
            };
            return next;
          });
          setActiveSources(event.sources ?? []);
          loadSessions();
        }
      }
    } catch (err) {
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], report: `⚠ ${err instanceof Error ? err.message : "error"}`, streaming: false };
        return next;
      });
    } finally {
      setBusy(false);
    }
  };

  // Quick-console launch: /research?session=ID&q=... from the top bar.
  useEffect(() => {
    const sid = params.get("session");
    const q = params.get("q");
    if (sid && !autoSentRef.current) {
      autoSentRef.current = true;
      const id = Number(sid);
      setSessionId(id);
      loadSessions().then(() => {
        if (q) {
          send(q);
        } else {
          openSession(id);
        }
      });
      setParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex gap-4 h-[calc(100vh-6rem)]">
      <div className="card w-52 shrink-0 p-3 hidden lg:flex lg:flex-col">
        <button onClick={newSession} className="mb-3 px-3 py-2 rounded-lg bg-accent-gradient text-white text-sm font-medium shadow-card">
          + {t("research.new")}
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`w-full text-left px-2.5 py-2 rounded-lg text-xs truncate ${
                s.id === sessionId ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary hover:bg-accent-soft"
              }`}
            >
              {s.title}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-edge">
          <h1 className="font-display text-lg font-semibold">{t("research.title")}</h1>
          <p className="text-xs text-ink-secondary">{t("research.subtitle")}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {turns.length === 0 && <p className="text-sm text-ink-muted text-center mt-12">{t("research.empty")}</p>}
          {turns.map((turn, i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed bg-accent-gradient text-white">
                  {turn.query}
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed bg-surface2">
                  {turn.streaming && !turn.report ? (
                    <div className="flex items-center gap-2 text-ink-muted">
                      <span className="radar-ring w-4 h-4" />
                      {t("research.searching")}
                    </div>
                  ) : (
                    <>
                      <p className="font-display">{renderWithCitations(turn.report, setHighlighted)}</p>
                      {turn.streaming && <span className="animate-pulse">▌</span>}
                    </>
                  )}
                  {turn.search_mode === "mock" && (
                    <div className="mt-2 text-[11px] text-warning font-mono">⚠ {t("research.mockNotice")}</div>
                  )}
                  {turn.ghost_citations && !turn.ghost_citations.passed && (
                    <div className="mt-2 text-[11px] text-critical font-mono">
                      ⚠ {t("research.ghostDetected")} ({turn.ghost_citations.ghost_citations.length})
                    </div>
                  )}
                  {turn.groundedness && (
                    <div className="mt-2 pt-2 border-t border-edge/50 flex items-center gap-2 text-[11px] font-mono">
                      <span className={turn.groundedness.passed ? "text-good" : "text-warning"}>
                        {turn.groundedness.passed ? `✓ ${t("research.grounded")}` : `⚠ ${t("research.partiallyGrounded")}`}
                      </span>
                      <span className="text-ink-muted">
                        ({Math.round(turn.groundedness.content_check.score * 100)}% · {turn.synth_mode})
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="px-6 py-4 border-t border-edge space-y-2">
          <div className="flex gap-3 text-xs text-ink-secondary">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={useRerank} onChange={(e) => setUseRerank(e.target.checked)} />
              {t("research.useRerank")}
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={useOpenRouter} onChange={(e) => setUseOpenRouter(e.target.checked)} />
              {t("research.useOpenRouter")}
            </label>
          </div>
          <div className="flex gap-2">
            <input
              className="flex-1 px-3.5 py-2.5 rounded-lg border border-edge bg-transparent text-sm"
              placeholder={t("research.placeholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={busy}
            />
            <button
              onClick={() => send()}
              disabled={busy || !input.trim()}
              className="px-4 py-2.5 rounded-lg bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-card"
            >
              {t("research.send")}
            </button>
          </div>
        </div>
      </div>

      <div className="card w-80 shrink-0 p-4 hidden xl:flex xl:flex-col overflow-hidden">
        <h2 className="text-sm font-semibold mb-3">{t("research.sources")}</h2>
        <div className="flex-1 overflow-y-auto space-y-2">
          {activeSources.length === 0 && <p className="text-xs text-ink-muted">{t("research.noSources")}</p>}
          {activeSources.map((s, i) => (
            <div
              key={i}
              className={`p-3 rounded-lg border text-xs ${highlighted === i + 1 ? "border-accent bg-accent-soft" : "border-edge"}`}
            >
              <div className="font-medium mb-1 flex items-center justify-between gap-2">
                <span className="truncate">
                  [{i + 1}] {s.title}
                </span>
                {s.source === "mock" && <span className="text-warning shrink-0 font-mono text-[10px]">mock</span>}
              </div>
              <a href={s.href} target="_blank" rel="noreferrer" className="text-accent-2 text-[10px] font-mono break-all block mb-1">
                {s.href}
              </a>
              <p className="text-ink-secondary line-clamp-3">{s.body}</p>
              <div className="mt-1 text-[10px] text-ink-muted font-mono tabular-nums">
                {s.rerank_score !== undefined ? `rerank ${s.rerank_score.toFixed(3)}` : `bi ${((s.bi_score ?? 0) * 100).toFixed(1)}%`}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
