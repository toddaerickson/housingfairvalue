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
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
        pool_timeout=10,
    )


def load_monthly_fact() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT obs_date, median_price, median_income, mortgage_rate_30y, "
        "oer_index, cs_hpi, zhvi, treasury_10y, cpi, real_dpi_per_capita "
        "FROM monthly_fact ORDER BY obs_date",
        engine(),
        parse_dates=["obs_date"],
    )
    return df.set_index("obs_date")
