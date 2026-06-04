"""Shared normalization for source-provided body text persisted into
signals_v2.snippet. Strip, cap to a bounded length, and coerce empty to None
so the column stores either real text or NULL (never '')."""
from __future__ import annotations

_MAX_SNIPPET_LEN = 500


def clean_snippet(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    return cleaned[:_MAX_SNIPPET_LEN]
