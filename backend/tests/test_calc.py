"""Unit tests on the calc engine using deterministic synthetic input.

These don't depend on FRED data — they exercise the math on small inputs with
hand-computed expectations. They run on every pytest invocation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.calc.affordability import dti, monthly_payment, piti
from backend.calc.composite import Weights, compute_composite
from backend.calc.ratios import oer_to_dollar_rent, price_to_income, price_to_rent


def test_monthly_payment_matches_amortization_formula() -> None:
    # $400k loan, 6% APR, 30 years → standard textbook payment ~ $2,398.20
    pmt = float(monthly_payment(400_000, 6.0))
    assert abs(pmt - 2398.20) < 1.0


def test_monthly_payment_zero_rate() -> None:
    pmt = float(monthly_payment(360_000, 0.0))
    assert abs(pmt - 1000.0) < 1e-6


def test_piti_includes_taxes_and_insurance() -> None:
    p = float(piti(500_000, 6.0, down_pct=0.20, prop_tax_pct=0.012, insurance_pct=0.004))
    pi_only = float(monthly_payment(400_000, 6.0))
    monthly_ti = 500_000 * (0.012 + 0.004) / 12
    assert abs(p - (pi_only + monthly_ti)) < 1e-6


def test_dti_aligns_indices() -> None:
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    price = pd.Series([400_000, 410_000, 420_000, 430_000], index=idx)
    rate = pd.Series([6.0, 6.0, 6.0, 6.0], index=idx)
    income = pd.Series([100_000.0], index=[pd.Timestamp("2020-01-31")])
    out = dti(price, rate, income)
    assert len(out) == 4
    assert out.iloc[0] > 0


def test_oer_to_dollar_rent_anchors_at_base_year() -> None:
    idx = pd.date_range("2009-01-31", "2011-12-31", freq="ME")
    oer = pd.Series(np.linspace(95, 110, len(idx)), index=idx)
    rent = oer_to_dollar_rent(oer, base_year=2010, base_monthly_rent=1000.0)
    assert abs(rent.loc[rent.index.year == 2010].mean() - 1000.0) < 1e-6


def test_price_to_income_simple() -> None:
    idx = pd.date_range("2020-01-31", periods=2, freq="ME")
    price = pd.Series([300_000, 360_000], index=idx)
    income = pd.Series([60_000.0], index=[pd.Timestamp("2020-01-31")])
    pi = price_to_income(price, income)
    assert pi.iloc[0] == 5.0
    assert pi.iloc[1] == 6.0


def test_price_to_rent_simple() -> None:
    idx = pd.date_range("2010-01-31", "2010-12-31", freq="ME")
    price = pd.Series([240_000.0] * 12, index=idx)
    oer = pd.Series([100.0] * 12, index=idx)
    pr = price_to_rent(price, oer)
    # base_year=2010 anchor → $1000/mo, $12000/yr → P/R = 240k/12k = 20
    assert all(abs(pr - 20.0) < 1e-6)


def test_compute_composite_sane_on_synthetic_input() -> None:
    """End-to-end check that the engine produces well-formed output.

    Build a 30-year monthly frame with linear price growth, flat income, flat
    rate, flat OER. The composite z should range smoothly and the percentile
    rank should land at 100 at the final (highest-priced) observation.
    """
    idx = pd.date_range("1995-01-31", "2024-12-31", freq="ME")
    n = len(idx)
    df = pd.DataFrame({
        "median_price":      np.linspace(100_000, 400_000, n),
        "median_income":     np.full(n, 60_000.0),
        "mortgage_rate_30y": np.full(n, 6.0),
        "oer_index":         np.full(n, 100.0),
    }, index=idx)
    df.index.name = "obs_date"

    out = compute_composite(df, baseline_start=pd.Timestamp("1995-01-01"))
    assert {"composite_z", "overvaluation_pct", "percentile_rank"}.issubset(out.columns)
    assert out["percentile_rank"].iloc[-1] >= 99.0
    assert out["percentile_rank"].iloc[0] <= 1.0
    # Mean of z over baseline ≈ 0
    assert abs(out["composite_z"].mean()) < 1e-6


def test_weights_must_sum_to_one() -> None:
    import pytest as _pytest
    with _pytest.raises(ValueError):
        Weights(0.5, 0.3, 0.3)
