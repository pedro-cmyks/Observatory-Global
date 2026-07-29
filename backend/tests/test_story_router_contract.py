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


def test_invalid_id_short_circuits_before_db():
    # shape validation must run before any Redis/DB work
    assert "_TOPIC_ID_RE" in ROUTER
    assert ROUTER.index("invalid_thread_id") < ROUTER.index("db.pool is None")


def test_contract_violation_not_mislabeled_as_db_error():
    assert "except ValueError" in ROUTER
    assert "internal_error" in ROUTER


def test_unsupported_anchor_type_is_explicit():
    assert "unsupported_anchor_type" in ROUTER


def test_umbrella_resolution_present():
    # T10 follow-up (2026-07-29): /threads top rows are R2 umbrellas sharing
    # the dynamic-topic- prefix; the lens must resolve them via their largest
    # walkable child rather than 100%-missing the biggest stories.
    assert "parent_id" in ROUTER
    assert "is_umbrella" in ROUTER
    assert "umbrella_resolved_via_child" in ROUTER


def test_umbrella_child_excluded_from_siblings():
    assert "s.topic_key != child_key" in ROUTER


def test_normalize_thread_id_behavior():
    from app.routers.story import _normalize_thread_id
    assert _normalize_thread_id("dynamic-topic-5245") == "dynamic-topic-5245"
    assert _normalize_thread_id("disinformation-influence-operation--us-gb") == "disinformation-influence-operation"
    assert _normalize_thread_id("x" * 70) is None
    assert _normalize_thread_id("") is None
    assert _normalize_thread_id("a b") is None
    assert _normalize_thread_id("../etc/passwd") is None
