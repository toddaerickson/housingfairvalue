"""FastAPI app entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import history, sensitivity

app = FastAPI(
    title="Housing Fair Value API",
    description="National US housing overvaluation composite signal — history + sensitivity.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(history.router)
app.include_router(sensitivity.router)


@app.get("/health")
def health():
    return {"status": "ok"}
