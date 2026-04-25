import { useQuery } from "@tanstack/react-query";
import { api, HeatmapCell } from "../lib/api";

function colorFor(pct: number): string {
  // Diverging blue-white-red, ±50% range
  const clamped = Math.max(-50, Math.min(50, pct));
  const t = (clamped + 50) / 100;
  const r = Math.round(255 * t);
  const b = Math.round(255 * (1 - t));
  const g = Math.round(255 * (1 - Math.abs(t - 0.5) * 2));
  return `rgb(${r},${g},${b})`;
}

export default function SensitivityHeatmap() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["heatmap"],
    queryFn: api.heatmap,
  });

  if (isLoading) return <div className="muted">Computing heatmap…</div>;
  if (isError || !data) return <div className="muted">Heatmap unavailable.</div>;

  const rates = Array.from(new Set(data.cells.map((c) => c.rate_pct))).sort((a, b) => a - b);
  const dtis = Array.from(new Set(data.cells.map((c) => c.dti_pct))).sort((a, b) => b - a);
  const lookup = new Map<string, HeatmapCell>(
    data.cells.map((c) => [`${c.rate_pct}|${c.dti_pct}`, c]),
  );

  return (
    <div className="chart-card">
      <h2>Implied fair-value price (% deviation from current)</h2>
      <p className="muted">
        Rows: qualifying DTI. Cols: 30-yr mortgage rate. Cell value: implied
        median price as % deviation from current ${data.current.median_price.toLocaleString()}.
      </p>
      <table style={{ borderCollapse: "collapse", fontSize: 11 }}>
        <thead>
          <tr>
            <th></th>
            {rates.map((r) => (
              <th key={r} style={{ padding: "4px 6px", textAlign: "center" }}>{r.toFixed(2)}%</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dtis.map((d) => (
            <tr key={d}>
              <th style={{ padding: "4px 6px", textAlign: "right" }}>{d.toFixed(0)}%</th>
              {rates.map((r) => {
                const cell = lookup.get(`${r}|${d}`);
                if (!cell) return <td key={r}></td>;
                return (
                  <td
                    key={r}
                    title={`Rate ${r}%, DTI ${d}% → ${cell.pct_deviation_from_current.toFixed(1)}%`}
                    style={{
                      background: colorFor(cell.pct_deviation_from_current),
                      padding: "6px 4px",
                      textAlign: "center",
                      width: 38,
                      color: Math.abs(cell.pct_deviation_from_current) > 25 ? "#fff" : "#222",
                    }}
                  >
                    {cell.pct_deviation_from_current.toFixed(0)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
