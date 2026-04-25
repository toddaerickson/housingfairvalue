"""Daily ingest pipeline orchestration.

Run:
    python -m backend.ingest.pipeline          # default: 35-day lookback
    python -m backend.ingest.pipeline --backfill  # full history

Wraps fred.run() with ingest_run tracking and optional Healthchecks.io ping.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import structlog

from .fred import START_DATE, run

log = structlog.get_logger()

LOOKBACK_DAYS = 35  # Covers FRED revision window + quarterly lag


def _ping_healthcheck(success: bool) -> None:
    """Ping Healthchecks.io if configured."""
    url = os.environ.get("HEALTHCHECK_PING_URL")
    if not url:
        return
    try:
        import httpx
        suffix = "" if success else "/fail"
        httpx.get(f"{url}{suffix}", timeout=10)
    except Exception as exc:
        log.warning("healthcheck ping failed", error=str(exc))


def _record_ingest_run(
    since_date: date,
    rows_obs: int,
    rows_fact: int,
    rows_composite: int,
    status: str,
    error_detail: str | None = None,
) -> None:
    """Write to ingest_run table if it exists."""
    try:
        from sqlalchemy import create_engine, text
        url = os.environ.get("DATABASE_URL")
        if not url:
            return
        eng = create_engine(url)
        with eng.begin() as conn:
            conn.execute(text("""
                INSERT INTO ingest_run (since_date, rows_obs, rows_fact, status, error_detail, finished_at)
                VALUES (:since_date, :rows_obs, :rows_fact, :status, :error_detail, now())
            """), {
                "since_date": since_date,
                "rows_obs": rows_obs,
                "rows_fact": rows_fact,
                "status": status,
                "error_detail": error_detail,
            })
    except Exception as exc:
        log.warning("failed to record ingest run", error=str(exc))


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Daily ingest pipeline")
    p.add_argument("--backfill", action="store_true", help="full history from 1980")
    args = p.parse_args()

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )

    if args.backfill:
        since = START_DATE
    else:
        since = date.today() - timedelta(days=LOOKBACK_DAYS)

    log.info("pipeline.start", since=str(since), backfill=args.backfill)

    try:
        monthly, rows_obs, rows_fact, rows_composite = run(since, write=True)

        status = "no_data" if (rows_obs == 0 and rows_fact == 0) else "ok"
        log.info(
            "pipeline.complete",
            status=status,
            rows_obs=rows_obs,
            rows_fact=rows_fact,
            rows_composite=rows_composite,
            date_range_start=str(monthly.index.min()) if not monthly.empty else None,
            date_range_end=str(monthly.index.max()) if not monthly.empty else None,
        )

        _record_ingest_run(since, rows_obs, rows_fact, rows_composite, status)
        _ping_healthcheck(success=True)

    except Exception as exc:
        log.error("pipeline.failed", error=str(exc), exc_info=True)
        _record_ingest_run(since, 0, 0, 0, "error", str(exc))
        _ping_healthcheck(success=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
