import { TiltCard } from "./TiltCard";

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <TiltCard maxDeg={4}>
      <div className="clay p-6">
        <div className="text-sm text-ink-secondary">{label}</div>
        <div className="mt-2 text-3xl font-display font-semibold tabular-nums text-ink">{value}</div>
        {hint && <div className="mt-1 text-xs text-ink-muted">{hint}</div>}
      </div>
    </TiltCard>
  );
}
