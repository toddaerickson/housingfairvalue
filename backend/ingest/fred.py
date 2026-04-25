"""FRED ingestion + monthly resampling + pre-1984 income stitch.

Run:
    python -m backend.ingest.fred --backfill              # full history 1980->today
    python -m backend.ingest.fred --since 2024-01-01      # incremental

Reads FRED_API_KEY from env. Writes raw observations to `observation` and a
joined monthly grid to `monthly_fact`.
"""

from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from datetime import date

import pandas as pd
from fredapi import Fred
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)


SERIES = {
    "MSPUS":                "Q",
    "MEHOINUSA646N":        "A",
    "MORTGAGE30US":         "W",
    "CUSR0000SEHC":         "M",
    "CSUSHPINSA":           "M",
    "USAUCSFRCONDOSMSAMID": "M",
    "DGS10":                "D",
    "CPIAUCSL":             "M",
    "A229RX0":              "M",
}

START_DATE = date(1980, 1, 1)
INCOME_SPLICE_DATE = pd.Timestamp("1984-01-01")


@dataclass(frozen=True)
class Config:
    fred_api_key: str
    database_url: str

    @classmethod
    def from_env(cls) -> "Config":
        key = os.environ.get("FRED_API_KEY")
        if not key:
            raise SystemExit("FRED_API_KEY not set")
        url = os.environ.get("DATABASE_URL", "postgresql+psycopg://hfv:hfv@localhost:5432/hfv")
        return cls(fred_api_key=key, database_url=url)


def fetch_series(fred: Fred, series_id: str, start: date) -> pd.Series:
    s = fred.get_series(series_id, observation_start=start)
    s.name = series_id
    s.index = pd.to_datetime(s.index)
    return s.dropna()


def to_monthly(s: pd.Series, freq: str) -> pd.Series:
    """Resample a series to a monthly grid using rules appropriate to its native freq.

    - D/W: month-end last value (proxies weekly mortgage rate, daily 10y treasury).
    - M: month-end as is.
    - Q/A: forward-fill within the reporting period (no linear interpolation).
    """
    if freq in ("D", "W"):
        return s.resample("ME").last()
    if freq == "M":
        return s.resample("ME").last()
    if freq in ("Q", "A"):
        return s.resample("ME").ffill()
    raise ValueError(f"unknown freq: {freq}")


def stitch_income(median_income_m: pd.Series, real_dpi_m: pd.Series) -> pd.Series:
    """Backfill MEHOINUSA646N (1984+) with A229RX0 scaled at the splice point.

    Scales the real DPI per capita series to dollar-match median household
    income at January 1984, the first available month of the household income
    series. Pre-1984 values use the scaled DPI; 1984+ uses the actual median
    income series unchanged.
    """
    if median_income_m.empty or real_dpi_m.empty:
        return median_income_m

    splice = INCOME_SPLICE_DATE.to_period("M").to_timestamp("M")
    if splice not in median_income_m.index or splice not in real_dpi_m.index:
        log.warning("Income splice point %s missing — returning unspliced series", splice)
        return median_income_m

    scale = median_income_m.loc[splice] / real_dpi_m.loc[splice]
    pre = real_dpi_m.loc[:splice - pd.Timedelta(days=1)] * scale
    return pd.concat([pre, median_income_m]).sort_index()


def build_monthly_fact(raw: dict[str, pd.Series]) -> pd.DataFrame:
    monthly = {sid: to_monthly(s, SERIES[sid]) for sid, s in raw.items()}

    income_spliced = stitch_income(monthly["MEHOINUSA646N"], monthly["A229RX0"])

    df = pd.DataFrame({
        "median_price":         monthly["MSPUS"],
        "median_income":        income_spliced,
        "mortgage_rate_30y":    monthly["MORTGAGE30US"],
        "oer_index":            monthly["CUSR0000SEHC"],
        "cs_hpi":               monthly["CSUSHPINSA"],
        "zhvi":                 monthly["USAUCSFRCONDOSMSAMID"],
        "treasury_10y":         monthly["DGS10"],
        "cpi":                  monthly["CPIAUCSL"],
        "real_dpi_per_capita":  monthly["A229RX0"],
    })
    df.index.name = "obs_date"
    return df.loc[df.index >= pd.Timestamp(START_DATE)]


def write_observations(engine, raw: dict[str, pd.Series]) -> None:
    rows: list[dict] = []
    for sid, s in raw.items():
        for ts, v in s.items():
            rows.append({"series_id": sid, "obs_date": ts.date(), "value": float(v)})
    if not rows:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO observation (series_id, obs_date, value)
            VALUES (:series_id, :obs_date, :value)
            ON CONFLICT (series_id, obs_date) DO UPDATE SET value = EXCLUDED.value
        """), rows)


def write_monthly_fact(engine, df: pd.DataFrame) -> None:
    if df.empty:
        return
    cols = list(df.columns)
    payload = [
        {"obs_date": ts.date(), **{c: (None if pd.isna(row[c]) else float(row[c])) for c in cols}}
        for ts, row in df.iterrows()
    ]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
    sql = f"""
        INSERT INTO monthly_fact (obs_date, {", ".join(cols)})
        VALUES (:obs_date, {", ".join(":" + c for c in cols)})
        ON CONFLICT (obs_date) DO UPDATE SET {set_clause}
    """
    with engine.begin() as conn:
        conn.execute(text(sql), payload)


def run(start: date, write: bool = True) -> pd.DataFrame:
    cfg = Config.from_env()
    fred = Fred(api_key=cfg.fred_api_key)
    raw = {sid: fetch_series(fred, sid, start) for sid in SERIES}
    monthly = build_monthly_fact(raw)

    if write:
        engine = create_engine(cfg.database_url)
        write_observations(engine, raw)
        write_monthly_fact(engine, monthly)
        log.info("wrote %d monthly rows (%s..%s)", len(monthly), monthly.index.min(), monthly.index.max())
    return monthly


def main() -> None:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--backfill", action="store_true", help="pull history from 1980-01-01")
    g.add_argument("--since", type=lambda s: date.fromisoformat(s), help="pull from YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="don't write to DB")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    start = START_DATE if args.backfill else args.since
    run(start, write=not args.dry_run)


if __name__ == "__main__":
    main()
