"""FastAPI app entrypoint."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from .db import engine
from .routers import history, sensitivity

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Housing Fair Value API",
    description="National US housing overvaluation composite signal — history + sensitivity.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.include_router(history.router)
app.include_router(sensitivity.router)

# Cache-Control values for different endpoint groups
_CACHE_HISTORY = "public, max-age=3600, stale-while-revalidate=86400"
_CACHE_SENSITIVITY = "public, max-age=3600"


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    path = request.url.path
    if path.startswith("/history/"):
        response.headers["Cache-Control"] = _CACHE_HISTORY
    elif path.startswith("/sensitivity/"):
        response.headers["Cache-Control"] = _CACHE_SENSITIVITY
    return response


@app.get("/health")
def health():
    """Liveness only — does not touch the DB."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness — pings the DB. Render/k8s should use this for traffic gating."""
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db unavailable: {e}") from e
    return {"status": "ready"}


@app.get("/health/data")
def health_data():
    """Data freshness check — queries ingest_run and monthly_fact for staleness."""
    try:
        with engine().connect() as conn:
            # Check latest ingest run
            row = conn.execute(text(
                "SELECT finished_at, status, rows_obs, rows_fact "
                "FROM ingest_run WHERE status = 'ok' "
                "ORDER BY finished_at DESC LIMIT 1"
            )).fetchone()

            # Check latest data point
            latest = conn.execute(text(
                "SELECT MAX(obs_date) AS max_date FROM monthly_fact"
            )).fetchone()

        if row is None:
            return Response(
                content='{"status":"stale","detail":"no successful ingest runs"}',
                status_code=503,
                media_type="application/json",
            )

        from datetime import datetime, timezone
        finished = row[0]
        hours_since = (datetime.now(timezone.utc) - finished).total_seconds() / 3600.0
        latest_date = str(latest[0]) if latest and latest[0] else None

        result = {
            "status": "stale" if hours_since > 48 else "ok",
            "last_run": finished.isoformat(),
            "hours_since_run": round(hours_since, 1),
            "latest_data": latest_date,
        }
        if hours_since > 48:
            return Response(
                content=__import__("json").dumps(result),
                status_code=503,
                media_type="application/json",
            )
        return result

    except Exception:
        # ingest_run table may not exist yet (pre-migration)
        return {"status": "unknown", "detail": "ingest_run table not available"}
