"""Source-contract tests for the story siblings router (no DB fixture exists;
mirror tests/test_query_thread_router_contract.py's approach)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = (ROOT / "app" / "routers" / "story.py").read_text()
MAIN = (ROOT / "app" / "main_v2.py").read_text()
RATE = (ROOT / "app" / "rate_limit.py").read_text()


def test_registered_in_main():
    assert re.search(r"from app\.routers import .*\bstory\b", MAIN) or "routers.story" in MAIN
    assert "app.include_router(story.router)" in MAIN


def test_paid_bucket_rule():
    assert re.search(r"story/\[?\^?/?\]?\+?/siblings", RATE) or "/api/v2/story/" in RATE


def test_full_path_and_contract():
    assert '@router.get("/api/v2/story/{thread_id}/siblings")' in ROUTER
    assert "story-siblings-v1" in ROUTER


def test_membership_scoping_verbatim():
    # country receipts must scope topic_members exactly (2026-07-27 bug class)
    assert "role = 'evidence'" in ROUTER
    assert "engine_version = 'v1-compat'" in ROUTER
    assert "quarantined IS NOT TRUE" in ROUTER


def test_honest_degrade_never_cached():
    assert "db.pool is None" in ROUTER
    assert "setex" in ROUTER
    # the degraded branch returns before any setex call
    degraded = ROUTER.index("db.pool is None")
    assert ROUTER.index("setex") > degraded


def test_statement_timeout_set():
    assert "SET statement_timeout" in ROUTER
