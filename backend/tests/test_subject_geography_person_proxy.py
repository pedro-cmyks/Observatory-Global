"""#238 Fix 1 — person-proxy demotion in subject-geography verification.

The ingest lexicons deliberately carry leader names (Putin→RU, Trump→US,
Зеленськ→UA, …) — good enough for coarse volume geo-tagging, but a person
mention is NOT verify-grade SUBJECT geography. Measured failure (dt-714,
docs/research/subject-geo/2026-07-16-inference-quality.md): a Romania-domestic
politics thread VERIFIED RU because "mesaj către Putin" receipts hit the
Putin→RU proxy across ≥2 outlets.

Contract pinned here:

* A receipt whose country evidence survives ONLY via person tokens carries
  method ``person_proxy`` for that country.
* person_proxy-only receipts NEVER count toward the ≥2-receipt/≥2-outlet
  verified bar — the bar must be met by non-proxy evidence alone.
* When the demotion suppressed a would-be verify, the ledger says so
  (``person_proxy_evidence_demoted`` in reason_codes) — no silent filtering.
* Ingest ``extract_country`` is deliberately unchanged (person tags stay fine
  for volume tagging); the demotion lives in subject_geography scoring only.
"""
from __future__ import annotations

from app.services.subject_geography import (
    headline_country_evidence,
    infer_receipt_subject_geography,
)


# ── Method-level: person-only matches are labeled person_proxy ────────────────
def test_person_proxy_only_headline_gets_person_proxy_method():
    evidence = headline_country_evidence("Donald Trump, mesaj către Putin")
    assert evidence["RU"] == {"person_proxy"}
    assert evidence["US"] == {"person_proxy"}


def test_country_named_alongside_person_stays_non_proxy():
    # Путін is a person token, but Росія is real country evidence — the
    # receipt must remain verify-grade for RU.
    evidence = headline_country_evidence("Путін заявив, що Росія переможе")
    assert "native_pattern" in evidence["RU"]


def test_latin_country_named_alongside_person_stays_non_proxy():
    evidence = headline_country_evidence("Trump lands in Washington for summit")
    assert "headline_pattern" in evidence["US"]


# ── (a) proxy-only receipts can NEVER verify ──────────────────────────────────
_PUTIN_ONLY_RECEIPTS = [
    {"id": 1, "headline": "Donald Trump, mesaj către Putin", "source_name": "Digi24"},
    {"id": 2, "headline": "Mesaj dur către Putin din partea liderilor europeni", "source_name": "Adevărul"},
    {"id": 3, "headline": "Ce i-a transmis premierul lui Putin la summit", "source_name": "HotNews"},
]


def test_person_proxy_receipts_never_verify():
    # 3 receipts / 3 outlets — clears the old bar, but every RU hit is
    # Putin-proxy → RU stays candidate, thread stays partial.
    result = infer_receipt_subject_geography(_PUTIN_ONLY_RECEIPTS)
    assert result["status"] == "partial"
    assert result["verified_subject_countries"] == []
    ru = next(c for c in result["candidates"] if c["country"] == "RU")
    assert ru["status"] == "candidate"
    assert ru["receipt_count"] == 3
    assert ru["outlet_count"] == 3
    assert ru["non_proxy_receipt_count"] == 0
    assert ru["non_proxy_outlet_count"] == 0
    assert "person_proxy" in ru["methods"]


# ── (b) mixed evidence: the bar is met by non-proxy receipts alone ────────────
def test_mixed_receipts_verify_on_non_proxy_evidence_alone():
    receipts = [
        {"id": 1, "headline": "Росія відкидає умови припинення вогню", "source_name": "Outlet A"},
        {"id": 2, "headline": "Росія готує новий наступ на сході", "source_name": "Outlet B"},
        {"id": 3, "headline": "Путін відповів на ультиматум", "source_name": "Outlet C"},
    ]
    result = infer_receipt_subject_geography(receipts)
    assert result["status"] == "verified"
    assert result["verified_subject_countries"] == ["RU"]
    ru = next(c for c in result["candidates"] if c["country"] == "RU")
    assert ru["receipt_count"] == 3          # ledger keeps the full tally
    assert ru["non_proxy_receipt_count"] == 2
    assert ru["non_proxy_outlet_count"] == 2


def test_verified_without_any_proxy_receipts_carries_no_demotion_note():
    receipts = [
        {"id": 1, "headline": "Washington unveils sweeping tariff package", "source_name": "R"},
        {"id": 2, "headline": "United States confirms new tariff schedule", "source_name": "A"},
    ]
    result = infer_receipt_subject_geography(receipts)
    assert result["verified_subject_countries"] == ["US"]
    assert "person_proxy_evidence_demoted" not in result["reason_codes"]


# ── (c) suppression is visible in the ledger, never silent ────────────────────
def test_reason_codes_surface_person_proxy_demotion():
    result = infer_receipt_subject_geography(_PUTIN_ONLY_RECEIPTS)
    assert "person_proxy_evidence_demoted" in result["reason_codes"]
    assert "subject_geography_not_independently_corroborated" in result["reason_codes"]


def test_suppressed_candidate_is_flagged_in_the_candidate_row():
    result = infer_receipt_subject_geography(_PUTIN_ONLY_RECEIPTS)
    ru = next(c for c in result["candidates"] if c["country"] == "RU")
    assert ru["person_proxy_suppressed"] is True


# ── The measured dt-714 class, end to end ─────────────────────────────────────
def test_dt714_romanian_domestic_thread_verifies_ro_never_ru():
    # Real receipt shapes from the 2026-07-16 measurement: Romanian domestic
    # politics; RU appears via "Rusiei" (one real mention) + a Putin proxy.
    # Expected: RO verified (self-name lexicon, Fix 2), RU stays candidate.
    receipts = [
        {
            "id": 1,
            "headline": "Nicuşor Dan: România e o ţară suverană şi nu se lasă intimidată de ameninţările Rusiei",
            "source_name": "Digi24",
        },
        {
            "id": 2,
            "headline": "Dăianu: România nu putea evita majorarea taxelor",
            "source_name": "Adevărul",
        },
        {
            "id": 3,
            "headline": "Donald Trump, mesaj către Putin",
            "source_name": "HotNews",
        },
    ]
    result = infer_receipt_subject_geography(receipts)
    assert result["status"] == "verified"
    assert result["verified_subject_countries"] == ["RO"]
    ru = next(c for c in result["candidates"] if c["country"] == "RU")
    assert ru["status"] == "candidate"
