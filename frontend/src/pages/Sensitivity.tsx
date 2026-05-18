import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import SensitivityHeatmap from "../charts/SensitivityHeatmap";
import SensitivityTornado from "../charts/SensitivityTornado";
import BreakpointCards from "../components/BreakpointCards";
import YearsToFvGrid from "../components/YearsToFvGrid";
import SensitivityInputs, {
  DEFAULTS,
  type SensitivityState,
} from "../components/SensitivityInputs";

const KEY_MAP: Record<keyof SensitivityState, string> = {
  rate_min: "rmin",
  rate_max: "rmax",
  dti_min: "dmin",
  dti_max: "dmax",
};

function parseFromUrl(sp: URLSearchParams): SensitivityState {
  const next = { ...DEFAULTS };
  (Object.keys(KEY_MAP) as Array<keyof SensitivityState>).forEach((k) => {
    const raw = sp.get(KEY_MAP[k]);
    if (raw === null || raw === "") return;
    const n = Number(raw);
    if (Number.isFinite(n)) next[k] = n;
  });
  // Guard: swap rather than reset on inversion, so a malformed bookmark
  // (?rmin=8&rmax=7) preserves the user's intent.
  if (next.rate_min >= next.rate_max) {
    [next.rate_min, next.rate_max] = [
      Math.min(next.rate_min, next.rate_max),
      Math.max(next.rate_min, next.rate_max),
    ];
    if (next.rate_min === next.rate_max) next.rate_max = next.rate_min + 0.25;
  }
  if (next.dti_min >= next.dti_max) {
    [next.dti_min, next.dti_max] = [
      Math.min(next.dti_min, next.dti_max),
      Math.max(next.dti_min, next.dti_max),
    ];
    if (next.dti_min === next.dti_max) next.dti_max = next.dti_min + 2;
  }
  return next;
}

export default function Sensitivity() {
  const [searchParams, setSearchParams] = useSearchParams();
  const state = useMemo(() => parseFromUrl(searchParams), [searchParams]);

  const writeUrl = useCallback(
    (next: SensitivityState) => {
      const sp = new URLSearchParams(searchParams);
      (Object.keys(KEY_MAP) as Array<keyof SensitivityState>).forEach((k) => {
        if (next[k] === DEFAULTS[k]) sp.delete(KEY_MAP[k]);
        else sp.set(KEY_MAP[k], String(next[k]));
      });
      setSearchParams(sp, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleChange = useCallback(
    (patch: Partial<SensitivityState>) => writeUrl({ ...state, ...patch }),
    [state, writeUrl],
  );

  const handleReset = useCallback(() => writeUrl(DEFAULTS), [writeUrl]);

  return (
    <div className="layout-2col">
      <aside>
        <SensitivityInputs state={state} onChange={handleChange} onReset={handleReset} />
      </aside>
      <section>
        <BreakpointCards />
        <SensitivityHeatmap params={state} />
        <YearsToFvGrid />
        <SensitivityTornado />
        <div className="chart-card">
          <h2>Monte Carlo</h2>
          <p className="muted">Wired in a subsequent phase. API endpoint already exists.</p>
        </div>
      </section>
    </div>
  );
}
