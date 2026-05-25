import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type FairValueResponse, type FairValueSolveFor } from "../lib/api";

type Field = FairValueSolveFor;

const FIELD_LABELS: Record<Field, string> = {
  rate: "Mortgage rate (%)",
  price_growth: "Annual home price growth (%)",
  years: "Years to equilibrium",
};

const FIELD_PLACEHOLDERS: Record<Field, string> = {
  rate: "e.g. 6.50",
  price_growth: "e.g. 3.0",
  years: "e.g. 7",
};

function parseField(s: string): number | null {
  const t = s.trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function formatField(field: Field, value: number): string {
  if (field === "years") return value.toFixed(1);
  return value.toFixed(2);
}

export default function FairValue() {
  const [rate, setRate] = useState("");
  const [priceGrowth, setPriceGrowth] = useState("");
  const [years, setYears] = useState("");
  const [incomeGrowth, setIncomeGrowth] = useState("3.0");
  const [result, setResult] = useState<FairValueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const values: Record<Field, number | null> = {
    rate: parseField(rate),
    price_growth: parseField(priceGrowth),
    years: parseField(years),
  };
  const giValid = parseField(incomeGrowth) !== null;

  function canSolveFor(target: Field): boolean {
    if (!giValid) return false;
    return (["rate", "price_growth", "years"] as Field[])
      .filter((f) => f !== target)
      .every((f) => values[f] !== null);
  }

  const mutation = useMutation({
    mutationFn: (solveFor: Field) =>
      api.fairValue({
        rate: solveFor === "rate" ? null : values.rate,
        price_growth: solveFor === "price_growth" ? null : values.price_growth,
        years: solveFor === "years" ? null : values.years,
        income_growth: parseField(incomeGrowth)!,
        solve_for: solveFor,
      }),
    onSuccess: (data, solveFor) => {
      setResult(data);
      setError(null);
      const formatted = formatField(solveFor, data[solveFor]);
      if (solveFor === "rate") setRate(formatted);
      else if (solveFor === "price_growth") setPriceGrowth(formatted);
      else setYears(formatted);
    },
    onError: (err: Error) => setError(err.message),
  });

  const setters: Record<Field, (s: string) => void> = {
    rate: setRate,
    price_growth: setPriceGrowth,
    years: setYears,
  };
  const rawValues: Record<Field, string> = {
    rate,
    price_growth: priceGrowth,
    years,
  };

  return (
    <div className="layout-2col">
      <aside>
        <div className="chart-card">
          <h2>How it works</h2>
          <p className="muted">
            Solver finds the input that makes the composite z-score reach 0 at year y, given
            forward paths for price, income, and rent. Fill in any two of mortgage rate, price
            growth, and years to equilibrium; click <strong>Solve</strong> next to the third
            to back out its value. With all three filled, every field gets a Solve button so
            you can recompute any one.
          </p>
          <p className="muted">
            PTI is a derived readout — it does not appear in the equilibrium equation. Income
            growth is a required assumption (it sets the forward path for both income and
            rent).
          </p>
        </div>
      </aside>
      <section>
        <div className="chart-card">
          <h2>Fair Value Solver</h2>

          <div className="fv-form">
            <div className="fv-row">
              <label htmlFor="fv-income">Income growth (% per yr, required)</label>
              <input
                id="fv-income"
                type="number"
                step="0.1"
                value={incomeGrowth}
                onChange={(e) => setIncomeGrowth(e.target.value)}
                placeholder="3.0"
              />
              <div className="fv-solve-slot" />
            </div>

            {(["rate", "price_growth", "years"] as Field[]).map((f) => (
              <div className="fv-row" key={f}>
                <label htmlFor={`fv-${f}`}>{FIELD_LABELS[f]}</label>
                <input
                  id={`fv-${f}`}
                  type="number"
                  step={f === "years" ? "0.5" : "0.1"}
                  value={rawValues[f]}
                  onChange={(e) => setters[f](e.target.value)}
                  placeholder={FIELD_PLACEHOLDERS[f]}
                />
                <div className="fv-solve-slot">
                  {canSolveFor(f) && (
                    <button
                      type="button"
                      className="fv-solve-btn"
                      onClick={() => mutation.mutate(f)}
                      disabled={mutation.isPending}
                    >
                      {mutation.isPending && mutation.variables === f ? "Solving…" : "Solve"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {error && <div className="fv-error">Error: {error}</div>}

          <div className="fv-readout">
            <div className="fv-readout-row">
              <span className="muted">Implied PTI (PITI / income)</span>
              <strong>
                {result ? `${(result.implied_pti * 100).toFixed(1)}%` : "—"}
              </strong>
            </div>
            <div className="fv-readout-row">
              <span className="muted">Composite z at year y</span>
              <strong>{result ? result.composite_z_at_y.toFixed(3) : "—"}</strong>
            </div>
            {result && (
              <>
                <div className="fv-readout-row">
                  <span className="muted">Price at year y</span>
                  <strong>${Math.round(result.future_price).toLocaleString()}</strong>
                </div>
                <div className="fv-readout-row">
                  <span className="muted">Income at year y</span>
                  <strong>${Math.round(result.future_income).toLocaleString()}</strong>
                </div>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
