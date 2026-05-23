"""Shape tests for backend/scripts/backfill_lexicon_topics.py (Issue #171).

DB-less: pins the SQL surface area that we depend on (idempotent upsert,
evidence jsonb, v2 model_version isolation, OR-semantics qualification,
top-N ranking, headline length filter).
"""
from __future__ import annotations

import re
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "backfill_lexicon_topics.py"
)


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists():
    assert SCRIPT.exists()


def test_writes_under_v2_model_version_only():
    src = _source()
    assert 'MODEL_VERSION = "theme-hint-lex-v2"' in src
    # The v1 tag must NOT appear as a written value here; v1 lives in
    # classify_topics.py and we keep them isolated for A/B.
    assert "theme-hint-lex-v1" not in src


def test_targets_signal_topic_assignments_with_upsert():
    src = _source()
    assert "INSERT INTO signal_topic_assignments" in src
    assert "ON CONFLICT (signal_id, topic_id, method, model_version)" in src
    assert "DO UPDATE SET" in src
    assert "confidence = EXCLUDED.confidence" in src
    assert "evidence   = EXCLUDED.evidence" in src


def test_qualification_uses_or_semantics():
    """v2 must accept either lex match OR >=1 theme hit (lift recall vs v1)."""
    src = _source()
    # Joiner across atlas_topics uses an OR for lexicon match vs theme overlap.
    assert "s.themes && t.gdelt_theme_hints" in src
    assert re.search(
        r"WHERE cardinality\(matched_lex_terms\) >= 1\s+OR theme_hits >= 1",
        src,
    )


def test_confidence_formula_components_present():
    src = _source()
    # base 0.55 + lex 0.10*min(lex,3) + theme 0.05*min(theme_hits,4) + cross 0.05
    assert "0.55" in src
    assert "0.10 * LEAST(cardinality(matched_lex_terms), 3)" in src
    assert "0.05 * LEAST(theme_hits, 4)" in src
    # cross-evidence bonus only fires when both signals are present.
    assert "cardinality(matched_lex_terms) > 0 AND theme_hits >= 2" in src
    # confidence capped at 0.95 to keep room for analyst confirmation.
    assert "LEAST(\n            0.95::double precision" in src


def test_evidence_jsonb_includes_components_and_terms():
    src = _source()
    assert "jsonb_build_object(" in src
    for key in (
        "'theme_hits'",
        "'hint_count'",
        "'lex_count'",
        "'matched_terms'",
        "'formula'",
        "'base'",
        "'lex_component'",
        "'theme_component'",
        "'cross_component'",
    ):
        assert key in src, f"evidence missing key {key}"


def test_top_n_ranking_and_min_confidence_floor():
    src = _source()
    assert "ROW_NUMBER() OVER (" in src
    assert "PARTITION BY signal_id" in src
    assert "WHERE rnk <= $7" in src
    # min_confidence floor parameterized at $3
    assert "WHERE confidence >= $3" in src


def test_short_headlines_are_filtered():
    src = _source()
    # length filter parameterized at $2 — protects against
    # headline-only false positives on tweets/aggregator stubs.
    assert "length(headline) >= $2" in src
    assert "DEFAULT_MIN_HEADLINE_LEN = 20" in src


def test_only_active_atlas_topics_are_considered():
    src = _source()
    assert "t.is_active = true" in src


def test_method_is_lexicon():
    src = _source()
    assert 'METHOD = "lexicon"' in src


def test_dry_run_path_does_not_insert():
    src = _source()
    assert "DRY_RUN_SQL" in src
    # The dry-run statement must not contain an INSERT.
    dry_block = src.split("DRY_RUN_SQL")[1]
    head = dry_block.split('"""', 2)[1]
    assert "INSERT" not in head.upper()
