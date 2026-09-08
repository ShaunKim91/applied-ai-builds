import React, { useEffect, useRef, useState } from "react";

import { api, streamPost } from "../api/client";
import { useI18n } from "../i18n";

interface Citation {
  id: string;
  text: string;
  metadata: { title?: string; language?: string; document_id?: number };
  similarity: number;
  rerank_score?: number;
}
interface Groundedness {
  passed: boolean;
  citation_check: { passed: boolean; invalid: number[] };
  content_check: { passed: boolean; score: number };
}
interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  groundedness?: Groundedness;
  retrieval_mode?: string;
  provider?: string;
  streaming?: boolean;
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
        className="inline-flex items-center justify-center align-super text-[10px] font-bold w-4 h-4 rounded-full bg-accent-gradient text-white mx-0.5 leading-none"
      >
        {n}
      </button>
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

export default function Chat() {
  const { t } = useI18n();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [useRerank, setUseRerank] = useState(false);
  const [useOpenRouter, setUseOpenRouter] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadSessions = () => api.get<Session[]>("/api/chat/sessions").then(setSessions).catch(() => {});

  useEffect(() => {
    loadSessions();
  }, []);

  const openSession = async (id: number) => {
    setSessionId(id);
    const msgs = await api.get<Message[]>(`/api/chat/sessions/${id}/messages`);
    setMessages(msgs);
    const lastAssistant = [...msgs].reverse().find((m) => m.role === "assistant");
    setActiveCitations(lastAssistant?.citations ?? []);
  };

  const newSession = async () => {
    const s = await api.post<Session>("/api/chat/sessions");
    setSessions((prev) => [s, ...prev]);
    setSessionId(s.id);
    setMessages([]);
    setActiveCitations([]);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || busy) return;
    let sid = sessionId;
    if (!sid) {
      const s = await api.post<Session>("/api/chat/sessions");
      setSessions((prev) => [s, ...prev]);
      sid = s.id;
      setSessionId(sid);
    }
    const question = input;
    setInput("");
    setBusy(true);
    setMessages((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "", streaming: true }]);

    try {
      for await (const event of streamPost<{ delta?: string; error?: string; done?: boolean; citations?: Citation[]; groundedness?: Groundedness; message_id?: number }>(
        `/api/chat/sessions/${sid}/messages`,
        { content: question, use_rerank: useRerank, use_openrouter: useOpenRouter }
      )) {
        if (event.error) {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { role: "assistant", content: `⚠ ${event.error}` };
            return next;
          });
          break;
        }
        if (event.delta) {
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            next[lastIdx] = { ...next[lastIdx], content: next[lastIdx].content + event.delta };
            return next;
          });
        }
        if (event.done) {
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            next[lastIdx] = {
              ...next[lastIdx],
              streaming: false,
              id: event.message_id,
              citations: event.citations,
              groundedness: event.groundedness,
              retrieval_mode: useRerank ? "bi+cross" : "bi",
              provider: useOpenRouter ? "openrouter" : "local",
            };
            return next;
          });
          setActiveCitations(event.citations ?? []);
          loadSessions();
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content: `⚠ ${err instanceof Error ? err.message : "error"}` };
        return next;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-2rem)]">
      <div className="card w-52 shrink-0 p-3 hidden lg:flex lg:flex-col">
        <button
          onClick={newSession}
          className="mb-3 px-3 py-2 rounded-xl bg-accent-gradient text-white text-sm font-medium shadow-glass"
        >
          + {t("chat.newChat")}
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`w-full text-left px-2.5 py-2 rounded-lg text-xs truncate transition-colors ${
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
          <h1 className="text-lg font-bold">{t("chat.title")}</h1>
          <p className="text-xs text-ink-secondary">{t("chat.subtitle")}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && <p className="text-sm text-ink-muted text-center mt-12">{t("chat.empty")}</p>}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user" ? "bg-accent-gradient text-white" : "bg-accent-soft text-ink"
                }`}
              >
                {m.role === "assistant" ? renderWithCitations(m.content || "…", (n) => setHighlightedSource(n)) : m.content}
                {m.streaming && <span className="animate-pulse">▌</span>}
                {m.groundedness && (
                  <div className="mt-2 pt-2 border-t border-edge/50 flex items-center gap-2 text-[11px]">
                    <span className={m.groundedness.passed ? "text-good" : "text-warning"}>
                      {m.groundedness.passed ? `✓ ${t("chat.grounded")}` : `⚠ ${t("chat.partiallyGrounded")}`}
                    </span>
                    <span className="text-ink-muted">
                      ({Math.round(m.groundedness.content_check.score * 100)}% · {m.retrieval_mode} · {m.provider})
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="px-6 py-4 border-t border-edge space-y-2">
          <div className="flex gap-3 text-xs text-ink-secondary">
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={useRerank} onChange={(e) => setUseRerank(e.target.checked)} />
              {t("chat.useRerank")}
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={useOpenRouter} onChange={(e) => setUseOpenRouter(e.target.checked)} />
              {t("chat.useOpenRouter")}
            </label>
          </div>
          <div className="flex gap-2">
            <input
              className="flex-1 px-3.5 py-2.5 rounded-xl border border-edge bg-transparent text-sm"
              placeholder={t("chat.placeholder")}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="px-4 py-2.5 rounded-xl bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-glass"
            >
              {t("chat.send")}
            </button>
          </div>
        </div>
      </div>

      <div className="card w-80 shrink-0 p-4 hidden xl:flex xl:flex-col overflow-hidden">
        <h2 className="text-sm font-semibold mb-3">{t("chat.sources")}</h2>
        <div className="flex-1 overflow-y-auto space-y-2">
          {activeCitations.length === 0 && <p className="text-xs text-ink-muted">{t("chat.noSources")}</p>}
          {activeCitations.map((c, i) => (
            <div
              key={c.id}
              className={`p-3 rounded-xl border text-xs transition-colors ${
                highlightedSource === i + 1 ? "border-accent bg-accent-soft" : "border-edge"
              }`}
            >
              <div className="font-medium mb-1 flex items-center justify-between">
                <span className="truncate">
                  [{i + 1}] {c.metadata.title}
                </span>
                <span className="text-ink-muted shrink-0 ml-2">{c.metadata.language}</span>
              </div>
              <p className="text-ink-secondary line-clamp-4">{c.text}</p>
              <div className="mt-1 text-[10px] text-ink-muted tabular-nums">
                {c.rerank_score !== undefined ? `rerank ${c.rerank_score.toFixed(3)}` : `sim ${(c.similarity * 100).toFixed(1)}%`}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
