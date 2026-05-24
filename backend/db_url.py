"""Shared DB-URL normalization.

Supabase, Heroku, and most Postgres hosts hand out connection strings that
start with `postgresql://...`. SQLAlchemy's default driver for that scheme
is psycopg2, but this project pins `psycopg[binary]` (psycopg3) — so the
bare scheme fails at runtime with `No module named 'psycopg2'`.

`normalize_db_url()` rewrites `postgresql://` and `postgres://` to
`postgresql+psycopg://` so any standard Postgres URL works out of the box.
Already-prefixed URLs (`postgresql+psycopg://`, `postgresql+asyncpg://`, …)
pass through unchanged.
"""

from __future__ import annotations


def normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url
