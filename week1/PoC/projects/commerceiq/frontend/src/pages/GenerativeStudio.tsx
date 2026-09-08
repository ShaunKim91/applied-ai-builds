import React, { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useI18n } from "../i18n";

interface GalleryItem {
  id: number;
  prompt: string;
  status: string;
  image_url: string | null;
  duration_seconds: number;
  created_at: string;
}

interface JobState {
  status: "queued" | "running" | "done" | "failed";
  result?: { image_url: string; duration_seconds: number };
  error?: string;
}

export default function GenerativeStudio() {
  const { t } = useI18n();
  const [prompt, setPrompt] = useState("a minimalist studio product photo of a ceramic coffee mug, white background");
  const [steps, setSteps] = useState(12);
  const [guidance, setGuidance] = useState(7.0);
  const [job, setJob] = useState<JobState | null>(null);
  const [gallery, setGallery] = useState<GalleryItem[]>([]);
  const pollRef = useRef<number | null>(null);

  const refreshGallery = () => api.get<GalleryItem[]>("/api/generate/gallery").then(setGallery).catch(() => {});

  useEffect(() => {
    refreshGallery();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  const generate = async () => {
    setJob({ status: "queued" });
    const { job_id } = await api.post<{ job_id: string }>("/api/generate", {
      prompt,
      steps,
      guidance_scale: guidance,
    });
    pollRef.current = window.setInterval(async () => {
      const j = await api.get<JobState>(`/api/generate/jobs/${job_id}`);
      setJob(j);
      if (j.status === "done" || j.status === "failed") {
        if (pollRef.current) window.clearInterval(pollRef.current);
        refreshGallery();
      }
    }, 2000);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t("generate.title")}</h1>
        <p className="text-ink-secondary mt-1">{t("generate.subtitle")}</p>
      </div>

      <div className="card p-6 space-y-4">
        <div>
          <label className="text-sm text-ink-secondary block mb-1.5">{t("generate.promptLabel")}</label>
          <textarea
            className="w-full px-3 py-2 rounded-lg border border-edge bg-surface text-ink text-sm min-h-[72px]"
            placeholder={t("generate.promptPlaceholder")}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-6">
          <div>
            <label className="text-sm text-ink-secondary block mb-1.5">
              {t("generate.steps")}: {steps}
            </label>
            <input type="range" min={4} max={30} value={steps} onChange={(e) => setSteps(Number(e.target.value))} />
          </div>
          <div>
            <label className="text-sm text-ink-secondary block mb-1.5">
              {t("generate.guidance")}: {guidance.toFixed(1)}
            </label>
            <input
              type="range"
              min={1}
              max={15}
              step={0.5}
              value={guidance}
              onChange={(e) => setGuidance(Number(e.target.value))}
            />
          </div>
        </div>
        <button
          onClick={generate}
          disabled={job?.status === "queued" || job?.status === "running"}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-60"
        >
          {t("generate.button")}
        </button>

        {job && (
          <div className="pt-3 border-t border-edge text-sm">
            {job.status === "queued" && <span className="text-ink-muted">{t("generate.queued")}</span>}
            {job.status === "running" && <span className="text-ink-muted">{t("generate.running")}</span>}
            {job.status === "failed" && <span className="text-critical">{job.error}</span>}
            {job.status === "done" && job.result && (
              <div className="flex items-center gap-4">
                <img src={job.result.image_url} alt={prompt} className="w-40 h-40 object-cover rounded-lg" />
                <span className="text-ink-muted text-xs">{job.result.duration_seconds.toFixed(1)}s</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-ink-secondary mb-3">{t("generate.gallery")}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {gallery
            .filter((g) => g.status === "done" && g.image_url)
            .map((g) => (
              <div key={g.id} className="card overflow-hidden">
                <img src={g.image_url!} alt={g.prompt} className="w-full h-28 object-cover" />
                <div className="p-2.5">
                  <div className="text-xs truncate" title={g.prompt}>
                    {g.prompt}
                  </div>
                  <div className="text-[11px] text-ink-muted">{g.duration_seconds.toFixed(1)}s</div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
