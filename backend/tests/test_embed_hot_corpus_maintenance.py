"""Regression guards for safe HNSW maintenance in the local embed writer."""
from pathlib import Path
from types import SimpleNamespace

from app.services.research_semantic import _clear_device_cache


SCRIPT = Path(__file__).parents[1] / "scripts/embed_hot_corpus.py"


def test_bulk_reindex_rebuild_is_owned_by_outer_connection_finally():
    source = SCRIPT.read_text()

    assert "async def _rebuild_hnsw_index" in source
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
