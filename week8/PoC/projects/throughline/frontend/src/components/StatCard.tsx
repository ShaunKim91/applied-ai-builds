export default function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wide font-mono" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div className="font-display text-3xl font-bold mt-1" style={{ color: "var(--text-primary)" }}>
        {value}
      </div>
      {hint && (
        <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}
