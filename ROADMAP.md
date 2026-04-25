# Development Roadmap

Living document. Captures everything that's planned but not yet shipped.
Owners + dates intentionally left blank — fill in as work is picked up.

Conventions:

- **P0** = blocks the public dashboard from being useful
- **P1** = visible gap in scope vs. the approved plan
- **P2** = polish, perf, or quality-of-life
- Items reference the source review where applicable: `QA #N`,
  `SK #N` (silent killer), `Sec #N`, `UI #N`, or `Plan` (approved plan
  in the project notes).

---

## Status snapshot

What's shipped on `main` today:

- FRED ingestion of 9 series, monthly resample with the pre-1984 income stitch.
- Composite z-score engine (3 lenses, equal-weighted, mid-rank percentile).
- 4 historical reference regimes pinned in `backend/calc/regimes.py`.
- FastAPI app with 8 endpoints: `/health`, `/ready`, `/history/{composite,series,kpi,regimes}`, `/sensitivity/{heatmap,tornado,breakpoints,years-to-fv,montecarlo}`.
- React/Vite/Recharts frontend, three tabs (History, Sensitivity, Methodology).
  - History tab renders KPI strip + composite history chart with regime
    markers + brush.
  - Sensitivity tab renders the heatmap of implied fair-value price.
  - Methodology tab discloses the equal-weighting assumption and the
    pre-1984 income stitch.
- Tests: 16 calc-engine, 9 API smoke, 4 parametrized validation-gate
  (skip until backfill).
- Security/infra hygiene: non-root container, loopback-only Postgres,
  CORS from env, no creds-bearing default DSN, `/ready` for DB-aware
  health checks.

---

## P0 — gate first deploy

### 1. Run the first real backfill and unblock the validation gate

The validation gate currently skips because no FRED data exists in
`monthly_fact`. Until it actually runs end-to-end, `pct_per_sigma`
calibration in `backend/calc/composite.py` is provisional (19.0).

- [ ] Provision a FRED API key.
- [ ] `python -m backend.ingest.fred --backfill`.
- [ ] Run `pytest backend/tests/test_validation_gate.py -v`.
- [ ] If the 2024 regime fails its 1pp tolerance, retune `DEFAULT_PCT_PER_SIGMA`.
      The std-to-pct factor is the only knob that should move; lens
      math should not be edited to make the gate pass.
- [ ] Commit a small CSV fixture under `backend/fixtures/monthly_fact.csv`
      (sampled, not the full 540-row series) so the gate can run in CI
      without a live DB. Record exact regime targets in
      `backend/calc/regimes.py` once confirmed.

### 2. Deploy the dashboard publicly

- [ ] Provision Supabase Postgres (TimescaleDB extension enabled).
- [ ] Deploy API to Render. Point `/ready` at the Render health check.
      Set `DATABASE_URL`, `FRED_API_KEY`, `ALLOWED_ORIGINS=https://<vercel-domain>`.
- [ ] Deploy frontend to Vercel. Set the API base URL via env so the
      Vite dev proxy is replaced in production builds.
- [ ] Add a daily Render cron job: `python -m backend.ingest.fred --since YYYY-MM-DD`.
      Use a 24-hour lookback to absorb FRED revisions.

---

## P1 — Phase 2/3 finishes (History tab)

These charts are described in the approved plan and currently render as
"coming soon" placeholders.

### 3. Three-lens decomposition chart `Plan §4.2`

- [ ] Backend: extend `/history/composite` to also return per-lens z-scores
      (already in the response) and document the "stacked area vs. small
      multiples" choice.
- [ ] Frontend: new `frontend/src/charts/LensDecomposition.tsx` rendering
      a 3-panel small-multiple of `z_affordability`, `z_price_income`,
      `z_price_rent`. Shared x-axis with the headline chart.

### 4. Distribution / percentile strip `Plan §4.3`

- [ ] Frontend: new `frontend/src/charts/PercentileDistribution.tsx`
      rendering a histogram of monthly composite readings 1980→present
      with a vertical "current" line and 50/90/95/97/99th percentile markers.
- [ ] Pull histogram bins from a new `/history/distribution` endpoint
      (cheap; just `np.histogram` on `compute_composite` output).

### 5. Regime comparison panel `Plan §4.4`

- [ ] Frontend: render the existing `/history/regimes` payload as
      side-by-side cards (1980 trough, 2006 peak, 2012 trough, current).
- [ ] Backend: extend `/history/regimes` to include a "subsequent 5 years"
      block per regime (mean composite, peak drawdown, recovery years).

---

## P1 — Phase 4 finishes (Sensitivity tab)

API endpoints exist; UI wiring pending.

### 6. Inputs panel with live sliders

- [ ] `frontend/src/components/SensitivityInputs.tsx` with sliders for
      mortgage rate, income growth, OER growth, property tax %,
      insurance %, down payment %, qualifying DTI %.
- [ ] URL query-string state (linkable scenarios) per `Plan §5.6`.
- [ ] Reset-to-current button.

### 7. Tornado chart

- [ ] Frontend: `frontend/src/charts/TornadoChart.tsx` rendering
      `/sensitivity/tornado` output as a horizontal bar chart sorted by
      `abs_effect`.

### 8. Years-to-fair-value grid

- [ ] Frontend: `frontend/src/charts/YearsToFvGrid.tsx` rendering
      `/sensitivity/years-to-fv` as a 3×3 table with color encoding.

### 9. Monte Carlo histogram

- [ ] Frontend: `frontend/src/charts/MonteCarloHistogram.tsx` rendering
      `/sensitivity/montecarlo` `histogram_counts` with median + 10/90
      percentile bands. Tooltip surfaces `share_reaching_fv` and
      `censored_count` so users can read the right-censoring honestly.

### 10. Mechanical breakpoint cards

- [ ] Frontend: `frontend/src/components/BreakpointCards.tsx` rendering
      `/sensitivity/breakpoints` as 3 cards: rate / income / price-decline
      that neutralizes the composite at current readings.

### 11. CSV export

- [ ] Add a small `/sensitivity/heatmap.csv` content negotiation path so
      the heatmap is exportable without a separate route.

---

## P1 — Methodology page polish

### 12. Methodology content `Plan §3, §6`

- [ ] Add an interactive weights toggle (locked by default, exposes the
      sum-to-one-constrained sliders).
- [ ] Document `pct_per_sigma` calibration once the gate lands.
- [ ] Add citations: Williams 2013, Hein & Lamb 1981 — referenced in the
      plan for the pre-1984 backfill rationale.

---

## P2 — Operational hygiene

### 13. Reproducible builds

- [ ] Generate a Python lockfile (`uv lock` or `pip-tools`) and switch
      CI to `pip install --require-hashes`. Currently CI uses
      `pip install -e ".[dev]"` which floats transitive deps. (`Sec #1, #13`)
- [ ] Pin GitHub Actions to commit SHAs (currently major-version pinned).
      (`Sec #12`)

### 14. Rate limiting

- [ ] Add `slowapi` to FastAPI before public deploy. `/sensitivity/montecarlo`
      allocates `n_paths × horizon` arrays and is the most attractive
      DoS vector. (`Sec #14`)

### 15. Frontend bundle size

- [ ] Vite build emits a 620 kB single chunk. Code-split per route
      (`React.lazy` on the three pages) and split Recharts into its own
      chunk via `manualChunks`. Bundle warning surfaced in the
      `npm run build` log.

### 16. Frontend skeletons + error states

- [ ] Replace "Loading…" / "Unavailable" muted text with fixed-height
      skeleton blocks so layout doesn't shift when data arrives.
      (`UI #16`)

### 17. Logging + observability

- [ ] Wire `structlog` (or stdlib JSON logging) so Render captures
      structured logs.
- [ ] Add Sentry or equivalent on both API and frontend.
- [ ] Emit a metric on each ingest run: row count, max obs_date, splice
      anchor month.

---

## P2 — Calc engine open questions

### 18. Quarterly/annual semantic alignment

The current resample marks a quarterly observation at the *start* of the
period (e.g., MSPUS Q1 2024 lands at 2024-01-31 then ffills through March),
but semantically the value represents the full quarter. During fast rate
moves this biases the affordability lens by ~2 months. (`SK #19`)

- [ ] Decide on a convention: tag-at-period-end, or tag-at-period-mid?
      Current ffill+bfill approximates tag-at-period-start.
- [ ] Document whichever choice is made and add a test that pins the
      alignment for at least one quarterly observation across a known
      regime change.

### 19. Income time-axis leak

Z-scores currently use the full 1980→present mean/std applied to the
1980 readings. Fine as a *historical descriptive statistic*; not fine
for any forward-looking out-of-sample claim. (`SK #3`)

- [ ] Decide whether the dashboard reports the descriptive statistic
      (current behavior) or an expanding-window z (which changes the
      headline 2024 reading). Document the choice in Methodology.

### 20. Tornado: hold baseline mean/std fixed

Today the tornado perturbs the last row and recomputes the full
mean/std, mixing "effect on last z" with "effect on baseline." Effect
is small (~0.02% of mean per ±10% perturbation) but flips sign for
low-influence inputs. (`SK #17`)

- [ ] Cache (mean, std) from the unperturbed series and apply
      z = (perturbed - mean)/std only at the last observation.

---

## P2 — Test coverage gaps

### 21. Tests for sensitivity endpoints

Currently zero tests for `/sensitivity/{tornado,breakpoints,years-to-fv,montecarlo}`.
The Monte Carlo handler is the most algorithmically dense and has the
highest risk of silent regressions. (`QA #15`)

- [ ] Pin Monte Carlo histogram length, censored-share semantics, and
      bivariate-normal correlation under a fixed seed.
- [ ] Smoke test for `/sensitivity/breakpoints` returning floats (or
      `null` when no sign change exists).
- [ ] Smoke test for tornado bar ordering.

### 22. Tests for ingest path

`backend/ingest/fred.py` has zero tests. The splice-anchor logic
(`stitch_income`) is unit-tested in `test_calc.py`, but `to_monthly`
across all four frequency conventions is not.

- [ ] Test `to_monthly` for D/W/M/Q/A inputs against known monthly outputs.
- [ ] Test `write_observations` and `write_monthly_fact` chunking against
      a SQLite mock or the test container.

---

## Out of scope (intentionally)

These came up during planning/audit and are explicitly **not** on the
roadmap:

- Per-MSA or per-ZIP breakouts. National only, by design.
- Rent-vs-buy calculator UI. Covered by the affordability lens already.
- Predictive modeling / forecasting. The composite is descriptive.
- Auth / multi-user. Public read-only dashboard.

---

## Definition of done — "v1.0 shipped"

The dashboard ships when:

1. All P0 items are complete (validation gate passes against real
   backfill, deployed at a public URL).
2. Items 3, 4, 5, 6, 7 (the History tab finishes + sensitivity inputs
   panel + tornado) are landed.
3. Items 13 (lockfile) and 14 (rate limiting) are landed.
4. The Methodology tab reflects the final calibration decision (item 12).

Items 8–11, 15–22 can land post-v1.0.
