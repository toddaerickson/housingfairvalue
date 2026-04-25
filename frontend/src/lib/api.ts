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

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const api = {
  composite: () => get<{ data: CompositePoint[] }>("/history/composite"),
  kpi: () => get<Kpi>("/history/kpi"),
  regimes: () => get<{ regimes: RegimeRow[] }>("/history/regimes"),
  heatmap: () => get<{ current: { rate_pct: number; median_price: number }; cells: HeatmapCell[] }>("/sensitivity/heatmap"),
};
