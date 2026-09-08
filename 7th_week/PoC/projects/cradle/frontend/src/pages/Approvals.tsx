import React, { useEffect, useState } from "react";

import { api } from "../api/client";
import { TiltCard } from "../components/TiltCard";
import { useI18n } from "../i18n";

interface Approval {
  id: number;
  run_id: number;
  tool_name: string;
  tool_arg: string;
  status: string;
  reason: string;
  requested_at: string;
  resolved_at: string | null;
}

export default function Approvals() {
  const { t } = useI18n();
  const [tab, setTab] = useState<"pending" | "all">("pending");
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [reasonById, setReasonById] = useState<Record<number, string>>({});

  const refresh = () => api.get<Approval[]>(`/api/approvals?status=${tab}`).then(setApprovals).catch(() => {});

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 6000);
    return () => window.clearInterval(id);
  }, [tab]);

  const decide = async (id: number, approve: boolean) => {
    setBusyId(id);
    try {
      await api.post(`/api/approvals/${id}/decide`, { approve, reason: reasonById[id] ?? "" });
      refresh();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight">{t("approvals.title")}</h1>
        <p className="text-ink-secondary mt-1 max-w-[70ch]">{t("approvals.subtitle")}</p>
      </div>

      <div className="flex gap-1 clay-inset rounded-full p-1 w-fit text-sm">
        {(["pending", "all"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-1.5 rounded-full ${tab === k ? "bg-accent-gradient text-white font-medium" : "text-ink-secondary"}`}
          >
            {t(`approvals.tab.${k}`)}
          </button>
        ))}
      </div>

      {approvals.length === 0 && <p className="text-sm text-ink-muted">{t("approvals.empty")}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {approvals.map((a) => (
          <TiltCard key={a.id} maxDeg={3}>
            <div className="clay p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-sm font-semibold text-accent">{a.tool_name}({a.tool_arg})</span>
                <span
                  className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${
                    a.status === "pending" ? "bg-warning/15 text-warning" : a.status === "approved" ? "bg-good/15 text-good" : "bg-critical/15 text-critical"
                  }`}
                >
                  {a.status}
                </span>
              </div>
              <p className="text-xs text-ink-muted font-mono">run #{a.run_id} · {new Date(a.requested_at).toLocaleString()}</p>
              {a.reason && <p className="text-xs text-ink-secondary mt-2">{a.reason}</p>}

              {a.status === "pending" && (
                <div className="mt-4 space-y-2">
                  <input
                    className="w-full px-3 py-2 rounded-full clay-inset bg-transparent text-xs outline-none"
                    placeholder={t("approvals.reasonPlaceholder")}
                    value={reasonById[a.id] ?? ""}
                    onChange={(e) => setReasonById((prev) => ({ ...prev, [a.id]: e.target.value }))}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(a.id, true)}
                      disabled={busyId === a.id}
                      className="flex-1 py-2 rounded-full bg-good/15 text-good text-xs font-medium hover:bg-good/25 disabled:opacity-50"
                    >
                      ✓ {t("approvals.approve")}
                    </button>
                    <button
                      onClick={() => decide(a.id, false)}
                      disabled={busyId === a.id}
                      className="flex-1 py-2 rounded-full bg-critical/15 text-critical text-xs font-medium hover:bg-critical/25 disabled:opacity-50"
                    >
                      ✕ {t("approvals.deny")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </TiltCard>
        ))}
      </div>
    </div>
  );
}
