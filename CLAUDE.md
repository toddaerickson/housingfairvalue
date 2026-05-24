# CLAUDE.md — Housing Fair Value

## Project Overview
National Housing Fair Value Calculator — interactive dashboard blending three affordability lenses (payment-affordability, price-to-income, price-to-rent) into a composite z-score overvaluation signal with 45 years of monthly history (1980→present). Python backend (FastAPI + FRED ingestion), React frontend (Vite + Recharts), Postgres + TimescaleDB via docker-compose.

## Development Commands
```bash
# First-time setup
cp .env.example .env          # Set FRED_API_KEY, POSTGRES_PASSWORD
docker compose up -d db       # Start Postgres (migrations auto-apply)
pip install -e ".[dev]"       # Install Python deps
python -m backend.ingest.fred --backfill  # Populate monthly_fact (1980→now)

# Run locally
uvicorn backend.api.main:app --reload    # API at :8000
cd frontend && npm install && npm run dev # Frontend at :5173

# Test & lint
pytest                        # Calc engine + API smoke + validation gate
ruff check backend            # Lint Python
ruff format backend           # Auto-format

# Data pipeline
python -m backend.ingest.fred --since 2025-01-01  # Incremental FRED ingest
```

## Architecture
- `backend/` — FastAPI app, three calc lenses, FRED ingestion, tests
- `frontend/` — React + Vite dashboard (History, Sensitivity, Methodology tabs)
- `db/migrations/` — Two-file schema: init + ingest tracking (auto-apply on compose up)
- `backend/calc/composite.py` — Equal-weighted z-blend of three lenses with empirical CDF percentile
- `backend/api/routers/{history,sensitivity}.py` — Two endpoints; empty-data returns 503 with detail

## Key Conventions
1. **Validation gate (non-negotiable):** `pytest backend/tests/test_validation_gate.py` enforces 2024 composite ±1pp of +38%, 1980/2006/2012 regime marks ±2pp. Reference values in `backend/calc/regimes.py`; calibration knob is `DEFAULT_PCT_PER_SIGMA` in `composite.py` (currently 19.0, provisional).
2. **Pre-1984 income stitch:** `backend/ingest/fred.py` anchors on first non-NaN month of `MEHOINUSA646N`, scales `A229RX0` to match.
3. **Common-availability mask:** All three z-series use the same observations so the composite is stable.
4. **No ZIP/MSA breakouts:** National scope only.

## CI/Deploy
- **GitHub Actions** (`ci.yml`): ruff lint + pytest + frontend typecheck/build on push to main and PRs
- **Daily FRED ingest** (`daily-ingest.yml`): cron 2 PM UTC; upserts via pipeline job
- **Docker:** non-root `app` user on port 8000. Health check: `/ready` (DB-touching)

## Pitfalls
- Gate failures post-backfill → suspect `pct_per_sigma` calibration (the only tunable knob)
- Sensitivity perturbation endpoints (`/sensitivity/breakpoints`, `/tornado`, `/heatmap`) must act on the latest *complete* row (`comp.index[-1]`), not `monthly.iloc[-1]` — the tail of `monthly_fact` carries fresh rates with stale (NaN) `median_income`/`median_price`, which `compute_lenses` drops
- `fly deploy` must be invoked with `--build-arg GIT_SHA="$(git rev-parse --short HEAD)"` so `/health` reports the running commit; otherwise it returns `"git_sha":"unknown"`
