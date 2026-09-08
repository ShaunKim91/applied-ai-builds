import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamPost } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface Turn {
  id: number;
  role: "human" | "ai" | "tool";
  content: string;
  redacted: boolean;
  tool_name: string;
  created_at: string;
}
interface Fact {
  field_name: string;
  field_value: string;
  confidence: string;
  updated_at: string;
}
interface Conflict {
  id: number;
  field_name: string;
  old_value: string;
  new_value: string;
  resolution: string;
  created_at: string;
}
interface CaseDetail {
  id: number;
  title: string;
  status: string;
  case_summary: string;
  turns: Turn[];
  facts: Fact[];
  pending_conflicts: Conflict[];
}

export default function Workspace() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { t } = useLang();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState("");
  const [routerInfo, setRouterInfo] = useState<{ action: string; tool_name: string | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [escalation, setEscalation] = useState<{ text: string; model: string } | null>(null);
  const [escalating, setEscalating] = useState(false);
  const [purging, setPurging] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = () => api.get<CaseDetail>(`/api/cases/${caseId}`).then(setDetail);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [detail, streaming]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setStreaming("");
    setRouterInfo(null);
    setEscalation(null);
    try {
      for await (const evt of streamPost<Record<string, unknown>>(`/api/cases/${caseId}/messages`, { message })) {
        if (evt.router) setRouterInfo(evt.router as { action: string; tool_name: string | null });
        if (typeof evt.delta === "string") setStreaming((s) => s + (evt.delta as string));
        if (evt.done) {
          await load();
          setStreaming("");
          setRouterInfo(null);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const resolveConflict = async (conflictId: number, resolution: "accepted_new" | "kept_old") => {
    await api.post(`/api/cases/${caseId}/conflicts/${conflictId}/resolve`, { resolution });
    await load();
  };

  const escalate = async () => {
    setEscalating(true);
    try {
      const result = await api.post<{ text: string; model: string }>(`/api/cases/${caseId}/escalate`, {});
      setEscalation(result);
    } catch (err) {
      setEscalation({ text: err instanceof Error ? err.message : "error", model: "" });
    } finally {
      setEscalating(false);
    }
  };

  const purge = async () => {
    if (!window.confirm(t("workspace.purgeConfirm"))) return;
    setPurging(true);
    try {
      await api.post(`/api/cases/${caseId}/purge`, {});
      navigate("/cases");
    } finally {
      setPurging(false);
    }
  };

  if (!detail) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6 items-start">
      <div>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <h1 className="font-display font-bold text-xl">{detail.title}</h1>
            <span className={`badge ${detail.status === "open" ? "badge-good" : ""}`}>{detail.status}</span>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary text-xs px-3 py-1.5" onClick={escalate} disabled={escalating}>
              ☁ {t("workspace.escalate")}
            </button>
            <button className="btn-secondary text-xs px-3 py-1.5" style={{ color: "var(--critical)" }} onClick={purge} disabled={purging}>
              🗑 {t("workspace.purge")}
            </button>
          </div>
        </div>

        {detail.case_summary && (
          <div className="card p-4 mb-4 text-sm" style={{ color: "var(--text-secondary)" }}>
            <div className="text-xs font-mono uppercase mb-1" style={{ color: "var(--text-muted)" }}>
              {t("workspace.rollingSummary")}
            </div>
            {detail.case_summary}
          </div>
        )}

        {detail.pending_conflicts.length > 0 && (
          <div className="card p-4 mb-4" style={{ borderColor: "var(--warning)" }}>
            <div className="text-xs font-mono uppercase mb-2" style={{ color: "var(--warning)" }}>
              {t("workspace.conflictsTitle")}
            </div>
            {detail.pending_conflicts.map((c) => (
              <div key={c.id} className="text-sm mb-2 pb-2 border-b last:border-0" style={{ borderColor: "var(--border-color)" }}>
                <div className="font-mono-num mb-1">{c.field_name}</div>
                <div style={{ color: "var(--text-secondary)" }}>
                  {t("workspace.conflictOld")}: <strong>{c.old_value}</strong> &nbsp;→&nbsp; {t("workspace.conflictNew")}: <strong>{c.new_value}</strong>
                </div>
                <div className="flex gap-2 mt-1">
                  <button className="btn-secondary text-xs px-3 py-1" onClick={() => resolveConflict(c.id, "accepted_new")}>
                    {t("workspace.conflictAccept")}
                  </button>
                  <button className="btn-secondary text-xs px-3 py-1" onClick={() => resolveConflict(c.id, "kept_old")}>
                    {t("workspace.conflictKeep")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-3">
          {detail.turns.length === 0 && <EmptyState>{t("workspace.empty")}</EmptyState>}
          {detail.turns.map((turn) => (
            <div key={turn.id} className={`message-card role-${turn.role}`}>
              <div className="role-chip mb-1">
                {turn.role === "tool" ? `⚙ ${turn.tool_name}` : turn.role === "human" ? t("workspace.roleRep") : t("workspace.roleAssistant")}
                {turn.redacted && <span className="ml-2">🔒 {t("workspace.redacted")}</span>}
              </div>
              <div style={{ color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>{turn.content}</div>
            </div>
          ))}
          {busy && (
            <div className="message-card role-ai">
              <div className="role-chip mb-1">
                {t("workspace.roleAssistant")}
                {routerInfo?.action === "tool" && <span className="ml-2">⚙ {routerInfo.tool_name}</span>}
              </div>
              <div style={{ color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>{streaming || "…"}</div>
            </div>
          )}
          {escalation && (
            <div className="message-card role-ai" style={{ borderLeftColor: "var(--warning)" }}>
              <div className="role-chip mb-1">☁ {escalation.model || t("workspace.escalate")}</div>
              <div style={{ color: "var(--text-primary)", whiteSpace: "pre-wrap" }}>{escalation.text}</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={send} className="flex gap-2 mt-4 sticky bottom-0 pt-2" style={{ background: "var(--page-plane)" }}>
          <input
            className="flex-1 px-3 py-2.5 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-1)" }}
            placeholder={t("workspace.inputPlaceholder")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <button type="submit" disabled={busy || !input.trim()} className="btn-primary px-5 py-2.5">
            {t("workspace.send")}
          </button>
        </form>
      </div>

      <aside className="flex flex-col gap-2 lg:sticky lg:top-4 self-start">
        <div className="text-xs font-mono uppercase mb-1" style={{ color: "var(--text-muted)" }}>
          {t("workspace.factsTitle")}
        </div>
        {detail.facts.length === 0 && <p className="text-sm" style={{ color: "var(--text-muted)" }}>{t("workspace.factsEmpty")}</p>}
        {detail.facts.map((f) => (
          <div key={f.field_name} className={`index-card ${f.confidence === "inferred" ? "confidence-inferred" : ""}`}>
            <span className="field-label">{f.field_name.replace(/_/g, " ")}</span>
            <span className="field-value">{f.field_value}</span>
            {f.confidence === "inferred" && (
              <span className="text-xs mt-1 block" style={{ color: "var(--warning)" }}>
                {t("workspace.inferred")}
              </span>
            )}
          </div>
        ))}
      </aside>
    </div>
  );
}
