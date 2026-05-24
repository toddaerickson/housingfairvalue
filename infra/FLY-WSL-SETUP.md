# Fly.io setup from WSL — first-time deploy

Quick-start for creating the `housingfairvalue-api` Fly app from a WSL
shell. Skip to step 3 if you already have `flyctl` installed.

For the full deployment runbook (Supabase, Vercel, daily cron), see
`infra/DEPLOY.md`. This file is the **subset that runs from your WSL
terminal**.

## Why a separate doc

Two WSL-specific gotchas the generic runbook doesn't address:

1. `fly auth login` opens a browser. WSL2 will launch the Windows
   default browser fine if `wslu` is installed; if not, it prints a URL
   you copy/paste into Windows yourself.
2. The `curl -L https://fly.io/install.sh | sh` line puts `flyctl` in
   `~/.fly/bin/flyctl` inside WSL — not in Windows. You'll want this
   binary on the WSL `PATH`, not your Windows one.

---

## 1. Install `flyctl` inside WSL

```sh
curl -L https://fly.io/install.sh | sh
```

After install, add the bin dir to your WSL shell startup (one-time):

```sh
echo 'export FLYCTL_INSTALL="$HOME/.fly"' >> ~/.bashrc
echo 'export PATH="$FLYCTL_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

If you use `zsh`, swap `.bashrc` for `.zshrc`.

Verify:

```sh
flyctl version
```

## 2. Sign in

```sh
flyctl auth login
```

A browser tab opens. If WSL says "no display" or nothing happens, copy
the URL it prints and paste into a Windows browser manually — same
login flow. Fly stores credentials at `~/.fly/config.yml` inside WSL.

If you're a brand-new Fly account: you may be asked to add a payment
method even though this app fits the free tier. Fly does this to deter
abuse; nothing is charged unless you exceed the free allowance.

## 3. Clone the repo (if it's not already in WSL)

```sh
git clone https://github.com/toddaerickson/housingfairvalue.git
cd housingfairvalue
```

> WSL line-ending note: don't `git clone` into a Windows `C:\` mount
> and run the build from inside `\\wsl$\`. Mixing line endings between
> Windows and WSL git triggers spurious diffs in CI. Clone *inside*
> WSL's filesystem (e.g. `~/code/housingfairvalue`).

## 4. Create the app

From the repo root:

```sh
flyctl launch \
  --no-deploy \
  --copy-config \
  --name housingfairvalue-api \
  --region iad \
  --org personal
```

`flyctl` will read the committed `fly.toml` (already correct: region
`iad`, port 8000, 256 MB, `/ready` health check) and ask a couple of
questions:

| Question                                                    | Answer  |
| ----------------------------------------------------------- | ------- |
| Would you like to copy its configuration to the new app?    | **yes** |
| Do you want to tweak these settings before proceeding?      | **no**  |
| Would you like to set up a Postgres database now?           | **no**  |
| Would you like to set up an Upstash Redis database now?     | **no**  |
| Create .dockerignore from .gitignore?                       | yes     |

We use Supabase for Postgres, not Fly's own Postgres. Saying "yes" to
the Postgres question would provision and bill a second database we
don't need.

If `--org personal` isn't right, run `flyctl orgs list` first and use
the slug you see there.

## 5. Set secrets

You'll need three values handy:

- `DATABASE_URL` — from Supabase dashboard → Project Settings → Database
  → Connection string → **Session pooler (port 5432)**. The bare
  `postgresql://...` form is fine; the backend normalizes the scheme.
- `FRED_API_KEY` — from <https://fredaccount.stlouisfed.org/apikey>
- `ALLOWED_ORIGINS` — your Vercel frontend URL, e.g.
  `https://housingfairvalue.vercel.app`

```sh
flyctl secrets set \
  DATABASE_URL='postgresql://postgres.<ref>:<pwd>@aws-0-us-east-1.pooler.supabase.com:5432/postgres' \
  FRED_API_KEY='<fred-key>' \
  ALLOWED_ORIGINS='https://housingfairvalue.vercel.app' \
  --app housingfairvalue-api
```

> Wrap the values in **single quotes** in WSL — both Supabase URLs
> and FRED keys can contain `&`, `?`, and other shell metacharacters.

`flyctl secrets list --app housingfairvalue-api` shows names but masks
values. Re-running `secrets set` just overwrites.

## 6. Deploy

```sh
flyctl deploy --app housingfairvalue-api \
  --build-arg GIT_SHA="$(git rev-parse --short HEAD)"
```

The `GIT_SHA` build arg is baked into the image so `/health` reports
which commit is actually running. Omit the flag and `/health` reports
`"git_sha":"unknown"` — useful sometimes (local docker build), bad on
prod because `/verify-deploy` can't confirm the match.

First deploy builds the Docker image (3-5 minutes) and pushes it.
Subsequent deploys cache layers.

Watch the tail with:

```sh
flyctl logs --app housingfairvalue-api
```

## 7. Smoke test

Once `flyctl deploy` prints `Visit your newly deployed app at https://housingfairvalue-api.fly.dev/`:

```sh
curl https://housingfairvalue-api.fly.dev/health
# expect: {"status":"ok"}

curl https://housingfairvalue-api.fly.dev/ready
# expect: {"status":"ready"}     ← proves DB connectivity

curl https://housingfairvalue-api.fly.dev/history/kpi
# expect: {"overvaluation_pct": ..., "percentile_rank": ..., ...}
```

If `/ready` returns `503 {"detail":"database unavailable"}`:

- The DSN is wrong, expired, or Supabase is paused. Open the Supabase
  dashboard to confirm the project is awake.
- After fixing, redeploy isn't needed — `flyctl secrets set` triggers
  an automatic rolling restart.

If `/history/kpi` returns 503 `"no monthly_fact data — run backfill"`:

- The ingest cron hasn't populated `monthly_fact` yet. Trigger it
  manually: <https://github.com/toddaerickson/housingfairvalue/actions/workflows/daily-ingest.yml>
  → Run workflow.

## 8. Cost / scaling notes

The committed `fly.toml` sets:

```toml
auto_stop_machines = "stop"
min_machines_running = 0
```

That means the VM **shuts down when idle** and **cold-starts** on the
next request (~2 seconds). Free-tier friendly. If you announce the
dashboard publicly and expect sustained traffic, change to
`min_machines_running = 1` and redeploy.

VM size is `shared-cpu-1x` / 256 MB — fine for this workload because
the API does small NumPy operations on a ~540-row dataframe, and the
materialized `composite_history` table means `/history/composite` is a
straight DB read, no recompute. If memory ever pinches, bump to 512 MB
in `fly.toml`.

## 9. Day-to-day commands

| Task                         | Command                                                                                        |
| ---------------------------- | ---------------------------------------------------------------------------------------------- |
| Tail logs                    | `flyctl logs --app housingfairvalue-api`                                                       |
| Open an SSH shell to the VM  | `flyctl ssh console --app housingfairvalue-api`                                                |
| Restart the app              | `flyctl machines restart --app housingfairvalue-api`                                           |
| Rotate a secret              | `flyctl secrets set KEY=value --app housingfairvalue-api`                                      |
| Redeploy after a code change | `flyctl deploy --app housingfairvalue-api --build-arg GIT_SHA="$(git rev-parse --short HEAD)"` |
| See machine state            | `flyctl status --app housingfairvalue-api`                                                     |

## 10. If something goes wrong

- **`flyctl launch` says "app name taken"** — someone (probably you in
  an earlier attempt) already created `housingfairvalue-api`. Skip
  `launch` and go straight to step 5 (`secrets set`) and step 6
  (`deploy`).
- **Browser doesn't open on `auth login`** — install `wslu`
  (`sudo apt install wslu`), or copy the printed URL into Windows
  manually.
- **Docker build fails on `psycopg`** — make sure you're on a recent
  enough commit to include PR #27 (DB URL normalization). The build
  itself doesn't depend on the URL, but the runtime does.
- **`/ready` works but `/history/kpi` 503s** — Supabase has the schema
  but the ingest cron hasn't run yet. Manual-trigger the workflow per
  step 7.
