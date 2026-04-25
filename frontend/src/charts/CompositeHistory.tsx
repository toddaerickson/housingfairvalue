import { useQuery } from "@tanstack/react-query";
import {
  Area,
  Brush,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";

const REGIMES: { date: string; label: string }[] = [
  { date: "1981-12-31", label: "1980 trough" },
  { date: "1989-06-30", label: "1989 S&L peak" },
  { date: "2006-06-30", label: "2006 peak" },
  { date: "2012-01-31", label: "2012 trough" },
];

function snapToData(target: string, dataDates: string[]): string | null {
  if (!dataDates.length) return null;
  const t = Date.parse(target);
  let best = dataDates[0];
  let bestDelta = Math.abs(Date.parse(best) - t);
  for (const d of dataDates) {
    const delta = Math.abs(Date.parse(d) - t);
    if (delta < bestDelta) {
      best = d;
      bestDelta = delta;
    }
  }
  return bestDelta <= 35 * 86_400_000 ? best : null;
}

export default function CompositeHistory() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["composite"],
    queryFn: api.composite,
  });

  if (isLoading) return <div className="muted">Loading composite history…</div>;
  if (isError || !data) return <div className="muted">No composite data — run backfill.</div>;

  const series = data.data;
  const dataDates = series.map((d) => d.obs_date);

  return (
    <div className="chart-card">
      <h2>Composite overvaluation, 1980 → present</h2>
      <ResponsiveContainer width="100%" height={420}>
        <ComposedChart data={series} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="obs_date" minTickGap={50} />
          <YAxis tickFormatter={(v: number) => `${v}%`} />
          <Tooltip
            formatter={(v: number) => `${v.toFixed(1)}%`}
            labelFormatter={(l) => l as string}
          />
          <ReferenceLine y={0} stroke="#888" />
          {REGIMES.map((r) => {
            const x = snapToData(r.date, dataDates);
            if (!x) return null;
            return (
              <ReferenceLine
                key={r.date}
                x={x}
                stroke="#aaa"
                strokeDasharray="2 2"
                label={{ value: r.label, position: "top", fontSize: 10, fill: "#666" }}
              />
            );
          })}
          <Area
            dataKey="overvaluation_pct"
            stroke="#2c3e50"
            strokeWidth={1.5}
            fill="#2c3e50"
            fillOpacity={0.18}
            isAnimationActive={false}
          />
          <Brush dataKey="obs_date" height={24} stroke="#888" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
