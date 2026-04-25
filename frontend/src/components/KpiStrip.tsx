import { useQuery } from "@tanstack/react-query";
import { api, Kpi } from "../lib/api";

function tile(label: string, value: string, tone: "high" | "low" | "neutral" = "neutral") {
  return (
    <div className="kpi" key={label}>
      <div className="label">{label}</div>
      <div className={`value ${tone === "neutral" ? "" : tone}`}>{value}</div>
    </div>
  );
}

export default function KpiStrip() {
  const { data, isLoading, isError } = useQuery<Kpi>({
    queryKey: ["kpi"],
    queryFn: api.kpi,
  });

  if (isLoading) return <div className="muted">Loading KPIs…</div>;
  if (isError || !data) return <div className="muted">KPIs unavailable (run backfill?)</div>;

  const ovTone = data.overvaluation_pct > 10 ? "high" : data.overvaluation_pct < -10 ? "low" : "neutral";
  const rankTone = data.percentile_rank > 90 ? "high" : data.percentile_rank < 10 ? "low" : "neutral";

  return (
    <div className="kpi-strip">
      {tile("Overvaluation", `${data.overvaluation_pct.toFixed(1)}%`, ovTone)}
      {tile("Percentile rank", `${data.percentile_rank.toFixed(0)}`, rankTone)}
      {tile("Price / income", data.price_to_income.toFixed(1))}
      {tile("Price / rent", data.price_to_rent.toFixed(1))}
      {tile("30-yr rate", `${data.mortgage_rate_30y.toFixed(2)}%`)}
    </div>
  );
}
