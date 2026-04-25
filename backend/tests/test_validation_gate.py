"""The non-negotiable validation gate.

Reproduces the source 2026 Excel workbook's headline reading and three
historical inflection points. Blocks UI ship if any check fails.

Tolerances are encoded in `backend/calc/regimes.py`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backend.calc.composite import compute_composite
from backend.calc.regimes import REGIMES


@pytest.fixture(scope="module")
def composite(monthly_fact: pd.DataFrame) -> pd.DataFrame:
    return compute_composite(monthly_fact)


@pytest.mark.parametrize("regime", REGIMES, ids=lambda r: r.name)
def test_regime_matches_reference(composite: pd.DataFrame, regime) -> None:
    target_date = pd.Timestamp(regime.obs_date)
    if target_date not in composite.index:
        nearest = composite.index[composite.index.get_indexer([target_date], method="nearest")[0]]
        assert abs((nearest - target_date).days) <= 35, (
            f"no composite reading within 35d of {regime.obs_date} (got {nearest})"
        )
        target_date = nearest

    row = composite.loc[target_date]
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
