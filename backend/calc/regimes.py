"""Reference regimes used by the validation gate and the regime-comparison UI.

Each regime pins a specific month in the composite history and the expected
overvaluation % and percentile rank. Calibrated 2026-04-25 against a full
FRED backfill (1980-present) with pct_per_sigma=28.0.

The composite history starts at 1983-01 because that is the earliest month
where all four required inputs (price, income, mortgage rate, OER) are
non-null simultaneously. The "2024 current" regime uses 2024-01-31 because
median household income (MEHOINUSA646N, annual) is published with a ~1 year
lag, limiting how far forward the composite extends.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Regime:
    name: str
    obs_date: str             # YYYY-MM-DD, end-of-month for monthly grid
    overvaluation_pct: float  # expected overvaluation reading
    percentile_rank: float    # expected percentile (0-100)
    pct_tol: float            # absolute pp tolerance on overvaluation_pct
    rank_tol: float           # absolute pp tolerance on percentile_rank


REGIMES: tuple[Regime, ...] = (
    Regime(
        name="2024 current",
        obs_date="2024-01-31",
        overvaluation_pct=31.4,
        percentile_rank=93.8,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
    Regime(
        name="2006 peak",
        obs_date="2006-06-30",
        overvaluation_pct=30.3,
        percentile_rank=93.6,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
    Regime(
        name="2012 trough",
        obs_date="2012-01-31",
        overvaluation_pct=-8.0,
        percentile_rank=45.3,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
    Regime(
        name="1983 affordability trough",
        obs_date="1983-01-31",
        overvaluation_pct=-16.0,
        percentile_rank=24.7,
        pct_tol=2.0,
        rank_tol=3.0,
    ),
)


def regime_by_name(name: str) -> Regime:
    for r in REGIMES:
        if r.name == name:
            return r
    raise KeyError(name)
