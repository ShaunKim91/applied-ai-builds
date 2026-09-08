import { useEffect, useState } from "react";
import { api } from "../api/client";
import StatCard from "../components/StatCard";
import { useLang } from "../i18n";

type Tab = "users" | "audit" | "budget" | "metrics" | "errors" | "analytics";

interface UserRow {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  locked: boolean;
}
interface AuditRow {
  id: number;
  user_email: string;
  action: string;
  model_used: string;
  detail: string;
  latency_ms: number;
  status: string;
  created_at: string;
}
interface MetricRow {
  route: string;
  count: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}
interface ErrorRow {
  id: number;
  request_id: string;
  route: string;
  method: string;
  error_class: string;
  message: string;
  created_at: string;
}
interface Analytics {
  total_reports: number;
  by_mode: Record<string, number>;
  ghost_citation_failures: number;
  users: number;
  cat_events: number;
}

export default function Admin() {
  const { t } = useLang();
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("admin.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("admin.subtitle")}</p>

      <div className="flex flex-wrap gap-2 mt-4">
        {(["users", "audit", "budget", "metrics", "errors", "analytics"] as Tab[]).map((tb) => (
          <button
            key={tb}
            className="text-sm px-4 py-2 rounded-full border"
            style={{
              borderColor: "var(--border-color)",
              background: tab === tb ? "var(--accent)" : "var(--surface-2)",
              color: tab === tb ? "#fdfaf3" : "var(--text-secondary)",
              fontWeight: tab === tb ? 700 : 500,
            }}
            onClick={() => setTab(tb)}
          >
            {t(`admin.tab${tb.charAt(0).toUpperCase() + tb.slice(1)}`)}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "users" && <UsersTab t={t} />}
        {tab === "audit" && <AuditTab t={t} />}
        {tab === "budget" && <BudgetTab t={t} />}
        {tab === "metrics" && <MetricsTab t={t} />}
        {tab === "errors" && <ErrorsTab t={t} />}
        {tab === "analytics" && <AnalyticsTab t={t} />}
      </div>
    </div>
  );
}

function UsersTab({ t }: { t: (k: string) => string }) {
  const [users, setUsers] = useState<UserRow[]>([]);
  useEffect(() => {
    api.get<UserRow[]>("/api/admin/users").then(setUsers);
  }, []);
  return (
    <div className="card p-4 overflow-x-auto">
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Name</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td className="font-mono-num">{u.email}</td>
              <td>{u.display_name}</td>
              <td>
                <span className="badge">{u.role}</span>
              </td>
              <td>{u.locked ? <span className="badge badge-critical">locked</span> : u.is_active ? "active" : "inactive"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditTab({ t }: { t: (k: string) => string }) {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [verify, setVerify] = useState<{ intact: boolean; checked: number; first_broken_id: number | null } | null>(null);

  useEffect(() => {
    api.get<AuditRow[]>("/api/admin/audit-log").then(setRows);
  }, []);

  const runVerify = async () => {
    const r = await api.get<{ intact: boolean; checked: number; first_broken_id: number | null }>("/api/admin/audit-log/verify");
    setVerify(r);
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <button className="btn-secondary text-sm px-4 py-2" onClick={runVerify}>
          🔐 {t("admin.verifyIntegrity")}
        </button>
        {verify && (
          <span className="text-sm" style={{ color: verify.intact ? "var(--good)" : "var(--critical)" }}>
            {verify.intact ? t("admin.chainIntact") : t("admin.chainBroken").replace("{id}", String(verify.first_broken_id))}
          </span>
        )}
      </div>
      <div className="card p-4 overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Action</th>
              <th>Model</th>
              <th>Latency</th>
              <th>Status</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="font-mono-num">{r.user_email}</td>
                <td>{r.action}</td>
                <td className="text-xs">{r.model_used}</td>
                <td className="font-mono-num">{r.latency_ms.toFixed(0)}ms</td>
                <td>{r.status}</td>
                <td className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {new Date(r.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BudgetTab({ t }: { t: (k: string) => string }) {
  const [limit, setLimit] = useState(1);
  const [spent, setSpent] = useState(0);
  useEffect(() => {
    api.get<{ daily_limit_usd: number; spent_today_usd: number }>("/api/admin/budget").then((r) => {
      setLimit(r.daily_limit_usd);
      setSpent(r.spent_today_usd);
    });
  }, []);
  return (
    <div className="card p-5 max-w-sm">
      <label className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
        {t("admin.dailyLimit")}
      </label>
      <input
        type="number"
        step="0.01"
        className="w-full mt-1 mb-3 px-3 py-2 rounded-ledger-sm border font-mono-num"
        style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
        value={limit}
        onChange={(e) => setLimit(parseFloat(e.target.value))}
      />
      <p className="text-sm mb-3" style={{ color: "var(--text-secondary)" }}>
        {t("admin.spentToday")}: <span className="font-mono-num">${spent.toFixed(4)}</span>
      </p>
      <button className="btn-primary px-5 py-2" onClick={() => api.put("/api/admin/budget", { daily_limit_usd: limit })}>
        {t("admin.save")}
      </button>
    </div>
  );
}

function MetricsTab({ t }: { t: (k: string) => string }) {
  const [rows, setRows] = useState<MetricRow[]>([]);
  useEffect(() => {
    api.get<MetricRow[]>("/api/admin/metrics").then(setRows);
  }, []);
  return (
    <div className="card p-4 overflow-x-auto">
      <table>
        <thead>
          <tr>
            <th>{t("admin.route")}</th>
            <th>{t("admin.count")}</th>
            <th>{t("admin.p50")}</th>
            <th>{t("admin.p95")}</th>
            <th>{t("admin.p99")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.route}>
              <td className="font-mono-num text-xs">{r.route}</td>
              <td className="font-mono-num">{r.count}</td>
              <td className="font-mono-num">{r.p50_ms}ms</td>
              <td className="font-mono-num">{r.p95_ms}ms</td>
              <td className="font-mono-num">{r.p99_ms}ms</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ErrorsTab({ t }: { t: (k: string) => string }) {
  const [rows, setRows] = useState<ErrorRow[]>([]);
  useEffect(() => {
    api.get<ErrorRow[]>("/api/admin/errors").then(setRows);
  }, []);
  if (rows.length === 0) return <p style={{ color: "var(--text-muted)" }}>{t("admin.noErrors")}</p>;
  return (
    <div className="card p-4 overflow-x-auto">
      <table>
        <thead>
          <tr>
            <th>Route</th>
            <th>Error</th>
            <th>Message</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="font-mono-num text-xs">
                {r.method} {r.route}
              </td>
              <td>{r.error_class}</td>
              <td className="text-xs">{r.message}</td>
              <td className="text-xs" style={{ color: "var(--text-muted)" }}>
                {new Date(r.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AnalyticsTab({ t }: { t: (k: string) => string }) {
  const [a, setA] = useState<Analytics | null>(null);
  useEffect(() => {
    api.get<Analytics>("/api/admin/analytics").then(setA);
  }, []);
  if (!a) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label={t("dashboard.totalReports")} value={a.total_reports} />
      <StatCard label={t("dashboard.ghostFailures")} value={a.ghost_citation_failures} />
      <StatCard label="Users" value={a.users} />
      <StatCard label={t("dashboard.catEvents")} value={a.cat_events} />
    </div>
  );
}
