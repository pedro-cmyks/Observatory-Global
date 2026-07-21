"""Unit tests for NLP pipeline selection + entity validation (issues #162, #163).

These tests do NOT require a running model. They cover the pure-Python helpers
that gate which signals enter the pipeline and which entities are kept.
"""
from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path

import pytest


def _reload_pipeline(mode: str):
    os.environ["NLP_MULTILINGUAL_MODE"] = mode
    import enrichment.nlp_pipeline as pipeline
    return importlib.reload(pipeline)


@pytest.fixture(autouse=True)
def restore_mode():
    original = os.environ.get("NLP_MULTILINGUAL_MODE")
    yield
    if original is None:
        os.environ.pop("NLP_MULTILINGUAL_MODE", None)
    else:
        os.environ["NLP_MULTILINGUAL_MODE"] = original


# ── _entity_valid: non-Latin scripts ─────────────────────────────────────────
def test_entity_valid_accepts_arabic_when_source_lang_known():
    pipeline = _reload_pipeline("on")
    # "Arab League" in Arabic — pure Arabic script
    assert pipeline._entity_valid("جامعة الدول العربية", source_lang="ar") is True


def test_entity_valid_accepts_hindi_when_source_lang_known():
    pipeline = _reload_pipeline("on")
    # "Bharatiya Janata Party" in Devanagari
    assert pipeline._entity_valid("भारतीय जनता पार्टी", source_lang="hi") is True


def test_entity_valid_accepts_thai_when_source_lang_known():
    pipeline = _reload_pipeline("on")
    # "Bangkok" in Thai
    assert pipeline._entity_valid("กรุงเทพมหานคร", source_lang="th") is True


def test_entity_valid_rejects_digits_and_tiny_strings():
    pipeline = _reload_pipeline("on")
    assert pipeline._entity_valid("1", source_lang="en") is False
    assert pipeline._entity_valid("12345", source_lang="ar") is False
    assert pipeline._entity_valid("A", source_lang="en") is False


def test_entity_valid_rejects_overlong_spans():
    pipeline = _reload_pipeline("on")
    long_span = "Word One Two Three Four Five Six"
    assert pipeline._entity_valid(long_span, source_lang="en") is False


def test_entity_valid_in_off_mode_still_rejects_high_non_ascii_when_no_lang():
    pipeline = _reload_pipeline("off")
    # No source_lang hint -> falls back to legacy 0.4 threshold.
    assert pipeline._entity_valid("جامعة الدول العربية", source_lang=None) is False


def test_entity_valid_in_multilingual_mode_relaxes_threshold_when_no_lang():
    pipeline = _reload_pipeline("on")
    # No source_lang hint, but multilingual mode raises threshold to 0.6.
    # An ASCII-dominant mixed string should still pass.
    assert pipeline._entity_valid("Macron Élysée", source_lang=None) is True


# ── _multilingual_enabled / _shadow_writes flags ─────────────────────────────
def test_mode_off_is_default_and_not_multilingual():
    pipeline = _reload_pipeline("off")
    assert pipeline._multilingual_enabled() is False
    assert pipeline._shadow_writes() is False


def test_mode_shadow_enables_multilingual_and_shadow_writes():
    pipeline = _reload_pipeline("shadow")
    assert pipeline._multilingual_enabled() is True
    assert pipeline._shadow_writes() is True


def test_mode_on_enables_multilingual_without_shadow_writes():
    pipeline = _reload_pipeline("on")
    assert pipeline._multilingual_enabled() is True
    assert pipeline._shadow_writes() is False


def test_hf_ner_batches_headlines_in_one_model_call(monkeypatch):
    pipeline = _reload_pipeline("on")
    monkeypatch.setattr(pipeline, "NER_BATCH_SIZE", 8)
    calls = []

    class FakeNer:
        def __call__(self, headlines, *, batch_size=None):
            calls.append((headlines, batch_size))
            return [
                [{"entity_group": "PER", "word": "Alice"}],
                [{"entity_group": "LOC", "word": "Bogotá"}],
            ]

    result = pipeline._extract_entities_hf_batch(
        FakeNer(),
        [("Alice speaks", "en"), ("Noticias de Bogotá", "es")],
    )

    assert calls == [(["Alice speaks", "Noticias de Bogotá"], 8)]
    assert result == [
        [{"name": "Alice", "type": "PERSON"}],
        [{"name": "Bogotá", "type": "LOC"}],
    ]


def test_hf_ner_batch_failure_degrades_to_per_headline_calls():
    pipeline = _reload_pipeline("on")
    calls = []

    class BatchRejectingNer:
        def __call__(self, value, **kwargs):
            calls.append(value)
            if isinstance(value, list):
                raise RuntimeError("batch rejected")
            return [{"entity_group": "ORG", "word": value.split()[0]}]

    result = pipeline._extract_entities_hf_batch(
        BatchRejectingNer(),
        [("Atlas publishes", "en"), ("Reuters reports", "en")],
    )

    assert calls == [
        ["Atlas publishes", "Reuters reports"],
        "Atlas publishes",
        "Reuters reports",
    ]
    assert result == [
        [{"name": "Atlas", "type": "ORG"}],
        [{"name": "Reuters", "type": "ORG"}],
    ]


def test_ner_phase_groups_transformer_rows_before_inference():
    pipeline = _reload_pipeline("on")
    source = inspect.getsource(pipeline._run_ner_phase)

    assert "hf_rows.append(row)" in source
    assert "cyrillic_rows.append(row)" in source
    assert "_extract_entities_hf_batch(" in source


def test_ner_phase_emits_route_counts_and_measured_duration():
    pipeline = _reload_pipeline("on")
    source = inspect.getsource(pipeline._run_ner_phase)

    assert "time.monotonic()" in source
    assert "spacy=%d, primary_hf=%d, cyrillic_hf=%d, duration=%.2fs" in source


def test_ner_phase_has_an_independent_bounded_work_budget(monkeypatch):
    pipeline = _reload_pipeline("on")
    monkeypatch.setattr(pipeline, "NER_LIMIT", 1200)

    assert pipeline._ner_phase_limit(300) == 1200
    monkeypatch.setattr(pipeline, "NER_LIMIT", 0)
    assert pipeline._ner_phase_limit(300) == 300


def test_local_fleet_sets_measured_ner_budget_without_expanding_other_phases():
    source = Path("../scripts/run-nlp-fleet-local.sh").read_text(encoding="utf-8")

    assert 'NLP_FLEET_WORKER_LIMIT="${ATLAS_NLP_LIMIT:-300}"' in source
    assert 'NLP_NER_LIMIT="${ATLAS_NLP_NER_LIMIT:-1200}"' in source
    assert 'NLP_NER_BATCH_SIZE="${ATLAS_NLP_NER_BATCH_SIZE:-16}"' in source


# ── _columns target routing ──────────────────────────────────────────────────
def test_columns_target_production_in_off_mode():
    pipeline = _reload_pipeline("off")
    cols = pipeline._columns()
    assert cols["sentiment_target"] == "nlp_sentiment"
    assert cols["framing_target"] == "nlp_framing"
    assert cols["persons_target"] == "nlp_persons"


def test_columns_target_shadow_in_shadow_mode():
    pipeline = _reload_pipeline("shadow")
    cols = pipeline._columns()
    assert cols["sentiment_target"] == "nlp_sentiment_xlm"
    assert cols["framing_target"] == "nlp_framing_xlm"
    assert cols["persons_target"] == "nlp_persons_xlm"


def test_columns_target_production_in_on_mode():
    pipeline = _reload_pipeline("on")
    cols = pipeline._columns()
    assert cols["sentiment_target"] == "nlp_sentiment"


def test_sentiment_phase_marks_production_writes_as_transformer():
    pipeline = _reload_pipeline("on")
    source = inspect.getsource(pipeline._run_sentiment_phase)

    assert "nlp_method=$6" in source
    assert 'method = None if _shadow_writes() else "transformer"' in source


# ── Sentiment mapping ────────────────────────────────────────────────────────
def test_map_sentiment_returns_signed_score_and_confidence():
    pipeline = _reload_pipeline("on")
    score, conf = pipeline._map_sentiment([
        {"label": "positive", "score": 0.8},
        {"label": "neutral", "score": 0.15},
        {"label": "negative", "score": 0.05},
    ])
    assert score == pytest.approx(0.8 * 5.0 + 0.05 * -5.0, rel=1e-3)
    assert conf == pytest.approx(0.8)


def test_map_sentiment_handles_negative_dominant():
    pipeline = _reload_pipeline("on")
    score, conf = pipeline._map_sentiment([
        {"label": "negative", "score": 0.92},
        {"label": "neutral", "score": 0.06},
        {"label": "positive", "score": 0.02},
    ])
    assert score < 0
    assert conf == pytest.approx(0.92)


# ── Priority SQL ─────────────────────────────────────────────────────────────
def test_priority_sql_orders_by_age_minus_language_boost():
    pipeline = _reload_pipeline("on")
    sql = pipeline._priority_select_sql("nlp_processed_at")
    # Spot-check that priority components are present.
    assert "nlp_processed_at IS NULL" in sql
    assert "source_lang" in sql
    assert "source_family" in sql
    assert "geo_confidence" in sql
    assert "ORDER BY" in sql
    assert "LIMIT $1" in sql


def test_priority_sql_allocates_hot_lane_before_sample_and_backlog():
    pipeline = _reload_pipeline("on")
    sql = pipeline._priority_select_sql("nlp_processed_at")

    assert "hot_lane AS" in sql
    assert "sample_lane AS" in sql
    assert "backlog_lane AS" in sql
    assert sql.index("hot_lane AS") < sql.index("sample_lane AS") < sql.index("backlog_lane AS")
    assert "0.65" in sql
    assert "0.25" in sql
    assert "0.10" in sql
    assert "created_at > NOW() - INTERVAL '24 hours'" in sql
    assert "created_at <= NOW() - INTERVAL '24 hours'" in sql


def test_priority_sql_targets_correct_column_for_phase():
    pipeline = _reload_pipeline("on")
    sentiment_sql = pipeline._priority_select_sql("nlp_processed_at")
    persons_sql = pipeline._priority_select_sql("nlp_persons")
    framing_sql = pipeline._priority_select_sql("nlp_framing")
    assert "nlp_processed_at IS NULL" in sentiment_sql
    assert "nlp_persons IS NULL" in persons_sql
    assert "nlp_framing IS NULL" in framing_sql


def test_stratified_refresh_sql_targets_requested_column_and_is_bounded():
    pipeline = _reload_pipeline("shadow")
    sql = pipeline._stratified_refresh_sql("nlp_processed_at_xlm")

    assert "nlp_processed_at_xlm IS NULL" in sql
    assert "nlp_processed_at IS NULL" not in sql
    assert "recent_pool AS" in sql
    assert "LIMIT 75000" in sql
    assert "PARTITION BY" in sql
    assert "source_family" in sql
    assert "signal_class" in sql


def test_shadow_mode_has_created_at_indexes_for_worker_priority():
    migration = (
        os.path.dirname(os.path.dirname(__file__))
        + "/migrations/023_nlp_shadow_priority_indexes.sql"
    )
    with open(migration, encoding="utf-8") as f:
        sql = f.read()

    assert "idx_signals_v2_nlp_xlm_unprocessed_created_at" in sql
    assert "idx_signals_v2_nlp_xlm_unprocessed_recent" in sql
    assert "WHERE nlp_processed_at_xlm IS NULL" in sql
    assert "created_at ASC" in sql
    assert "created_at DESC" in sql


def test_sample_queue_cleanup_is_batched_and_exists_based():
    pipeline = _reload_pipeline("on")
    sql = pipeline.CLEANUP_DRAINED_SAMPLE_QUEUE_SQL
    assert "WITH candidates AS" in sql
    assert "drained AS" in sql
    assert "FROM candidates c" in sql
    assert "JOIN signals_v2 s ON s.id = c.id" in sql
    assert "LIMIT $1" in sql
    # Orphans: queue rows whose signal was retention-deleted never match the
    # drained JOIN and would accumulate forever — the cleanup must also purge
    # ids with no signals_v2 row, inside the same batched candidate window.
    assert "orphaned AS" in sql
    assert "NOT EXISTS" in sql
    assert "DELETE FROM nlp_sample_queue q" in sql
    assert "USING removable d" in sql
    assert "WHERE q.id = d.id" in sql
    assert pipeline.SAMPLE_CLEANUP_LIMIT == 500
    assert pipeline.SAMPLE_CLEANUP_TIMEOUT_SECONDS == 10
