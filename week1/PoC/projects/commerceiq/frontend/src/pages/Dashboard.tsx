import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import { StatCard } from "../components/StatCard";
import { useI18n } from "../i18n";

interface CatalogItem {
  id: number;
  label: string;
  confidence: number;
  image_url: string;
}
interface ForecastRun {
  id: number;
  mae: number | null;
  mape: number | null;
  anomaly_count: number;
  created_at: string;
}

export default function Dashboard() {
  const { t } = useI18n();
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [galleryCount, setGalleryCount] = useState<number | null>(null);
  const [runs, setRuns] = useState<ForecastRun[]>([]);
  const [searchBackend, setSearchBackend] = useState<string>("…");

  useEffect(() => {
    api.get<CatalogItem[]>("/api/vision/catalog").then(setCatalog).catch(() => {});
    api.get<unknown[]>("/api/generate/gallery").then((g) => setGalleryCount(g.length)).catch(() => {});
    api.get<ForecastRun[]>("/api/forecast/runs").then(setRuns).catch(() => {});
    api.get<{ backend: string }>("/api/search/status").then((s) => setSearchBackend(s.backend)).catch(() => {});
  }, []);

  const lastRun = runs[0];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t("dashboard.catalogItems")} value={catalog.length} />
        <StatCard label={t("dashboard.generatedImages")} value={galleryCount ?? "…"} />
        <StatCard
          label={t("dashboard.forecastRuns")}
          value={runs.length}
          hint={lastRun ? `MAE ${lastRun.mae?.toFixed(1)} · MAPE ${lastRun.mape?.toFixed(1)}%` : undefined}
        />
        <StatCard label={t("dashboard.vectorBackend")} value={searchBackend} />
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("dashboard.quickActions")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { to: "/vision", icon: "🖼️", label: "nav.vision" },
            { to: "/generate", icon: "🎨", label: "nav.generate" },
            { to: "/forecast", icon: "📈", label: "nav.forecast" },
            { to: "/search", icon: "🔎", label: "nav.search" },
          ].map((a) => (
            <Link key={a.to} to={a.to} className="card p-5 hover:border-accent transition-colors text-center">
              <div className="text-2xl mb-2">{a.icon}</div>
              <div className="text-sm font-medium">{t(a.label)}</div>
            </Link>
          ))}
        </div>
      </div>

      {catalog.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("vision.recent")}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {catalog.slice(0, 6).map((item) => (
              <div key={item.id} className="card overflow-hidden">
                <img src={item.image_url} alt={item.label} className="w-full h-24 object-cover" />
                <div className="p-2">
                  <div className="text-xs font-medium truncate">{item.label}</div>
                  <div className="text-[11px] text-ink-muted">{(item.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
