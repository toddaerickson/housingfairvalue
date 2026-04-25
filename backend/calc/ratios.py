"""Price-to-income and price-to-rent ratios.

P/I  = median home price / median household income
P/R  = median home price / annualized dollar rent

Dollar rent is reconstructed from the OER index by anchoring it to a base-year
dollar rent. The base year is configurable; default 2010 with a $1,000/mo
anchor mirrors the source workbook's convention. The chosen anchor only
shifts the level — the std-z-score is invariant to it — but it makes the
P/R series easier to read.
"""

from __future__ import annotations

import pandas as pd

OER_BASE_YEAR = 2010
OER_BASE_MONTHLY_RENT = 1000.0


def price_to_income(price: pd.Series, annual_income: pd.Series) -> pd.Series:
    income_aligned = annual_income.reindex(price.index).ffill()
    return (price / income_aligned).rename("price_to_income")


def oer_to_dollar_rent(
    oer_index: pd.Series,
    base_year: int = OER_BASE_YEAR,
    base_monthly_rent: float = OER_BASE_MONTHLY_RENT,
) -> pd.Series:
    """Scale the OER index to dollar rent at a base-year anchor.

    Uses the mean of the base-year OER index values as the divisor so the
    resulting series equals `base_monthly_rent` on average during that year.
    """
    mask = oer_index.index.year == base_year
    if not mask.any():
        raise ValueError(f"OER index has no observations in base year {base_year}")
    base = oer_index.loc[mask].mean()
    return (oer_index / base * base_monthly_rent).rename("dollar_rent")


def price_to_rent(price: pd.Series, oer_index: pd.Series, **kwargs) -> pd.Series:
    rent_monthly = oer_to_dollar_rent(oer_index, **kwargs).reindex(price.index).ffill()
    rent_annual = rent_monthly * 12.0
    return (price / rent_annual).rename("price_to_rent")
