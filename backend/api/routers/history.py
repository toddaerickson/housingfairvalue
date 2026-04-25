"""History tab endpoints: composite series, decomposition, KPI strip."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Query

from backend.calc.composite import compute_composite
from backend.calc.regimes import REGIMES

from ..db import load_monthly_fact

router = APIRouter(prefix="/history", tags=["history"])


def _records(df: pd.DataFrame) -> list[dict]:
    out = df.reset_index()
    out["obs_date"] = out["obs_date"].dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


@router.get("/composite")
def composite(
    start: str = Query("1980-01-01"),
    end: str | None = Query(None),
):
    monthly = load_monthly_fact()
    comp = compute_composite(monthly)
    sliced = comp.loc[start:end] if end else comp.loc[start:]
    return {"data": _records(sliced)}


@router.get("/series")
def series(
    name: str = Query(..., description="column name from monthly_fact"),
    start: str = Query("1980-01-01"),
    end: str | None = Query(None),
):
    monthly = load_monthly_fact()
    if name not in monthly.columns:
        return {"error": f"unknown series '{name}'", "available": list(monthly.columns)}
    s = monthly[[name]].loc[start:end] if end else monthly[[name]].loc[start:]
    return {"data": _records(s)}


@router.get("/kpi")
def kpi():
    monthly = load_monthly_fact()
    comp = compute_composite(monthly)
    last = comp.iloc[-1]
    last_m = monthly.loc[comp.index[-1]]
    return {
        "obs_date": comp.index[-1].strftime("%Y-%m-%d"),
        "overvaluation_pct": float(last["overvaluation_pct"]),
        "percentile_rank": float(last["percentile_rank"]),
        "price_to_income": float(last_m["median_price"] / last_m["median_income"]),
        "price_to_rent": float(last_m["median_price"] / (last_m["oer_index"] / 100.0 * 12000.0)),
        "mortgage_rate_30y": float(last_m["mortgage_rate_30y"]),
    }


@router.get("/regimes")
def regimes():
    monthly = load_monthly_fact()
    comp = compute_composite(monthly)
    out = []
    for r in REGIMES:
        ts = pd.Timestamp(r.obs_date)
        idx = comp.index[comp.index.get_indexer([ts], method="nearest")[0]]
        row = comp.loc[idx]
        m = monthly.loc[idx]
        out.append({
            "name": r.name,
            "obs_date": idx.strftime("%Y-%m-%d"),
            "overvaluation_pct": float(row["overvaluation_pct"]),
            "percentile_rank": float(row["percentile_rank"]),
            "median_price": float(m["median_price"]),
            "mortgage_rate_30y": float(m["mortgage_rate_30y"]),
            "median_income": float(m["median_income"]),
        })
    return {"regimes": out}
