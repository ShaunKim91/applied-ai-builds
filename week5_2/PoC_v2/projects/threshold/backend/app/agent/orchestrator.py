"""The resumable ReAct loop engine — one shared generator function consumed
two different ways: live-streamed as SSE for a fresh run
(`routers/agent.py::create_run`), or drained synchronously (no live
connection) to resume a run that paused for Human-in-the-Loop approval,
potentially long after the original request ended
(`routers/approvals.py::decide`). `AgentRun.messages_json` snapshots the
full LLM conversation state needed to resume exactly where a paused run
left off.

Opens its own fresh `SessionLocal()` rather than relying on a
`Depends(get_db)`-injected session — a dependency-injected session closes
when the route handler *returns*, which happens before a StreamingResponse
generator body has finished running. Same lesson already applied in the
predecessor Cradle PoC, carried forward here rather than rediscovered.
"""
import json

from .. import models
from ..database import SessionLocal
from . import guardrails, react_loop, tools


def get_guardrail_settings(db):
    org_id = db.query(models.Organization.id).scalar()
    row = db.query(models.GuardrailSetting).filter(models.GuardrailSetting.org_id == org_id).first()
    if not row:
        from ..config import settings

        row = models.GuardrailSetting(
            org_id=org_id,
            allowed_tools_json=json.dumps(sorted(tools.ALLOWED_TOOLS.keys())),
            max_steps=settings.default_max_steps,
            cost_cap=settings.default_cost_cap,
            payout_approval_threshold_usd=settings.payout_approval_threshold_usd,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _persist_step(db, run_id: int, step_number: int, kind: str, content: str) -> None:
    db.add(models.AgentStep(run_id=run_id, step_number=step_number, kind=kind, content=content))


def run_react_loop(run_id: int, resume_injection: dict | None = None):
    """resume_injection: {"kind": str, "content": str, "observation_message":
    str, "new_spent": int} — the result of a just-resolved approval decision,
    injected before the loop continues generating the NEXT step. Each
    yielded event includes 'step_count' (Threshold numbers a whole
    thought_action+observation cycle as ONE step, matching the persisted
    AgentStep numbering, so a live view and a reopened view always agree —
    the exact bug class the predecessor Cradle PoC found and fixed, applied
    correctly here from the start)."""
    db = SessionLocal()
    try:
        run = db.get(models.AgentRun, run_id)
        messages = json.loads(run.messages_json)
        step_count = run.step_count
        spent = run.spent_cost
        gset = get_guardrail_settings(db)
        allowed_tools = set(json.loads(gset.allowed_tools_json))
        from ..config import settings

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
                arg,
                step_count=step_count,
                max_steps=run.max_steps,
                allowed_tools=allowed_tools,
                tool_cost=tool_cost,
                spent=spent,
                cost_cap=run.cost_cap,
                hitl_tools=tools.HITL_TOOL_NAMES,
                payout_approval_threshold_usd=gset.payout_approval_threshold_usd,
            )

            if verdict.status == "AWAITING_APPROVAL":
                run.status = "AWAITING_APPROVAL"
                run.step_count = step_count
                run.messages_json = json.dumps(messages)
                db.commit()
                approval = models.ApprovalRequest(run_id=run_id, tool_name=tool_name, tool_arg=arg, status="pending", reason=verdict.detail)
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
