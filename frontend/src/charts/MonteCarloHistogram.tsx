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
import { api } from "../lib/api";

type Bin = {
  year: number;
  count: number;
  inP10P90: boolean;
  isMedian: boolean;
};

export default function MonteCarloHistogram() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["monte-carlo"],
    queryFn: api.monteCarlo,
    // Rate-limited at 5/min on the backend; avoid auto-refetch.
    staleTime: 60 * 60_000,
    retry: false,
  });

  const bins = useMemo<Bin[]>(() => {
    if (!data) return [];
    const median = data.median_years ?? -1;
    const p10 = data.p10_years ?? -1;
    const p90 = data.p90_years ?? -1;
    return data.histogram_years.map((year, i) => ({
      year,
      count: data.histogram_counts[i] ?? 0,
      inP10P90: year >= p10 && year <= p90,
      isMedian: Math.abs(year - median) < 0.5,
    }));
  }, [data]);

  if (isLoading) return <div className="chart-card muted">Running Monte Carlo (5,000 paths)…</div>;
  if (isError || !data) {
    return (
      <div className="chart-card muted">
        Monte Carlo unavailable.{" "}
        <button className="link-btn" type="button" onClick={() => refetch()} disabled={isFetching}>
          Retry
        </button>
      </div>
    );
  }

  const sharePct = (data.share_reaching_fv * 100).toFixed(0);

  return (
    <div className="chart-card">
      <h2>How long until fair value, across {data.n_paths.toLocaleString()} simulated paths?</h2>
      <p className="muted">
        Years until composite returns to ±5% under a bivariate-normal model
        of rate and price shocks (income growth N(3%, 1.5%); rates AR(1) around
        a 6% long-run mean; price-rate ρ = -0.4). Dark bars: between the 10th
        and 90th percentile of paths that reached fair value. Orange bar:
        median.
      </p>

      <div className="mc-headline">
        <div className="mc-stat">
          <div className="mc-stat-label">Median</div>
          <div className="mc-stat-value">
            {data.median_years === null ? "—" : `${data.median_years.toFixed(0)} yr`}
          </div>
        </div>
        <div className="mc-stat">
          <div className="mc-stat-label">10th / 90th</div>
          <div className="mc-stat-value">
            {data.p10_years === null || data.p90_years === null
              ? "—"
              : `${data.p10_years.toFixed(0)} – ${data.p90_years.toFixed(0)} yr`}
          </div>
        </div>
        <div className="mc-stat">
          <div className="mc-stat-label">Reach FV in {data.horizon_years}y</div>
          <div className="mc-stat-value">{sharePct}%</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={bins} margin={{ left: 10, right: 20, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="year"
            tickFormatter={(v: number) => `${v}y`}
            allowDecimals={false}
          />
          <YAxis
            allowDecimals={false}
            label={{ value: "paths", angle: -90, position: "insideLeft", fontSize: 11, fill: "#666" }}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            formatter={(v: number) => [`${v} paths`, "count"]}
            labelFormatter={(l) => `Year ${l}`}
          />
          {data.median_years !== null && (
            <ReferenceLine
              x={Math.round(data.median_years)}
              stroke="#e07a3c"
              strokeWidth={2}
              label={{ value: "median", position: "top", fontSize: 10, fill: "#e07a3c", fontWeight: 600 }}
            />
          )}
          <Bar dataKey="count" isAnimationActive={false}>
            {bins.map((b, i) => (
              <Cell
                key={i}
                fill={b.isMedian ? "#e07a3c" : b.inP10P90 ? "#2c3e50" : "#a4afbb"}
                fillOpacity={b.isMedian ? 1 : 0.9}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {data.censored_count > 0 && (
        <p className="muted mc-censored">
          {data.censored_count.toLocaleString()} of {data.n_paths.toLocaleString()} paths
          ({(100 - data.share_reaching_fv * 100).toFixed(0)}%) did not reach fair value
          within {data.horizon_years} years and are excluded from the median / quantiles.
        </p>
      )}
    </div>
  );
}
