"""#238: why_now must never present coverage geography as a subject claim.

The old template said "concentrated in {top coverage countries}" — a
coverage-proxy lie on threads whose subject is elsewhere (live case: a
verified-IT "Trump Attacks Meloni" thread reading "concentrated in Iran and
Russia"). New contract: the geo clause appears ONLY when subject geography is
VERIFIED (then it is a subject claim, "centered on X"); otherwise why_now is
movement-only. Coverage countries stay on the card as labeled chips — they
just never masquerade as the subject inside the why-now sentence.
"""

from app.services.thread_intelligence import _why_now


def test_verified_subject_uses_centered_on():
    out = _why_now(16, subject_countries=["IT"], subject_status="verified")
    assert out == "Up 16 vs the prior 10h (net new coverage), centered on Italy."


def test_verified_two_subjects_joined():
    out = _why_now(-5, subject_countries=["IR", "US"], subject_status="verified")
    assert out == (
        "Down 5 vs the prior 10h (coverage cooling), "
        "centered on Iran and United States."
    )


def test_unverified_subject_drops_geo_clause_entirely():
    out = _why_now(29, subject_countries=[], subject_status="partial")
    assert out == "Up 29 vs the prior 10h (net new coverage)."
    assert "concentrated in" not in out and "centered on" not in out


def test_no_subject_info_is_movement_only():
    assert _why_now(12) == "Up 12 vs the prior 10h (net new coverage)."
    assert _why_now(-3) == "Down 3 vs the prior 10h (coverage cooling)."
    assert _why_now(0) == "Signal volume is steady vs the prior 10h."


def test_verified_but_empty_list_is_movement_only():
    out = _why_now(7, subject_countries=[], subject_status="verified")
    assert out == "Up 7 vs the prior 10h (net new coverage)."


def test_coverage_countries_never_leak_into_the_sentence():
    # even if a caller passes coverage codes by mistake in subject_countries,
    # a non-verified status must suppress them
    out = _why_now(10, subject_countries=["IR", "RU"], subject_status="partial")
    assert "Iran" not in out and "Russia" not in out
