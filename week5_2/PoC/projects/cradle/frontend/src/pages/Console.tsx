import React, { useEffect, useRef, useState } from "react";

import { api, streamPost } from "../api/client";
import { TiltCard } from "../components/TiltCard";
import { useI18n } from "../i18n";

interface Step {
  step_number: number;
  kind: string;
  content: string;
}
interface RunSummary {
  id: number;
  question: string;
  status: string;
}
interface RunDetail {
  id: number;
  question: string;
  status: string;
  final_answer: string;
  step_count: number;
  spent_cost: number;
  cost_cap: number;
  synth_mode: string;
  steps: Step[];
}

const KIND_LABEL: Record<string, string> = {
  thought_action: "Thought → Action",
  observation: "Observation",
  final_answer: "Final Answer",
  blocked: "Guardrail Stop",
  awaiting_approval: "Awaiting Approval",
  cloud_escalation: "Cloud Escalation",
};

const KIND_COLOR: Record<string, string> = {
  thought_action: "text-accent",
  observation: "text-accent-2",
  final_answer: "text-good",
  blocked: "text-critical",
  awaiting_approval: "text-warning",
  cloud_escalation: "text-accent",
};

function StepCard({ step, index }: { step: Step; index: number }) {
  const tilt = index % 2 === 0 ? -0.5 : 0.5;
  return (
    <div className="step-card clay-sm p-4" style={{ "--tilt": `${tilt}deg` } as React.CSSProperties}>
      <div className={`text-[11px] font-mono uppercase tracking-wide mb-1.5 ${KIND_COLOR[step.kind] ?? "text-ink-muted"}`}>
        {KIND_LABEL[step.kind] ?? step.kind} · step {step.step_number}
      </div>
      <div className="text-sm whitespace-pre-wrap leading-relaxed">{step.content}</div>
    </div>
  );
}

export default function Console() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [approvalId, setApprovalId] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadRuns = () => api.get<RunSummary[]>("/api/agent/runs").then(setRuns).catch(() => {});

  useEffect(() => {
    loadRuns();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps, streamingText]);

  const openRun = async (id: number) => {
    const run = await api.get<RunDetail>(`/api/agent/runs/${id}`);
    setActiveRunId(run.id);
    // The backend persists a "final_answer"-kind AgentStep for a completed
    // run (so the raw trace/audit record is complete) — but the dedicated
    // "✓ Final Answer" card below is the one place that answer is shown in
    // this UI. Reloading a past run without this filter duplicated it:
    // once as an ordinary step-card, once as the dedicated card. The live
    // streaming path never has this problem (the backend's Final Answer
    // step never emits its own step_complete event), so this filter keeps
    // both paths rendering identically. See debug/issue-02.
    setSteps(run.steps.filter((s) => s.kind !== "final_answer"));
    setStatus(run.status);
    setFinalAnswer(run.final_answer);
    setStreamingText("");
    setApprovalId(null);
  };

  const send = async () => {
    const q = question.trim();
    if (!q || busy) return;
    setQuestion("");
    setBusy(true);
    setSteps([]);
    setStreamingText("");
    setStatus("RUNNING");
    setFinalAnswer("");
    setApprovalId(null);

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
          // Use the backend's own step_count (one Thought/Action+Observation
          // cycle = one number, matching how a reopened past run numbers its
          // persisted AgentStep rows in openRun() below) rather than a raw
          // card-index counter. The two disagreed until this fix: a live run
          // showed "OBSERVATION · STEP 2" for a thought_action+observation
          // pair that, once persisted and reopened, showed "OBSERVATION ·
          // STEP 1" — the same run displaying different step numbers
          // depending on how you looked at it. Falls back to a card-index
          // counter only if an older backend build omits step_count.
          setSteps((prev) => [
            ...prev,
            { step_number: event.step_count ?? prev.length + 1, kind: event.kind!, content: event.content! },
          ]);
          setStreamingText("");
        }
        if (event.done) {
          // The backend's terminal "Final Answer" step never emits its own
          // step_complete event (see agent/orchestrator.py — it goes
          // straight from streaming deltas to 'done') — so without this,
          // the raw in-progress "Thinking…" box (still showing the literal
          // "Final Answer: ..." text plus a permanently-blinking cursor)
          // was left stale on screen forever, duplicating the real Final
          // Answer card rendered below it. Confirmed by direct observation:
          // the stale box persisted unchanged for 30+ seconds after
          // completion before this fix.
          setStreamingText("");
          setStatus(event.status ?? null);
          if (event.final_answer) setFinalAnswer(event.final_answer);
          if (event.approval_request_id) setApprovalId(event.approval_request_id);
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
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      <div className="clay w-52 shrink-0 p-3 hidden lg:flex lg:flex-col">
        <h2 className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2 px-1">{t("console.pastRuns")}</h2>
        <div className="flex-1 overflow-y-auto space-y-1">
          {runs.map((r) => (
            <button
              key={r.id}
              onClick={() => openRun(r.id)}
              className={`w-full text-left px-2.5 py-2 rounded-xl text-xs truncate ${
                r.id === activeRunId ? "bg-accent-soft text-accent font-medium" : "text-ink-secondary hover:bg-accent-soft"
              }`}
            >
              {r.question}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 clay p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-edge">
          <h1 className="font-display text-lg font-bold">{t("console.title")}</h1>
          <p className="text-xs text-ink-secondary">{t("console.subtitle")}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-3">
          {steps.length === 0 && !streamingText && <p className="text-sm text-ink-muted text-center mt-12">{t("console.empty")}</p>}

          {steps.map((s, i) => (
            <StepCard key={i} step={s} index={i} />
          ))}

          {streamingText && (
            <div className="step-card clay-sm p-4">
              <div className="text-[11px] font-mono uppercase tracking-wide mb-1.5 text-ink-muted">{t("console.thinking")}</div>
              <div className="text-sm whitespace-pre-wrap leading-relaxed">
                {streamingText}
                <span className="animate-pulse">▌</span>
              </div>
            </div>
          )}

          {status === "AWAITING_APPROVAL" && (
            <div className="clay-sm p-4 border-2 border-warning/40">
              <div className="text-sm font-medium text-warning">⏸ {t("console.awaitingApproval")}</div>
              <p className="text-xs text-ink-secondary mt-1">{t("console.awaitingApprovalHint")}</p>
            </div>
          )}

          {finalAnswer && status === "COMPLETED" && (
            <TiltCard maxDeg={3}>
              <div className="clay p-5 border-2 border-good/30">
                <div className="text-[11px] font-mono uppercase tracking-wide mb-1.5 text-good">✓ {t("console.finalAnswer")}</div>
                <p className="text-sm font-display leading-relaxed">{finalAnswer}</p>
              </div>
            </TiltCard>
          )}

          {status && status.startsWith("STOPPED") && (
            <div className="clay-sm p-4 border-2 border-critical/30">
              <div className="text-sm font-medium text-critical">■ {t(`console.status.${status}`)}</div>
            </div>
          )}
          {status === "BLOCKED_PERMISSION" && (
            <div className="clay-sm p-4 border-2 border-critical/30">
              <div className="text-sm font-medium text-critical">■ {t("console.status.BLOCKED_PERMISSION")}</div>
            </div>
          )}

          {canEscalate && (
            <button
              onClick={escalate}
              disabled={escalating}
              className="text-xs px-3 py-2 rounded-full clay-inset text-accent hover:bg-accent-soft disabled:opacity-50"
            >
              {escalating ? t("console.escalating") : `☁ ${t("console.escalate")}`}
            </button>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-6 py-4 border-t border-edge">
          <div className="flex gap-2">
            <input
              className="flex-1 px-4 py-2.5 rounded-full clay-inset bg-transparent text-sm outline-none"
              placeholder={t("console.placeholder")}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy || !question.trim()}
              className="px-5 py-2.5 rounded-full bg-accent-gradient text-white text-sm font-medium disabled:opacity-50 shadow-clay-sm"
            >
              {t("console.send")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
