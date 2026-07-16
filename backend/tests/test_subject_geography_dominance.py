"""#238 dominance cap — measured next fix (post-fix remeasure, 2026-07-16).

The lexicon-recall fixes exposed over-verification of cluster side-mentions
(dt-320 verified a 4-receipt IR beside a 15-receipt GR; dt-606 verified 4
countries where the judge names 2). Simulated on the replay ledger, the cap
takes the window from 66.7%/32.3% to 86.7%/41.9% — above the 75.0%/38.7%
baseline on both axes. Contract: a verified country must hold receipt_count
>= 1/3 of the leading verified country's; the verified set is capped at 2,
ordered by receipts; capped countries stay visible as candidates with a
dominance_capped flag + a reason code (never silently dropped).
"""

from app.services.subject_geography import infer_receipt_subject_geography


def _receipts(spec):
    """spec: list of (headline, source) tuples."""
    return [{"headline": h, "source_name": s} for h, s in spec]


def _ua(n, start=0):
    return [(f"Херсон під обстрілом, репортаж {i}", f"ua-outlet-{i}") for i in range(start, start + n)]


def test_side_mention_below_third_is_capped_not_verified():
    # leader: 9 Greece receipts; side-mention: 2 Iran receipts (2 < 9/3)
    rows = _receipts(
        [(f"Τραγωδία στη Χαλκιδική, ρεπορτάζ {i}", f"gr-{i}") for i in range(9)]
        + [("Το Ιράν απειλεί με αντίποινα", "gr-a"), ("Ιράν: νέες κυρώσεις", "gr-b")]
    )
    out = infer_receipt_subject_geography(rows)
    assert out["verified_subject_countries"] == ["GR"]
    capped = [c for c in out.get("candidates", []) if c.get("country") == "IR"]
    assert capped and capped[0].get("dominance_capped") is True
    assert "subject_geography_dominance_capped" in out["reason_codes"]


def test_genuine_co_subject_above_third_survives():
    # RU 6 receipts, UA 3 (3 >= 6/3) — both real parties stay verified
    rows = _receipts(
        [(f"Росія атакувала об'єкти, звіт {i}", f"o{i}") for i in range(6)]
        + [(h, s) for h, s in _ua(3)]
    )
    out = infer_receipt_subject_geography(rows)
    assert set(out["verified_subject_countries"]) == {"RU", "UA"}


def test_verified_set_capped_at_two_ordered_by_receipts():
    # ES 8, FR 5, AR 4, GB 4 -> cap 2 -> [ES, FR]
    rows = _receipts(
        [(f"España avanza a la final, crónica {i}", f"es-{i}") for i in range(8)]
        + [(f"Francia cae en semifinales, análisis {i}", f"fr-{i}") for i in range(5)]
        + [(f"Argentina celebra la victoria {i}", f"ar-{i}") for i in range(4)]
        + [(f"Inglaterra queda eliminada {i}", f"gb-{i}") for i in range(4)]
    )
    out = infer_receipt_subject_geography(rows)
    assert out["verified_subject_countries"] == ["ES", "FR"]
    assert "subject_geography_dominance_capped" in out["reason_codes"]


def test_single_verified_country_unaffected():
    rows = _receipts([(f"Ukraine reports strikes, wire {i}", f"w{i}") for i in range(4)])
    out = infer_receipt_subject_geography(rows)
    assert out["verified_subject_countries"] == ["UA"]
    assert "subject_geography_dominance_capped" not in out["reason_codes"]
