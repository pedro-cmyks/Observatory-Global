"""Tests for the interim per-IP rate limiter (app/rate_limit.py)."""
from __future__ import annotations

import re

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
def test_paid_bucket_holds_only_genuinely_costly_calls():
    """W4: `paid` protects what COSTS — an LLM pass, an outbound fetch, an
    embed. Everything here bills real money or real external work per call."""
    mw = _mw()
    for path in (
        "/api/v2/research/plan",                     # query embed (embed service)
        "/api/v2/research/articles/fetch",           # outbound HTTP per URL
        "/api/v2/research/articles/read",            # DeepSeek grounded pass
        "/api/v2/research/articles/crossread",       # DeepSeek cross-read
        "/api/v2/research/leads",                    # pool + LLM-adjacent
        "/api/v2/theme/dynamic-topic-9/insight",     # LLM insight
        "/api/v2/briefing/insight",                  # LLM insight
        "/api/v2/dossier/synthesize",                # LLM synthesis
        "/api/v2/dossier/corroborate",               # LLM + external corpora
        "/api/v2/dossier/corroborate/start",         # same, async start
        "/api/v2/corroborate",                       # DOC 2.0 + embeds
    ):
        bucket, _ = mw._bucket_for(_req(path), path)
        assert bucket == "paid", path


def test_llm_endpoints_that_used_to_ride_the_generous_bucket_are_paid_now():
    """The inverse of the reader bug: real LLM POSTs sat on `global`
    (600/60s) while a 1s artifact read sat on `paid` (20/300s)."""
    mw = _mw()
    for path in ("/api/v2/dossier/synthesize", "/api/v2/corroborate"):
        _, (max_hits, window) = mw._bucket_for(_req(path), path)
        assert (max_hits, window) == (20, 300), path


def test_corroborate_status_poll_is_not_paid():
    # The job STATUS poll is a cheap lookup the client repeats while the paid
    # job runs; bucketing it with the job itself would throttle the wait.
    mw = _mw()
    path = "/api/v2/dossier/corroborate/status/abc-123"
    assert mw._bucket_for(_req(path), path)[0] != "paid"


# ── the reader's own lane (W4) ─────────────────────────────────────────────
def test_reader_reads_are_not_paid():
    """MEASURED 2026-08-13 against prod, all three are DB/cache reads with no
    LLM and no outbound call:

      /country-edition       0.76-1.12s  (mig 098 artifact, one indexed read)
      /attention/eclipse     0.41s       (Redis 300s; ~24s only on a cold miss)
      /signal/{id}/context   3.3-6.7s    (pgvector kNN)

    They were on `paid` (20/300s) while /api/v2/briefing (10.4s) and
    /api/v2/theme/{id} (8.2s) rode `global` (600/60s) — the tightest bucket
    held the cheapest requests. That inversion is the reader-facing bug."""
    mw = _mw()
    for path in (
        "/api/v2/country-edition",
        "/api/v2/attention/eclipse",
        "/api/v2/signal/123/context",
    ):
        assert mw._bucket_for(_req(path), path)[0] == "read", path


def test_read_bucket_covers_a_measured_heavy_reading_session():
    """Sizing math, not a guess. A heavy tour inside one 300s window:
    10 country doors + a retry each (20) + 4 open tabs polling eclipse every
    240s (8) + a story's signal-context (1) = 29 reads. The cap must clear
    that with headroom, and the window must be the 300s the readers' 429
    message quotes."""
    mw = _mw()
    _, (max_hits, window) = mw._bucket_for(_req("/api/v2/country-edition"), "/api/v2/country-edition")
    assert window == 300
    assert max_hits >= 60


def test_read_bucket_is_still_bounded_and_tighter_than_global():
    """The API is still open — every lane keeps a ceiling. At the cap the
    read bucket costs ~90 x 1.0s = 90 connection-seconds per 300s = 0.3 of a
    single pool connection (pool=10), so one IP at full tilt takes ~3% of the
    pool."""
    mw = _mw()
    _, read_limit = mw._bucket_for(_req("/api/v2/country-edition"), "/api/v2/country-edition")
    read_rate = read_limit[0] / read_limit[1]
    global_rate = mw.global_limit[0] / mw.global_limit[1]
    assert read_rate < global_rate
    assert read_limit[0] < 1000  # finite, not a disguised bypass


# ── per-item micro-LLM (translation) ──────────────────────────────────────
def test_translate_is_its_own_micro_llm_bucket():
    """Translation is an LLM call, but a MICRO one (~30 in / ~35 out tokens,
    ~$0.00002) that is server-cached per (signal_id, lang) and fires N times
    per rendered page, automatically. Sharing the 20/300s action bucket with
    dossier synthesis is a category error in both directions."""
    mw = _mw()
    for path in ("/api/v2/translate", "/api/v2/translate/batch", "/api/v2/translate/text"):
        assert mw._bucket_for(_req(path), path)[0] == "micro_llm", path


def test_micro_llm_bucket_covers_translate_all_on_a_full_brief():
    """MEASURED on the 2026-08-13 prod payload: 83 receipts across the Brief's
    10 stories are translate-eligible, and 'Translate all' fires every one of
    them. A cap below that turns the control into the silent no-op W3 chases."""
    mw = _mw()
    _, (max_hits, window) = mw._bucket_for(_req("/api/v2/translate"), "/api/v2/translate")
    assert window == 300
    assert max_hits >= 83


def test_micro_llm_bucket_is_bounded_by_spend():
    """At the cap, worst case (100% cache misses) is max_hits x ~65 tokens.
    Keep the ceiling where a full-tilt IP costs cents/day, not dollars/hour."""
    mw = _mw()
    _, (max_hits, _window) = mw._bucket_for(_req("/api/v2/translate"), "/api/v2/translate")
    assert max_hits <= 300


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


def test_every_bucket_keeps_a_finite_ceiling():
    """Abuse posture is unchanged: re-bucketing moves cheap reads to a looser
    lane, it never removes the lane."""
    mw = _mw()
    for name, (max_hits, window) in mw.limits.items():
        assert max_hits >= 1 and window >= 1, name
        assert max_hits < 10000, name


# ── the re-judge's witness, as a regression test ──────────────────────────
# docs/research/gold/2026-08-13-brief-rejudge.md: a reader searched Nigeria on
# /brief, the header rendered its counts and the body said "the door did not
# answer"; the retry failed identically. Replayed against prod 2026-08-13 the
# session made 21 `paid` requests against a 20/300s cap and the 21st — the NG
# country-edition retry — came back 429 while every `global` call (briefing
# 10.4s, theme 8.2s, siblings 6.4s) sailed through.
JUDGE_SESSION = [
    # /brief load
    ("/api/v2/briefing", ""),
    ("/api/v2/briefing/insight", ""),
    ("/api/v2/investigation/daily-publication", ""),
    ("/api/v2/attention/eclipse", ""),          # BriefNewspaper
    ("/api/v2/attention/eclipse", ""),          # EclipseModeContext
    ("/api/v2/delight", ""),
    *[("/api/v2/translate", "")] * 3,           # auto-fire on non-English receipts
    # search Nigeria
    ("/api/v2/search/unified", ""),
    ("/api/v2/search/unified", ""),
    # country door NG
    ("/api/v2/nodes", ""),
    ("/api/v2/threads", ""),
    ("/api/v2/country-edition", ""),
    # scrolling the sections
    *[("/api/v2/translate", "")] * 6,
    # opening a story
    ("/api/v2/theme/dynamic-topic-11877", ""),
    ("/api/v2/story/dynamic-topic-11877/siblings", ""),
    ("/api/v2/signal/17831605/context", ""),
    # translate all
    *[("/api/v2/translate", "")] * 3,
    ("/api/v2/translate/text", ""),
    # poll + second door + the retry that broke
    ("/api/v2/attention/eclipse", ""),
    ("/api/v2/country-edition", ""),
    ("/api/v2/country-edition", ""),            # <- the judge's retry
]


def test_the_judges_reading_session_never_hits_the_wall():
    mw = _mw()
    now = 0.0
    walls = []
    for path, query in JUDGE_SESSION:
        bucket, (max_hits, window) = mw._bucket_for(_req(path, query=query), path)
        if mw._hit(bucket, "reader", max_hits, window, now=now):
            walls.append((path, bucket))
        now += 5.0  # the whole session inside one 300s window (worst case)
    assert walls == [], f"reader hit the wall: {walls}"


def test_the_same_session_would_have_429d_under_the_old_all_paid_rules():
    """Guards the test above from being vacuously true: with the pre-W4 rules
    (country-edition + eclipse + signal-context + translate all on `paid`),
    the identical session 429s."""
    old_rules = [
        (re.compile(r"^/api/v2/country-edition$"), "paid", None),
        (re.compile(r"^/api/v2/attention/eclipse$"), "paid", None),
        (re.compile(r"^/api/v2/translate(?:/batch|/text)?$"), "paid", None),
        (re.compile(r"^/api/v2/briefing/insight$"), "paid", None),
        (re.compile(r"^/api/v2/signal/[^/]+/context$"), "paid", None),
    ]
    mw = RateLimitMiddleware(app=None, rules=old_rules)
    now, walls = 0.0, 0
    for path, query in JUDGE_SESSION:
        bucket, (max_hits, window) = mw._bucket_for(_req(path, query=query), path)
        if mw._hit(bucket, "reader", max_hits, window, now=now):
            walls += 1
        now += 5.0
    assert walls >= 1


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
