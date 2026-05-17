"""Single shared slowapi Limiter for the app.

Lives in its own module so routers can import the same instance that
`main.py` binds to `app.state.limiter` without creating a circular
import (main imports routers; routers can't import main).

Per-route `@limiter.limit("N/minute")` decorators only fire when
`SlowAPIMiddleware` is installed on the app — see `main.py` for that
registration. `key_func=get_remote_address` reads `X-Forwarded-For` only
when uvicorn is launched with `--proxy-headers --forwarded-allow-ips='*'`
(set in `infra/api.Dockerfile`'s CMD), so per-IP buckets work behind
Fly's edge proxy.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
