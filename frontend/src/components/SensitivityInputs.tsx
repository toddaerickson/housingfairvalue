import type { HeatmapParams } from "../lib/api";

export type SensitivityState = Required<
  Pick<HeatmapParams, "rate_min" | "rate_max" | "dti_min" | "dti_max">
>;

export const DEFAULTS: SensitivityState = {
  rate_min: 4.0,
  rate_max: 9.0,
  dti_min: 20.0,
  dti_max: 36.0,
};

// Backend Query() validators in sensitivity.py
const RATE_FLOOR = 0.5;
const RATE_CEILING = 20.0;
const DTI_FLOOR = 5.0;
const DTI_CEILING = 60.0;

type Props = {
  state: SensitivityState;
  onChange: (patch: Partial<SensitivityState>) => void;
  onReset: () => void;
};

function Slider({
  id, label, min, max, step, value, suffix, onChange,
}: {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="input-row">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="val" aria-live="polite">
        {value.toFixed(step < 1 ? 2 : 0)}{suffix}
      </span>
    </div>
  );
}

export default function SensitivityInputs({ state, onChange, onReset }: Props) {
  const isDefault =
    state.rate_min === DEFAULTS.rate_min &&
    state.rate_max === DEFAULTS.rate_max &&
    state.dti_min === DEFAULTS.dti_min &&
    state.dti_max === DEFAULTS.dti_max;

  return (
    <div className="chart-card sticky-aside">
      <h2>Inputs</h2>
      <p className="muted">
        Move the sliders to reshape the heatmap. Range bounds are mirrored in the
        URL so you can share a specific scenario.
      </p>

      <fieldset className="input-grid">
        <legend>Mortgage rate range</legend>
        <Slider
          id="rate-min"
          label="Min"
          min={RATE_FLOOR}
          max={Math.max(state.rate_max - 0.25, RATE_FLOOR)}
          step={0.25}
          value={state.rate_min}
          suffix="%"
          onChange={(v) => onChange({ rate_min: v })}
        />
        <Slider
          id="rate-max"
          label="Max"
          min={Math.min(state.rate_min + 0.25, RATE_CEILING)}
          max={RATE_CEILING}
          step={0.25}
          value={state.rate_max}
          suffix="%"
          onChange={(v) => onChange({ rate_max: v })}
        />
      </fieldset>

      <fieldset className="input-grid">
        <legend>Qualifying DTI range</legend>
        <Slider
          id="dti-min"
          label="Min"
          min={DTI_FLOOR}
          max={Math.max(state.dti_max - 2, DTI_FLOOR)}
          step={2}
          value={state.dti_min}
          suffix="%"
          onChange={(v) => onChange({ dti_min: v })}
        />
        <Slider
          id="dti-max"
          label="Max"
          min={Math.min(state.dti_min + 2, DTI_CEILING)}
          max={DTI_CEILING}
          step={2}
          value={state.dti_max}
          suffix="%"
          onChange={(v) => onChange({ dti_max: v })}
        />
      </fieldset>

      <button
        type="button"
        className="reset-btn"
        onClick={onReset}
        disabled={isDefault}
      >
        Reset to defaults
      </button>
    </div>
  );
}
