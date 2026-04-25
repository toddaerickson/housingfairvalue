"""Composite z-score blending the three valuation lenses.

  z_lens     = (lens - mean(lens)) / std(lens)
  composite  = w_aff * z_aff + w_pi * z_pi + w_pr * z_pr   (default equal weights)
  pct        = composite * pct_per_sigma
  rank       = empirical CDF of composite over the full window

The historical baseline window (default 1980-01..present) is used for both
the mean/std and the empirical CDF — using a single window keeps the percentile
rank coherent with the z-score.

`pct_per_sigma` is the std_to_pct factor that maps a 1-sigma move to a
percentage overvaluation. It must be calibrated once against a known
historical regime so the headline number is interpretable in % terms.
The source workbook calibrates so that the 2024 reading lands at ~+38%.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .affordability import dti
from .ratios import price_to_income, price_to_rent

DEFAULT_BASELINE_START = pd.Timestamp("1980-01-01")
DEFAULT_PCT_PER_SIGMA = 19.0  # % overvaluation per 1σ; calibrated in test_validation_gate


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
    std = base.std(ddof=0)
    if std == 0 or np.isnan(std):
        raise ValueError(f"zero/nan std for series {series.name}")
    return (series - mean) / std, float(mean), float(std)


def _empirical_cdf(values: np.ndarray, x: float) -> float:
    if len(values) == 0:
        return float("nan")
    return float((values <= x).sum() / len(values))


def compute_lenses(monthly: pd.DataFrame) -> pd.DataFrame:
    """Compute the three lens series from a monthly_fact frame."""
    price = monthly["median_price"]
    rate = monthly["mortgage_rate_30y"]
    income = monthly["median_income"]
    oer = monthly["oer_index"]

    aff = dti(price, rate, income)
    pi = price_to_income(price, income)
    pr = price_to_rent(price, oer)

    out = pd.DataFrame({
        "affordability": aff,
        "price_to_income": pi,
        "price_to_rent": pr,
    })
    return out.dropna()


def compute_composite(
    monthly: pd.DataFrame,
    weights: Weights = Weights(),
    baseline_start: pd.Timestamp = DEFAULT_BASELINE_START,
    pct_per_sigma: float = DEFAULT_PCT_PER_SIGMA,
) -> pd.DataFrame:
    """Build the full composite history frame."""
    lenses = compute_lenses(monthly)
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
    }).dropna()
