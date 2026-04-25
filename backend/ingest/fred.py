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
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise SystemExit("DATABASE_URL not set")
        return cls(fred_api_key=key, database_url=url)


def fetch_series(fred: Fred, series_id: str, start: date) -> pd.Series:
    s = fred.get_series(series_id, observation_start=start)
    s.name = series_id
    s.index = pd.to_datetime(s.index)
    return s.dropna()


def to_monthly(s: pd.Series, freq: str) -> pd.Series:
    """Resample a series to a monthly grid.

    - D/W/M: month-end last value (mortgage rate weekly, treasury daily, OER monthly).
    - Q/A: forward-fill *and* back-fill within the reporting period so the first
      observation propagates into earlier months of the same period rather than
      being dropped (FRED quarterly/annual stamps are typically at period start;
      `resample("ME")` would otherwise leave the period's leading months NaN).
    """
    if freq in ("D", "W", "M"):
        return s.resample("ME").last()
    if freq in ("Q", "A"):
        return s.resample("ME").ffill().bfill()
    raise ValueError(f"unknown freq: {freq}")


def stitch_income(median_income_m: pd.Series, real_dpi_m: pd.Series) -> pd.Series:
    """Backfill MEHOINUSA646N (1984+) with A229RX0 scaled at the splice point.

    Anchors on the *first non-NaN month* of the median household income series
    (rather than a hardcoded date) since the actual splice month varies with
    FRED's reporting cadence and our resampling rules. Pre-splice values use
    the scaled DPI; post-splice values are unchanged.
    """
    if median_income_m.dropna().empty or real_dpi_m.dropna().empty:
        return median_income_m

    splice = median_income_m.dropna().index.min()
    if splice not in real_dpi_m.index or pd.isna(real_dpi_m.loc[splice]):
        log.warning("Income splice anchor %s not in real DPI — returning unspliced", splice)
        return median_income_m

    scale = median_income_m.loc[splice] / real_dpi_m.loc[splice]
    pre = real_dpi_m.loc[real_dpi_m.index < splice] * scale
    return pd.concat([pre, median_income_m.dropna()]).sort_index()


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


_INSERT_CHUNK = 1000

ALLOWED_FACT_COLS = {
    "median_price", "median_income", "mortgage_rate_30y", "oer_index",
    "cs_hpi", "zhvi", "treasury_10y", "cpi", "real_dpi_per_capita",
}


def _chunked(rows: list[dict], n: int = _INSERT_CHUNK):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def write_observations(engine, raw: dict[str, pd.Series]) -> None:
    rows: list[dict] = []
    for sid, s in raw.items():
        for ts, v in s.items():
            rows.append({"series_id": sid, "obs_date": ts.date(), "value": float(v)})
    if not rows:
        return
    sql = text("""
        INSERT INTO observation (series_id, obs_date, value)
        VALUES (:series_id, :obs_date, :value)
        ON CONFLICT (series_id, obs_date) DO UPDATE SET value = EXCLUDED.value
    """)
    with engine.begin() as conn:
        for chunk in _chunked(rows):
            conn.execute(sql, chunk)


def write_monthly_fact(engine, df: pd.DataFrame) -> None:
    if df.empty:
        return
    cols = list(df.columns)
    bad = set(cols) - ALLOWED_FACT_COLS
    if bad:
        raise ValueError(f"monthly_fact has unexpected columns: {sorted(bad)}")
    df = df.dropna(how="all")
    if df.empty:
        return
    payload = [
        {"obs_date": ts.date(), **{c: (None if pd.isna(row[c]) else float(row[c])) for c in cols}}
        for ts, row in df.iterrows()
    ]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
    sql = text(
        f"INSERT INTO monthly_fact (obs_date, {', '.join(cols)}) "
        f"VALUES (:obs_date, {', '.join(':' + c for c in cols)}) "
        f"ON CONFLICT (obs_date) DO UPDATE SET {set_clause}"
    )
    with engine.begin() as conn:
        for chunk in _chunked(payload):
            conn.execute(sql, chunk)


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
