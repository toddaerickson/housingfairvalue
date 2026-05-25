import { useQuery } from "@tanstack/react-query";
import { api, type RegimeRow } from "../lib/api";

const usd0 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function fmtPct(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

function toneFor(pct: number): "high" | "low" | "neutral" {
  if (pct > 10) return "high";
  if (pct < -10) return "low";
  return "neutral";
}

function fmtDate(iso: string): string {
  // Render month-end YYYY-MM-DD as "MMM YYYY" so 2024-01-31 → "Jan 2024"
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function RegimeCard({ r }: { r: RegimeRow }) {
  if (r.missing) {
    return (
      <div className="regime-card regime-missing">
        <h3>{r.name}</h3>
        <p className="muted">data unavailable for {r.obs_date}</p>
      </div>
    );
  }
  const tone = toneFor(r.overvaluation_pct);
  return (
    <div className="regime-card">
      <h3>{r.name}</h3>
      <div className="regime-date">{fmtDate(r.obs_date)}</div>
      <div className={`regime-headline ${tone}`}>
        {fmtPct(r.overvaluation_pct)}
        <span className="regime-rank"> · p{Math.round(r.percentile_rank)}</span>
      </div>
      <dl className="regime-stats">
        <div>
          <dt>Price</dt>
          <dd>{usd0.format(r.median_price)}</dd>
        </div>
        <div>
          <dt>Income</dt>
          <dd>{usd0.format(r.median_income)}</dd>
        </div>
        <div>
          <dt>30-yr rate</dt>
          <dd>{r.mortgage_rate_30y.toFixed(2)}%</dd>
        </div>
        <div>
          <dt>P/I</dt>
          <dd>{(r.median_price / r.median_income).toFixed(1)}</dd>
        </div>
      </dl>
    </div>
  );
}

export default function RegimeCards() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["regimes"],
    queryFn: api.regimes,
  });

  if (isLoading) return <div className="chart-card muted">Loading regime comparison…</div>;
  if (isError || !data) return <div className="chart-card muted">Regime data unavailable.</div>;

  return (
    <div className="chart-card">
      <h2>How does today compare to past regimes?</h2>
      <p className="muted">
        Snapshots of the composite signal at the four most-cited inflection
        points. The headline number is overvaluation %; the suffix is the
        percentile rank against the 1983–present distribution.
      </p>
      <div className="regime-grid">
        {data.regimes.map((r) => (
          <RegimeCard key={r.name} r={r} />
        ))}
      </div>
    </div>
  );
}
