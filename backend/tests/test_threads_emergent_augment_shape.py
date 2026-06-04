"""Query-shape guardrails for the emergent-cluster augment of /api/v2/threads.

`thread_intelligence.fetch_threads` was extended to merge atlas-anchored
threads with emergent-cluster threads sourced from the latest
`emergent_clusters` snapshot. `fetch_thread_detail` dispatches on the
`emergent-cluster-<id>` thread_id prefix to a parallel detail builder.

These tests freeze the structural decisions so a future edit cannot
silently break Narrative Threads on /app.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app" / "services" / "thread_intelligence.py"


def _src() -> str:
    return SERVICE.read_text(encoding="utf-8")


def test_emergent_thread_prefix_constant():
    """`EMERGENT_CLUSTER_THREAD_PREFIX` must be the literal
    'emergent-cluster-' since the detail dispatcher reads it."""
    source = _src()
    assert 'EMERGENT_CLUSTER_THREAD_PREFIX = "emergent-cluster-"' in source


def test_dynamic_topic_thread_prefix_constant():
    source = _src()
    assert 'DYNAMIC_TOPIC_THREAD_PREFIX = "dynamic-topic-"' in source


def test_dynamic_topic_fetcher_reads_active_dynamic_topics():
    source = _src()
    assert "async def _fetch_dynamic_threads_with_conn(" in source
    block = source[
        source.index("async def _fetch_dynamic_threads_with_conn("):
        source.index("async def _fetch_emergent_threads_with_conn(")
    ]
    assert "to_regclass('dynamic_topics')" in block
    assert "dynamic_topic_members" in block
    assert "dt.state = 'active'" in source
    assert "dt.noise_rate" in source


def test_assemble_emergent_thread_defined():
    source = _src()
    assert "def assemble_emergent_thread(" in source


def test_assemble_emergent_thread_emits_required_contract_fields():
    """The same fields as `assemble_thread` so NarrativeThreads renders
    both kinds uniformly."""
    source = _src()
    body_start = source.index("def assemble_emergent_thread(")
    body_end = source.index("_EMERGENT_SAMPLE_SIGNALS_SQL")
    body = source[body_start:body_end]
    required = [
        '"thread_id"',
        '"label"',
        '"summary"',
        '"anchor_topics"',
        '"signal_count"',
        '"source_count"',
        '"country_count"',
        '"avg_confidence"',
        '"first_seen"',
        '"changed_10h"',
        '"trend"',
        '"top_countries"',
        '"top_sources"',
        '"top_entities"',
        '"hourly_timeline"',
        '"source_mix"',
        '"quality"',
        '"confidence"',
        '"why_now"',
        '"evidence_samples"',
        '"narrative_note"',
    ]
    for key in required:
        assert key in body, f"emergent thread missing contract key {key}"


def test_emergent_fetcher_guards_missing_table():
    source = _src()
    fetcher_start = source.index("async def _fetch_emergent_threads_with_conn(")
    fetcher_end = source.index("async def _fetch_emergent_thread_detail(")
    block = source[fetcher_start:fetcher_end]
    assert "to_regclass('emergent_clusters')" in block
    assert "MAX(snapshot_at)" in block


def test_fetch_threads_merges_atlas_and_emergent():
    """Merged ranking by `signal_count` desc with the requested `limit`."""
    source = _src()
    merged_start = source.index("async def fetch_threads(")
    # Inner sort on signal_count is the merge contract.
    next_def = source.index("async def fetch_thread_detail(")
    block = source[merged_start:next_def]
    assert "_fetch_dynamic_threads_with_conn" in block
    assert "_fetch_emergent_threads_with_conn" in block
    assert "return dynamic[:limit]" in block
    assert "dynamic_topics is canonical when active rows exist" in block
    assert 'sort(key=lambda t: int(t.get("signal_count") or 0), reverse=True)' in block
    # Atlas-only when filtered by topic/country
    assert "is_atlas_filtered" in block


def test_fetch_thread_detail_dispatches_on_prefix():
    source = _src()
    detail_start = source.index("async def fetch_thread_detail(")
    block = source[detail_start:]
    assert "thread_id.startswith(DYNAMIC_TOPIC_THREAD_PREFIX)" in block
    assert "_fetch_dynamic_thread_detail" in block
    assert "thread_id.startswith(EMERGENT_CLUSTER_THREAD_PREFIX)" in block
    assert "_fetch_emergent_thread_detail" in block
