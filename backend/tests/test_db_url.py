"""Unit tests for backend.db_url.normalize_db_url."""

from __future__ import annotations

from backend.db_url import normalize_db_url


def test_rewrites_postgresql_scheme() -> None:
    raw = "postgresql://user:pw@host:5432/db"
    assert normalize_db_url(raw) == "postgresql+psycopg://user:pw@host:5432/db"


def test_rewrites_postgres_scheme() -> None:
    raw = "postgres://user:pw@host:5432/db"
    assert normalize_db_url(raw) == "postgresql+psycopg://user:pw@host:5432/db"


def test_passes_through_already_prefixed() -> None:
    raw = "postgresql+psycopg://user:pw@host:5432/db"
    assert normalize_db_url(raw) == raw


def test_passes_through_other_drivers() -> None:
    raw = "postgresql+asyncpg://user:pw@host:5432/db"
    assert normalize_db_url(raw) == raw


def test_passes_through_non_postgres() -> None:
    raw = "sqlite:///./test.db"
    assert normalize_db_url(raw) == raw


def test_preserves_query_string() -> None:
    raw = "postgresql://user:pw@host:5432/db?sslmode=require"
    assert normalize_db_url(raw) == "postgresql+psycopg://user:pw@host:5432/db?sslmode=require"
