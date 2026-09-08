import { useEffect, useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useLang } from "../i18n";

interface Approval {
  id: number;
  run_id: number;
  tool_name: string;
  tool_arg: string;
  status: string;
  reason: string;
  requested_at: string;
}

export default function Approvals() {
  const { t } = useLang();
  const [tab, setTab] = useState<"pending" | "all">("pending");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [reasons, setReasons] = useState<Record<number, string>>({});

  const load = () => api.get<Approval[]>(`/api/approvals?status=${tab}`).then(setApprovals);
  useEffect(() => {
    load();
  }, [tab]);

  const decide = async (id: number, approve: boolean) => {
    await api.post(`/api/approvals/${id}/decide`, { approve, reason: reasons[id] || "" });
    load();
  };

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("approvals.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("approvals.subtitle")}</p>

      <div className="flex gap-2 mt-4">
        <button className="text-sm px-4 py-2 rounded-full border" style={{ borderColor: "var(--border-color)", background: tab === "pending" ? "var(--accent)" : "var(--surface-2)", color: tab === "pending" ? "#fdfaf3" : "var(--text-secondary)" }} onClick={() => setTab("pending")}>
          {t("approvals.pending")}
        </button>
        <button className="text-sm px-4 py-2 rounded-full border" style={{ borderColor: "var(--border-color)", background: tab === "all" ? "var(--accent)" : "var(--surface-2)", color: tab === "all" ? "#fdfaf3" : "var(--text-secondary)" }} onClick={() => setTab("all")}>
          {t("approvals.all")}
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {approvals.length === 0 && <EmptyState>{t("approvals.empty")}</EmptyState>}
        {approvals.map((a) => (
          <div key={a.id} className="card p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-mono-num font-medium">
                  {a.tool_name}({a.tool_arg})
                </div>
                <div className="text-xs font-mono mt-1" style={{ color: "var(--text-muted)" }}>
                  run #{a.run_id} · {new Date(a.requested_at).toLocaleString()}
                </div>
              </div>
              <span className={`badge ${a.status === "pending" ? "badge-warning" : a.status === "approved" ? "badge-good" : "badge-critical"}`}>{a.status}</span>
            </div>
            {a.status === "pending" && (
              <>
                <input
                  className="w-full mt-3 px-3 py-2 rounded-ledger-sm border text-sm"
                  style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
                  placeholder={t("approvals.reason")}
                  value={reasons[a.id] || ""}
                  onChange={(e) => setReasons({ ...reasons, [a.id]: e.target.value })}
                />
                <div className="flex gap-3 mt-3">
                  <button className="text-sm font-medium" style={{ color: "var(--good)" }} onClick={() => decide(a.id, true)}>
                    {t("approvals.approve")}
                  </button>
                  <button className="text-sm font-medium" style={{ color: "var(--critical)" }} onClick={() => decide(a.id, false)}>
                    {t("approvals.deny")}
                  </button>
                </div>
              </>
            )}
            {a.reason && a.status !== "pending" && (
              <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
                {a.reason}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
