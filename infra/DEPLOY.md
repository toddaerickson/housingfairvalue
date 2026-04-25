# Deployment Runbook

Step-by-step guide to deploy the Housing Fair Value dashboard from scratch.

## Architecture

```
[FRED API] → [Daily Cron (GH Actions)] → [Supabase Postgres] → [Render FastAPI] → [Vercel React SPA]
```

## Prerequisites

- FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html
- GitHub account with repo access
- Supabase account (free tier)
- Render account (free or Starter tier)
- Vercel account (Hobby tier)

## 1. Provision Supabase Database

1. Create a new project at https://supabase.com/dashboard
2. Note the connection string from Settings > Database > Connection string (URI)
3. Run migrations via the SQL editor:
   - Paste contents of `db/migrations/001_init.sql`
   - Paste contents of `db/migrations/002_ingest_tracking.sql`
4. The `DATABASE_URL` format: `postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
   - Use port **6543** (PgBouncer/pooler) for the API
   - Use port **5432** (direct) for the ingest cron in GitHub Actions

## 2. Run Initial Backfill

From a local machine with Python 3.11+:

```bash
pip install -e .
export FRED_API_KEY=<your-key>
export DATABASE_URL=<supabase-direct-connection-port-5432>
python -m backend.ingest.pipeline --backfill
```

Verify: the pipeline should report 500+ monthly_fact rows and composite_history rows.

## 3. Deploy API to Render

1. Connect the GitHub repo to Render
2. Create a **Web Service** from the repo
3. Settings:
   - **Docker:** use `infra/api.Dockerfile`
   - **Health check path:** `/ready`
4. Environment variables:
   - `DATABASE_URL` = Supabase pooler connection string (port 6543)
   - `FRED_API_KEY` = your FRED key
   - `ALLOWED_ORIGINS` = `https://housingfairvalue.vercel.app` (or your custom domain)
5. Enable auto-deploy from `main` branch

## 4. Deploy Frontend to Vercel

1. Connect the GitHub repo to Vercel
2. Settings:
   - **Root directory:** `frontend`
   - **Build command:** `npm run build`
   - **Output directory:** `dist`
3. Environment variables:
   - `VITE_API_BASE` = `https://<your-render-service>.onrender.com` (no trailing slash)
4. Vercel auto-deploys from `main`

## 5. Configure Daily Cron

1. In the GitHub repo, go to Settings > Secrets and variables > Actions
2. Add repository secrets:
   - `DATABASE_URL` = Supabase **direct** connection string (port 5432)
   - `FRED_API_KEY` = your FRED key
   - `HEALTHCHECK_PING_URL` = (optional) Healthchecks.io ping URL
3. The `.github/workflows/daily-ingest.yml` runs at 2 PM UTC daily
4. Verify: trigger the workflow manually via Actions > Daily FRED Ingest > Run workflow

## 6. Set Up Monitoring

### UptimeRobot (free)
- Monitor 1: `GET https://<render-url>/health` (liveness, 5-min interval)
- Monitor 2: `GET https://<render-url>/health/data` (freshness, alert on 503)
- Monitor 3: `GET https://<vercel-url>/` (frontend, 5-min interval)
- Alert contact: terickson@marathoncre.com

### Healthchecks.io (free, optional)
- Create a check with 36-hour grace period
- Add the ping URL as `HEALTHCHECK_PING_URL` GitHub secret
- Alerts if the daily cron stops running

## 7. Custom Domain (Optional)

1. Register/own a domain
2. In Vercel, go to project Settings > Domains > Add
3. Add a CNAME record in your DNS pointing to `cname.vercel-dns.com`
4. Update `ALLOWED_ORIGINS` in Render to include the custom domain

## Recovery

If everything breaks, the full database can be rebuilt in ~10 minutes:

```bash
# 1. Re-run migrations in Supabase SQL editor
# 2. Backfill
python -m backend.ingest.pipeline --backfill
```

All data comes from FRED — there is no user-generated data to lose.

## Environment Variables Summary

| Variable | Where | Value |
|----------|-------|-------|
| `DATABASE_URL` | Render | Supabase pooler (port 6543) |
| `DATABASE_URL` | GitHub Actions | Supabase direct (port 5432) |
| `FRED_API_KEY` | Render, GitHub Actions | FRED API key |
| `ALLOWED_ORIGINS` | Render | Vercel URL(s), comma-separated |
| `VITE_API_BASE` | Vercel | Render service URL |
| `HEALTHCHECK_PING_URL` | GitHub Actions | Healthchecks.io ping URL (optional) |
