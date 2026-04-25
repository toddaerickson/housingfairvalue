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


def _synth_monthly(n_years: int = 30, end: str = "2024-12-31") -> pd.DataFrame:
    end_ts = pd.Timestamp(end)
    start = end_ts - pd.DateOffset(years=n_years) + pd.DateOffset(days=1)
    idx = pd.date_range(start, end_ts, freq="ME")
    n = len(idx)
    return pd.DataFrame({
        "median_price":      np.linspace(100_000, 400_000, n),
        "median_income":     np.full(n, 60_000.0),
        "mortgage_rate_30y": np.full(n, 6.0),
        "oer_index":         np.full(n, 100.0),
    }, index=idx).rename_axis("obs_date")


def test_compute_composite_sane_on_synthetic_input() -> None:
    df = _synth_monthly()
    out = compute_composite(df, baseline_start=df.index.min())
    assert {"composite_z", "overvaluation_pct", "percentile_rank"}.issubset(out.columns)
    # Mid-rank empirical CDF: min ~ 1/(2N), max ~ 100 - 1/(2N).
    assert out["percentile_rank"].iloc[-1] > 99.0
    assert out["percentile_rank"].iloc[0] < 1.0
    assert abs(out["composite_z"].mean()) < 1e-6


def test_compute_composite_empty_input_returns_empty_frame() -> None:
    empty = pd.DataFrame(
        columns=["median_price", "median_income", "mortgage_rate_30y", "oer_index"],
        index=pd.DatetimeIndex([], name="obs_date"),
    )
    out = compute_composite(empty)
    assert out.empty
    assert {"composite_z", "overvaluation_pct", "percentile_rank"}.issubset(out.columns)


def test_compute_composite_baseline_start_after_data_raises() -> None:
    import pytest as _pytest
    df = _synth_monthly(n_years=5, end="2010-12-31")
    with _pytest.raises(ValueError):
        compute_composite(df, baseline_start=pd.Timestamp("2030-01-01"))


def test_dti_zero_rate_path() -> None:
    idx = pd.date_range("2020-01-31", periods=2, freq="ME")
    price = pd.Series([360_000.0, 360_000.0], index=idx)
    rate = pd.Series([0.0, 0.0], index=idx)
    income = pd.Series([120_000.0], index=[pd.Timestamp("2020-01-31")])
    out = dti(price, rate, income, prop_tax_pct=0.0, insurance_pct=0.0, down_pct=0.0)
    # zero-rate principal-only payment: 360k/360 = $1000; income/12 = $10k → 10%
    assert abs(out.iloc[0] - 0.10) < 1e-6


def test_dti_raises_on_no_overlap_income() -> None:
    import pytest as _pytest
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    price = pd.Series([400_000.0] * 4, index=idx)
    rate = pd.Series([6.0] * 4, index=idx)
    income = pd.Series(dtype=float)  # empty
    with _pytest.raises(ValueError):
        dti(price, rate, income)


def test_empirical_cdf_min_max_bounds() -> None:
    from backend.calc.composite import _empirical_cdf
    base = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    # Mid-rank: min → 0.5/N = 0.1; max → (N-0.5)/N = 0.9; middle → 0.5
    assert abs(_empirical_cdf(base, 1.0) - 0.1) < 1e-9
    assert abs(_empirical_cdf(base, 5.0) - 0.9) < 1e-9
    assert abs(_empirical_cdf(base, 3.0) - 0.5) < 1e-9


def test_monthly_payment_array_with_mixed_zero_and_nonzero() -> None:
    pmts = monthly_payment(np.array([360_000.0, 400_000.0]), np.array([0.0, 6.0]))
    assert abs(pmts[0] - 1000.0) < 1e-6
    assert abs(pmts[1] - 2398.20) < 1.0


def test_weights_must_sum_to_one() -> None:
    import pytest as _pytest
    with _pytest.raises(ValueError):
        Weights(0.5, 0.3, 0.3)


def test_stitch_income_anchors_on_first_non_nan() -> None:
    from backend.ingest.fred import stitch_income
    idx = pd.date_range("1980-01-31", "1990-12-31", freq="ME")
    median_income = pd.Series(np.nan, index=idx, name="MEHOINUSA646N")
    median_income.loc["1984-01-31":] = np.linspace(20000.0, 25000.0, len(median_income.loc["1984-01-31":]))
    real_dpi = pd.Series(np.linspace(10000.0, 15000.0, len(idx)), index=idx, name="A229RX0")

    spliced = stitch_income(median_income, real_dpi)
    splice = pd.Timestamp("1984-01-31")

    assert abs(spliced.loc[splice] - median_income.loc[splice]) < 1e-9
    assert not spliced.loc[:splice - pd.Timedelta(days=1)].isna().any()
    expected_pre = real_dpi.loc[idx < splice] * (median_income.loc[splice] / real_dpi.loc[splice])
    diff = (spliced.reindex(expected_pre.index) - expected_pre).abs().max()
    assert diff < 1e-6
