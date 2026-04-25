# National Housing Fair Value Calculator

Interactive dashboard for a US national housing overvaluation signal that
blends three lenses — payment-affordability, price-to-income, price-to-rent —
into a single composite z-score with ~45 years of monthly history (1980 →
present).

National scope only. No ZIP, no per-MSA breakouts.

## Repo layout

```
backend/        FastAPI + ingestion + calc engine + tests
db/migrations/  Postgres + TimescaleDB schema (auto-applied on first compose up)
frontend/       React + Vite + Recharts dashboard
infra/          Docker / Render / Vercel config
pyproject.toml  Python project (importable as `backend.*`)
docker-compose.yml
```

## Where the code lives

GitHub: <https://github.com/toddaerickson/housingfairvalue>
Active branch: `claude/housing-affordability-calculator-J9aG3` (also pushed
to `main`).

```sh
git clone https://github.com/toddaerickson/housingfairvalue.git
cd housingfairvalue
```

## Prerequisites

- Python ≥ 3.11
- Node ≥ 20 + npm
- Docker + Docker Compose (for Postgres/TimescaleDB)
- A free FRED API key — <https://fred.stlouisfed.org/docs/api/api_key.html>

## First-time setup

1. Copy the env template and fill it in:

   ```sh
   cp .env.example .env
   # edit .env: set FRED_API_KEY and POSTGRES_PASSWORD
   ```

2. Boot Postgres + TimescaleDB (migrations auto-apply):

   ```sh
   docker compose up -d db
   ```

3. Install Python deps and run the FRED backfill (1980 → today). This
   populates `monthly_fact` so the API has data to serve:

   ```sh
   pip install -e ".[dev]"
   set -a && source .env && set +a
   python -m backend.ingest.fred --backfill
   ```

   You should see a log line like `wrote 540 monthly rows (1980-01-31..2025-XX-31)`.

4. Run the test suite:

   ```sh
   pytest
   ```

   16 calc-engine + 9 API smoke tests run against synthetic data. The 4
   parametrized validation-gate tests run against the real backfill and
   pin the composite to four reference regimes (1980 trough, 2006 peak,
   2012 trough, 2024 current). They skip cleanly until `monthly_fact`
   is populated.

5. Start the API and the frontend:

   ```sh
   # terminal 1 — API at http://localhost:8000
   uvicorn backend.api.main:app --reload

   # terminal 2 — frontend at http://localhost:5173
   cd frontend && npm install && npm run dev
   ```

## Accessing the running app

| What                  | URL                                  | Notes                                              |
| --------------------- | ------------------------------------ | -------------------------------------------------- |
| **Frontend (dashboard)** | <http://localhost:5173>           | Vite dev server. Hot-reload on save.              |
| Backend API           | <http://localhost:8000>              | Uvicorn. Bound to loopback by docker-compose.     |
| **Interactive API docs** | <http://localhost:8000/docs>      | FastAPI's Swagger UI — try every endpoint live.   |
| Alt API docs (Redoc)  | <http://localhost:8000/redoc>        |                                                    |
| Liveness probe        | <http://localhost:8000/health>       | Cheap; doesn't touch the DB.                       |
| Readiness probe       | <http://localhost:8000/ready>        | Pings the DB. Use this for k8s/Render health checks. |
| Postgres (host)       | `127.0.0.1:5432`                     | Bound to loopback only. Creds from `.env`.         |

The frontend talks to the API via Vite's dev proxy: requests to `/api/*`
get forwarded to `http://localhost:8000/*`.

### Frontend tabs

- **History** — KPI strip, composite-overvaluation chart 1980 → present
  with regime markers and a brush selector for zoom.
- **Sensitivity** — heatmap of implied fair-value price across mortgage
  rate × qualifying DTI. Tornado / Monte Carlo / breakpoint cards arrive
  in the next phase (API endpoints already exist).
- **Methodology** — discloses the equal-weighting assumption and the
  pre-1984 income stitch.

## Day-to-day commands

| Task                              | Command                                                    |
| --------------------------------- | ---------------------------------------------------------- |
| Install Python deps               | `pip install -e ".[dev]"`                                 |
| Install frontend deps             | `cd frontend && npm install`                              |
| Run all tests                     | `pytest`                                                   |
| Run only the calc-engine unit tests | `pytest backend/tests/test_calc.py -v`                  |
| Run the validation gate           | `pytest backend/tests/test_validation_gate.py -v`         |
| Lint Python                       | `ruff check backend`                                       |
| Auto-format Python                | `ruff format backend`                                      |
| Typecheck + build frontend        | `cd frontend && npm run build`                             |
| Daily/incremental FRED ingest     | `python -m backend.ingest.fred --since 2025-01-01`         |
| Full backfill (idempotent)        | `python -m backend.ingest.fred --backfill`                 |
| Boot everything in Docker         | `docker compose up`                                        |
| Tear down (preserves volume)      | `docker compose down`                                      |
| Tear down + delete DB             | `docker compose down -v`                                   |

## Validation gate (non-negotiable)

`pytest backend/tests/test_validation_gate.py` enforces:

- 2024 composite within **1 pp** of +38% overvaluation, within **2 pp** of
  the 97th percentile rank.
- 1980 trough, 2006 peak, 2012 trough each match within **2 pp**.

Reference values live in `backend/calc/regimes.py`. The gate skips when no
backfilled data is present, so unit tests can run on a fresh checkout.
After backfill, the gate runs end-to-end on every commit.

If the gate fails after a real backfill, check the calibration of
`DEFAULT_PCT_PER_SIGMA` in `backend/calc/composite.py` (currently 19.0,
provisional). The std-to-pct conversion is the only knob that should move.

## Backend internals (one-paragraph tour)

- `backend/ingest/fred.py` — pulls 9 FRED series, monthly resamples them
  with frequency-appropriate rules, performs the **pre-1984 income stitch**
  (anchors on the first non-NaN month of `MEHOINUSA646N`, scales `A229RX0`
  to match), and chunked-upserts into `observation` and `monthly_fact`.
- `backend/calc/composite.py` — equal-weighted z-blend of the three lenses
  (`affordability`, `price_to_income`, `price_to_rent`) with a mid-rank
  empirical CDF for the percentile signal. Lenses share a common-availability
  mask so all three z-series use the same observations.
- `backend/api/main.py` — FastAPI app with CORS sourced from
  `ALLOWED_ORIGINS`, plus `/health` (liveness) and `/ready` (DB-touching).
- `backend/api/routers/{history,sensitivity}.py` — endpoints for the two
  dashboard tabs. Empty-data states return `503` with a structured detail
  rather than an unhandled 500.

## Deployment notes

- **Render** for the API. Use `/ready` as the health check so traffic isn't
  routed before the DB is reachable. Set `DATABASE_URL`, `FRED_API_KEY`,
  `ALLOWED_ORIGINS=https://your-vercel-domain.example.com`.
- **Vercel** for the frontend. Set the API origin via env or rewrites.
- **Supabase** for managed Postgres+TimescaleDB.
- The Docker image runs as a non-root `app` user on port 8000.
- Add a daily cron on Render running `python -m backend.ingest.fred --since YYYY-MM-DD`
  to keep `monthly_fact` current.

## What we know is unfinished

- Calibration of `pct_per_sigma` against a real backfill (provisional 19.0).
- Three-lens decomposition chart, distribution / percentile strip, regime
  comparison panel.
- Sensitivity tab inputs panel (sliders), tornado chart, years-to-FV grid,
  Monte Carlo histogram, breakpoint cards (API endpoints already exist; UI
  wiring pending).
- A frontend `package-lock.json` (commit it before turning on `npm ci`).

## Contributing notes

- `pyproject.toml` lives at the repo root; the package is importable as
  `backend.*`. Always run `pip install -e ".[dev]"` from the repo root.
- New tests go in `backend/tests/`. Anything that needs the DB should use
  the same `monkeypatch.setattr(history, "load_monthly_fact", lambda: df)`
  pattern in `test_api.py`.
- `git push` triggers GitHub Actions: ruff + pytest + frontend
  typecheck/build.
