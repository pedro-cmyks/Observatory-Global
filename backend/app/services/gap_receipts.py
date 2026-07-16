"""Extended-tier receipts for the coverage-gap box (#225/#172).

Measured basis (docs/research/gap-pool/2026-07-16-gap-pool-relevance.md,
adversarially verified): ~4-6% of a gap category's raw pool is genuinely
relevant, but the 2-3 most newsworthy hits (Crimea 16h/day mobile shutdown,
Telegram t.me global block) sit above the topic's extended (~75%) threshold
and are recoverable NOW. Gap-slice precision of that tier measured 29-43% —
hence the hard K=3 cap and the mandatory "extended · unverified" tier label.
Anything below the extended threshold stays hidden here (its recovery lever
is per-topic gate recall, not this box).
"""

from __future__ import annotations

from typing import Any

from app.services.research_semantic import is_junk_headline

GAP_RECEIPTS_K = 3


def pick_extended_receipts(
    rows: list[dict[str, Any]],
    threshold: float | None,
    k: int = GAP_RECEIPTS_K,
) -> list[dict[str, Any]]:
    """Top-k extended-tier receipts for one gap category.

    Filters to gate_score >= the topic's extended threshold (no threshold ->
    no receipts, never leak raw rows), drops junk/empty headlines, dedupes
    syndicated copies by headline keeping the best score, orders by score.
    """
    if threshold is None:
        return []
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        headline = (row.get("headline") or "").strip()
        score = row.get("gate_score")
        if not headline or score is None or float(score) < threshold:
            continue
        if is_junk_headline(headline):
            continue
        prev = best.get(headline)
        if prev is None or float(score) > prev["_score"]:
            best[headline] = {
                "headline": headline,
                "source": row.get("source"),
                "url": row.get("url"),
                "_score": float(score),
            }
    ranked = sorted(best.values(), key=lambda r: r["_score"], reverse=True)[:k]
    return [
        {
            "headline": r["headline"],
            "source": r["source"],
            "url": r["url"],
            "gate_score": round(r["_score"], 3),
            "tier": "extended",
        }
        for r in ranked
    ]
