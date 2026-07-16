"""Per-IP rate limiting for the public API (pre-accounts interim hardening).

Why this exists: before Atlas is opened to strangers it has NO auth and NO
throttle on any endpoint (see docs/state/2026-07-06-security-audit.md). The
expensive endpoints (OpenAI embeds, DeepSeek/Anthropic LLM calls, the 25s
GDELT external-depth scan) are direct billing/DoS drains when anonymous.

This installs a single in-process sliding-window limiter keyed by client IP.
The API runs as one Fly app machine, so module/instance state is sufficient
(same assumption the waitlist limiter already documents). It is NOT durable
across restarts, which is acceptable for the interim.

Buckets (per IP), all env-tunable:
  - "paid"   expensive LLM/embed endpoints          default 20 / 5 min
  - "slow"   external-depth (holds a DB conn ~25s)  default  8 / 5 min
  - "write"  anonymous DB writes (telemetry/events) default 60 / 1 min
  - "global" everything else                        default 600 / 1 min

Kill switch: ATLAS_RATE_LIMIT_ENABLED=false disables all limiting.

Ordering note: install this BEFORE adding CORSMiddleware so CORS stays the
outermost middleware and a 429 response still carries CORS headers.
"""
from __future__ import annotations

import os
import re
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Paths that must never be throttled (Fly health checks, docs).
_EXEMPT_PATHS = frozenset({"/", "/health", "/docs", "/openapi.json", "/redoc"})


def client_ip(request: Request) -> str:
    """Best-effort real client IP.

    The production frontend proxies /api/* through the Vercel rewrite, so the
    request reaching Fly originates from Vercel's egress — Fly-Client-IP would
    be that single proxy IP, collapsing ALL users into one rate-limit bucket.
    The real client is the leftmost X-Forwarded-For entry that Vercel forwards.
    Fall back to Fly-Client-IP for any direct-to-Fly request.

    Caveat (interim): X-Forwarded-For is client-spoofable on a direct hit to
    fly.dev, so a determined attacker bypassing the Vercel proxy can rotate it
    to dodge the limit. The durable fix is per-account quotas plus a
    trusted-proxy allowlist (deferred to the accounts build).
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        first = fwd.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    fly_ip = request.headers.get("fly-client-ip")
    if fly_ip:
        return fly_ip.strip()
    return request.client.host if request.client else "unknown"


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _limits() -> dict[str, tuple[int, int]]:
    return {
        "paid": (_int_env("ATLAS_RL_PAID_MAX", 20), _int_env("ATLAS_RL_PAID_WINDOW", 300)),
        "slow": (_int_env("ATLAS_RL_SLOW_MAX", 8), _int_env("ATLAS_RL_SLOW_WINDOW", 300)),
        "write": (_int_env("ATLAS_RL_WRITE_MAX", 60), _int_env("ATLAS_RL_WRITE_WINDOW", 60)),
        "global": (_int_env("ATLAS_RL_GLOBAL_MAX", 600), _int_env("ATLAS_RL_GLOBAL_WINDOW", 60)),
    }


def _llm_flag(request: Request) -> bool:
    return request.query_params.get("llm", "").lower() in ("1", "true", "yes")


# (compiled path regex, bucket, optional predicate). First match wins.
# Predicate lets us throttle a path only for a specific query flag.
_RULE_SPECS: list[tuple[str, str, object]] = [
    (r"^/api/v2/theme/[^/]+/external-depth$", "slow", None),
    (r"^/api/v2/research/plan$", "paid", None),
    (r"^/api/v2/translate(?:/batch|/text)?$", "paid", None),
    (r"^/api/v2/theme/[^/]+/insight$", "paid", None),
    (r"^/api/v2/briefing/insight$", "paid", None),
    (r"^/api/v2/signal/[^/]+/context$", "paid", None),
    # Thread detail only triggers a paid DeepSeek note when llm= is set;
    # normal opens fall through to the generous global bucket.
    (r"^/api/v2/threads/[^/]+$", "paid", _llm_flag),
    (r"^/api/v2/telemetry$", "write", None),
    (r"^/api/v2/research/events$", "write", None),
]


def _build_rules() -> list[tuple[re.Pattern, str, object]]:
    return [(re.compile(p), bucket, pred) for (p, bucket, pred) in _RULE_SPECS]


def _enabled() -> bool:
    return os.getenv("ATLAS_RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rules=None, limits=None, global_limit=None, enabled=None):
        super().__init__(app)
        self.rules = rules if rules is not None else _build_rules()
        self.limits = limits if limits is not None else _limits()
        self.global_limit = global_limit or self.limits["global"]
        self.enabled = _enabled() if enabled is None else enabled
        # (bucket, ip) -> list[monotonic timestamps]
        self._log: dict[tuple[str, str], list[float]] = {}

    def _bucket_for(self, request: Request, path: str) -> tuple[str, tuple[int, int]]:
        for pattern, bucket, pred in self.rules:
            if pattern.match(path) and (pred is None or pred(request)):
                return bucket, self.limits.get(bucket, self.global_limit)
        return "global", self.global_limit

    def _hit(self, bucket: str, ip: str, max_hits: int, window: int, now: float | None = None) -> bool:
        """Record a hit; return True if the caller is over the limit."""
        now = time.monotonic() if now is None else now
        key = (bucket, ip)
        hits = [t for t in self._log.get(key, ()) if now - t < window]
        if len(hits) >= max_hits:
            self._log[key] = hits
            return True
        hits.append(now)
        self._log[key] = hits
        # Opportunistic prune so the dict can't grow unbounded under IP rotation.
        if len(self._log) > 10000:
            self._log = {
                k: [t for t in v if now - t < window] for k, v in self._log.items()
            }
            self._log = {k: v for k, v in self._log.items() if v}
        return False

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.method == "OPTIONS" or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)
        bucket, (max_hits, window) = self._bucket_for(request, request.url.path)
        ip = client_ip(request)
        if self._hit(bucket, ip, max_hits, window):
            return JSONResponse(
                {"detail": "rate limit exceeded", "bucket": bucket, "retry_after_seconds": window},
                status_code=429,
                headers={"Retry-After": str(window)},
            )
        return await call_next(request)


def install_rate_limiting(app) -> None:
    """Register the limiter. Call BEFORE add_middleware(CORSMiddleware)."""
    app.add_middleware(RateLimitMiddleware)
