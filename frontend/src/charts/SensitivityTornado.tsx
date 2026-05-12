import { useQuery } from "@tanstack/react-query";
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
import { api, type TornadoBar } from "../lib/api";

const LABELS: Record<string, string> = {
  mortgage_rate_30y: "30-yr mortgage rate",
  median_income: "Median income",
  median_price: "Median price",
  oer_index: "OER (rent) index",
};

// Mirrors the deltas defined in backend/api/routers/sensitivity.py::tornado:
// rate moves ±1pp, price ±10%, income/OER ±5%.
const PERTURBATION: Record<string, string> = {
  mortgage_rate_30y: "±100 bps",
  median_income: "±5%",
  median_price: "±10%",
  oer_index: "±5%",
};

function formatDelta(input: string): string {
  return PERTURBATION[input] ?? "perturbed";
}

type Row = {
  input: string;
  label: string;
  range: [number, number];
  z_up: number;
  z_dn: number;
};

function toRow(b: TornadoBar): Row {
  const lo = Math.min(b.z_up, b.z_dn);
  const hi = Math.max(b.z_up, b.z_dn);
  return {
    input: b.input,
    label: LABELS[b.input] ?? b.input,
    range: [lo, hi],
    z_up: b.z_up,
    z_dn: b.z_dn,
  };
}

export default function SensitivityTornado() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["tornado"],
    queryFn: api.tornado,
  });

  if (isLoading) return <div className="muted">Computing tornado…</div>;
  if (isError || !data) return <div className="muted">Tornado unavailable.</div>;

  const rows = data.bars.map(toRow);
  const base = data.base_z;

  return (
    <div className="chart-card">
      <h2>Input sensitivity (±1σ partial effect on composite z)</h2>
      <p className="muted">
        Each bar spans the composite z-score reached when the input moves up vs. down by the
        delta shown. Wider bars dominate the current reading; narrow bars barely move it.
        Reference line is the current composite z ({base.toFixed(2)}).
      </p>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 8, right: 24, bottom: 8, left: 96 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={["auto", "auto"]} tickFormatter={(v) => v.toFixed(2)} />
            <YAxis type="category" dataKey="label" width={140} />
            <ReferenceLine x={base} stroke="#888" strokeDasharray="4 4" />
            <Tooltip
              formatter={(_v, _n, ctx) => {
                const r = ctx?.payload as Row | undefined;
                if (!r) return ["", ""];
                return [
                  `${r.z_dn.toFixed(2)} … ${r.z_up.toFixed(2)} (${formatDelta(r.input)})`,
                  r.label,
                ];
              }}
              labelFormatter={() => ""}
            />
            <Bar dataKey="range" fill="#3b82f6" isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.input} fill={r.z_up >= r.z_dn ? "#3b82f6" : "#ef4444"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
