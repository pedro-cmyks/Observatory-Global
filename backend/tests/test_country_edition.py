from datetime import datetime, timezone

from app.services.country_edition import (
    CONTRACT,
    build_article_enrichment,
    build_country_edition_payload,
    gather_receipt_urls,
)


def test_gather_receipt_urls_dedupes_and_http_only():
    threads = [
        {"evidence_samples": [{"url": "http://a"}, {"url": "http://b"}, {"url": "http://a"}]},
        {"evidence_samples": [{"url": "http://c"}, {"url": "ftp://x"}, {"url": ""}]},
    ]
    assert gather_receipt_urls(threads, per_thread=4, cap=48) == [
        "http://a", "http://b", "http://c",
    ]


def test_gather_receipt_urls_per_thread_cap():
    threads = [{"evidence_samples": [{"url": f"http://{i}"} for i in range(10)]}]
    assert gather_receipt_urls(threads, per_thread=4, cap=48) == [
        "http://0", "http://1", "http://2", "http://3",
    ]


def test_gather_receipt_urls_total_cap():
    threads = [{"evidence_samples": [{"url": f"http://{i}"}]} for i in range(60)]
    assert len(gather_receipt_urls(threads, per_thread=4, cap=48)) == 48


def test_gather_receipt_urls_source_url_fallback():
    threads = [{"evidence_samples": [{"source_url": "http://z"}]}]
    assert gather_receipt_urls(threads) == ["http://z"]


def test_build_article_enrichment_yield_and_pending():
    urls = ["http://a", "http://b", "http://c"]
    states = [
        {"url": "http://a", "status": "ok", "excerpt": "x", "via": "live",
         "outlet": "A", "fetched_at": "t"},
        {"url": "http://b", "status": "pending"},
        {"url": "http://c", "status": "paywall"},
    ]
    enr = build_article_enrichment(urls, states)
    assert enr["contract"] == "country-edition-enrichment-v0"
    assert enr["yield"] == {"ok": 1, "attempted": 3, "pending": 1}
    assert enr["pending_urls"] == ["http://b"]
    assert enr["articles"]["http://a"]["excerpt"] == "x"
    assert enr["articles"]["http://a"]["status"] == "ok"


def test_build_article_enrichment_counts_queued_as_pending():
    urls = ["http://a"]
    states = [{"url": "http://a", "status": "queued"}]
    enr = build_article_enrichment(urls, states)
    assert enr["yield"]["pending"] == 1
    assert enr["pending_urls"] == ["http://a"]


def test_build_article_enrichment_empty():
    enr = build_article_enrichment([], [])
    assert enr["yield"] == {"ok": 0, "attempted": 0, "pending": 0}
    assert enr["pending_urls"] == []
    assert enr["articles"] == {}


def test_build_country_edition_payload_shape():
    gen = datetime(2026, 7, 21, tzinfo=timezone.utc)
    payload = build_country_edition_payload(
        country="CO",
        country_name="Colombia",
        ranked_threads=[{"thread_id": "t1"}],
        enrichment=build_article_enrichment([], []),
        coverage_gaps=[{"slug": "x", "label": "X", "raw_signals": 9,
                        "verified": 0, "scored": 9}],
        generated_at=gen,
        window_hours=24,
    )
    assert payload["contract"] == CONTRACT == "country-edition-v0"
    assert payload["country"] == "CO"
    assert payload["country_name"] == "Colombia"
    assert payload["threads"] == [{"thread_id": "t1"}]
    assert payload["coverage_gaps"][0]["slug"] == "x"
    assert payload["generated_at"] == "2026-07-21T00:00:00+00:00"
    assert payload["window_hours"] == 24


import pytest

import app.services.country_edition as ce


@pytest.mark.asyncio
async def test_fetch_country_edition_no_db_honest_empty(monkeypatch):
    monkeypatch.setattr(ce.db, "pool", None, raising=False)
    out = await ce.fetch_country_edition("co")
    assert out["contract"] == "country-edition-v0"
    assert out["country"] == "CO"                 # uppercased
    assert out["country_name"] == "CO"            # falls back to code, honest
    assert out["threads"] == []
    assert out["coverage_gaps"] == []
    assert out["article_enrichment"]["yield"]["attempted"] == 0


@pytest.mark.asyncio
async def test_fetch_country_edition_orchestrates(monkeypatch):
    async def fake_fetch_threads(**kwargs):
        assert kwargs["country_codes"] == ["CO"]
        return [{"thread_id": "t1", "label": "L1",
                 "evidence_samples": [{"url": "http://a"}]}]

    def fake_rank(threads):
        return threads

    async def fake_states(urls):
        return [{"url": "http://a", "status": "ok", "excerpt": "hi",
                 "via": "live", "outlet": "A", "fetched_at": "t"}]

    async def fake_enqueue(urls):
        return []

    class _Conn:
        async def fetchrow(self, *a):
            return {"name": "Colombia"}

        async def fetch(self, *a):
            return [{"slug": "labor", "label": "Labor strike",
                     "raw_signals": 12, "verified": 0, "scored": 12}]

    class _Acquire:
        async def __aenter__(self):
            return _Conn()

        async def __aexit__(self, *a):
            return False

    class _Pool:
        def acquire(self):
            return _Acquire()

    monkeypatch.setattr(ce.db, "pool", _Pool(), raising=False)
    monkeypatch.setattr(ce, "fetch_threads", fake_fetch_threads)
    monkeypatch.setattr(ce, "rank_threads", fake_rank)
    import app.services.article_fetch as af
    monkeypatch.setattr(af, "article_states", fake_states)
    monkeypatch.setattr(af, "enqueue_fetches", fake_enqueue)

    out = await ce.fetch_country_edition("co")
    assert out["country_name"] == "Colombia"
    assert out["threads"][0]["thread_id"] == "t1"
    assert out["coverage_gaps"][0]["slug"] == "labor"
    assert out["article_enrichment"]["yield"]["ok"] == 1
    assert out["article_enrichment"]["articles"]["http://a"]["excerpt"] == "hi"


@pytest.mark.asyncio
async def test_country_edition_handler_uppercases_and_delegates(monkeypatch):
    # app.routers.geo does `from app.main_v2 import app`, and app.main_v2
    # imports geo back (app.include_router(geo.router)) — importing geo
    # fresh (before main_v2 has been loaded) hits that circular import
    # mid-init and raises AttributeError on `geo.router`. Load main_v2
    # first (same fix used by tests/test_translate_text.py) so geo is
    # already fully initialized by the time we import it directly.
    import app.main_v2  # noqa: F401
    import app.routers.geo as geo

    async def fake(cc, hours=24):
        return {"contract": "country-edition-v0", "country": cc, "hours": hours}

    monkeypatch.setattr(
        "app.services.country_edition.fetch_country_edition", fake
    )
    monkeypatch.setattr(geo.app.state, "redis", None, raising=False)

    out = await geo.get_country_edition(cc="co")
    assert out["country"] == "CO"
    assert out["contract"] == "country-edition-v0"


@pytest.mark.asyncio
async def test_country_edition_handler_rejects_bad_cc(monkeypatch):
    import app.main_v2  # noqa: F401  (load first — geo<->main_v2 import cycle)
    import app.routers.geo as geo
    from fastapi import HTTPException

    monkeypatch.setattr(geo.app.state, "redis", None, raising=False)
    for bad in ("usa", "u", "1o", "co "):
        with pytest.raises(HTTPException):
            await geo.get_country_edition(cc=bad)
