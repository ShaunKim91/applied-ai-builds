import React, { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Point {
  date: string;
  value: number;
}
interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
}
interface Anomaly {
  date: string;
  value: number;
}

// Colors follow the dataviz-skill validated palette: series-1 (accent) for
// the primary forecast line, muted ink for history, critical red for
// anomalies, and a low-opacity accent fill for the 95% confidence band.
export function ForecastChart({
  history,
  forecast,
  anomalies,
}: {
  history: Point[];
  forecast: ForecastPoint[];
  anomalies: Anomaly[];
}) {
  const rows = useMemo(() => {
    const anomalySet = new Map(anomalies.map((a) => [a.date, a.value]));
    const historyRows = history.map((h) => ({
      date: h.date,
      actual: h.value,
      forecastValue: null as number | null,
      range: null as [number, number] | null,
      anomaly: anomalySet.has(h.date) ? h.value : null,
    }));
    const forecastRows = forecast.map((f) => ({
      date: f.date,
      actual: null as number | null,
      forecastValue: f.value,
      range: [f.lower, f.upper] as [number, number],
      anomaly: null as number | null,
    }));
    // bridge the two lines so they connect visually at the boundary
    if (historyRows.length && forecastRows.length) {
      forecastRows[0] = { ...forecastRows[0] };
      historyRows[historyRows.length - 1] = {
        ...historyRows[historyRows.length - 1],
        forecastValue: historyRows[historyRows.length - 1].actual,
      };
    }
    return [...historyRows, ...forecastRows];
  }, [history, forecast, anomalies]);

  const fmt = (v: number) => `£${Math.round(v).toLocaleString()}`;

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="var(--gridline)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "var(--text-muted)" }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--text-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => fmt(v)}
          width={64}
        />
        <Tooltip
          formatter={(value: number, name: string) => [fmt(value), name]}
          contentStyle={{
            background: "var(--surface-1)",
            border: "1px solid var(--border-color)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          dataKey="range"
          stroke="none"
          fill="var(--accent)"
          fillOpacity={0.12}
          name="95% interval"
          isAnimationActive={false}
        />
        <Line
          dataKey="actual"
          stroke="var(--text-secondary)"
          strokeWidth={2}
          dot={false}
          name="History"
          isAnimationActive={false}
        />
        <Line
          dataKey="forecastValue"
          stroke="var(--accent)"
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={false}
          name="Forecast"
          isAnimationActive={false}
        />
        <Scatter dataKey="anomaly" fill="var(--status-critical)" name="Anomaly" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
