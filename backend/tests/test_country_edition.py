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
