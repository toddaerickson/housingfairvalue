import { useQuery } from "@tanstack/react-query";
import {
  Area,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";

const REGIME_LINES: { date: string; label: string }[] = [
  { date: "1981-12-31", label: "1980 trough" },
  { date: "1989-06-30", label: "1989 S&L peak" },
  { date: "2006-06-30", label: "2006 peak" },
  { date: "2012-01-31", label: "2012 trough" },
];

export default function CompositeHistory() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["composite"],
    queryFn: api.composite,
  });

  if (isLoading) return <div className="muted">Loading composite history…</div>;
  if (isError || !data) return <div className="muted">No composite data — run backfill.</div>;

  const series = data.data.map((d) => ({
    obs_date: d.obs_date,
    overvaluation_pct: d.overvaluation_pct,
    band_2sigma: 2 * (d.overvaluation_pct / Math.max(Math.abs(d.composite_z), 1e-6)),
  }));

  return (
    <div className="chart-card">
      <h2>Composite overvaluation, 1980 → present</h2>
      <ResponsiveContainer width="100%" height={420}>
        <ComposedChart data={series} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="obs_date" minTickGap={50} />
          <YAxis tickFormatter={(v) => `${v}%`} />
          <Tooltip
            formatter={(v: number) => `${v.toFixed(1)}%`}
            labelFormatter={(l) => l}
          />
          <ReferenceLine y={0} stroke="#888" />
          {REGIME_LINES.map((r) => (
            <ReferenceLine key={r.date} x={r.date} stroke="#aaa" strokeDasharray="2 2" label={{ value: r.label, position: "top", fontSize: 10, fill: "#666" }} />
          ))}
          <Area dataKey="overvaluation_pct" stroke="#2c3e50" fill="#2c3e50" fillOpacity={0.15} />
          <Line dataKey="overvaluation_pct" stroke="#2c3e50" dot={false} strokeWidth={1.5} />
          <Brush dataKey="obs_date" height={24} stroke="#888" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
