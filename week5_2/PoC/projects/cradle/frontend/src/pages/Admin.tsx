import React, { useEffect, useState } from "react";

import { api } from "../api/client";
import { BarChart } from "../components/BarChart";
import { useI18n } from "../i18n";

interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}
interface AuditEntry {
  id: number;
  user_email: string;
  action: string;
  model_used: string;
  detail: string;
  latency_ms: number;
  status: string;
  created_at: string;
}
interface SystemStatus {
  counts: Record<string, number>;
  models: Record<string, boolean>;
  vectorstore_backend: string;
  disk: { total_gb: number; used_gb: number; free_gb: number } | null;
}
interface Analytics {
  run_count: number;
  status_counts: Record<string, number>;
  avg_steps_to_completion: number | null;
  step_counts: number[];
  blocked_permission_count: number;
  awaiting_approval_count: number;
}
interface Guardrails {
  allowed_tools: string[];
  available_tools: string[];
  hitl_tools: string[];
  max_steps: number;
  cost_cap: number;
}
interface Budget {
  daily_limit_usd: number;
  spent_today_usd: number;
  remaining_usd: number;
  cap_reached: boolean;
}

export default function Admin() {
  const { t } = useI18n();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [guardrails, setGuardrails] = useState<Guardrails | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [budgetInput, setBudgetInput] = useState("");
  const [tab, setTab] = useState<"system" | "analytics" | "guardrails" | "budget" | "users" | "log">("system");

  const refresh = () => {
    api.get<AdminUser[]>("/api/admin/users").then(setUsers).catch(() => {});
    api.get<AuditEntry[]>("/api/admin/audit-log").then(setLogs).catch(() => {});
    api.get<SystemStatus>("/api/admin/system").then(setSystem).catch(() => {});
    api.get<Analytics>("/api/admin/analytics").then(setAnalytics).catch(() => {});
    api.get<Guardrails>("/api/admin/guardrails").then(setGuardrails).catch(() => {});
    api.get<Budget>("/api/admin/budget").then((b) => {
      setBudget(b);
      setBudgetInput(String(b.daily_limit_usd));
    }).catch(() => {});
  };

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 8000);
    return () => window.clearInterval(id);
  }, []);

  const toggleActive = async (u: AdminUser) => {
    await api.patch(`/api/admin/users/${u.id}`, { is_active: !u.is_active });
    refresh();
  };
  const toggleRole = async (u: AdminUser) => {
    await api.patch(`/api/admin/users/${u.id}`, { role: u.role === "admin" ? "user" : "admin" });
    refresh();
  };
  const toggleTool = (name: string) => {
    if (!guardrails) return;
    const has = guardrails.allowed_tools.includes(name);
    setGuardrails({
      ...guardrails,
      allowed_tools: has ? guardrails.allowed_tools.filter((t) => t !== name) : [...guardrails.allowed_tools, name],
    });
  };
  const saveGuardrails = async () => {
    if (!guardrails) return;
    await api.put("/api/admin/guardrails", {
      allowed_tools: guardrails.allowed_tools,
      max_steps: guardrails.max_steps,
      cost_cap: guardrails.cost_cap,
    });
    refresh();
  };
  const saveBudget = async () => {
    const value = Number(budgetInput);
    if (Number.isNaN(value) || value < 0) return;
    await api.put("/api/admin/budget", { daily_limit_usd: value });
    refresh();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">{t("admin.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("admin.subtitle")}</p>
      </div>

      <div className="flex gap-1 clay-inset rounded-full p-1 w-fit text-sm overflow-x-auto">
        {(["system", "analytics", "guardrails", "budget", "users", "log"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-1.5 rounded-full whitespace-nowrap ${tab === k ? "bg-accent-gradient text-white font-medium" : "text-ink-secondary"}`}
          >
            {t(`admin.tab.${k}`)}
          </button>
        ))}
      </div>

      {tab === "system" && system && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.recordCounts")}</h3>
            <dl className="text-sm space-y-1.5 font-mono">
              {Object.entries(system.counts).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink-muted">{k}</dt>
                  <dd className="tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.modelsLoaded")}</h3>
            <dl className="text-sm space-y-1.5">
              {Object.entries(system.models).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center">
                  <dt className="text-ink-muted font-mono">{k}</dt>
                  <dd>
                    <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${v ? "bg-good" : "bg-ink-muted"}`} />
                    {k === "openrouter_key_present" ? (v ? "key found" : "no key file") : v ? "loaded" : "not yet"}
                  </dd>
                </div>
              ))}
              <div className="flex justify-between pt-2 border-t border-edge">
                <dt className="text-ink-muted">{t("admin.vectorStoreBackend")}</dt>
                <dd className="font-mono">{system.vectorstore_backend}</dd>
              </div>
            </dl>
          </div>
          {system.disk && (
            <div className="clay-sm p-5 md:col-span-2">
              <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.disk")}</h3>
              <div className="text-sm font-mono">
                {system.disk.used_gb} GB / {system.disk.total_gb} GB ({system.disk.free_gb} GB free)
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "analytics" && analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="clay-sm p-5 md:col-span-2">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">
              {t("admin.stepsPerRun")} ({analytics.avg_steps_to_completion ?? "—"} {t("admin.avgSteps")})
            </h3>
            <BarChart values={analytics.step_counts} unit=" steps" />
          </div>
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.statusSplit")}</h3>
            <dl className="text-sm space-y-1.5 font-mono">
              {Object.entries(analytics.status_counts).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink-muted">{k}</dt>
                  <dd className="tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.guardrailActivity")}</h3>
            <div className="text-sm space-y-1.5">
              <div className="flex justify-between"><span className="text-ink-muted">{t("admin.blockedPermission")}</span><span className="tabular-nums font-mono">{analytics.blocked_permission_count}</span></div>
              <div className="flex justify-between"><span className="text-ink-muted">{t("admin.awaitingApproval")}</span><span className="tabular-nums font-mono">{analytics.awaiting_approval_count}</span></div>
            </div>
          </div>
        </div>
      )}

      {tab === "guardrails" && guardrails && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.allowedTools")}</h3>
            <div className="space-y-2">
              {guardrails.available_tools.map((tool) => (
                <label key={tool} className="flex items-center justify-between text-sm">
                  <span className="font-mono">
                    {tool}
                    {guardrails.hitl_tools.includes(tool) && <span className="ml-1.5 text-[10px] text-warning">HITL</span>}
                  </span>
                  <input type="checkbox" checked={guardrails.allowed_tools.includes(tool)} onChange={() => toggleTool(tool)} />
                </label>
              ))}
            </div>
          </div>
          <div className="clay-sm p-5 space-y-4">
            <div>
              <label className="text-sm text-ink-secondary block mb-1">{t("admin.maxSteps")}</label>
              <input
                type="number"
                value={guardrails.max_steps}
                onChange={(e) => setGuardrails({ ...guardrails, max_steps: Number(e.target.value) })}
                className="w-24 px-3 py-1.5 rounded-full clay-inset bg-transparent text-sm font-mono outline-none"
              />
            </div>
            <div>
              <label className="text-sm text-ink-secondary block mb-1">{t("admin.costCap")}</label>
              <input
                type="number"
                value={guardrails.cost_cap}
                onChange={(e) => setGuardrails({ ...guardrails, cost_cap: Number(e.target.value) })}
                className="w-24 px-3 py-1.5 rounded-full clay-inset bg-transparent text-sm font-mono outline-none"
              />
            </div>
            <button onClick={saveGuardrails} className="text-xs px-4 py-2 rounded-full bg-accent-gradient text-white font-medium shadow-clay-sm">
              {t("admin.save")}
            </button>
          </div>
        </div>
      )}

      {tab === "budget" && budget && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.dailyBudget")}</h3>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-ink-muted font-mono text-sm">$</span>
              <input value={budgetInput} onChange={(e) => setBudgetInput(e.target.value)} className="w-24 px-3 py-1.5 rounded-full clay-inset bg-transparent text-sm font-mono outline-none" />
              <button onClick={saveBudget} className="text-xs px-3 py-1.5 rounded-full bg-accent-gradient text-white">
                {t("admin.save")}
              </button>
            </div>
            <p className="text-xs text-ink-muted">{t("admin.budgetHint")}</p>
          </div>
          <div className="clay-sm p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.spentToday")}</h3>
            <div className="text-2xl font-display font-bold tabular-nums">${budget.spent_today_usd.toFixed(4)}</div>
            <div className="w-full h-2 rounded-full clay-inset mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${budget.cap_reached ? "bg-critical" : "bg-accent-gradient"}`}
                style={{ width: `${Math.min(100, (budget.spent_today_usd / Math.max(budget.daily_limit_usd, 0.0001)) * 100)}%` }}
              />
            </div>
            <p className="text-xs text-ink-muted mt-2">
              {t("admin.remaining")}: ${budget.remaining_usd.toFixed(4)}
              {budget.cap_reached && <span className="text-critical ml-2">⚠ {t("admin.capReached")}</span>}
            </p>
          </div>
        </div>
      )}

      {tab === "users" && (
        <div className="clay-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted border-b border-edge font-mono text-xs uppercase">
                <th className="p-3">Email</th>
                <th className="p-3">Name</th>
                <th className="p-3">{t("admin.role")}</th>
                <th className="p-3">{t("admin.active")}</th>
                <th className="p-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-edge last:border-0">
                  <td className="p-3">{u.email}</td>
                  <td className="p-3">{u.display_name}</td>
                  <td className="p-3">
                    <button onClick={() => toggleRole(u)} className="px-2 py-0.5 rounded-full clay-inset text-xs">
                      {u.role}
                    </button>
                  </td>
                  <td className="p-3">
                    <button onClick={() => toggleActive(u)} className={`px-2 py-0.5 rounded-full text-xs ${u.is_active ? "bg-good/15 text-good" : "bg-critical/15 text-critical"}`}>
                      {u.is_active ? "active" : "disabled"}
                    </button>
                  </td>
                  <td className="p-3 text-ink-muted font-mono text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "log" && (
        <div className="clay-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted border-b border-edge font-mono text-xs uppercase">
                <th className="p-3">Time</th>
                <th className="p-3">User</th>
                <th className="p-3">Action</th>
                <th className="p-3">Model</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-edge last:border-0">
                  <td className="p-3 text-ink-muted whitespace-nowrap font-mono text-xs">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="p-3">{l.user_email}</td>
                  <td className="p-3">{l.action}</td>
                  <td className="p-3 text-ink-muted font-mono text-xs">{l.model_used}</td>
                  <td className="p-3">
                    <span className={l.status === "success" ? "text-good" : "text-critical"}>{l.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
