import { useState } from "react";
import { api } from "../api/client";
import { useLang } from "../i18n";

interface Verdict {
  verdict: string;
  reasoning: string;
}
interface RadarResult {
  topic: string;
  radar: { cost: Verdict; security: Verdict; approval_friction: Verdict } | null;
  extraction_failed: boolean;
  raw_text: string | null;
}

const LENSES = ["cost", "security", "approval_friction"] as const;

export default function Radar() {
  const { t } = useLang();
  const [topic, setTopic] = useState("");
  const [result, setResult] = useState<RadarResult | null>(null);
  const [busy, setBusy] = useState(false);

  const evaluate = async () => {
    if (!topic.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      const r = await api.post<RadarResult>("/api/radar/evaluate", { topic });
      setResult(r);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="font-display font-bold text-2xl mb-1">{t("radar.title")}</h1>
      <p style={{ color: "var(--text-secondary)" }}>{t("radar.subtitle")}</p>

      <div className="flex gap-2 mt-4">
        <input
          className="flex-1 px-3 py-2 rounded-ledger-sm border"
          style={{ borderColor: "var(--border-color)", background: "var(--surface-2)" }}
          placeholder={t("radar.placeholder")}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && evaluate()}
        />
        <button className="btn-primary px-5" disabled={busy} onClick={evaluate}>
          {t("radar.evaluate")}
        </button>
      </div>

      {result && (
        <div className="mt-6">
          {result.extraction_failed ? (
            <div className="card p-4">
              <p className="text-sm" style={{ color: "var(--critical)" }}>
                {t("radar.extractionFailed")}
              </p>
              <pre className="text-xs mt-2 whitespace-pre-wrap">{result.raw_text}</pre>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {LENSES.map((lens) => {
                const v = result.radar?.[lens];
                return (
                  <div key={lens} className="card p-4">
                    <div className="text-xs font-mono uppercase" style={{ color: "var(--text-muted)" }}>
                      {t(`radar.${lens === "approval_friction" ? "approvalFriction" : lens}`)}
                    </div>
                    <div className="font-display font-bold text-lg mt-1" style={{ color: "var(--accent)" }}>
                      {v?.verdict || t("radar.insufficientEvidence")}
                    </div>
                    <p className="text-sm mt-2" style={{ color: "var(--text-secondary)" }}>
                      {v?.reasoning}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
