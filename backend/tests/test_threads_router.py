from __future__ import annotations

from pathlib import Path


ROUTER_SOURCE = Path("app/routers/threads.py").read_text(encoding="utf-8")
MAIN_SOURCE = Path("app/main_v2.py").read_text(encoding="utf-8")


def test_threads_router_exposes_beta_collection_endpoint():
    assert '@router.get("/threads")' in ROUTER_SOURCE
    assert '"contract": "living-narrative-threads-v0"' in ROUTER_SOURCE
    # N15: the served page is captured once so meta.stamped_counts is computed
    # over EXACTLY the rows being returned.
    assert "threads = await fetch_threads(" in ROUTER_SOURCE
    assert '"threads": threads' in ROUTER_SOURCE
    assert "country_codes=[country] if country else None" in ROUTER_SOURCE


def test_threads_router_serves_stamped_counts_meta():
    """N15 fold-coverage observability: every /threads response carries a Label
    Court verdict census of the served page, so per-request fold coverage is
    measurable (the weekly read greps it)."""
    assert '"meta": {"stamped_counts": stamped_counts(threads)}' in ROUTER_SOURCE


def test_threads_router_exposes_beta_detail_endpoint():
    assert '@router.get("/threads/{thread_id}")' in ROUTER_SOURCE
    assert "await fetch_thread_detail(thread_id=thread_id, hours=hours)" in ROUTER_SOURCE
    assert 'HTTPException(status_code=404, detail="Thread not found")' in ROUTER_SOURCE


def test_main_registers_threads_router():
    assert "nlp_corrections, threads" in MAIN_SOURCE
    assert "app.include_router(threads.router)" in MAIN_SOURCE


def test_threads_router_caches_responses_in_redis():
    """Hot path: scoped CTE on signal_topic_assignments JOIN signals_v2 takes
    ~700 ms on production-sized 24h windows. Cache the assembled payload so
    repeat hits (Brief prefetch, frontend polling) skip the JOIN."""
    assert "THREADS_CACHE_TTL" in ROUTER_SOURCE
    assert "DETAIL_CACHE_TTL" in ROUTER_SOURCE
    assert "_cache_get" in ROUTER_SOURCE
    assert "_cache_set" in ROUTER_SOURCE
    # Both endpoints must check cache before doing the DB hit.
    assert 'cache_key = f"threads:list:' in ROUTER_SOURCE
    assert 'cache_key = f"threads:detail:' in ROUTER_SOURCE
