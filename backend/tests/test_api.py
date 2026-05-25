"""API smoke tests using FastAPI's TestClient.

Mocks `load_monthly_fact` so we don't depend on a live DB. Verifies the
empty-data path returns 503 cleanly (rather than the prior unhandled 500
from `compute_composite` / `iloc[-1]`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from backend.api import main  # noqa: E402
from backend.api.routers import history, sensitivity  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def _patch_loader(monkeypatch, df: pd.DataFrame) -> None:
    from backend.calc.composite import compute_composite
    monkeypatch.setattr(history, "load_monthly_fact", lambda: df)
    monkeypatch.setattr(sensitivity, "load_monthly_fact", lambda: df)
    monkeypatch.setattr(history, "_load_composite_history", lambda: compute_composite(df))


@pytest.fixture
def empty_data(monkeypatch) -> None:
    empty = pd.DataFrame(
        columns=[
            "median_price", "median_income", "mortgage_rate_30y", "oer_index",
            "cs_hpi", "zhvi", "treasury_10y", "cpi", "real_dpi_per_capita",
        ],
        index=pd.DatetimeIndex([], name="obs_date"),
    )
    _patch_loader(monkeypatch, empty)


@pytest.fixture
def sample_data(monkeypatch) -> None:
    idx = pd.date_range("1995-01-31", "2024-12-31", freq="ME")
    n = len(idx)
    df = pd.DataFrame({
        "median_price":      np.linspace(100_000, 400_000, n),
        "median_income":     np.full(n, 60_000.0),
        "mortgage_rate_30y": np.full(n, 6.0),
        "oer_index":         np.full(n, 100.0),
        "cs_hpi":            np.full(n, 100.0),
        "zhvi":              np.full(n, 100_000.0),
        "treasury_10y":      np.full(n, 4.0),
        "cpi":               np.full(n, 250.0),
        "real_dpi_per_capita": np.full(n, 50_000.0),
    }, index=idx).rename_axis("obs_date")
    _patch_loader(monkeypatch, df)


def test_health_does_not_touch_db(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "git_sha" in body  # populated from GIT_SHA build arg; "unknown" in tests


def test_history_composite_empty_returns_503(client: TestClient, empty_data) -> None:
    r = client.get("/history/composite")
    assert r.status_code == 503


def test_history_kpi_empty_returns_503(client: TestClient, empty_data) -> None:
    r = client.get("/history/kpi")
    assert r.status_code == 503


def test_history_series_unknown_name_returns_404(client: TestClient, sample_data) -> None:
    r = client.get("/history/series", params={"name": "definitely_not_a_column"})
    assert r.status_code == 404
    assert "available" not in r.json().get("detail", "")


def test_history_composite_with_data(client: TestClient, sample_data) -> None:
    r = client.get("/history/composite")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) > 0
    assert {"obs_date", "composite_z", "overvaluation_pct", "percentile_rank"}.issubset(
        body["data"][0].keys()
    )


def test_history_kpi_with_data(client: TestClient, sample_data) -> None:
    r = client.get("/history/kpi")
    assert r.status_code == 200
    body = r.json()
    for k in ("overvaluation_pct", "percentile_rank", "price_to_income",
              "price_to_rent", "mortgage_rate_30y"):
        assert k in body
    assert body["price_to_rent"] > 0


def test_sensitivity_heatmap_empty_returns_503(client: TestClient, empty_data) -> None:
    r = client.get("/sensitivity/heatmap")
    assert r.status_code == 503


def test_sensitivity_heatmap_with_data(client: TestClient, sample_data) -> None:
    r = client.get("/sensitivity/heatmap", params={"rate_min": 4, "rate_max": 6, "rate_step": 1})
    assert r.status_code == 200
    body = r.json()
    assert "cells" in body and len(body["cells"]) > 0


@pytest.fixture
def stale_tail_data(monkeypatch) -> None:
    """sample_data + extra months with NaN median_income.

    Mirrors production: MEHOINUSA646N is annual and lags the monthly grid by
    ~1 year, so the tail of monthly_fact carries fresh rates with stale
    income/price. The latest row driving composite_z.iloc[-1] is the last
    *complete* row, not the last row of monthly_fact.
    """
    idx = pd.date_range("1995-01-31", "2024-12-31", freq="ME")
    n = len(idx)
    body = pd.DataFrame({
        "median_price":      np.linspace(100_000, 400_000, n),
        "median_income":     np.full(n, 60_000.0),
        "mortgage_rate_30y": np.full(n, 6.0),
        "oer_index":         np.full(n, 100.0),
        "cs_hpi":            np.full(n, 100.0),
        "zhvi":              np.full(n, 100_000.0),
        "treasury_10y":      np.full(n, 4.0),
        "cpi":               np.full(n, 250.0),
        "real_dpi_per_capita": np.full(n, 50_000.0),
    }, index=idx).rename_axis("obs_date")
    tail_idx = pd.date_range("2025-01-31", periods=18, freq="ME")
    tail = pd.DataFrame({
        "median_price":      np.nan,
        "median_income":     np.nan,
        "mortgage_rate_30y": np.linspace(6.5, 7.5, 18),
        "oer_index":         np.linspace(105.0, 115.0, 18),
        "cs_hpi":            np.linspace(105.0, 115.0, 18),
        "zhvi":              np.linspace(105_000.0, 115_000.0, 18),
        "treasury_10y":      np.linspace(4.0, 4.5, 18),
        "cpi":               np.linspace(250.0, 270.0, 18),
        "real_dpi_per_capita": np.linspace(50_000.0, 52_000.0, 18),
    }, index=tail_idx).rename_axis("obs_date")
    _patch_loader(monkeypatch, pd.concat([body, tail]))


def test_sensitivity_breakpoints_with_stale_tail(client: TestClient, stale_tail_data) -> None:
    """Regression: perturbations must hit the last *complete* row, not the last
    row of monthly_fact (which the lenses drop for missing income/price)."""
    r = client.get("/sensitivity/breakpoints")
    assert r.status_code == 200
    body = r.json()
    assert body["current_z"] > 0
    neutralizers = (
        body["rate_to_neutralize_pct"],
        body["income_to_neutralize_usd"],
        body["price_decline_to_neutralize_pct"],
    )
    assert any(v is not None for v in neutralizers), neutralizers


def test_sensitivity_tornado_with_stale_tail(client: TestClient, stale_tail_data) -> None:
    """Regression: every tornado bar must register a non-zero abs_effect when
    the tail has stale income/price. If perturbation hit the stale row,
    abs_effect collapses to 0 for every input."""
    r = client.get("/sensitivity/tornado")
    assert r.status_code == 200
    body = r.json()
    assert any(b["abs_effect"] > 0 for b in body["bars"]), body["bars"]


def test_history_composite_invalid_date_returns_400(client: TestClient, sample_data) -> None:
    r = client.get("/history/composite", params={"start": "not-a-date"})
    assert r.status_code == 400
