"""A hand-rolled, in-memory sliding-window rate limiter.

Deliberately NOT a third-party dependency: the exact behavior needs to be
verifiable by reading this file, not assumed from a package's docs. This is
explicitly a single-process limiter — state lives in this module's own
dict, so a real multi-instance deployment would need a shared backend (e.g.
Redis) instead. That's a genuine, documented scope boundary (see
architecture.md's security section), not an oversight: this project's
standing infrastructure constraint is a single Docker container.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import settings

# key -> deque of request timestamps (monotonic seconds) within the window
_buckets: dict[str, deque] = defaultdict(deque)

_WINDOW_SECONDS = 60.0


def _check(key: str, limit_per_minute: int) -> None:
    now = time.monotonic()
    bucket = _buckets[key]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit_per_minute:
        raise HTTPException(429, "Too many requests — please slow down and try again shortly.")
    bucket.append(now)


def _client_key(request: Request, scope: str) -> str:
    # request.client is None in some test/proxy contexts; fall back to a
    # shared bucket rather than crashing the request.
    ip = request.client.host if request.client else "unknown"
    return f"{scope}:{ip}"


def rate_limit_auth(request: Request) -> None:
    _check(_client_key(request, "auth"), settings.rate_limit_auth_per_minute)


def rate_limit_ai(request: Request) -> None:
    _check(_client_key(request, "ai"), settings.rate_limit_ai_per_minute)
