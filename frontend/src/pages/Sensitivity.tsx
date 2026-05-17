import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import SensitivityHeatmap from "../charts/SensitivityHeatmap";
import SensitivityTornado from "../charts/SensitivityTornado";
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
    if (raw === null) return;
    const n = Number(raw);
    if (Number.isFinite(n)) next[k] = n;
  });
  // Guard: ensure mins stay strictly below maxes; fall back to defaults on inversion.
  if (next.rate_min >= next.rate_max) {
    next.rate_min = DEFAULTS.rate_min;
    next.rate_max = DEFAULTS.rate_max;
  }
  if (next.dti_min >= next.dti_max) {
    next.dti_min = DEFAULTS.dti_min;
    next.dti_max = DEFAULTS.dti_max;
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
        <SensitivityHeatmap params={state} />
        <SensitivityTornado />
        <div className="chart-card">
          <h2>Breakpoints / years-to-FV / Monte Carlo</h2>
          <p className="muted">Wired in subsequent phases. API endpoints already exist.</p>
        </div>
      </section>
    </div>
  );
}
