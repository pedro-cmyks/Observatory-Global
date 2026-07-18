"""Corroboration lane (council Phase 3a) — pure-math + degraded-contract tests.

Freezes: term extraction / DOC 2.0 query building, figure + official mirrors of
claimLedger.ts, the relation classifier (corroborates/contradicts/context), the
hot∪cold corpus query builder, dedup, the per-receipt verdict, and — the core
honesty requirement — the degraded-mode contract: a THROTTLED DOC 2.0 is
reported as such AND the Atlas-corpus matches still come back.

No network, no DB: every I/O boundary in corroborate_claim is injected.
"""
import pytest

from app.services import corroboration as c


class TestExtractClaimTerms:
    def test_significant_tokens_and_short_query(self):
        out = c.extract_claim_terms("Venezuela Earthquake Death Toll Rises")
        # stopwords stripped, order preserved, deduped
        assert out["terms"][:3] == ["venezuela", "earthquake", "death"]
        assert out["query"] == "venezuela earthquake death toll rises"

    def test_country_appended_only_when_query_short(self):
        out = c.extract_claim_terms("Ceasefire holds", country="SY")
        assert out["query"].endswith("sy")

    def test_country_not_appended_when_query_already_specific(self):
        out = c.extract_claim_terms(
            "Ankara NATO summit talks collapse suddenly", country="TR")
        # 5 tokens already → country not appended (would over-constrain)
        assert "tr" not in out["query"].split()


class TestFigureAndOfficial:
    def test_extract_figure_thousands(self):
        assert c.extract_figure("4,734 confirmed dead") == 4734.0

    def test_extract_figure_none(self):
        assert c.extract_figure("no numbers here") is None

    def test_official_wire_tokens(self):
        assert c.is_official_source("Reuters")
        assert c.is_official_source("AP News")
        assert c.is_official_source("Agence France-Presse")

    def test_official_word_boundary(self):
        assert c.is_official_source("AP") is True
        assert c.is_official_source("Apple Daily") is False


class TestFigureRelation:
    def test_within_tolerance_corroborates(self):
        assert c.figure_relation(1000, 1005) == "corroborates"

    def test_material_difference_contradicts(self):
        # the death-toll demo: 4,930 vs 4,734 = 4.1% > 1% tolerance
        assert c.figure_relation(4734, 4930) == "contradicts"

    def test_missing_figure_none(self):
        assert c.figure_relation(4734, None) is None
        assert c.figure_relation(None, 10) is None


class TestClassifyRelation:
    CLAIM = ["venezuela", "earthquake", "death", "toll"]

    def test_same_event_conflicting_figure_contradicts(self):
        rel = c.classify_relation(
            self.CLAIM, 4734.0,
            "Venezuela earthquake death toll reaches 4,930")
        assert rel == "contradicts"

    def test_same_event_matching_figure_corroborates(self):
        rel = c.classify_relation(
            self.CLAIM, 4734.0,
            "Venezuela earthquake death toll now 4,734")
        assert rel == "corroborates"

    def test_strong_term_overlap_no_figure_corroborates(self):
        rel = c.classify_relation(
            self.CLAIM, None,
            "Venezuela earthquake: death toll continues to climb")
        assert rel == "corroborates"

    def test_weak_overlap_is_context(self):
        rel = c.classify_relation(
            self.CLAIM, None,
            "Venezuela oil exports fall amid sanctions")
        assert rel == "context"

    def test_semantic_similarity_can_stand_in_for_terms(self):
        # hot-lane hit with different wording but high cosine
        rel = c.classify_relation(
            self.CLAIM, None,
            "Seismic disaster claims thousands in the Andes", similarity=0.92)
        assert rel == "corroborates"


class TestCorpusQueryBuilders:
    def test_cold_query_shape_and_params(self):
        sql, params = c.build_cold_corpus_query(
            ["venezuela", "earthquake"], country="VE", limit=25)
        assert "historical_evidence_samples" in sql
        assert "ILIKE ANY($1)" in sql
        assert params[0] == ["%venezuela%", "%earthquake%"]
        assert params[1] == "VE"
        assert params[2] == 25

    def test_cold_query_no_country(self):
        sql, params = c.build_cold_corpus_query(["armenia"])
        assert params[1] is None
        assert "($2::text IS NULL OR country_code = $2)" in sql

    def test_rows_to_archive_matches_filters_unrelated(self):
        rows = [
            {"headline": "Venezuela earthquake death toll rises to 4,900",
             "source_url": "https://reuters.com/a", "source_name": "Reuters",
             "country_code": "VE", "day": "2026-06-01", "topic_slug": "quake"},
            {"headline": "Local bakery wins award",  # unrelated → dropped
             "source_url": "https://x.com/b", "source_name": "X",
             "country_code": "VE", "day": "2026-06-01", "topic_slug": "food"},
        ]
        out = c.rows_to_archive_matches(
            rows, ["venezuela", "earthquake", "death", "toll"], 4734.0)
        assert len(out) == 1
        assert out[0]["basis"] == "atlas_archive"
        assert out[0]["relation"] == "contradicts"
        assert out[0]["official"] is True


class TestDedup:
    def test_dedup_by_url_and_title(self):
        ms = [
            {"url": "https://a.com/1", "snippet": "Toll rises", "relation": "corroborates"},
            {"url": "https://A.com/1", "snippet": "different", "relation": "context"},  # dup url
            {"url": "https://b.com/2", "snippet": "TOLL RISES", "relation": "context"},  # dup title
            {"url": "https://c.com/3", "snippet": "brand new", "relation": "corroborates"},
        ]
        out = c.dedup_matches(ms)
        assert len(out) == 2
        assert {m["url"] for m in out} == {"https://a.com/1", "https://c.com/3"}


class TestCitationVerdict:
    def test_corroborated_counts_official(self):
        v = c.citation_verdict([
            {"relation": "corroborates", "official": True},
            {"relation": "corroborates", "official": False},
            {"relation": "context", "official": False},
        ])
        assert v["status"] == "corroborated"
        assert v["corroborating"] == 2
        assert v["official_corroborating"] == 1
        assert "official/wire" in v["note"]

    def test_contradicted_when_contradictions_dominate(self):
        v = c.citation_verdict([
            {"relation": "corroborates", "official": False},
            {"relation": "contradicts", "official": True},
            {"relation": "contradicts", "official": False},
        ])
        assert v["status"] == "contradicted"
        assert v["contradicting"] == 2

    def test_uncorroborated_when_empty(self):
        v = c.citation_verdict([])
        assert v["status"] == "uncorroborated"
        assert v["corroborating"] == 0


# ── the degraded-mode contract (Marcos's honesty requirement) ────────────────

class _FakeConn:
    """Minimal asyncpg-style conn: returns canned archive rows for .fetch."""
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, sql, *params):
        return self._rows


@pytest.mark.asyncio
async def test_degraded_doc20_throttle_still_serves_atlas():
    """DOC 2.0 throttled → source_status.doc20 == 'throttled', and the archive
    matches are STILL returned (never silently fewer results as if complete)."""
    async def throttled_doc20(query):
        return {"status": "throttled", "articles": []}

    archive_rows = [{
        "headline": "Venezuela earthquake death toll rises to 4,930",
        "source_url": "https://reuters.com/x", "source_name": "Reuters",
        "country_code": "VE", "day": "2026-06-02", "topic_slug": "quake",
    }]
    conn = _FakeConn(archive_rows)

    out = await c.corroborate_claim(
        headline="Venezuela earthquake death toll reaches 4,734",
        figure=4734.0,
        country="VE",
        conn=conn,
        embed_fn=None,               # no embedder → hot lane not queried
        doc20_fetch=throttled_doc20,
    )
    assert out["source_status"]["doc20"] == "throttled"
    assert out["source_status"]["atlas_hot"] == "not_queried"
    assert out["source_status"]["atlas_archive"] == "ok"
    # the archive match survives the throttle and is a contradiction (4,930)
    assert len(out["contradicting"]) == 1
    assert out["contradicting"][0]["basis"] == "atlas_archive"
    assert out["verdict"]["status"] == "contradicted"


@pytest.mark.asyncio
async def test_doc20_ok_and_hot_lane_unify_and_dedup():
    async def ok_doc20(query):
        return {"status": "ok", "articles": [{
            "title": "Venezuela earthquake death toll now 4,734 confirmed",
            "url": "https://ap.org/a", "domain": "ap.org",
            "sourcecountry": "us", "seendate": "20260602T000000Z",
        }]}

    async def fake_hot(conn, vec, hours):
        return [{
            "headline": "Venezuela earthquake: rescue efforts continue",
            "country_code": "VE", "source_name": "El Nacional",
            "timestamp": "2026-06-02T10:00:00+00:00", "similarity": 0.91,
        }]

    conn = _FakeConn([])  # empty archive
    out = await c.corroborate_claim(
        headline="Venezuela earthquake death toll reaches 4,734",
        figure=4734.0, country="VE", conn=conn,
        embed_fn=lambda text: [0.0] * 768,  # non-None vec → hot lane runs
        hot_fetch=fake_hot,
        doc20_fetch=ok_doc20,
    )
    assert out["source_status"]["doc20"] == "ok"
    assert out["source_status"]["atlas_hot"] == "ok"
    bases = {m["basis"] for m in out["corroborating"]}
    assert bases == {"doc20", "atlas_hot"}
    assert out["verdict"]["status"] == "corroborated"


@pytest.mark.asyncio
async def test_doc20_down_reported_no_crash():
    async def boom(query):
        raise RuntimeError("connection refused")

    out = await c.corroborate_claim(
        headline="Armenia constitutional court annuls election result",
        doc20_fetch=boom,
    )
    assert out["source_status"]["doc20"] == "down"
    assert out["verdict"]["status"] == "uncorroborated"


def test_classify_doc20_parses_200_json_no_nameerror():
    # panel-gate regression: a live 200 with a real JSON body must parse to
    # status 'ok' with articles — not NameError (missing `import json`).
    import json as _json
    from app.services.corroboration import _classify_doc20
    body = _json.dumps({"articles": [{"title": "X", "url": "u", "domain": "reuters.com"}]}).encode()
    out = _classify_doc20(200, body)
    assert out["status"] == "ok"
    assert len(out["articles"]) == 1


def test_classify_doc20_nonjson_is_throttled():
    from app.services.corroboration import _classify_doc20
    out = _classify_doc20(200, b"Please limit requests to one every 5 seconds")
    assert out["status"] == "throttled"


def test_classify_doc20_429_and_5xx():
    from app.services.corroboration import _classify_doc20
    assert _classify_doc20(429, b"")["status"] == "throttled"
    assert _classify_doc20(503, b"")["status"] == "down"


# ── #260 DOC 2.0 response cache + cooldown backoff ───────────────────────────

class FakeCache:
    """Redis-shaped fake: async get/setex over a dict, recording setex TTLs."""
    def __init__(self):
        self.store: dict[str, str] = {}
        self.setex_calls: list[tuple[str, int]] = []

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl))
        self.store[key] = value


class BrokenCache:
    async def get(self, key):
        raise RuntimeError("redis down")

    async def setex(self, key, ttl, value):
        raise RuntimeError("redis down")


class TestDoc20CacheKey:
    def test_key_is_versioned_sha1_of_query_and_timespan(self):
        import hashlib
        k = c.doc20_cache_key("ankara nato summit", "1m")
        assert k == "doc20:v1:" + hashlib.sha1(
            b"ankara nato summit|1m").hexdigest()

    def test_timespan_changes_key(self):
        assert c.doc20_cache_key("q", "1m") != c.doc20_cache_key("q", "3m")

    def test_query_changes_key(self):
        assert c.doc20_cache_key("a", "1m") != c.doc20_cache_key("b", "1m")


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_ok_payload_without_network():
    import json as _json
    cache = FakeCache()
    key = c.doc20_cache_key("venezuela earthquake toll", "1m")
    cache.store[key] = _json.dumps(
        {"status": "ok", "articles": [{"title": "T", "domain": "reuters.com"}]})
    out = await c.doc20_fetch_status("venezuela earthquake toll", cache=cache)
    assert out["status"] == "ok"
    assert out["cache"] == "hit"
    assert out["articles"][0]["title"] == "T"


@pytest.mark.asyncio
async def test_cooldown_marker_short_circuits_as_honest_throttled():
    cache = FakeCache()
    cache.store[c._DOC20_COOLDOWN_KEY] = "1"
    out = await c.doc20_fetch_status("any fresh query", cache=cache)
    # No network attempt; still HONESTLY reported as throttled, not ok/empty.
    assert out["status"] == "throttled"
    assert out["cache"] == "cooldown"
    assert out["articles"] == []


@pytest.mark.asyncio
async def test_positive_cache_beats_cooldown():
    # A cached ok answer is served even while the cooldown marker is live.
    import json as _json
    cache = FakeCache()
    key = c.doc20_cache_key("cached query", "1m")
    cache.store[key] = _json.dumps({"status": "ok", "articles": []})
    cache.store[c._DOC20_COOLDOWN_KEY] = "1"
    out = await c.doc20_fetch_status("cached query", cache=cache)
    assert out["status"] == "ok"
    assert out["cache"] == "hit"


@pytest.mark.asyncio
async def test_store_caches_only_ok_and_sets_cooldown_on_throttle():
    cache = FakeCache()
    key = c.doc20_cache_key("q", "1m")

    # ok → positive cache with the 6h TTL
    await c.doc20_cache_store(cache, key, {"status": "ok", "articles": [1]})
    assert (key, c.DOC20_CACHE_TTL) in cache.setex_calls

    # throttled → ONLY the short cooldown marker, never a positive entry
    cache2 = FakeCache()
    await c.doc20_cache_store(cache2, key, {"status": "throttled", "articles": []})
    assert cache2.setex_calls == [(c._DOC20_COOLDOWN_KEY, c.DOC20_COOLDOWN_TTL)]
    assert key not in cache2.store

    # down → nothing cached (a blip must not suppress the next attempt)
    cache3 = FakeCache()
    await c.doc20_cache_store(cache3, key, {"status": "down", "articles": []})
    assert cache3.setex_calls == []


@pytest.mark.asyncio
async def test_broken_cache_degrades_to_no_cache():
    # Lookup + store both swallow cache errors (lane must not depend on Redis).
    assert await c.doc20_cache_lookup(BrokenCache(), "doc20:v1:x") is None
    await c.doc20_cache_store(BrokenCache(), "doc20:v1:x",
                              {"status": "ok", "articles": []})


@pytest.mark.asyncio
async def test_absent_cache_is_none_lookup_noop():
    assert await c.doc20_cache_lookup(None, "doc20:v1:x") is None
    await c.doc20_cache_store(None, "doc20:v1:x", {"status": "ok", "articles": []})


@pytest.mark.asyncio
async def test_corroborate_claim_meta_reports_cache_disposition():
    async def cached_doc20(query):
        return {"status": "ok", "articles": [], "cache": "hit"}

    out = await c.corroborate_claim(
        headline="Ankara summit collapses", doc20_fetch=cached_doc20)
    assert out["meta"]["cache"] == "hit"
    assert out["source_status"]["doc20"] == "ok"
