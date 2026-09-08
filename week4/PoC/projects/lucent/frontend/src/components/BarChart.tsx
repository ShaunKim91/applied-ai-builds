/** A small, dependency-free SVG bar chart — no charting library added just
 * for the admin dashboard's analytics section. Values are real, computed
 * server-side (see routers/admin.py::analytics) — this component only
 * lays them out, never invents data. */
export function BarChart({ values, labelFormatter, unit }: { values: number[]; labelFormatter?: (i: number) => string; unit?: string }) {
  if (values.length === 0) {
    return <div className="text-sm text-ink-muted py-8 text-center">No data yet</div>;
  }
  const max = Math.max(...values, 1);
  const width = 640;
  const height = 140;
  const barGap = 4;
  const barWidth = Math.max(4, width / values.length - barGap);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-36" preserveAspectRatio="none">
      {values.map((v, i) => {
        const barHeight = (v / max) * (height - 20);
        const x = i * (barWidth + barGap);
        const y = height - barHeight;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barWidth} height={barHeight} rx={3} fill="url(#lucent-bar-gradient)" opacity={0.9}>
              <title>
                {labelFormatter ? labelFormatter(i) : `#${i + 1}`}: {v}
                {unit ?? ""}
              </title>
            </rect>
          </g>
        );
      })}
      <defs>
        <linearGradient id="lucent-bar-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent-2)" />
          <stop offset="100%" stopColor="var(--accent)" />
        </linearGradient>
      </defs>
    </svg>
  );
}
