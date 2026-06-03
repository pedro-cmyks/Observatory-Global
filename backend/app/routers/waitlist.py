"""
Workbench early-access waitlist (public MVP launch gate).

  POST /api/v2/waitlist         — capture email + optional use_case.
  GET  /api/v2/waitlist/count   — aggregate waitlist size (no emails).

Emails are never returned by any GET. Bot defense is a hidden honeypot
field plus a soft in-process per-IP rate limit (the API runs as a single
Fly app machine, so in-process state is sufficient for the MVP).
"""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_EMAIL_LEN = 320


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def is_valid_email(email: str) -> bool:
    if not email or len(email) > _MAX_EMAIL_LEN:
        return False
    return _EMAIL_RE.match(email) is not None
