"""The non-negotiable validation gate.

Reproduces the source 2026 Excel workbook's headline reading and three
historical inflection points. Blocks UI ship if any check fails.

Tolerances are encoded in `backend/calc/regimes.py`. The gate enforces an
exact obs_date match for recent regimes (where the monthly grid is
unambiguous) and a tight ±35d fallback for very early regimes where the
1980/1981 splice can introduce one-month ambiguity.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backend.calc.composite import compute_composite
from backend.calc.regimes import REGIMES

EARLY_REGIME_NAMES = {"1980 affordability trough"}
EARLY_FALLBACK = pd.Timedelta(days=35)


@pytest.fixture(scope="module")
def composite(monthly_fact: pd.DataFrame) -> pd.DataFrame:
    return compute_composite(monthly_fact)


@pytest.mark.parametrize("regime", REGIMES, ids=lambda r: r.name)
def test_regime_matches_reference(composite: pd.DataFrame, regime) -> None:
    target_date = pd.Timestamp(regime.obs_date)
    if target_date in composite.index:
        idx = target_date
    elif regime.name in EARLY_REGIME_NAMES:
        nearest_pos = composite.index.get_indexer(
            [target_date], method="nearest", tolerance=EARLY_FALLBACK
        )[0]
        assert nearest_pos != -1, f"no composite reading within 35d of {regime.obs_date}"
        idx = composite.index[nearest_pos]
    else:
        pytest.fail(
            f"{regime.name}: target obs_date {regime.obs_date} not present in composite index"
        )

    row = composite.loc[idx]
    pct_diff = abs(row["overvaluation_pct"] - regime.overvaluation_pct)
    rank_diff = abs(row["percentile_rank"] - regime.percentile_rank)

    assert pct_diff <= regime.pct_tol, (
        f"{regime.name}: overvaluation {row['overvaluation_pct']:.1f}% "
        f"vs target {regime.overvaluation_pct:.1f}% (tol {regime.pct_tol})"
    )
    assert rank_diff <= regime.rank_tol, (
        f"{regime.name}: percentile {row['percentile_rank']:.1f} "
        f"vs target {regime.percentile_rank:.1f} (tol {regime.rank_tol})"
    )
