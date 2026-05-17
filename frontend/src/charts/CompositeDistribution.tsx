import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type CompositePoint } from "../lib/api";

const NUM_BINS = 30;
const PERCENTILE_MARKERS: { p: number; label: string; color: string }[] = [
  { p: 50, label: "p50", color: "#888" },
  { p: 90, label: "p90", color: "#aaa" },
  { p: 95, label: "p95", color: "#aaa" },
  { p: 97, label: "p97", color: "#aaa" },
  { p: 99, label: "p99", color: "#aaa" },
];

type Bin = { x0: number; x1: number; mid: number; count: number; containsCurrent: boolean };

function buildHistogram(values: number[], current: number): { bins: Bin[]; percentiles: number[] } {
  if (values.length === 0) return { bins: [], percentiles: [] };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1e-9);
  const width = span / NUM_BINS;

  const bins: Bin[] = Array.from({ length: NUM_BINS }, (_, i) => {
    const x0 = min + i * width;
    const x1 = i === NUM_BINS - 1 ? max : x0 + width;
    return { x0, x1, mid: (x0 + x1) / 2, count: 0, containsCurrent: false };
  });

  for (const v of values) {
    // Last bin is inclusive of max so the maximum doesn't fall off-grid.
    const idx = v === max ? NUM_BINS - 1 : Math.min(NUM_BINS - 1, Math.floor((v - min) / width));
    bins[idx].count += 1;
  }
  const currentIdx = current === max
    ? NUM_BINS - 1
    : Math.min(NUM_BINS - 1, Math.max(0, Math.floor((current - min) / width)));
  if (currentIdx >= 0 && currentIdx < NUM_BINS) bins[currentIdx].containsCurrent = true;

  const sorted = [...values].sort((a, b) => a - b);
  const percentiles = PERCENTILE_MARKERS.map(({ p }) => {
    const i = Math.min(sorted.length - 1, Math.max(0, Math.floor((p / 100) * sorted.length)));
    return sorted[i];
  });

  return { bins, percentiles };
}

function fmtPct(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

export default function CompositeDistribution() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["composite"],
    queryFn: api.composite,
  });

  const computed = useMemo(() => {
    if (!data?.data?.length) return null;
    const values = data.data.map((d: CompositePoint) => d.overvaluation_pct);
    const current = values[values.length - 1];
    return { ...buildHistogram(values, current), current, n: values.length };
  }, [data]);

  if (isLoading) return <div className="chart-card muted">Loading distribution…</div>;
  if (isError || !computed) return <div className="chart-card muted">Distribution unavailable.</div>;

  const { bins, percentiles, current, n } = computed;
  // Find the bin index the current value sits in for "you are here" emphasis.
  const peakCount = Math.max(...bins.map((b) => b.count), 1);

  return (
    <div className="chart-card">
      <h2>Distribution of monthly composite readings ({n.toLocaleString()} months since 1983)</h2>
      <p className="muted">
        Each bar is the count of months whose overvaluation reading fell in that
        range. The orange marker is today&apos;s reading; dashed lines mark the
        50th / 90th / 95th / 97th / 99th percentiles.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={bins} margin={{ left: 10, right: 20, top: 24, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="mid"
            type="number"
            domain={[bins[0].x0, bins[bins.length - 1].x1]}
            tickFormatter={(v: number) => `${Math.round(v)}%`}
            allowDecimals={false}
          />
          <YAxis
            allowDecimals={false}
            domain={[0, Math.ceil(peakCount * 1.1)]}
            label={{ value: "months", angle: -90, position: "insideLeft", fontSize: 11, fill: "#666" }}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            formatter={(v: number) => [`${v} months`, "count"]}
            labelFormatter={(_label: unknown, payload: ReadonlyArray<{ payload?: Bin }>) => {
              const b = payload?.[0]?.payload;
              return b ? `${fmtPct(b.x0)} to ${fmtPct(b.x1)}` : "";
            }}
          />
          <ReferenceLine x={0} stroke="#444" strokeWidth={1} />
          {percentiles.map((px, i) => (
            <ReferenceLine
              key={PERCENTILE_MARKERS[i].label}
              x={px}
              stroke={PERCENTILE_MARKERS[i].color}
              strokeDasharray="3 3"
              label={{
                value: PERCENTILE_MARKERS[i].label,
                position: "top",
                fontSize: 10,
                fill: "#666",
              }}
            />
          ))}
          <ReferenceLine
            x={current}
            stroke="#e07a3c"
            strokeWidth={2}
            label={{
              value: `today: ${fmtPct(current)}`,
              position: "top",
              fontSize: 11,
              fill: "#e07a3c",
              fontWeight: 600,
            }}
          />
          <Bar dataKey="count" isAnimationActive={false}>
            {bins.map((b, i) => (
              <Cell
                key={i}
                fill={b.containsCurrent ? "#e07a3c" : "#2c3e50"}
                fillOpacity={b.containsCurrent ? 1 : 0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
