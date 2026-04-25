"""History tab endpoints: composite series, decomposition, KPI strip."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.calc.composite import compute_composite
from backend.calc.ratios import oer_to_dollar_rent
from backend.calc.regimes import REGIMES

from ..db import engine, load_monthly_fact

router = APIRouter(prefix="/history", tags=["history"])

ALLOWED_SERIES = {
    "median_price", "median_income", "mortgage_rate_30y", "oer_index",
    "cs_hpi", "zhvi", "treasury_10y", "cpi", "real_dpi_per_capita",
}
REGIME_TOLERANCE = pd.Timedelta(days=35)


def _parse_date(label: str, value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        return pd.Timestamp(value)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"invalid {label}: {e}") from e


def _records(df: pd.DataFrame) -> list[dict]:
    out = df.reset_index()
    out["obs_date"] = out["obs_date"].dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def _require_data() -> pd.DataFrame:
    monthly = load_monthly_fact()
    if monthly.empty:
        raise HTTPException(status_code=503, detail="no monthly_fact data — run backfill")
    return monthly


def _load_composite_history() -> pd.DataFrame:
    """Load pre-materialized composite from DB; fall back to live compute if empty."""
    try:
        df = pd.read_sql(
            "SELECT obs_date, z_affordability, z_price_income, z_price_rent, "
            "composite_z, overvaluation_pct, percentile_rank "
            "FROM composite_history ORDER BY obs_date",
            engine(),
            parse_dates=["obs_date"],
        )
        if not df.empty:
            return df.set_index("obs_date")
    except Exception:
        pass
    # Fallback: compute live (bootstrap safety before first ingest)
    monthly = _require_data()
    return compute_composite(monthly)


@router.get("/composite")
def composite(
    start: str | None = Query("1980-01-01"),
    end: str | None = Query(None),
):
    comp = _load_composite_history()
    if comp.empty:
        raise HTTPException(status_code=503, detail="composite history is empty")
    s = _parse_date("start", start)
    e = _parse_date("end", end)
    sliced = comp.loc[s:e] if (s is not None or e is not None) else comp
    return {"data": _records(sliced)}


@router.get("/series")
def series(
    name: str = Query(..., description="series column from monthly_fact"),
    start: str | None = Query("1980-01-01"),
    end: str | None = Query(None),
):
    if name not in ALLOWED_SERIES:
        raise HTTPException(status_code=404, detail=f"unknown series '{name}'")
    monthly = _require_data()
    s = _parse_date("start", start)
    e = _parse_date("end", end)
    df = monthly[[name]].loc[s:e] if (s is not None or e is not None) else monthly[[name]]
    return {"data": _records(df)}


@router.get("/kpi")
def kpi():
    monthly = _require_data()
    comp = _load_composite_history()
    if comp.empty:
        raise HTTPException(status_code=503, detail="composite history is empty")
    last_date = comp.index[-1]
    last = comp.iloc[-1]
    last_m = monthly.loc[last_date]

    monthly_rent = float(oer_to_dollar_rent(monthly["oer_index"].dropna()).loc[last_date])
    return {
        "obs_date": last_date.strftime("%Y-%m-%d"),
        "overvaluation_pct": float(last["overvaluation_pct"]),
        "percentile_rank": float(last["percentile_rank"]),
        "price_to_income": float(last_m["median_price"] / last_m["median_income"]),
        "price_to_rent": float(last_m["median_price"] / (monthly_rent * 12.0)),
        "mortgage_rate_30y": float(last_m["mortgage_rate_30y"]),
    }


@router.get("/regimes")
def regimes():
    monthly = _require_data()
    comp = _load_composite_history()
    if comp.empty:
        raise HTTPException(status_code=503, detail="composite history is empty")
    out = []
    for r in REGIMES:
        ts = pd.Timestamp(r.obs_date)
        idx_pos = comp.index.get_indexer([ts], method="nearest", tolerance=REGIME_TOLERANCE)[0]
        if idx_pos == -1:
            out.append({"name": r.name, "obs_date": r.obs_date, "missing": True})
            continue
        idx = comp.index[idx_pos]
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
