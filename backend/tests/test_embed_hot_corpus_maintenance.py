"""Regression guards for safe ANN maintenance in the local embed writer."""
from pathlib import Path
from types import SimpleNamespace

from app.services.research_semantic import _clear_device_cache
from scripts.embed_hot_corpus import _ivfflat_list_count


SCRIPT = Path(__file__).parents[1] / "scripts/embed_hot_corpus.py"


def test_bulk_reindex_rebuild_is_owned_by_outer_connection_finally():
    source = SCRIPT.read_text()

    assert "async def _rebuild_ann_index" in source
    assert "index_dropped = False" in source
    assert "if index_dropped:" in source
    assert source.index("if index_dropped:") > source.index("finally:", source.index("async def main"))


def test_retention_sweep_happens_before_optional_index_drop():
    source = SCRIPT.read_text()

    sweep_at = source.index("DELETE FROM signal_embeddings WHERE embedded_at")
    drop_at = source.index("DROP INDEX IF EXISTS idx_signal_embeddings_vec")
    assert sweep_at < drop_at


def test_mps_cache_is_released_between_successful_batches():
    calls = []
    fake_torch = SimpleNamespace(mps=SimpleNamespace(empty_cache=lambda: calls.append("empty")))

    _clear_device_cache(fake_torch, "mps")
    _clear_device_cache(fake_torch, "cpu")

    assert calls == ["empty"]


def test_ivfflat_lists_follow_measured_sub_million_rule(monkeypatch):
    monkeypatch.delenv("ATLAS_IVFFLAT_LISTS", raising=False)
    assert _ivfflat_list_count(326_762) == 327
    assert _ivfflat_list_count(1) == 16

    monkeypatch.setenv("ATLAS_IVFFLAT_LISTS", "99999")
    assert _ivfflat_list_count(326_762) == 4096


def test_rebuild_uses_ivfflat_instead_of_hnsw_spill_path():
    source = SCRIPT.read_text()

    assert "USING ivfflat (vec halfvec_cosine_ops)" in source
    assert "USING hnsw (vec halfvec_cosine_ops)" not in source


def test_ivfflat_cutover_migration_is_idempotent_for_the_live_index():
    migration = (
        Path(__file__).parents[1] / "migrations/076_signal_embeddings_ivfflat.sql"
    ).read_text()

    assert "USING ivfflat (vec halfvec_cosine_ops)" in migration
    assert "indexdef ILIKE '%USING ivfflat%'" in migration
    assert "WITH (lists = 327)" in migration
