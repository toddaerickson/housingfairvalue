"""FastAPI app entrypoint."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .db import engine
from .routers import history, sensitivity

app = FastAPI(
    title="Housing Fair Value API",
    description="National US housing overvaluation composite signal — history + sensitivity.",
    version="0.1.0",
)

_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)

app.include_router(history.router)
app.include_router(sensitivity.router)


@app.get("/health")
def health():
    """Liveness only — does not touch the DB."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness — pings the DB. Render/k8s should use this for traffic gating."""
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db unavailable: {e}") from e
    return {"status": "ready"}
