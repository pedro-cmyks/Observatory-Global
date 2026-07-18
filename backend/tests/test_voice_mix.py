"""Voice Mix diversity metric (#160/#230).

The whole diversification program is judged by this number, so its behavior
must be pinned: a monoculture scores near 0, a balanced multilingual corpus
scores high, and unknown-language buckets never inflate the result.
"""
from app.services import voice_mix


def _origins():
    return {"US": 100, "GB": 50, "(null)": 200}


def test_monoculture_scores_near_zero():
    # All English, language-known. english_balance=0, entropy=0, cjk=0.
    r = voice_mix.compute({"en": 1000, "xx": 5000}, _origins(), 6000, 0, 10)
    assert r["english_share_of_known"] == 1.0
    assert r["cjk"]["total"] == 0
    assert r["diversity_score"] < 1.0


def test_diverse_corpus_scores_high():
    langs = {"en": 200, "zh": 200, "ja": 200, "ko": 200, "es": 200, "ar": 200}
    r = voice_mix.compute(langs, _origins(), 1200, 0, 50)
    assert r["cjk"]["total"] == 600
    assert r["cjk"]["share_of_known"] == 0.5          # well past 5% target
    assert r["components"]["cjk_coverage"] == 1.0
    assert r["non_english_share_of_known"] > 0.8
    assert r["diversity_score"] > 70


def test_diversity_score_strictly_rises_with_balance():
    mono = voice_mix.compute({"en": 1000}, _origins(), 1000, 0, 5)
    mixed = voice_mix.compute(
        {"en": 500, "zh": 200, "es": 150, "ru": 150}, _origins(), 1000, 0, 5)
    assert mixed["diversity_score"] > mono["diversity_score"]


def test_unknown_buckets_excluded_from_known_slice():
    # 'xx' and '(null)' must not count as a language nor dilute English share.
    r = voice_mix.compute(
        {"en": 100, "xx": 900, "(null)": 50}, _origins(), 1050, 0, 5)
    assert r["language_known"] == 100
    assert r["distinct_known_languages"] == 1
    assert r["english_share_of_known"] == 1.0


def test_cjk_coverage_caps_at_target():
    # Exactly the 5% target → coverage component saturates at 1.0.
    r = voice_mix.compute({"en": 950, "zh": 50}, _origins(), 1000, 0, 5)
    assert r["cjk"]["share_of_known"] == 0.05
    assert r["components"]["cjk_coverage"] == 1.0


def test_compute_exposes_voices_by_origin():
    r = voice_mix.compute({"en": 100}, {"US": 80, "GB": 20, "(null)": 5}, 105, 0, 5)
    vbo = {v["cc"]: v for v in r["voices_by_origin"]}
    assert vbo["US"]["pct"] == 0.8       # share of attributable origins
    assert "(null)" not in vbo            # unattributed excluded


def test_primary_langs_map():
    assert voice_mix.primary_langs("IR") == ("fa",)
    assert voice_mix.primary_langs("EG") == ("ar",)   # Arabic world
    assert voice_mix.primary_langs("xx") == ()        # unknown -> empty


def test_relation_self_voice_is_ownership_not_language():
    # 4000 attributable voices about a subject, 40 from domestic outlets.
    # 3000 are foreign outlets IN the local language (BBC-Persian-type) — these
    # must NOT count as self voice; they are soft power.
    r = voice_mix.relation(
        scope_total=6000, origin_known=4000, domestic=40,
        soft_power_local_lang=3000,
        foreign_origins=[("GB", 3200), ("US", 700)],
        foreign_langs=[("fa", 3000), ("en", 900)],
    )
    assert r["self_voice"] == 40
    assert r["self_voice_ratio"] == 0.01            # 40 / 4000
    assert r["foreign_voice"] == 3960
    assert r["soft_power_local_language"] == 3000   # foreign-in-local-language
    assert r["soft_power_ratio"] == 0.75
    assert r["unattributed"] == 2000                # GDELT, honestly reported
    assert r["dominant_outsider"]["origin"] == "GB"


def test_relation_domestic_dominated_subject():
    r = voice_mix.relation(1000, 1000, 900, 0, [("US", 100)], [("en", 100)])
    assert r["self_voice_ratio"] == 0.9
    assert r["foreign_voice"] == 100


def test_relation_handles_zero_attributable():
    # All GDELT, no outlet origin -> ratios are 0, nothing assumed.
    r = voice_mix.relation(500, 0, 0, 0, [], [])
    assert r["self_voice_ratio"] == 0.0
    assert r["unattributed"] == 500


# ── /voice-mix degraded path (2026-07-18, intermittent-503 fix) ──────────────
# Under M1 batch-window DB contention the aggregation used to bubble a
# QueryCanceledError into the global db_busy handler → 503. The router must
# instead serve an honest degraded 200 shape, and a slow country-relation
# query must degrade ONLY the relation, never the base report.

import asyncpg
import pytest

from app import db
from app.routers import voice_mix as vm_router


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        return False


class FakePool:
    """Each acquire() hands out the next conn (base block, then relation)."""
    def __init__(self, *conns):
        self._conns = list(conns)

    def acquire(self):
        conn = self._conns.pop(0) if len(self._conns) > 1 else self._conns[0]
        return _AcquireCtx(conn)


class BusyConn:
    async def execute(self, sql):
        return None

    async def fetch(self, sql, *params):
        raise asyncpg.exceptions.QueryCanceledError(
            "canceling statement due to statement timeout")

    async def fetchrow(self, sql, *params):
        raise asyncpg.exceptions.QueryCanceledError(
            "canceling statement due to statement timeout")


class OkBaseConn:
    async def execute(self, sql):
        # the router must bound every statement, not run unbounded
        assert "statement_timeout" in sql

    async def fetch(self, sql, *params):
        if "source_origin_country" in sql:
            return [{"o": "US", "n": 5}, {"o": "(null)", "n": 2}]
        return [{"lang": "en", "n": 8}, {"lang": "es", "n": 4}]

    async def fetchrow(self, sql, *params):
        return {"total": 12, "state_media": 1, "distinct_sources": 4}


@pytest.mark.asyncio
async def test_db_timeout_serves_degraded_200_shape(monkeypatch):
    monkeypatch.setattr(db, "pool", FakePool(BusyConn()), raising=False)
    out = await vm_router.get_voice_mix(hours=168, country=None)
    assert out["degraded"] is True
    assert out["reason"] == "db_busy"
    assert out["contract"] == "voice-mix-v0"
    assert out["window_hours"] == 168
    # NEVER a measured-looking zero: no stats fields on the degraded shape
    # (Landing guards on distinct_origin_countries, CountryBrief on relation).
    assert "distinct_origin_countries" not in out
    assert "diversity_score" not in out
    assert "relation" not in out


@pytest.mark.asyncio
async def test_relation_timeout_degrades_only_relation(monkeypatch):
    monkeypatch.setattr(db, "pool", FakePool(OkBaseConn(), BusyConn()), raising=False)
    out = await vm_router.get_voice_mix(hours=168, country="co")
    # base report intact
    assert "degraded" not in out
    assert "diversity_score" in out
    assert out["country"] == "CO"
    # relation lane honestly degraded, not silently absent
    assert out.get("relation_degraded") is True
    assert "relation" not in out
    assert out["primary_languages"] == ["es"]


@pytest.mark.asyncio
async def test_healthy_country_path_serves_relation(monkeypatch):
    class OkRelationConn(OkBaseConn):
        async def fetchrow(self, sql, *params):
            if "origin_known" in sql:
                return {"origin_known": 7, "domestic": 3, "soft_power": 1}
            return await super().fetchrow(sql, *params)

        async def fetch(self, sql, *params):
            if "ORDER BY n DESC LIMIT 6" in sql:
                if "source_origin_country" in sql:
                    return [{"cc": "US", "n": 4}]
                return [{"lang": "en", "n": 4}]
            return await super().fetch(sql, *params)

    monkeypatch.setattr(db, "pool", FakePool(OkBaseConn(), OkRelationConn()), raising=False)
    out = await vm_router.get_voice_mix(hours=168, country="co")
    assert out["relation"]["self_voice"] == 3
    assert "relation_degraded" not in out
