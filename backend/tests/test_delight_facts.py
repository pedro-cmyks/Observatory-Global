"""Loading-delight fact phrasing — honesty guards + template output."""
from app.services import delight_facts


def test_pulse_fact_phrases_real_numbers():
    f = delight_facts.pulse_fact(157_432, 126, 28)
    assert f is not None
    assert f["kind"] == "measured"
    assert f["window_hours"] == 24
    assert "157,432 headlines" in f["text"]
    assert "126 countries" in f["text"]
    assert "28 languages" in f["text"]
    assert f["measured_at"]


def test_pulse_fact_rejects_thin_data():
    assert delight_facts.pulse_fact(500, 126, 28) is None
    assert delight_facts.pulse_fact(157_432, 4, 28) is None


def test_pulse_fact_omits_languages_when_sparse():
    f = delight_facts.pulse_fact(10_000, 50, 3)
    assert f is not None
    assert "languages" not in f["text"]


def test_language_fact_computes_non_english_share():
    f = delight_facts.language_fact(10_000, 7_000, 21)
    assert f is not None
    assert "30%" in f["text"]
    assert "21 languages" in f["text"]


def test_language_fact_rejects_monoculture_and_thin():
    # ~0% non-English would be a sad fact, not delight
    assert delight_facts.language_fact(10_000, 9_950, 21) is None
    assert delight_facts.language_fact(100, 50, 21) is None
    assert delight_facts.language_fact(10_000, 7_000, 3) is None


def test_mover_fact():
    f = delight_facts.mover_fact("Venezuela Earthquake Response")
    assert f is not None
    assert "Venezuela Earthquake Response" in f["text"]
    assert delight_facts.mover_fact(None) is None
    assert delight_facts.mover_fact("  x ") is None


def test_gap_fact():
    f = delight_facts.gap_fact("Trade & export controls", 72)
    assert f is not None
    assert "72 headlines" in f["text"]
    assert "none verified yet" in f["text"]
    assert delight_facts.gap_fact("Trade", 5) is None
    assert delight_facts.gap_fact(None, 100) is None


def test_quiet_fact_bounds():
    f = delight_facts.quiet_fact("Lebanon", 34)
    assert f is not None
    assert "Lebanon" in f["text"]
    # high volume is not "under the radar"
    assert delight_facts.quiet_fact("United States", 5_000) is None
    assert delight_facts.quiet_fact(None, 34) is None
    assert delight_facts.quiet_fact("Lebanon", 0) is None
