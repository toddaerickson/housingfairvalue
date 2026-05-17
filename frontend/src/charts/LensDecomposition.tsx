import { useQuery } from "@tanstack/react-query";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type CompositePoint } from "../lib/api";

type LensKey = "z_affordability" | "z_price_income" | "z_price_rent";

const LENSES: { key: LensKey; label: string; color: string; explainer: string }[] = [
  {
    key: "z_affordability",
    label: "Payment affordability (PITI / income)",
    color: "#c0392b",
    explainer: "Higher = monthly mortgage payment is large relative to monthly income.",
  },
  {
    key: "z_price_income",
    label: "Price / income",
    color: "#2c3e50",
    explainer: "Higher = home prices are stretched against household incomes.",
  },
  {
    key: "z_price_rent",
    label: "Price / rent",
    color: "#1f6391",
    explainer: "Higher = home prices are stretched against the implied rental value.",
  },
];

function Panel({
  data,
  lens,
}: {
  data: CompositePoint[];
  lens: (typeof LENSES)[number];
}) {
  const last = data[data.length - 1];
  return (
    <div className="lens-panel">
      <div className="lens-header">
        <h3 style={{ color: lens.color }}>{lens.label}</h3>
        <span className="lens-current">
          today: <strong>{last[lens.key].toFixed(2)}σ</strong>
        </span>
      </div>
      <p className="lens-explainer">{lens.explainer}</p>
      <ResponsiveContainer width="100%" height={140}>
        <ComposedChart data={data} margin={{ left: 10, right: 16, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="obs_date" minTickGap={60} tick={{ fontSize: 10 }} />
          <YAxis
            tickFormatter={(v: number) => `${v.toFixed(0)}σ`}
            tick={{ fontSize: 10 }}
            domain={[-3, 3]}
            ticks={[-2, -1, 0, 1, 2]}
            width={36}
          />
          <Tooltip
            formatter={(v: number) => [`${v.toFixed(2)}σ`, "z-score"]}
            labelFormatter={(l) => l as string}
          />
          <ReferenceArea y1={-1} y2={1} fill="#000" fillOpacity={0.03} />
          <ReferenceLine y={0} stroke="#999" />
          <Area
            dataKey={lens.key}
            stroke={lens.color}
            strokeWidth={1.4}
            fill={lens.color}
            fillOpacity={0.12}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function LensDecomposition() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["composite"],
    queryFn: api.composite,
  });

  if (isLoading) return <div className="chart-card muted">Loading decomposition…</div>;
  if (isError || !data?.data?.length) {
    return <div className="chart-card muted">Decomposition unavailable.</div>;
  }

  return (
    <div className="chart-card">
      <h2>Which lens is driving the signal?</h2>
      <p className="muted">
        Each panel shows one lens&apos;s z-score (standard deviations from its
        1983–present mean). The shaded band is ±1σ — anything outside is
        historically notable. Comparing the three reveals which pressure
        dominates today&apos;s composite reading.
      </p>
      <div className="lens-decomp-grid">
        {LENSES.map((lens) => (
          <Panel key={lens.key} data={data.data} lens={lens} />
        ))}
      </div>
    </div>
  );
}
