"""Tests for the interim per-IP rate limiter (app/rate_limit.py)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.rate_limit import RateLimitMiddleware, client_ip


def _req(path: str, headers: dict | None = None, query: str = "") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": ("1.2.3.4", 1234),
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


def _mw() -> RateLimitMiddleware:
    return RateLimitMiddleware(app=None)


# ── client_ip precedence (proxied via Vercel → real client is XFF-leftmost) ──
def test_client_ip_prefers_xff_leftmost_over_fly_header():
    # Fly-Client-IP is the Vercel egress here; the real client is XFF-leftmost.
    r = _req("/x", {"fly-client-ip": "9.9.9.9", "x-forwarded-for": "8.8.8.8, 9.9.9.9"})
    assert client_ip(r) == "8.8.8.8"


def test_client_ip_falls_back_to_fly_then_peer():
    # Direct-to-Fly hit (no proxy headers) uses Fly-Client-IP.
    assert client_ip(_req("/x", {"fly-client-ip": "9.9.9.9"})) == "9.9.9.9"
    # Nothing at all → peer.
    assert client_ip(_req("/x")) == "1.2.3.4"


# ── rule → bucket mapping ─────────────────────────────────────────────────
def test_paid_endpoints_map_to_paid_bucket():
    mw = _mw()
    for path in (
        "/api/v2/research/plan",
        "/api/v2/translate",
        "/api/v2/translate/batch",
        "/api/v2/theme/dynamic-topic-9/insight",
        "/api/v2/briefing/insight",
        "/api/v2/signal/123/context",
        "/api/v2/attention/eclipse",
    ):
        bucket, _ = mw._bucket_for(_req(path), path)
        assert bucket == "paid", path


def test_eclipse_endpoint_paid_bucket_tolerates_a_few_polling_tabs():
    # EclipseModeContext.tsx polls every 240s from every open tab at the same
    # default params; a handful of tabs mounting near-simultaneously plus one
    # poll cycle inside a 300s window should never 429 on the paid bucket.
    mw = _mw()
    bucket, (max_hits, window) = mw._bucket_for(_req("/api/v2/attention/eclipse"), "/api/v2/attention/eclipse")
    assert bucket == "paid"
    assert window == 300
    assert max_hits >= 12  # headroom above a plausible multi-tab burst (~6-8)


def test_external_depth_maps_to_slow_bucket():
    mw = _mw()
    path = "/api/v2/theme/election-legitimacy--CO/external-depth"
    assert mw._bucket_for(_req(path), path)[0] == "slow"


def test_anonymous_writes_map_to_write_bucket():
    mw = _mw()
    for path in ("/api/v2/telemetry", "/api/v2/research/events"):
        assert mw._bucket_for(_req(path), path)[0] == "write"


def test_thread_detail_only_paid_with_llm_flag():
    mw = _mw()
    path = "/api/v2/threads/dynamic-topic-9"
    assert mw._bucket_for(_req(path), path)[0] == "global"
    assert mw._bucket_for(_req(path, query="llm=1"), path)[0] == "paid"


def test_unmatched_path_is_global():
    mw = _mw()
    for path in ("/api/v2/threads", "/api/v2/briefing", "/api/v2/voice-mix"):
        assert mw._bucket_for(_req(path), path)[0] == "global"


# ── sliding window enforcement ────────────────────────────────────────────
def test_hit_enforces_max_then_resets_after_window():
    mw = _mw()
    assert mw._hit("global", "ip", 2, 60, now=100.0) is False
    assert mw._hit("global", "ip", 2, 60, now=101.0) is False
    assert mw._hit("global", "ip", 2, 60, now=102.0) is True   # over limit
    # window elapsed -> counter resets
    assert mw._hit("global", "ip", 2, 60, now=200.0) is False


def test_hit_is_per_ip_and_per_bucket():
    mw = _mw()
    assert mw._hit("paid", "a", 1, 60, now=1.0) is False
    assert mw._hit("paid", "a", 1, 60, now=2.0) is True
    assert mw._hit("paid", "b", 1, 60, now=2.0) is False   # different ip
    assert mw._hit("write", "a", 1, 60, now=2.0) is False  # different bucket


# ── integration: 429 + CORS ordering + bypasses ───────────────────────────
def _app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, global_limit=(2, 60))
    app.add_middleware(CORSMiddleware, allow_origins=["http://x"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/v2/thing")
    def thing():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def test_returns_429_after_limit_with_cors_header():
    client = TestClient(_app())
    h = {"origin": "http://x"}
    assert client.get("/api/v2/thing", headers=h).status_code == 200
    assert client.get("/api/v2/thing", headers=h).status_code == 200
    r = client.get("/api/v2/thing", headers=h)
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"
    # CORS must remain outermost so the 429 is readable cross-origin.
    assert r.headers.get("access-control-allow-origin") == "http://x"


def test_health_path_is_exempt():
    client = TestClient(_app())
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_options_preflight_bypasses_limit():
    client = TestClient(_app())
    for _ in range(5):
        r = client.options(
            "/api/v2/thing",
            headers={"origin": "http://x", "access-control-request-method": "GET"},
        )
        assert r.status_code != 429
