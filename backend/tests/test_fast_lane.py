from __future__ import annotations

import importlib
import inspect

from pathlib import Path

from enrichment.fast_lane import FAST_NEUTRAL_CONFIDENCE, SELECT_SQL, classify_fast_lane


def test_fast_lane_uses_lexicon_when_headline_has_signal():
    decision = classify_fast_lane("Deadly attack kills civilians in border town", "en")

    assert decision.method == "lexicon"
    assert decision.confidence > 0


def test_fast_lane_neutral_fallback_is_low_confidence_and_explicit():
    decision = classify_fast_lane("Committee publishes regular weekly meeting agenda", "en")

    assert decision.method == "fast_neutral"
    assert decision.sentiment == 0
    assert decision.confidence == FAST_NEUTRAL_CONFIDENCE


def test_fast_lane_update_does_not_set_transformer_processed_at():
    import enrichment.fast_lane as fast_lane

    fast_lane = importlib.reload(fast_lane)

    assert "nlp_processed_at" not in fast_lane.UPDATE_SQL
    assert "AND nlp_method IS NULL" in fast_lane.UPDATE_SQL


def test_fast_lane_selector_matches_pending_method_index():
    migration = Path("migrations/027_fast_lane_nlp_method_index.sql").read_text(encoding="utf-8")

    assert "WHERE nlp_method IS NULL" in SELECT_SQL
    assert "created_at > NOW()" in SELECT_SQL
    assert "idx_signals_v2_fast_lane_pending_created_at" in migration
    assert "WHERE nlp_method IS NULL" in migration
    assert "ON signals_v2 (created_at DESC)" in migration


def test_nlp_worker_runs_fast_lane_before_transformer():
    import enrichment.nlp_worker as worker

    worker = importlib.reload(worker)
    source = inspect.getsource(worker._one_cycle)

    assert "run_fast_lane" in source
    assert source.index("run_fast_lane") < source.index("run_nlp_enrichment")
    assert "FAST_LANE_ENABLED" in source
