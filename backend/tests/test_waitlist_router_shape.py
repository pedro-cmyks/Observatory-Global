"""Source-string guardrails for the /api/v2/waitlist router, matching the
existing test_emergent_router_shape.py style (no live DB)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAITLIST_ROUTER = ROOT / "app" / "routers" / "waitlist.py"
MAIN = ROOT / "app" / "main_v2.py"


def _src() -> str:
    return WAITLIST_ROUTER.read_text(encoding="utf-8")


def test_post_endpoint_registered():
    assert '@router.post("/api/v2/waitlist")' in _src()


def test_count_endpoint_registered():
    assert '@router.get("/api/v2/waitlist/count")' in _src()


def test_honeypot_field_present():
    src = _src()
    assert "company" in src
    assert "honeypot" in src.lower()


def test_idempotent_insert():
    assert "ON CONFLICT" in _src()
    assert "DO NOTHING" in _src()


def test_count_is_aggregate_only():
    src = _src()
    assert "COUNT(*)" in src
    assert "SELECT email" not in src


def test_rate_limited_status_429():
    assert "429" in _src()


def test_table_guarded_with_to_regclass():
    assert "to_regclass('workbench_waitlist')" in _src()


def test_router_registered_in_main():
    main = MAIN.read_text(encoding="utf-8")
    assert "from app.routers import" in main or "import waitlist" in main
    assert "app.include_router(waitlist.router)" in main
