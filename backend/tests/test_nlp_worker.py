from __future__ import annotations

import importlib
import inspect


def test_low_volume_refresh_is_periodic_and_bounded():
    import enrichment.nlp_worker as worker

    worker = importlib.reload(worker)
    source = inspect.getsource(worker._one_cycle)

    assert "_should_refresh_stratified_sample(cycle_idx)" in source
    assert "asyncio.wait_for" in source
    assert "LOW_VOLUME_REFRESH_TIMEOUT_SECONDS" in source


def test_checkpoint_happens_before_optional_maintenance():
    import enrichment.nlp_worker as worker

    worker = importlib.reload(worker)
    source = inspect.getsource(worker._one_cycle)

    assert source.index("await _checkpoint") < source.index("await _maintenance")
    assert "maintenance_conn = await asyncpg.connect(db_url)" in source


def test_progress_metrics_avoids_full_table_filtered_aggregate():
    import enrichment.nlp_worker as worker

    worker = importlib.reload(worker)
    source = inspect.getsource(worker._progress_metrics)

    assert "COUNT(*) FILTER" not in source
    assert "timeout=5" in source
    assert "using previous estimate" in source


def test_sample_refresh_can_be_disabled_and_is_periodic(monkeypatch):
    import enrichment.nlp_worker as worker

    worker = importlib.reload(worker)

    monkeypatch.setattr(worker, "SAMPLE_REFRESH_EVERY_N_CYCLES", 0)
    assert worker._should_refresh_stratified_sample(1) is False
    assert worker._should_refresh_stratified_sample(180) is False

    monkeypatch.setattr(worker, "SAMPLE_REFRESH_EVERY_N_CYCLES", 180)
    assert worker._should_refresh_stratified_sample(1) is False
    assert worker._should_refresh_stratified_sample(179) is False
    assert worker._should_refresh_stratified_sample(180) is True
