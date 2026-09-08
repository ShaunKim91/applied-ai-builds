import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface LibraryResponse {
  total: number;
  duplicate_count: number;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [receiptCount, setReceiptCount] = useState<number | null>(null);
  const [pdfCount, setPdfCount] = useState<number | null>(null);
  const [tableCount, setTableCount] = useState<number | null>(null);
  const [duplicates, setDuplicates] = useState<number | null>(null);

  useEffect(() => {
    api.get<unknown[]>("/api/receipts").then((r) => setReceiptCount(r.length)).catch(() => {});
    api.get<unknown[]>("/api/pdfs").then((r) => setPdfCount(r.length)).catch(() => {});
    api.get<unknown[]>("/api/tables").then((r) => setTableCount(r.length)).catch(() => {});
    api.get<LibraryResponse>("/api/library").then((r) => setDuplicates(r.duplicate_count)).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-display-md">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t("dashboard.receipts")} value={receiptCount ?? "…"} />
        <StatCard label={t("dashboard.pdfs")} value={pdfCount ?? "…"} />
        <StatCard label={t("dashboard.tables")} value={tableCount ?? "…"} />
        <StatCard label={t("dashboard.duplicates")} value={duplicates ?? "…"} hint={t("dashboard.duplicatesHint")} />
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("dashboard.quickActions")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { to: "/receipts", icon: "🧾", label: "nav.receipts" },
            { to: "/pdfs", icon: "📄", label: "nav.pdfs" },
            { to: "/tables", icon: "🌐", label: "nav.tables" },
            { to: "/library", icon: "🗂️", label: "nav.library" },
          ].map((a) => (
            <Link key={a.to} to={a.to} className="card p-5 hover:shadow-paper-lg transition-shadow text-center">
              <div className="text-2xl mb-2">{a.icon}</div>
              <div className="text-sm font-medium">{t(a.label)}</div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
