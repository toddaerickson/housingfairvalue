"""Test fixtures.

The validation gate runs against a real backfilled monthly_fact frame. To
avoid a hard dependency on a live FRED key during routine `pytest` runs,
fixtures load from one of (in order):

  1. `backend/fixtures/monthly_fact.csv` — checked-in fixture if present
  2. DATABASE_URL — query the live `monthly_fact` table
  3. else: skip the gate test with a clear message

Unit tests on the calc engine use deterministic synthetic data and don't
depend on this loader.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "monthly_fact.csv"


@pytest.fixture(scope="session")
def monthly_fact() -> pd.DataFrame:
    if FIXTURE.exists():
        df = pd.read_csv(FIXTURE, parse_dates=["obs_date"]).set_index("obs_date")
        return df.sort_index()

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        engine = create_engine(db_url)
        df = pd.read_sql("SELECT * FROM monthly_fact ORDER BY obs_date", engine, parse_dates=["obs_date"])
        return df.set_index("obs_date")

    pytest.skip(
        "no monthly_fact fixture or DATABASE_URL — run `python -m backend.ingest.fred --backfill` "
        "or add backend/fixtures/monthly_fact.csv"
    )
