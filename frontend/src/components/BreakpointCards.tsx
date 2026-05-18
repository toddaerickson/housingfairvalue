import { useQuery } from "@tanstack/react-query";
import { api, type BreakpointsResponse } from "../lib/api";

const usd0 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

type CardSpec = {
  label: string;
  format: (b: BreakpointsResponse) => string | null;
  tagline: (b: BreakpointsResponse) => string;
};

const CARDS: CardSpec[] = [
  {
    label: "Mortgage rate that neutralizes the signal",
    format: (b) =>
      b.rate_to_neutralize_pct === null
        ? null
        : `${b.rate_to_neutralize_pct.toFixed(2)}%`,
    tagline: () =>
      "30-yr rate that, holding price and income constant, brings the composite to ~0σ.",
  },
  {
    label: "Income that neutralizes the signal",
    format: (b) =>
      b.income_to_neutralize_usd === null
        ? null
        : usd0.format(b.income_to_neutralize_usd),
    tagline: () =>
      "Median household income that, holding price and rate constant, fair-values the market.",
  },
  {
    label: "Price decline that neutralizes the signal",
    format: (b) =>
      b.price_decline_to_neutralize_pct === null
        ? null
        : `${b.price_decline_to_neutralize_pct >= 0 ? "−" : "+"}${Math.abs(
            b.price_decline_to_neutralize_pct,
          ).toFixed(1)}%`,
    tagline: () =>
      "Drop in median price needed at today's rates and incomes to neutralize the signal.",
  },
];

export default function BreakpointCards() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["breakpoints"],
    queryFn: api.breakpoints,
  });

  if (isLoading) return <div className="chart-card muted">Computing breakpoints…</div>;
  if (isError || !data) return <div className="chart-card muted">Breakpoints unavailable.</div>;

  return (
    <div className="chart-card">
      <h2>What would it take to neutralize the signal?</h2>
      <p className="muted">
        Each card answers a one-variable question: how far does this input have
        to move, with everything else held at today&apos;s values, for the
        composite to land back at fair value? Found by binary search on the
        backend; <code>null</code> means no neutralizing value exists inside
        the search range.
      </p>
      <div className="breakpoint-grid">
        {CARDS.map((c) => {
          const v = c.format(data);
          return (
            <div className="breakpoint-card" key={c.label}>
              <div className="breakpoint-label">{c.label}</div>
              <div className={`breakpoint-value ${v === null ? "missing" : ""}`}>
                {v ?? "no solution in range"}
              </div>
              <div className="breakpoint-tagline">{c.tagline(data)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
