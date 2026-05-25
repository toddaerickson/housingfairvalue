"""Sensitivity tab endpoints: heatmap, tornado, breakpoints, monte carlo, years-to-FV."""

from __future__ import annotations

from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.calc.affordability import piti
from backend.calc.composite import compute_composite

from ..db import load_monthly_fact
from ..limiter import limiter

router = APIRouter(prefix="/sensitivity", tags=["sensitivity"])


def _latest():
    """Return (monthly_fact, composite_history, last_complete_date).

    `last_complete_date` is the most recent obs_date where *all* fields
    required by `compute_lenses` are non-null (i.e. the row that actually
    drives `composite_z.iloc[-1]`). Sensitivity endpoints must perturb
    *this* row — perturbing `monthly.iloc[-1]` is a no-op whenever the
    tail of monthly_fact has stale fields like `median_income`.
    """
    monthly = load_monthly_fact()
    if monthly.empty:
        raise HTTPException(status_code=503, detail="no monthly_fact data — run backfill")
    comp = compute_composite(monthly)
    if comp.empty:
        raise HTTPException(status_code=503, detail="composite history is empty")
    return monthly, comp, comp.index[-1]


@router.get("/heatmap")
def heatmap(
    rate_min: float = Query(4.0, ge=0.5, le=20.0),
    rate_max: float = Query(9.0, ge=0.5, le=20.0),
    rate_step: float = Query(0.25, gt=0, le=2.0),
    dti_min: float = Query(20.0, ge=5.0, le=60.0),
    dti_max: float = Query(36.0, ge=5.0, le=60.0),
    dti_step: float = Query(2.0, gt=0, le=10.0),
):
    if rate_max <= rate_min or dti_max <= dti_min:
        raise HTTPException(status_code=400, detail="max must exceed min")

    monthly, _, last_date = _latest()
    last = monthly.loc[last_date]
    income_monthly = float(last["median_income"]) / 12.0
    rates = np.arange(rate_min, rate_max + rate_step / 2, rate_step)
    dtis = np.arange(dti_min, dti_max + dti_step / 2, dti_step)

    rows = []
    for d in dtis:
        target_piti = income_monthly * (d / 100.0)
        for r in rates:
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
    """Rank inputs by their absolute partial effect on composite_z (±1σ moves).

    Holds the *baseline* mean/std fixed and only perturbs the last observation,
    so the reported sensitivity is a clean ∂z/∂input of the most recent reading.
    """
    monthly, comp, last_date = _latest()
    last = monthly.loc[last_date]
    base_z = float(comp["composite_z"].iloc[-1])

    inputs = {
        "mortgage_rate_30y": (last["mortgage_rate_30y"], 1.0),
        "median_income":     (last["median_income"], last["median_income"] * 0.05),
        "median_price":      (last["median_price"], last["median_price"] * 0.10),
        "oer_index":         (last["oer_index"], last["oer_index"] * 0.05),
    }

    bars = []
    for name, (base, delta) in inputs.items():
        up = monthly.copy(deep=True)
        up.loc[last_date, name] = base + delta
        dn = monthly.copy(deep=True)
        dn.loc[last_date, name] = base - delta
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


def _bisect_to_zero(f, lo: float, hi: float, tol: float = 1e-3, max_iter: int = 50) -> float | None:
    """Standard bisection. Returns None if f(lo), f(hi) have the same sign."""
    f_lo = f(lo)
    f_hi = f(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


@router.get("/breakpoints")
@limiter.limit("10/minute")
def breakpoints(request: Request):
    """Three live numbers: rate / income / price-decline that neutralize composite."""
    monthly, comp, last_date = _latest()
    last = monthly.loc[last_date]
    base_z = float(comp["composite_z"].iloc[-1])

    def z_with(field: str, value: float) -> float:
        m = monthly.copy(deep=True)
        m.loc[last_date, field] = value
        return float(compute_composite(m)["composite_z"].iloc[-1])

    rate_neutral = _bisect_to_zero(lambda x: z_with("mortgage_rate_30y", x), 0.5, 15.0)
    income_neutral = _bisect_to_zero(
        lambda x: z_with("median_income", x),
        last["median_income"] * 0.5,
        last["median_income"] * 3.0,
    )
    price_neutral = _bisect_to_zero(
        lambda x: z_with("median_price", x),
        last["median_price"] * 0.3,
        last["median_price"] * 1.5,
    )
    price_decline_pct = (
        None if price_neutral is None
        else (last["median_price"] - price_neutral) / last["median_price"] * 100.0
    )

    return {
        "current_z": base_z,
        "rate_to_neutralize_pct": None if rate_neutral is None else float(rate_neutral),
        "income_to_neutralize_usd": None if income_neutral is None else float(income_neutral),
        "price_decline_to_neutralize_pct": (
            None if price_decline_pct is None else float(price_decline_pct)
        ),
    }


@router.get("/years-to-fv")
def years_to_fv(
    threshold_pct: float = Query(5.0, gt=0, le=20),
    horizon_years: int = Query(30, ge=1, le=50),
):
    """Linear-approximation grid: years for current overvaluation to decay
    below ±threshold_pct under fixed nominal price/income paths.

    Uses the sign of (price_growth - income_growth) as the per-year drift on
    the overvaluation %. Intentionally approximate; the Monte Carlo tab gives
    distributional bands.
    """
    _, comp, _ = _latest()
    base_pct = float(comp["overvaluation_pct"].iloc[-1])

    def years(price_g: float, income_g: float) -> int | None:
        pct = base_pct
        for y in range(1, horizon_years + 1):
            pct = pct + (price_g - income_g)
            if abs(pct) <= threshold_pct:
                return y
        return None

    grid = [
        {"price_growth_pct": pg, "income_growth_pct": ig, "years": years(pg, ig)}
        for pg in (-3.0, 0.0, 3.0)
        for ig in (2.0, 3.0, 4.0)
    ]
    return {"base_overvaluation_pct": base_pct, "grid": grid}


@router.post("/montecarlo")
@limiter.limit("5/minute")
def montecarlo(
    request: Request,
    n_paths: int = Query(5000, ge=100, le=20000),
    horizon_years: int = Query(15, ge=1, le=30),
    seed: int = Query(42),
    rho_price_rate: float = Query(-0.4, ge=-0.99, le=0.99),
    sigma_price: float = Query(3.0, gt=0, le=15.0),
    sigma_rate: float = Query(1.0, gt=0, le=5.0),
):
    """Monte-carlo years-to-fair-value distribution.

    rate: AR(1) around 6% LR mean (autoregression coefficient 0.7).
    income growth: N(3.0%, 1.5%) i.i.d.
    price growth and rate innovation drawn from a bivariate normal with
    correlation `rho_price_rate` so the documented coupling is exact (rather
    than the accidental ratio-of-variances behavior of the prior version).
    Right-censored paths report `None` years; the median/percentiles are
    computed only over paths that actually reach FV.
    """
    _, comp, _ = _latest()
    base_pct = float(comp["overvaluation_pct"].iloc[-1])
    rng = np.random.default_rng(seed)

    cov = np.array([[sigma_rate ** 2, rho_price_rate * sigma_rate * sigma_price],
                    [rho_price_rate * sigma_rate * sigma_price, sigma_price ** 2]])
    innov = rng.multivariate_normal(mean=[0.0, 0.0], cov=cov, size=(n_paths, horizon_years))
    rate_innov = innov[..., 0]
    price_g = innov[..., 1]
    income_g = rng.normal(3.0, 1.5, size=(n_paths, horizon_years))

    rate = np.full((n_paths, horizon_years), 6.0)
    for t in range(1, horizon_years):
        rate[:, t] = 0.7 * rate[:, t - 1] + 0.3 * 6.0 + rate_innov[:, t]
    price_g = price_g - 0.4 * (rate - 6.0)  # mean shift; correlation already encoded above

    pct = np.full(n_paths, base_pct)
    years_to = np.full(n_paths, np.nan)
    for t in range(horizon_years):
        pct = pct + (price_g[:, t] - income_g[:, t])
        hit = (np.abs(pct) <= 5.0) & np.isnan(years_to)
        years_to[hit] = t + 1

    valid = years_to[~np.isnan(years_to)]
    histogram = np.histogram(valid, bins=range(1, horizon_years + 2))[0].tolist() if valid.size else []

    return {
        "base_overvaluation_pct": base_pct,
        "n_paths": n_paths,
        "horizon_years": horizon_years,
        "share_reaching_fv": float(valid.size / n_paths),
        "median_years": float(np.median(valid)) if valid.size else None,
        "p10_years": float(np.percentile(valid, 10)) if valid.size else None,
        "p90_years": float(np.percentile(valid, 90)) if valid.size else None,
        "histogram_years": list(range(1, horizon_years + 1)),
        "histogram_counts": histogram,
        "censored_count": int(np.isnan(years_to).sum()),
    }


class FairValueRequest(BaseModel):
    rate: float | None = Field(None, description="30-yr mortgage rate %, e.g., 6.5")
    price_growth: float | None = Field(None, description="annual home price growth %")
    years: float | None = Field(None, description="years to equilibrium")
    income_growth: float = Field(..., description="annual income growth %, required")
    solve_for: Literal["rate", "price_growth", "years"] | None = Field(None)


@router.post("/fair-value")
def fair_value(req: FairValueRequest):
    """Solve for one of {rate, price_growth, years} that makes composite_z = 0
    at year y, given the other two and an income-growth assumption.

    Forward state at year y:
      price_y  = price_0 * (1 + price_growth/100)^y
      income_y = income_0 * (1 + income_growth/100)^y
      rate_y   = rate (held constant going forward)
      oer_y    = oer_0 * (1 + income_growth/100)^y  (rent grows with income)

    PTI is a *derived* readout (PITI(price_y, rate) * 12 / income_y); it does
    not appear in the equilibrium equation.
    """
    monthly, _, last_date = _latest()
    last = monthly.loc[last_date]
    p0 = float(last["median_price"])
    i0 = float(last["median_income"])
    oer0 = float(last["oer_index"])

    def composite_z_at(rate: float, gp: float, y: float) -> float:
        # Guard tiny/negative y; bisection bounds keep y >= 0.5 so this is
        # defensive only.
        y_safe = max(y, 1e-6)
        p_y = p0 * (1 + gp / 100.0) ** y_safe
        i_y = i0 * (1 + req.income_growth / 100.0) ** y_safe
        oer_y = oer0 * (1 + req.income_growth / 100.0) ** y_safe
        m = monthly.copy(deep=True)
        m.loc[last_date, "median_price"] = p_y
        m.loc[last_date, "median_income"] = i_y
        m.loc[last_date, "mortgage_rate_30y"] = rate
        m.loc[last_date, "oer_index"] = oer_y
        return float(compute_composite(m)["composite_z"].iloc[-1])

    if req.solve_for is None:
        if req.rate is None or req.price_growth is None or req.years is None:
            raise HTTPException(
                400,
                "without solve_for, all of rate/price_growth/years must be set",
            )
        rate_f, gp_f, y_f = req.rate, req.price_growth, req.years
    else:
        bounds = {
            "rate": (0.5, 15.0),
            "price_growth": (-10.0, 15.0),
            "years": (0.5, 50.0),
        }
        lo, hi = bounds[req.solve_for]

        if req.solve_for == "rate":
            if req.price_growth is None or req.years is None:
                raise HTTPException(400, "solving rate requires price_growth and years")
            gp_in, y_in = req.price_growth, req.years
            f = lambda r: composite_z_at(r, gp_in, y_in)  # noqa: E731
        elif req.solve_for == "price_growth":
            if req.rate is None or req.years is None:
                raise HTTPException(400, "solving price_growth requires rate and years")
            r_in, y_in = req.rate, req.years
            f = lambda g: composite_z_at(r_in, g, y_in)  # noqa: E731
        else:  # years
            if req.rate is None or req.price_growth is None:
                raise HTTPException(400, "solving years requires rate and price_growth")
            r_in, gp_in = req.rate, req.price_growth
            f = lambda y: composite_z_at(r_in, gp_in, y)  # noqa: E731

        result = _bisect_to_zero(f, lo, hi)
        if result is None:
            raise HTTPException(
                422,
                f"no solution for {req.solve_for} in [{lo}, {hi}] — "
                "composite_z does not cross zero across this range",
            )

        rate_f = req.rate if req.solve_for != "rate" else result
        gp_f = req.price_growth if req.solve_for != "price_growth" else result
        y_f = req.years if req.solve_for != "years" else result

    p_y_out = p0 * (1 + gp_f / 100.0) ** max(y_f, 1e-6)
    i_y_out = i0 * (1 + req.income_growth / 100.0) ** max(y_f, 1e-6)
    piti_monthly = float(piti(np.array([p_y_out]), np.array([rate_f]))[0])
    pti_y = piti_monthly * 12.0 / i_y_out
    z_final = composite_z_at(rate_f, gp_f, y_f)

    return {
        "rate": rate_f,
        "price_growth": gp_f,
        "years": y_f,
        "income_growth": req.income_growth,
        "implied_pti": pti_y,
        "composite_z_at_y": z_final,
        "future_price": p_y_out,
        "future_income": i_y_out,
    }
