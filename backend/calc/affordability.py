"""PITI / income affordability lens.

Standard 30-year amortizing PITI:
  payment = P * r / (1 - (1+r)^-n)  where r = monthly rate, n = 360
  PITI    = payment + monthly property tax + monthly insurance
  DTI     = PITI / monthly income

Defaults reflect typical underwriting assumptions used in the source workbook.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_DOWN_PCT = 0.20
DEFAULT_PROP_TAX_PCT = 0.0125
DEFAULT_INSURANCE_PCT = 0.0035


def monthly_payment(
    principal: float | np.ndarray,
    annual_rate_pct: float | np.ndarray,
    n_months: int = 360,
) -> np.ndarray:
    """Standard amortizing monthly payment, vectorized.

    Splits the zero- and non-zero-rate branches on disjoint masks so that
    extreme small-rate inputs don't pollute the non-zero computation with
    floating noise.
    """
    p = np.asarray(principal, dtype=float)
    r = np.asarray(annual_rate_pct, dtype=float) / 100.0 / 12.0
    p_b, r_b = np.broadcast_arrays(p, r)
    out = np.empty_like(p_b, dtype=float)
    zero = r_b == 0
    nz = ~zero
    out[zero] = p_b[zero] / n_months
    rn = r_b[nz]
    out[nz] = p_b[nz] * rn / (1 - (1 + rn) ** -n_months)
    return out


def piti(
    price: float | np.ndarray | pd.Series,
    rate_pct: float | np.ndarray | pd.Series,
    down_pct: float = DEFAULT_DOWN_PCT,
    prop_tax_pct: float = DEFAULT_PROP_TAX_PCT,
    insurance_pct: float = DEFAULT_INSURANCE_PCT,
) -> np.ndarray:
    price_arr = np.asarray(price, dtype=float)
    loan = price_arr * (1 - down_pct)
    pi = monthly_payment(loan, np.asarray(rate_pct, dtype=float))
    taxes_ins = price_arr * (prop_tax_pct + insurance_pct) / 12.0
    return pi + taxes_ins


def dti(
    price: pd.Series,
    rate_pct: pd.Series,
    annual_income: pd.Series,
    **piti_kwargs,
) -> pd.Series:
    """Monthly PITI / monthly income, aligned on the price index.

    Uses ffill+bfill to backstop both leading and trailing NaNs from
    lower-frequency inputs (rate is weekly, income is annual). Fully-NaN
    inputs surface as a clean ValueError rather than silent NaN propagation.
    """
    aligned_rate = rate_pct.reindex(price.index).ffill().bfill()
    aligned_income = annual_income.reindex(price.index).ffill().bfill()
    if aligned_rate.isna().any() or aligned_income.isna().any():
        raise ValueError("dti: rate or income series has no overlap with price index")
    monthly_income = aligned_income / 12.0
    p = piti(price.values, aligned_rate.values, **piti_kwargs)
    return pd.Series(p / monthly_income.values, index=price.index, name="dti")
