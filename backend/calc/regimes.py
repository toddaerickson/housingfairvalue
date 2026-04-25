"""Reference regimes used by the validation gate and the regime-comparison UI.

Each regime pins a specific month in the composite history and the expected
overvaluation % and percentile rank as taken from the source 2026 Excel
workbook. The validation gate enforces tolerances against these values.

Targets below are the working numbers; they are the values to lock down once
a real backfill has been run end-to-end. Until then they serve as a target
for calibration of `pct_per_sigma`.
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
        obs_date="2024-12-31",
        overvaluation_pct=38.0,
        percentile_rank=97.0,
        pct_tol=1.0,
        rank_tol=2.0,
    ),
    Regime(
        name="2006 peak",
        obs_date="2006-06-30",
        overvaluation_pct=30.0,
        percentile_rank=95.0,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
    Regime(
        name="2012 trough",
        obs_date="2012-01-31",
        overvaluation_pct=-15.0,
        percentile_rank=10.0,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
    Regime(
        name="1980 affordability trough",
        obs_date="1981-12-31",
        overvaluation_pct=-10.0,
        percentile_rank=15.0,
        pct_tol=2.0,
        rank_tol=2.0,
    ),
)


def regime_by_name(name: str) -> Regime:
    for r in REGIMES:
        if r.name == name:
            return r
    raise KeyError(name)
