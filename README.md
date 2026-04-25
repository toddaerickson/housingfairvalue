# National Housing Fair Value Calculator

Interactive dashboard for a US national housing overvaluation signal that
blends three lenses — payment-affordability, price-to-income, price-to-rent —
into a single composite z-score with ~45 years of monthly history.

National scope only. No ZIP, no per-MSA breakouts.

## Layout

```
backend/        FastAPI + ingestion + calc engine + tests
db/migrations/  Postgres + TimescaleDB schema
frontend/       React + Vite + Recharts dashboard
infra/          Render / Vercel / Supabase config
```

## Local dev

```sh
docker compose up -d           # postgres + timescale
cd backend && uv sync          # or: pip install -e .
export FRED_API_KEY=<key>
python -m backend.ingest.fred --backfill
pytest backend/tests
cd ../frontend && pnpm i && pnpm dev
```

## Validation gate

`pytest backend/tests/test_validation_gate.py` must pass before any UI ships:

- 2024 composite within 1pp of +38% overvaluation, within 2 pctile of 97th rank
- 1980 trough, 2006 peak, 2012 trough each match within 2pp

See `backend/calc/regimes.py` for reference values.
