import { useEffect, useState } from "react";
import { api, streamPost } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface Run {
  id: number;
  question: string;
  status: string;
  final_answer: string;
  step_count: number;
  synth_mode: string;
  created_at: string;
}

interface Step {
  step_number: number;
  kind: string;
  content: string;
}

const KIND_LABEL: Record<string, string> = {
  thought_action: "console.thoughtAction",
  observation: "console.observation",
};

export default function Console() {
  const { t } = useLang();
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [question, setQuestion] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [approvalId, setApprovalId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [detail, setDetail] = useState("");

  const loadRuns = () => api.get<Run[]>("/api/agent/runs").then(setRuns);

  useEffect(() => {
    loadRuns();
  }, []);

  const openRun = async (id: number) => {
    setActiveRunId(id);
    const run = await api.get<Run & { steps: Step[] }>(`/api/agent/runs/${id}`);
    // The backend persists a final_answer-kind AgentStep for the audit
    // trail — filtered out here so it isn't ALSO rendered as an ordinary
    // trace card duplicating the dedicated Final Answer card below.
    setSteps(run.steps.filter((s) => s.kind !== "final_answer"));
    setStatus(run.status);
    setFinalAnswer(run.final_answer);
    setApprovalId(null);
    setDetail("");
  };

  const send = async () => {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setSteps([]);
    setStreamingText("");
    setFinalAnswer("");
    setDetail("");
    setStatus("RUNNING");
    setApprovalId(null);
    setQuestion("");

    try {
      for await (const event of streamPost<{
        delta?: string;
        step_complete?: boolean;
        kind?: string;
        content?: string;
        done?: boolean;
        status?: string;
        final_answer?: string;
        detail?: string;
        approval_request_id?: number;
        run_id?: number;
        step_count?: number;
      }>("/api/agent/runs", { question: q })) {
        if (event.run_id) setActiveRunId(event.run_id);
        if (event.delta) {
          setStreamingText((prev) => prev + event.delta);
        }
        if (event.step_complete) {
          setSteps((prev) => [...prev, { step_number: event.step_count ?? prev.length + 1, kind: event.kind!, content: event.content! }]);
          setStreamingText("");
        }
        if (event.done) {
          // The backend's terminal Final Answer step never emits its own
          // step_complete event — cleared unconditionally here so a stale
          // "thinking" box never lingers after a live run's own completion.
          setStreamingText("");
          setStatus(event.status ?? null);
          if (event.final_answer) setFinalAnswer(event.final_answer);
          if (event.approval_request_id) setApprovalId(event.approval_request_id);
          if (event.detail) setDetail(event.detail);
          loadRuns();
        }
      }
    } catch (err) {
      setStatus("FAILED");
      setFinalAnswer(err instanceof Error ? err.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const escalate = async () => {
    if (!activeRunId || escalating) return;
    setEscalating(true);
    try {
      const result = await api.post<{ final_answer: string }>(`/api/agent/runs/${activeRunId}/escalate`);
      setFinalAnswer(result.final_answer);
      setStatus("COMPLETED");
      loadRuns();
    } catch (err) {
      setFinalAnswer((prev) => `${prev}\n\n⚠ ${err instanceof Error ? err.message : "escalation failed"}`);
    } finally {
      setEscalating(false);
    }
  };

  const canEscalate = status === "STOPPED_STEP_LIMIT" || status === "COMPLETED";

  return (
    <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] gap-6">
      <div>
        <div className="text-xs uppercase tracking-wide font-mono mb-2" style={{ color: "var(--text-muted)" }}>
          {t("console.pastRuns")}
        </div>
        <div className="space-y-1 max-h-[60vh] overflow-y-auto">
          {runs.map((r) => (
            <button
              key={r.id}
              onClick={() => openRun(r.id)}
              className="w-full text-left text-sm px-3 py-2 rounded-ledger-sm truncate block"
              style={{ background: activeRunId === r.id ? "var(--accent-soft)" : "transparent", color: activeRunId === r.id ? "var(--accent)" : "var(--text-secondary)" }}
            >
              {r.question}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h1 className="font-display font-bold text-2xl mb-1">{t("console.title")}</h1>
        <p style={{ color: "var(--text-secondary)" }}>{t("console.subtitle")}</p>

        <div className="mt-6 space-y-4">
          {steps.length === 0 && !streamingText && !finalAnswer && <EmptyState>{t("console.empty")}</EmptyState>}
          {steps.map((s, i) => (
            <div key={i} className={`card p-4 step-entry kind-${s.kind}`}>
              <div className="text-xs font-mono uppercase mb-1" style={{ color: "var(--text-muted)" }}>
                {t(KIND_LABEL[s.kind] ?? s.kind)} · {t("console.step")} {s.step_number}
              </div>
              <pre className="whitespace-pre-wrap text-sm font-sans">{s.content}</pre>
            </div>
          ))}
          {streamingText && (
            <div className="card p-4 step-entry kind-thought_action">
              <pre className="whitespace-pre-wrap text-sm font-sans">{streamingText}</pre>
              <span className="inline-block w-2 h-4 ml-1 animate-pulse" style={{ background: "var(--accent)" }} />
            </div>
          )}

          {status === "AWAITING_APPROVAL" && (
            <div className="card p-4 step-entry kind-awaiting_approval">
              <div className="text-sm font-medium" style={{ color: "var(--warning)" }}>
                ⏸ {t("console.status.AWAITING_APPROVAL")}
              </div>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
                This action needs a reviewer's sign-off before it can run — check the Approvals page.
              </p>
            </div>
          )}
          {finalAnswer && status === "COMPLETED" && (
            <div className="card p-4 step-entry kind-final_answer">
              <div className="text-xs font-mono uppercase mb-1" style={{ color: "var(--good)" }}>
                ✓ {t("console.finalAnswer")}
              </div>
              <pre className="whitespace-pre-wrap text-sm font-sans font-mono-num">{finalAnswer}</pre>
            </div>
          )}
          {status === "BLOCKED_PERMISSION" && (
            <div className="card p-4 step-entry kind-blocked">
              <div className="text-sm font-medium" style={{ color: "var(--critical)" }}>
                ■ {t("console.status.BLOCKED_PERMISSION")}
              </div>
              {detail && <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{detail}</p>}
            </div>
          )}
          {(status === "STOPPED_STEP_LIMIT" || status === "STOPPED_COST_CAP") && (
            <div className="card p-4 step-entry kind-blocked">
              <div className="text-sm font-medium" style={{ color: "var(--critical)" }}>
                ■ {t(`console.status.${status}`)}
              </div>
              {detail && <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{detail}</p>}
            </div>
          )}

          {canEscalate && (
            <button className="text-xs px-3 py-2 rounded-full" style={{ color: "var(--accent-2)", border: "1px solid var(--border-color)", background: "var(--surface-2)" }} disabled={escalating} onClick={escalate}>
              ☁ {t("console.useCloud")}
            </button>
          )}
        </div>

        <div className="flex gap-2 mt-6">
          <input
            className="flex-1 px-3 py-2.5 rounded-ledger-sm border"
            style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
            placeholder={t("console.placeholder")}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={busy}
          />
          <button className="btn-primary px-5 py-2.5" disabled={busy || !question.trim()} onClick={send}>
            {t("console.run")}
          </button>
        </div>
      </div>
    </div>
  );
}
