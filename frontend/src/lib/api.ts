const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type CompositePoint = {
  obs_date: string;
  z_affordability: number;
  z_price_income: number;
  z_price_rent: number;
  composite_z: number;
  overvaluation_pct: number;
  percentile_rank: number;
};

export type Kpi = {
  obs_date: string;
  overvaluation_pct: number;
  percentile_rank: number;
  price_to_income: number;
  price_to_rent: number;
  mortgage_rate_30y: number;
};

export type RegimeRow = {
  name: string;
  obs_date: string;
  overvaluation_pct: number;
  percentile_rank: number;
  median_price: number;
  mortgage_rate_30y: number;
  median_income: number;
};

export type HeatmapCell = {
  rate_pct: number;
  dti_pct: number;
  implied_price: number;
  pct_deviation_from_current: number;
};

export type TornadoBar = {
  input: string;
  delta: number;
  z_up: number;
  z_dn: number;
  abs_effect: number;
};

export type TornadoResponse = {
  base_z: number;
  bars: TornadoBar[];
};

export type FairValueSolveFor = "rate" | "price_growth" | "years";

export type FairValueRequest = {
  rate: number | null;
  price_growth: number | null;
  years: number | null;
  income_growth: number;
  solve_for: FairValueSolveFor | null;
};

export type FairValueResponse = {
  rate: number;
  price_growth: number;
  years: number;
  income_growth: number;
  implied_pti: number;
  composite_z_at_y: number;
  future_price: number;
  future_income: number;
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(detail.detail ?? `${path}: ${r.status}`);
  }
  return r.json();
}

export const api = {
  composite: () => get<{ data: CompositePoint[] }>("/history/composite"),
  kpi: () => get<Kpi>("/history/kpi"),
  regimes: () => get<{ regimes: RegimeRow[] }>("/history/regimes"),
  heatmap: () => get<{ current: { rate_pct: number; median_price: number }; cells: HeatmapCell[] }>("/sensitivity/heatmap"),
  tornado: () => get<TornadoResponse>("/sensitivity/tornado"),
  fairValue: (body: FairValueRequest) => postJson<FairValueResponse>("/sensitivity/fair-value", body),
};
