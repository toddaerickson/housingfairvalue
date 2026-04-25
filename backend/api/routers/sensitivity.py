"""Sensitivity tab endpoints: heatmap, tornado, breakpoints, monte carlo, years-to-FV.

These run cheap NumPy calculations on top of the latest monthly_fact row.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.calc.affordability import piti
from backend.calc.composite import DEFAULT_PCT_PER_SIGMA, compute_composite

from ..db import load_monthly_fact

router = APIRouter(prefix="/sensitivity", tags=["sensitivity"])


class Inputs(BaseModel):
    mortgage_rate_pct: float | None = None
    income_growth_pct: float = 3.0
    oer_growth_pct: float = 3.0
    property_tax_pct: float = 1.25
    insurance_pct: float = 0.35
    down_pct: float = 20.0
    qualifying_dti_pct: float = 28.0


def _latest():
    monthly = load_monthly_fact()
    comp = compute_composite(monthly)
    return monthly, comp


@router.get("/heatmap")
def heatmap(
    rate_min: float = 4.0,
    rate_max: float = 9.0,
    rate_step: float = 0.25,
    dti_min: float = 20.0,
    dti_max: float = 36.0,
    dti_step: float = 2.0,
):
    monthly, _ = _latest()
    last = monthly.iloc[-1]
    income_monthly = last["median_income"] / 12.0
    rates = np.arange(rate_min, rate_max + rate_step / 2, rate_step)
    dtis = np.arange(dti_min, dti_max + dti_step / 2, dti_step)

    rows = []
    for d in dtis:
        target_piti = income_monthly * (d / 100.0)
        for r in rates:
            # Solve P from PITI = P * factor(r) (approx; uses default tax/ins/down).
            unit_piti = float(piti(1.0, r))
            implied_price = target_piti / unit_piti
            pct_dev = (implied_price - last["median_price"]) / last["median_price"] * 100.0
            rows.append({
                "rate_pct": float(r),
                "dti_pct": float(d),
                "implied_price": float(implied_price),
                "pct_deviation_from_current": float(pct_dev),
            })
    return {
        "current": {
            "rate_pct": float(last["mortgage_rate_30y"]),
            "median_price": float(last["median_price"]),
        },
        "cells": rows,
    }


@router.get("/tornado")
def tornado():
    """Rank inputs by their absolute partial effect on composite_z (±1σ moves)."""
    monthly, comp = _latest()
    last = monthly.iloc[-1]
    base_z = float(comp["composite_z"].iloc[-1])

    inputs = {
        "mortgage_rate_30y": (last["mortgage_rate_30y"], 1.0),
        "median_income":     (last["median_income"], last["median_income"] * 0.05),
        "median_price":      (last["median_price"], last["median_price"] * 0.10),
        "oer_index":         (last["oer_index"], last["oer_index"] * 0.05),
    }

    bars = []
    for name, (base, delta) in inputs.items():
        up = monthly.copy(); up.loc[up.index[-1], name] = base + delta
        dn = monthly.copy(); dn.loc[dn.index[-1], name] = base - delta
        z_up = float(compute_composite(up)["composite_z"].iloc[-1])
        z_dn = float(compute_composite(dn)["composite_z"].iloc[-1])
        bars.append({
            "input": name,
            "delta": float(delta),
            "z_up": z_up,
            "z_dn": z_dn,
            "abs_effect": abs(z_up - base_z) + abs(z_dn - base_z),
        })
    bars.sort(key=lambda b: b["abs_effect"], reverse=True)
    return {"base_z": base_z, "bars": bars}


@router.get("/breakpoints")
def breakpoints():
    """Three live numbers: rate / income / price-decline that neutralize composite."""
    monthly, comp = _latest()
    last = monthly.iloc[-1]
    base_z = float(comp["composite_z"].iloc[-1])

    def z_with(field: str, value: float) -> float:
        m = monthly.copy()
        m.loc[m.index[-1], field] = value
        return float(compute_composite(m)["composite_z"].iloc[-1])

    def bisect(field: str, lo: float, hi: float, target: float = 0.0, tol: float = 1e-3) -> float:
        for _ in range(60):
            mid = (lo + hi) / 2.0
            z = z_with(field, mid)
            if abs(z - target) < tol:
                return mid
            # Direction depends on sign convention; figure it out from endpoints.
            z_lo = z_with(field, lo)
            if (z_lo - target) * (z - target) < 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2.0

    rate_neutral = bisect("mortgage_rate_30y", 0.5, 15.0)
    income_neutral = bisect("median_income", last["median_income"] * 0.5, last["median_income"] * 3.0)
    price_neutral = bisect("median_price", last["median_price"] * 0.3, last["median_price"] * 1.5)
    price_decline_pct = (last["median_price"] - price_neutral) / last["median_price"] * 100.0

    return {
        "current_z": base_z,
        "rate_to_neutralize_pct": float(rate_neutral),
        "income_to_neutralize_usd": float(income_neutral),
        "price_decline_to_neutralize_pct": float(price_decline_pct),
    }


@router.get("/years-to-fv")
def years_to_fv(
    pct_per_sigma: float = DEFAULT_PCT_PER_SIGMA,
    threshold_pct: float = 5.0,
    horizon_years: int = 30,
):
    monthly, comp = _latest()
    base_pct = float(comp["overvaluation_pct"].iloc[-1])
    last = monthly.iloc[-1]

    rows = []
    for price_g in (-3.0, 0.0, 3.0):
        for income_g in (2.0, 3.0, 4.0):
            years = _years_until(last, base_pct, price_g, income_g, threshold_pct, horizon_years, pct_per_sigma)
            rows.append({"price_growth_pct": price_g, "income_growth_pct": income_g, "years": years})
    return {"base_overvaluation_pct": base_pct, "grid": rows}


def _years_until(last, base_pct, price_g, income_g, thresh, horizon, pct_per_sigma):
    pct = base_pct
    p, inc = float(last["median_price"]), float(last["median_income"])
    sigma_pct = pct_per_sigma  # change per sigma
    for y in range(1, horizon + 1):
        p *= (1 + price_g / 100.0)
        inc *= (1 + income_g / 100.0)
        # Rough PI-driven decay: pct moves with log(P/I) / log(P/I)_baseline
        # Linearization: %Δ in pct ~ %Δ(P) - %Δ(I) scaled by sigma_pct
        pct = pct + (price_g - income_g) - 0  # nominal-only proxy
        if abs(pct) <= thresh:
            return y
    return None


@router.post("/montecarlo")
def montecarlo(
    n_paths: int = Query(5000, ge=100, le=20000),
    horizon_years: int = Query(15, ge=1, le=30),
    seed: int = Query(42),
):
    monthly, comp = _latest()
    base_pct = float(comp["overvaluation_pct"].iloc[-1])
    rng = np.random.default_rng(seed)

    income_g = rng.normal(3.0, 1.5, size=(n_paths, horizon_years))
    rate = np.full((n_paths, horizon_years), 6.0)
    rate_innov = rng.normal(0.0, 1.0, size=(n_paths, horizon_years))
    for t in range(1, horizon_years):
        rate[:, t] = 0.7 * rate[:, t - 1] + 0.3 * 6.0 + rate_innov[:, t]
    # Price growth correlated with rate change at ρ ≈ -0.4
    price_innov = rng.normal(0.0, 3.0, size=(n_paths, horizon_years))
    price_g = -0.4 * (rate - 6.0) * 2.0 + price_innov

    pct = np.full(n_paths, base_pct)
    years_to_fv = np.full(n_paths, np.nan)
    for t in range(horizon_years):
        pct = pct + (price_g[:, t] - income_g[:, t])
        hit = (np.abs(pct) <= 5.0) & np.isnan(years_to_fv)
        years_to_fv[hit] = t + 1

    valid = years_to_fv[~np.isnan(years_to_fv)]
    pct_finite = years_to_fv.copy()
    pct_finite[np.isnan(pct_finite)] = horizon_years + 1  # treated as right-censored

    return {
        "base_overvaluation_pct": base_pct,
        "n_paths": n_paths,
        "horizon_years": horizon_years,
        "median_years": float(np.median(pct_finite)),
        "p10_years": float(np.percentile(pct_finite, 10)),
        "p90_years": float(np.percentile(pct_finite, 90)),
        "share_reaching_fv": float(len(valid) / n_paths),
        "histogram": np.histogram(pct_finite, bins=range(horizon_years + 2))[0].tolist(),
    }
