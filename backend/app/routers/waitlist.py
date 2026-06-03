"""
Workbench early-access waitlist (public MVP launch gate).

  POST /api/v2/waitlist         — capture email + optional use_case.
  GET  /api/v2/waitlist/count   — aggregate waitlist size (no emails).

Emails are never returned by any GET. Bot defense is a hidden honeypot
field plus a soft in-process per-IP rate limit (the API runs as a single
Fly app machine, so in-process state is sufficient for the MVP).
"""
from __future__ import annotations

import logging
import re
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import db

logger = logging.getLogger(__name__)
router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_EMAIL_LEN = 320

# Soft in-process per-IP rate limit. Single Fly app machine -> module state is
# enough for the MVP. Not durable across restarts; that is acceptable here.
_RATE_WINDOW_SECONDS = 600  # 10 minutes
_RATE_MAX = 5
_rate_log: dict[str, list[float]] = {}


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def is_valid_email(email: str) -> bool:
    if not email or len(email) > _MAX_EMAIL_LEN:
        return False
    return _EMAIL_RE.match(email) is not None


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _rate_log.get(ip, []) if now - t < _RATE_WINDOW_SECONDS]
    if len(hits) >= _RATE_MAX:
        _rate_log[ip] = hits
        return True
    hits.append(now)
    _rate_log[ip] = hits
    return False


class WaitlistPayload(BaseModel):
    email: str = Field(..., max_length=_MAX_EMAIL_LEN)
    use_case: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=200)  # honeypot field


@router.post("/api/v2/waitlist")
async def join_waitlist(payload: WaitlistPayload, request: Request):
    """Capture an early-access signup. Idempotent on email.

    Never reveals whether the email already existed. A non-empty `company`
    honeypot field means a bot filled a hidden input -> silent success.
    """
    # honeypot: hidden field real users never fill
    if payload.company and payload.company.strip():
        return {"ok": True}

    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(status_code=429, detail="too many requests")

    email = normalize_email(payload.email)
    if not is_valid_email(email):
        raise HTTPException(status_code=422, detail="invalid email")

    use_case = (payload.use_case or "").strip() or None
    referrer = request.headers.get("referer")

    async with db.pool.acquire() as conn:
        if await conn.fetchval("SELECT to_regclass('workbench_waitlist')") is None:
            logger.error("workbench_waitlist missing — is migration 051 applied?")
            raise HTTPException(status_code=503, detail="waitlist unavailable")
        await conn.execute(
            """
            INSERT INTO workbench_waitlist (email, use_case, referrer)
            VALUES ($1, $2, $3)
            ON CONFLICT (email) DO NOTHING
            """,
            email,
            use_case,
            referrer,
        )

    return {"ok": True}


@router.get("/api/v2/waitlist/count")
async def waitlist_count():
    """Aggregate waitlist size only. Never returns emails."""
    async with db.pool.acquire() as conn:
        if await conn.fetchval("SELECT to_regclass('workbench_waitlist')") is None:
            return {"count": 0}
        n = await conn.fetchval("SELECT COUNT(*) FROM workbench_waitlist")
    return {"count": int(n or 0)}
