from __future__ import annotations

from pathlib import Path


ROUTER_SOURCE = Path("app/routers/threads.py").read_text(encoding="utf-8")
MAIN_SOURCE = Path("app/main_v2.py").read_text(encoding="utf-8")


def test_threads_router_exposes_beta_collection_endpoint():
    assert '@router.get("/threads")' in ROUTER_SOURCE
    assert '"contract": "living-narrative-threads-v0"' in ROUTER_SOURCE
    assert '"threads": await fetch_threads(hours=hours, limit=limit)' in ROUTER_SOURCE


def test_threads_router_exposes_beta_detail_endpoint():
    assert '@router.get("/threads/{thread_id}")' in ROUTER_SOURCE
    assert "await fetch_thread_detail(thread_id=thread_id, hours=hours)" in ROUTER_SOURCE
    assert 'HTTPException(status_code=404, detail="Thread not found")' in ROUTER_SOURCE


def test_main_registers_threads_router():
    assert "nlp_corrections, threads" in MAIN_SOURCE
    assert "app.include_router(threads.router)" in MAIN_SOURCE
