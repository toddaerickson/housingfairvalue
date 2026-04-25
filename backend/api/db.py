"""DB session helpers + cached monthly_fact loader."""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@lru_cache(maxsize=1)
def engine() -> Engine:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(url, pool_pre_ping=True)


def load_monthly_fact() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT * FROM monthly_fact ORDER BY obs_date",
        engine(),
        parse_dates=["obs_date"],
    )
    return df.set_index("obs_date")
