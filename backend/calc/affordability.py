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


def monthly_payment(principal: float | np.ndarray, annual_rate_pct: float | np.ndarray, n_months: int = 360) -> float | np.ndarray:
    r = np.asarray(annual_rate_pct) / 100.0 / 12.0
    p = np.asarray(principal)
    safe_r = np.where(r == 0, 1e-12, r)
    pmt = p * safe_r / (1 - (1 + safe_r) ** -n_months)
    return np.where(r == 0, p / n_months, pmt)


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
    """Monthly PITI / monthly income, aligned on the price index."""
    aligned_rate = rate_pct.reindex(price.index).ffill()
    aligned_income = annual_income.reindex(price.index).ffill()
    monthly_income = aligned_income / 12.0
    p = piti(price.values, aligned_rate.values, **piti_kwargs)
    out = pd.Series(p / monthly_income.values, index=price.index, name="dti")
    return out
