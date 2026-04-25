"""Composite z-score blending the three valuation lenses.

  z_lens     = (lens - mean(lens)) / std(lens)         # baseline-window stats
  composite  = w_aff * z_aff + w_pi * z_pi + w_pr * z_pr   (default equal weights)
  pct        = composite * pct_per_sigma
  rank       = empirical CDF of composite over the same baseline window

The historical baseline window (default 1980-01..present) is used for both
the mean/std and the empirical CDF — using a single window keeps the percentile
rank coherent with the z-score in their *baseline distribution*. Note that
`overvaluation_pct = z * pct_per_sigma` and `percentile_rank` are NOT a
deterministic transform of one another — pct is linear in z while rank is the
empirical CDF, which is non-Gaussian. They are reported as two independent
indicators.

`pct_per_sigma` is calibrated once against a known regime so the headline
number is interpretable in % terms; the source workbook's calibration places
the 2024 reading near +38%.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .affordability import dti
from .ratios import price_to_income, price_to_rent

DEFAULT_BASELINE_START = pd.Timestamp("1980-01-01")
DEFAULT_PCT_PER_SIGMA = 28.0  # % overvaluation per 1σ; calibrated 2026-04-25 against real FRED data


@dataclass(frozen=True)
class Weights:
    affordability: float = 1 / 3
    price_income: float = 1 / 3
    price_rent: float = 1 / 3

    def __post_init__(self) -> None:
        s = self.affordability + self.price_income + self.price_rent
        if not np.isclose(s, 1.0, atol=1e-6):
            raise ValueError(f"weights must sum to 1, got {s}")


def _z(series: pd.Series, baseline_start: pd.Timestamp) -> tuple[pd.Series, float, float]:
    base = series.loc[series.index >= baseline_start].dropna()
    mean = base.mean()
    std = base.std(ddof=1)
    if std == 0 or np.isnan(std):
        raise ValueError(f"zero/nan std for series {series.name}")
    return (series - mean) / std, float(mean), float(std)


def _empirical_cdf(values: np.ndarray, x: float) -> float:
    """Mid-rank empirical CDF (average of `<x` and `<=x` shares).

    Avoids the off-by-one in the strictly-`<=` form where the minimum baseline
    value gets a non-zero rank. At the min: rank ≈ 1/(2N); at the max: rank ≈ 1.
    """
    if len(values) == 0:
        return float("nan")
    less = float((values < x).sum())
    leq = float((values <= x).sum())
    return (less + leq) / (2.0 * len(values))


def compute_lenses(monthly: pd.DataFrame) -> pd.DataFrame:
    """Compute the three lens series from a monthly_fact frame.

    Restricted to rows where every input column is non-null so the three
    lenses share a common-availability index — required for the composite
    z-blend to be meaningful.
    """
    required = ["median_price", "median_income", "mortgage_rate_30y", "oer_index"]
    df = monthly[required].dropna()
    if df.empty:
        return pd.DataFrame(columns=["affordability", "price_to_income", "price_to_rent"])

    aff = dti(df["median_price"], df["mortgage_rate_30y"], df["median_income"])
    pi = price_to_income(df["median_price"], df["median_income"])
    pr = price_to_rent(df["median_price"], df["oer_index"])

    return pd.DataFrame({
        "affordability": aff,
        "price_to_income": pi,
        "price_to_rent": pr,
    })


def compute_composite(
    monthly: pd.DataFrame,
    weights: Weights = Weights(),
    baseline_start: pd.Timestamp = DEFAULT_BASELINE_START,
    pct_per_sigma: float = DEFAULT_PCT_PER_SIGMA,
) -> pd.DataFrame:
    """Build the full composite history frame.

    Returns an empty DataFrame with the correct schema if no lens data is
    available — callers (API endpoints) can detect this without hitting an
    exception.
    """
    schema_cols = [
        "z_affordability",
        "z_price_income",
        "z_price_rent",
        "composite_z",
        "overvaluation_pct",
        "percentile_rank",
    ]
    lenses = compute_lenses(monthly)
    if lenses.empty:
        return pd.DataFrame(columns=schema_cols, index=pd.DatetimeIndex([], name="obs_date"))

    if not (lenses.index >= baseline_start).any():
        raise ValueError(
            f"no lens observations on or after baseline_start={baseline_start.date()}"
        )

    z_aff, _, _ = _z(lenses["affordability"], baseline_start)
    z_pi, _, _ = _z(lenses["price_to_income"], baseline_start)
    z_pr, _, _ = _z(lenses["price_to_rent"], baseline_start)

    composite_z = (
        weights.affordability * z_aff
        + weights.price_income * z_pi
        + weights.price_rent * z_pr
    )

    base = composite_z.loc[composite_z.index >= baseline_start].dropna().values
    pct_rank = composite_z.apply(lambda x: _empirical_cdf(base, x) * 100.0)

    return pd.DataFrame({
        "z_affordability": z_aff,
        "z_price_income": z_pi,
        "z_price_rent": z_pr,
        "composite_z": composite_z,
        "overvaluation_pct": composite_z * pct_per_sigma,
        "percentile_rank": pct_rank,
    }).dropna(subset=["composite_z"])
