import { useQuery } from "@tanstack/react-query";
import { api, type HeatmapCell } from "../lib/api";

function colorFor(pct: number): string {
  const clamped = Math.max(-50, Math.min(50, pct));
  const t = (clamped + 50) / 100;
  const r = Math.round(255 * t);
  const b = Math.round(255 * (1 - t));
  const g = Math.round(255 * (1 - Math.abs(t - 0.5) * 2));
  return `rgb(${r},${g},${b})`;
}

const LEGEND_STOPS = [-50, -25, 0, 25, 50];

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
        Numeric values — not just color — convey magnitude.
      </p>

      <div className="heatmap-legend" aria-hidden="true">
        {LEGEND_STOPS.map((v) => (
          <span key={v} style={{ background: colorFor(v) }}>{v > 0 ? `+${v}` : v}%</span>
        ))}
      </div>

      <div className="heatmap-scroll">
        <table className="heatmap-table">
          <caption className="sr-only">
            Implied fair-value price as percent deviation from current, indexed by mortgage rate (columns) and qualifying DTI (rows).
          </caption>
          <thead>
            <tr>
              <th scope="col" aria-label="DTI"></th>
              {rates.map((r) => (
                <th key={r} scope="col">{r.toFixed(2)}%</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dtis.map((d) => (
              <tr key={d}>
                <th scope="row">{d.toFixed(0)}%</th>
                {rates.map((r) => {
                  const cell = lookup.get(`${r}|${d}`);
                  if (!cell) return <td key={r}></td>;
                  const useLight = Math.abs(cell.pct_deviation_from_current) > 15;
                  return (
                    <td
                      key={r}
                      title={`Rate ${r}%, DTI ${d}% → ${cell.pct_deviation_from_current.toFixed(1)}%`}
                      style={{
                        background: colorFor(cell.pct_deviation_from_current),
                        color: useLight ? "#fff" : "#111",
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
    </div>
  );
}
