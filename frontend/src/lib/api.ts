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

export type RegimeRow =
  | {
      name: string;
      obs_date: string;
      missing: true;
    }
  | {
      name: string;
      obs_date: string;
      missing?: false;
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

export type BreakpointsResponse = {
  current_z: number;
  rate_to_neutralize_pct: number | null;
  income_to_neutralize_usd: number | null;
  price_decline_to_neutralize_pct: number | null;
};

export type YearsToFvCell = {
  price_growth_pct: number;
  income_growth_pct: number;
  years: number | null;
};

export type YearsToFvResponse = {
  base_overvaluation_pct: number;
  grid: YearsToFvCell[];
};

export type HeatmapParams = {
  rate_min?: number;
  rate_max?: number;
  rate_step?: number;
  dti_min?: number;
  dti_max?: number;
  dti_step?: number;
};

export type HeatmapResponse = {
  current: { rate_pct: number; median_price: number };
  cells: HeatmapCell[];
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

function qs(params: Record<string, number | string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  if (!entries.length) return "";
  return "?" + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

export const api = {
  composite: () => get<{ data: CompositePoint[] }>("/history/composite"),
  kpi: () => get<Kpi>("/history/kpi"),
  regimes: () => get<{ regimes: RegimeRow[] }>("/history/regimes"),
  heatmap: (params: HeatmapParams = {}) => get<HeatmapResponse>(`/sensitivity/heatmap${qs(params)}`),
  tornado: () => get<TornadoResponse>("/sensitivity/tornado"),
  breakpoints: () => get<BreakpointsResponse>("/sensitivity/breakpoints"),
  yearsToFv: () => get<YearsToFvResponse>("/sensitivity/years-to-fv"),
};
