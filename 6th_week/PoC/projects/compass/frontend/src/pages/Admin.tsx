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
  report_count: number;
  latencies_ms: number[];
  avg_latency_ms: number | null;
  groundedness_pass_rate: number | null;
  search_mode_counts: Record<string, number>;
  synth_mode_counts: Record<string, number>;
  reports_with_ghost_citations: number;
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
  const [budget, setBudget] = useState<Budget | null>(null);
  const [budgetInput, setBudgetInput] = useState("");
  const [searchCheck, setSearchCheck] = useState<{ mode: string; ok: boolean } | null>(null);
  const [tab, setTab] = useState<"system" | "analytics" | "budget" | "users" | "log">("system");

  const refresh = () => {
    api.get<AdminUser[]>("/api/admin/users").then(setUsers).catch(() => {});
    api.get<AuditEntry[]>("/api/admin/audit-log").then(setLogs).catch(() => {});
    api.get<SystemStatus>("/api/admin/system").then(setSystem).catch(() => {});
    api.get<Analytics>("/api/admin/analytics").then(setAnalytics).catch(() => {});
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
  const saveBudget = async () => {
    const value = Number(budgetInput);
    if (Number.isNaN(value) || value < 0) return;
    await api.put("/api/admin/budget", { daily_limit_usd: value });
    refresh();
  };
  const runSearchCheck = async () => {
    setSearchCheck(await api.get("/api/admin/web-search-check"));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{t("admin.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("admin.subtitle")}</p>
      </div>

      <div className="flex gap-1 border-b border-edge text-sm overflow-x-auto">
        {(["system", "analytics", "budget", "users", "log"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-2 border-b-2 -mb-px whitespace-nowrap ${
              tab === k ? "border-accent text-accent font-semibold" : "border-transparent text-ink-secondary"
            }`}
          >
            {t(`admin.tab.${k}`)}
          </button>
        ))}
      </div>

      {tab === "system" && system && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card p-5">
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
          <div className="card p-5">
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
          <div className="card p-5 md:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-ink-secondary">{t("admin.webSearchCheck")}</h3>
              <button onClick={runSearchCheck} className="text-xs px-2.5 py-1 rounded-full border border-edge hover:bg-accent-soft">
                {t("admin.recheck")}
              </button>
            </div>
            {searchCheck && (
              <div className="text-sm font-mono flex items-center gap-2">
                <span className={`inline-block w-2 h-2 rounded-full ${searchCheck.ok ? "bg-good" : "bg-warning"}`} />
                mode={searchCheck.mode}
              </div>
            )}
          </div>
          {system.disk && (
            <div className="card p-5 md:col-span-2">
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
          <div className="card p-5 md:col-span-2">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">
              {t("admin.recentLatency")} ({analytics.avg_latency_ms ?? "—"} ms avg)
            </h3>
            <BarChart values={analytics.latencies_ms} unit=" ms" />
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.groundednessRate")}</h3>
            <div className="text-3xl font-display font-semibold tabular-nums">
              {analytics.groundedness_pass_rate !== null ? `${Math.round(analytics.groundedness_pass_rate * 100)}%` : "—"}
            </div>
            <p className="text-xs text-ink-muted mt-1">{t("admin.reportCount").replace("{n}", String(analytics.report_count))}</p>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.ghostCitationRate")}</h3>
            <div className="text-3xl font-display font-semibold tabular-nums text-warning">
              {analytics.reports_with_ghost_citations}
            </div>
            <p className="text-xs text-ink-muted mt-1">{t("admin.reportsFlagged")}</p>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.searchModeSplit")}</h3>
            <dl className="text-sm space-y-1.5 font-mono">
              {Object.entries(analytics.search_mode_counts).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink-muted">{k}</dt>
                  <dd className="tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.synthModeSplit")}</h3>
            <dl className="text-sm space-y-1.5 font-mono">
              {Object.entries(analytics.synth_mode_counts).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-ink-muted">{k}</dt>
                  <dd className="tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}

      {tab === "budget" && budget && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.dailyBudget")}</h3>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-ink-muted font-mono text-sm">$</span>
              <input
                value={budgetInput}
                onChange={(e) => setBudgetInput(e.target.value)}
                className="w-24 px-2 py-1 rounded-lg border border-edge bg-transparent text-sm font-mono"
              />
              <button onClick={saveBudget} className="text-xs px-3 py-1.5 rounded-full bg-accent-gradient text-white">
                {t("admin.save")}
              </button>
            </div>
            <p className="text-xs text-ink-muted">{t("admin.budgetHint")}</p>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-ink-secondary mb-3">{t("admin.spentToday")}</h3>
            <div className="text-2xl font-display font-semibold tabular-nums">${budget.spent_today_usd.toFixed(4)}</div>
            <div className="w-full h-2 rounded-full bg-surface2 mt-3 overflow-hidden">
              <div
                className={`h-full ${budget.cap_reached ? "bg-critical" : "bg-accent-gradient"}`}
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
        <div className="card overflow-x-auto">
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
                    <button onClick={() => toggleRole(u)} className="px-2 py-0.5 rounded-full border border-edge text-xs">
                      {u.role}
                    </button>
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => toggleActive(u)}
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        u.is_active ? "bg-good/15 text-good" : "bg-critical/15 text-critical"
                      }`}
                    >
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
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted border-b border-edge font-mono text-xs uppercase">
                <th className="p-3">Time</th>
                <th className="p-3">User</th>
                <th className="p-3">Action</th>
                <th className="p-3">Model</th>
                <th className="p-3">Latency</th>
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
                  <td className="p-3 tabular-nums font-mono text-xs">{l.latency_ms.toFixed(0)}ms</td>
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
