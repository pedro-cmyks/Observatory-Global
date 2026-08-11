from datetime import datetime, timezone

from app.services.country_edition import (
    CONTRACT,
    SLOT_GUARD_CONTRACT,
    build_article_enrichment,
    build_country_edition_payload,
    filter_edition_slots,
    gather_receipt_urls,
    slot_guard_enabled,
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
    monkeypatch.setattr(ce.db, "pool", None)
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

    monkeypatch.setattr(ce.db, "pool", _Pool())
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


# ── slot guard (council R4 N17, 2026-08-11) ───────────────────────────────────
# Colombia's edition led with 'Japan Earthquake Traps Shoppers' — court
# ENTAILED, subject-geo VERIFIED ['CO'], 95 signals — while all of its receipts
# read 'terremoto 7,4 sacude Colombia'. The slotter admitted a thread whose own
# receipts contradict its label text, on the country door where the lie is
# loudest. The guard excludes it from THIS country's sections only; the thread
# is never demoted globally.
_N17_THREAD = {
    "thread_id": "dynamic-topic-8597",
    "label": "Japan Earthquake Traps Shoppers",
    "evidence_samples": [
        {"headline": "Terremoto de magnitud 7.4 sacudió gran parte de Colombia",
         "url": "http://a"},
        {"headline": "Potente sismo de 7,4 sacude a Colombia (VER IMÁGENES)",
         "url": "http://b"},
        {"headline": "Sismo de 7.4 sacude Colombia", "url": "http://c"},
    ],
}
_HONEST_CO_THREAD = {
    "thread_id": "dynamic-topic-1",
    "label": "Colombia Earthquake Rescue Effort",
    "evidence_samples": [
        {"headline": "Sismo de 7.4 sacude Colombia", "url": "http://d"},
        {"headline": "Rescatistas trabajan en Colombia tras el terremoto", "url": "http://e"},
        {"headline": "Colombia: al menos 22 muertos por el terremoto", "url": "http://f"},
    ],
}


def test_slot_guard_excludes_the_n17_witness_from_the_co_edition():
    kept, guard = filter_edition_slots([_N17_THREAD, _HONEST_CO_THREAD], "CO")
    assert [t["thread_id"] for t in kept] == ["dynamic-topic-1"]
    assert guard["excluded"] == 1
    assert guard["contract"] == SLOT_GUARD_CONTRACT
    (row,) = guard["exclusions"]
    assert row["thread_id"] == "dynamic-topic-8597"
    assert row["label_country"] == "JP"
    assert row["edition_country"] == "CO"
    assert row["reason_code"] == "label_country_contradicts_edition_slot"
    # counted AND named — the payload can show why the row is missing
    assert "label says Japan (JP); receipts 3/3 CO" in row["reason"]


def test_slot_guard_keeps_a_thread_whose_label_matches_the_edition():
    kept, guard = filter_edition_slots([_HONEST_CO_THREAD], "CO")
    assert kept == [_HONEST_CO_THREAD]
    assert guard["excluded"] == 0
    assert guard["exclusions"] == []


def test_slot_guard_keeps_a_foreign_label_whose_own_receipts_support_it():
    # a genuine Venezuela story carried by Colombian press: the label is not
    # lying about its receipts, so this is an editorial question, not a defect
    # — the guard must not empty the door of real foreign coverage.
    thread = {
        "thread_id": "dynamic-topic-2",
        "label": "Venezuela Border Crossing Closure",
        "evidence_samples": [
            {"headline": "Venezuela cierra el paso fronterizo de Cucuta"},
            {"headline": "Caracas anuncia el cierre de la frontera con Colombia"},
            {"headline": "Venezuela mantiene cerrada la frontera"},
        ],
    }
    kept, guard = filter_edition_slots([thread], "CO")
    assert kept == [thread]
    assert guard["excluded"] == 0


def test_slot_guard_skips_multi_country_and_geoless_labels():
    threads = [
        {"thread_id": "a", "label": "Russia Sanctions and Ukraine War Updates",
         "evidence_samples": [{"headline": "Sismo de 7.4 sacude Colombia"},
                              {"headline": "Terremoto en Colombia deja heridos"},
                              {"headline": "Colombia: sismo de 7,4"}]},
        {"thread_id": "b", "label": "Global Markets Rally",
         "evidence_samples": [{"headline": "Sismo de 7.4 sacude Colombia"},
                              {"headline": "Terremoto en Colombia deja heridos"},
                              {"headline": "Colombia: sismo de 7,4"}]},
        {"thread_id": "c", "label": "Trump Tariffs Escalate",
         "evidence_samples": [{"headline": "Sismo de 7.4 sacude Colombia"},
                              {"headline": "Terremoto en Colombia deja heridos"},
                              {"headline": "Colombia: sismo de 7,4"}]},
    ]
    kept, guard = filter_edition_slots(threads, "CO")
    assert len(kept) == 3
    assert guard["excluded"] == 0


def test_slot_guard_abstains_on_the_syros_case_and_says_so():
    # dt-4071 'Syros Rescuer Murder Suspect Remanded' serves on the SY edition
    # because its signals are country-tagged SY. Neither the label nor its
    # Greek receipts resolve to a country in the shared lexicons/gazetteer, so
    # the guard ABSTAINS rather than guessing — pinned as the honest limit,
    # not a silent gap.
    thread = {
        "thread_id": "dynamic-topic-4071",
        "label": "Syros Rescuer Murder Suspect Remanded",
        "evidence_samples": [
            {"headline": "Σύρος: Προσωρινά κρατούμενος στις φυλακές Χίου ο 41χρονος"},
            {"headline": "Σύρος: Προφυλακίστηκε ο δράστης της ανθρωποκτονίας"},
            {"headline": "Σύρος: Ενώπιον του Συμβουλίου Πλημμελειοδικών σήμερα"},
        ],
    }
    kept, guard = filter_edition_slots([thread], "SY")
    assert kept == [thread]
    assert guard["excluded"] == 0


def test_slot_guard_catches_the_syros_class_when_geography_is_detectable():
    thread = {
        "thread_id": "dynamic-topic-9",
        "label": "Greek Island Rescuer Murder Trial",
        "evidence_samples": [
            {"headline": "Damascus court remands suspect over Syria paramedic killing"},
            {"headline": "Syria paramedic murder: suspect appears before Damascus judges"},
            {"headline": "Syrian rescuer killing — Damascus prosecutors seek detention"},
        ],
    }
    kept, guard = filter_edition_slots([thread], "SY")
    assert kept == []
    assert guard["exclusions"][0]["label_country"] == "GR"


def test_slot_guard_folds_subject_country_aliases_for_the_edition_code():
    # GZ/WE fold to PS in the shared detector; a 'Gaza …' label on the PS
    # edition is the SAME country, never a contradiction
    thread = {
        "thread_id": "dynamic-topic-3",
        "label": "Gaza Aid Convoy Blocked",
        "evidence_samples": [
            {"headline": "Sismo de 7.4 sacude Colombia"},
            {"headline": "Terremoto en Colombia deja heridos"},
            {"headline": "Colombia: sismo de 7,4 deja daños"},
        ],
    }
    kept, guard = filter_edition_slots([thread], "PS")
    assert kept == [thread] and guard["excluded"] == 0
    # ...and the same label on an unrelated edition, contradicted by its own
    # receipts, is excluded
    assert filter_edition_slots([thread], "CO")[1]["excluded"] == 1


def test_slot_guard_kill_switch_off_keeps_every_thread(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_EDITION_SLOT_GUARD", "off")
    assert slot_guard_enabled() is False
    kept, guard = filter_edition_slots([_N17_THREAD, _HONEST_CO_THREAD], "CO")
    assert len(kept) == 2
    assert guard["enabled"] is False
    assert guard["excluded"] == 0


def test_slot_guard_defaults_on(monkeypatch):
    monkeypatch.delenv("ATLAS_COUNTRY_EDITION_SLOT_GUARD", raising=False)
    assert slot_guard_enabled() is True


def test_slot_guard_handles_empty_and_malformed_threads():
    kept, guard = filter_edition_slots([], "CO")
    assert kept == [] and guard["excluded"] == 0
    kept, _ = filter_edition_slots([{"thread_id": "x"}, {}], "CO")
    assert len(kept) == 2


def test_payload_carries_the_slot_guard_block():
    gen = datetime(2026, 8, 11, tzinfo=timezone.utc)
    _, guard = filter_edition_slots([_N17_THREAD], "CO")
    payload = build_country_edition_payload(
        country="CO", country_name="Colombia", ranked_threads=[],
        enrichment=build_article_enrichment([], []), coverage_gaps=[],
        generated_at=gen, window_hours=24, slot_guard=guard,
    )
    assert payload["slot_guard"]["excluded"] == 1
    assert payload["slot_guard"]["exclusions"][0]["thread_id"] == "dynamic-topic-8597"


def test_payload_slot_guard_defaults_to_an_honest_empty_block():
    gen = datetime(2026, 8, 11, tzinfo=timezone.utc)
    payload = build_country_edition_payload(
        country="CO", country_name="Colombia", ranked_threads=[],
        enrichment=build_article_enrichment([], []), coverage_gaps=[],
        generated_at=gen, window_hours=24,
    )
    assert payload["slot_guard"]["excluded"] == 0
    assert payload["slot_guard"]["exclusions"] == []


def test_slot_guard_residual_actor_label_is_excluded_and_named():
    # KNOWN RESIDUAL, pinned so it is never a silent gap: dt-3469 'Ukraine
    # Strikes Wildberries Warehouses' names the ACTOR country while its
    # receipts name where the drones landed. The court clears this class by
    # widening its absence pool to 40 receipts; this door has only the
    # receipts in its payload and must not grow queries (it already 503s on
    # cold open, council R4 N26). The row is withheld from ONE door, counted
    # and NAMED — never silently dropped, and one env var reverts it.
    thread = {
        "thread_id": "dynamic-topic-3469",
        "label": "Ukraine Strikes Wildberries Warehouses",
        "evidence_samples": [
            {"headline": "На порятунок Wildberries Росії може знадобитися трильйон"},
            {"headline": "Wildberries у Росії — удари дронів змушують Кремль шукати план"},
            {"headline": "Склади Wildberries у Росії горять після атаки дронів"},
        ],
    }
    kept, guard = filter_edition_slots([thread], "RU")
    assert kept == []
    (row,) = guard["exclusions"]
    assert row["label_country"] == "UA" and row["dominant_receipt_country"] == "RU"
    assert "label says Ukraine (UA); receipts 3/3 RU" in row["reason"]
