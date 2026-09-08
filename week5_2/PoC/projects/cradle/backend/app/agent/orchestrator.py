"""The single ReAct-loop-plus-guardrails engine, shared by both entry
points that can drive a run forward:

  1. routers/agent.py's initial POST — streamed live to the browser as SSE.
  2. routers/approvals.py's decide() — resumes a run that paused for human
     approval, potentially much later, with no open connection to stream
     to; it just drains this same generator and returns the final result.

Both consume the *same* generator function so the guardrail-check order,
persistence shape, and stopping conditions can never drift between the
"fresh run" and "resumed run" code paths — the exact kind of two-path
duplication that has caused real, documented bugs in prior weeks of this
project (Week4's debug/issue-02: two endpoints returning differently-
shaped data for what should be the same underlying event).

Each fresh SessionLocal() is opened here rather than relying on a
Depends()-injected session, for the same reason Week4's Lucent PoC
documents: a dependency-injected session closes when the route handler
*returns*, which happens before a StreamingResponse generator body has
actually finished running.
"""
import json

from .. import models
from ..config import settings
from ..database import SessionLocal
from . import guardrails, react_loop, tools


def _persist_step(db, run_id: int, step_number: int, kind: str, content: str) -> None:
    db.add(models.AgentStep(run_id=run_id, step_number=step_number, kind=kind, content=content))
    db.commit()


def get_guardrail_settings(db) -> models.GuardrailSetting:
    row = db.get(models.GuardrailSetting, 1)
    if not row:
        row = models.GuardrailSetting(
            id=1,
            allowed_tools_json=json.dumps(sorted(tools.ALLOWED_TOOLS.keys())),
            max_steps=settings.default_max_steps,
            cost_cap=settings.default_cost_cap,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def run_react_loop(run_id: int, resume_injection: dict | None = None):
    """Yields plain dict events (the caller decides how to serialize them —
    SSE lines for a live stream, or just the last one for a synchronous
    resume). `resume_injection`, when given, is
    {"kind": "observation"|"blocked", "content": str, "observation_message": str,
    "new_spent": int} — the result of a just-resolved approval decision,
    injected before the loop continues generating the NEXT step."""
    db = SessionLocal()
    try:
        run = db.get(models.AgentRun, run_id)
        messages = json.loads(run.messages_json)
        step_count = run.step_count
        spent = run.spent_cost
        gset = get_guardrail_settings(db)
        allowed_tools = set(json.loads(gset.allowed_tools_json))
        tool_cost = settings.default_tool_cost

        if resume_injection is not None:
            messages.append({"role": "user", "content": resume_injection["observation_message"]})
            spent = resume_injection.get("new_spent", spent)
            _persist_step(db, run_id, step_count, resume_injection["kind"], resume_injection["content"])
            run.status = "RUNNING"
            run.spent_cost = spent
            db.commit()
            yield {"step_complete": True, "kind": resume_injection["kind"], "content": resume_injection["content"], "step_count": step_count}

        while True:
            step_count += 1
            fragments: list[str] = []
            for fragment in react_loop.stream_one_step(messages):
                fragments.append(fragment)
                yield {"delta": fragment}
            raw = "".join(fragments)
            gen = react_loop.truncate_generation(raw) or raw.strip()

            if "Final Answer:" in gen:
                final = gen.split("Final Answer:", 1)[1].strip()
                messages.append({"role": "assistant", "content": gen})
                _persist_step(db, run_id, step_count, "final_answer", final)
                run.status = "COMPLETED"
                run.final_answer = final
                run.step_count = step_count
                run.messages_json = json.dumps(messages)
                db.commit()
                yield {"done": True, "status": "COMPLETED", "final_answer": final, "step_count": step_count, "run_id": run_id}
                return

            action = react_loop.parse_action(gen)
            messages.append({"role": "assistant", "content": gen})
            _persist_step(db, run_id, step_count, "thought_action", gen)
            yield {"step_complete": True, "kind": "thought_action", "content": gen, "step_count": step_count}

            if action is None:
                messages.append({"role": "user", "content": "Observation: (format error — please retry with the exact Action format)"})
                run.step_count = step_count
                run.messages_json = json.dumps(messages)
                db.commit()
                continue

            tool_name, arg = action
            verdict = guardrails.check_guardrails(
                tool_name,
                step_count=step_count,
                max_steps=run.max_steps,
                allowed_tools=allowed_tools,
                tool_cost=tool_cost,
                spent=spent,
                cost_cap=run.cost_cap,
                hitl_tools=tools.HITL_TOOL_NAMES,
            )

            if verdict.status == "AWAITING_APPROVAL":
                run.status = "AWAITING_APPROVAL"
                run.step_count = step_count
                run.messages_json = json.dumps(messages)
                db.commit()
                approval = models.ApprovalRequest(run_id=run_id, tool_name=tool_name, tool_arg=arg, status="pending")
                db.add(approval)
                db.commit()
                db.refresh(approval)
                _persist_step(db, run_id, step_count, "awaiting_approval", f"{tool_name}({arg})")
                yield {"done": True, "status": "AWAITING_APPROVAL", "approval_request_id": approval.id, "step_count": step_count, "run_id": run_id}
                return

            if verdict.status in ("BLOCKED_PERMISSION", "STOPPED_STEP_LIMIT", "STOPPED_COST_CAP"):
                _persist_step(db, run_id, step_count, "blocked", verdict.detail)
                run.status = verdict.status
                run.step_count = step_count
                run.messages_json = json.dumps(messages)
                db.commit()
                yield {"done": True, "status": verdict.status, "detail": verdict.detail, "step_count": step_count, "run_id": run_id}
                return

            # ALLOWED
            result = guardrails.execute_tool(tool_name, arg)
            spent += verdict.cost
            messages.append({"role": "user", "content": f"Observation: {result}"})
            _persist_step(db, run_id, step_count, "observation", result)
            run.step_count = step_count
            run.spent_cost = spent
            run.messages_json = json.dumps(messages)
            db.commit()
            yield {"step_complete": True, "kind": "observation", "content": result, "step_count": step_count}
    finally:
        db.close()
