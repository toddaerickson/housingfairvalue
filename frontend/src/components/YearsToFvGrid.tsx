import { useQuery } from "@tanstack/react-query";
import { api, type YearsToFvCell } from "../lib/api";

// Color ramp: faster (fewer years) is "easier"; null is censored.
function bgFor(years: number | null): string {
  if (years === null) return "#eee";
  if (years <= 3) return "#1f9d55";   // green
  if (years <= 6) return "#3aa856";
  if (years <= 10) return "#c0a020";  // yellow-ish
  if (years <= 15) return "#d97e2a";  // orange
  return "#b22222";                   // red
}

function fmt(years: number | null): string {
  if (years === null) return "—";
  return `${years}y`;
}

function pctLabel(v: number): string {
  return `${v > 0 ? "+" : ""}${v.toFixed(0)}%`;
}

export default function YearsToFvGrid() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["years-to-fv"],
    queryFn: api.yearsToFv,
  });

  if (isLoading) return <div className="chart-card muted">Loading years-to-FV grid…</div>;
  if (isError || !data) return <div className="chart-card muted">Years-to-FV grid unavailable.</div>;

  const incomeCols = Array.from(new Set(data.grid.map((c) => c.income_growth_pct))).sort((a, b) => a - b);
  const priceRows = Array.from(new Set(data.grid.map((c) => c.price_growth_pct))).sort((a, b) => b - a);
  const lookup = new Map<string, YearsToFvCell>(
    data.grid.map((c) => [`${c.price_growth_pct}|${c.income_growth_pct}`, c]),
  );

  return (
    <div className="chart-card">
      <h2>How long until fair value, under different scenarios?</h2>
      <p className="muted">
        Years until the composite drifts within ±5% of fair value. Rows: nominal
        price growth per year. Columns: nominal income growth per year. Faster
        income growth + slower price growth = quicker normalization. &mdash;
        means the path doesn&apos;t reach fair value within 30 years.
      </p>
      <div className="ytfv-scroll">
        <table className="ytfv-table">
          <caption className="sr-only">
            Years to fair value indexed by nominal price growth (rows) and nominal income growth (columns).
          </caption>
          <thead>
            <tr>
              <th scope="col" aria-label="Price growth"></th>
              <th scope="col" colSpan={incomeCols.length}>Income growth</th>
            </tr>
            <tr>
              <th scope="col" aria-label="Price growth"></th>
              {incomeCols.map((c) => (
                <th key={c} scope="col">{pctLabel(c)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {priceRows.map((p, i) => (
              <tr key={p}>
                <th scope="row">
                  {i === 0 && <span className="ytfv-row-axis">Price growth</span>}
                  {pctLabel(p)}
                </th>
                {incomeCols.map((c) => {
                  const cell = lookup.get(`${p}|${c}`);
                  const years = cell?.years ?? null;
                  return (
                    <td
                      key={c}
                      style={{ background: bgFor(years), color: years === null ? "#444" : "#fff" }}
                      title={
                        years === null
                          ? `Price ${pctLabel(p)}/yr, income ${pctLabel(c)}/yr → does not reach FV in 30 years`
                          : `Price ${pctLabel(p)}/yr, income ${pctLabel(c)}/yr → ${years} years to FV`
                      }
                    >
                      {fmt(years)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted ytfv-base">
        Starting overvaluation: <strong>{data.base_overvaluation_pct.toFixed(1)}%</strong>.
      </p>
    </div>
  );
}
