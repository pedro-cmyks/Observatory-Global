"""Gap-box extended receipts (#225/#172 + gap-pool measurement 2026-07-16).

The coverage-gap box said "raw N · 0 verified" and showed nothing — yet the
measured gap pool buries the 2-3 most newsworthy category hits (Crimea mobile
shutdown, Telegram global block) recoverable via the extended (~75%) tier.
Measured gap-slice precision is only 29-43%, so the contract is: at most K=3
receipts, ordered by gate_score, deduped by headline, NEVER below the topic's
extended threshold, always labeled tier="extended" (unverified).
"""

from app.services.gap_receipts import pick_extended_receipts


def _row(headline, score, source="src", url="https://x/a"):
    return {"headline": headline, "source": source, "url": url, "gate_score": score}


def test_filters_below_threshold_and_orders_by_score():
    rows = [_row("Crimea cuts mobile internet daily", 0.81), _row("Telegram blocked at national level", 0.95), _row("Sudan telecom outage confirmed", 0.79)]
    out = pick_extended_receipts(rows, threshold=0.80, k=3)
    assert [r["headline"] for r in out] == ["Telegram blocked at national level", "Crimea cuts mobile internet daily"]
    assert all(r["tier"] == "extended" for r in out)


def test_dedupes_syndicated_headlines_keeping_best_score():
    rows = [_row("Regulator suspends telecom licences nationwide", 0.82, source="s1"), _row("Regulator suspends telecom licences nationwide", 0.9, source="s2"), _row("Mobile networks down across region", 0.85)]
    out = pick_extended_receipts(rows, threshold=0.80, k=3)
    assert {r["headline"] for r in out} == {"Regulator suspends telecom licences nationwide", "Mobile networks down across region"}
    assert len(out) == 2
    best = next(r for r in out if r["headline"].startswith("Regulator"))
    assert best["gate_score"] == 0.9


def test_caps_at_k():
    rows = [_row(f"Internet shutdown reported in region {i} today", 0.8 + i / 100) for i in range(6)]
    assert len(pick_extended_receipts(rows, threshold=0.80, k=3)) == 3


def test_no_threshold_means_no_receipts():
    # a topic with no extended threshold must never leak raw rows
    assert pick_extended_receipts([_row("Internet blocked across the country", 0.99)], threshold=None, k=3) == []


def test_junk_and_empty_headlines_dropped():
    rows = [_row("", 0.9), _row("Doc 12.Shtml", 0.95), _row("Crimea mobile internet shut 16h a day", 0.85)]
    out = pick_extended_receipts(rows, threshold=0.80, k=3)
    assert [r["headline"] for r in out] == ["Crimea mobile internet shut 16h a day"]


def test_scores_rounded_and_fields_complete():
    out = pick_extended_receipts([_row("Authorities restrict internet access nationwide", 0.84567)], threshold=0.80, k=3)
    assert out[0] == {
        "headline": "Authorities restrict internet access nationwide", "source": "src", "url": "https://x/a",
        "gate_score": 0.846, "tier": "extended",
    }
