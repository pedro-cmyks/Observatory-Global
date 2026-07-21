# Country Edition + On-Demand Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the L1 country door into a full country edition — three adaptive/honest country-scoped sections with progressive, cache-first article enrichment — served by a new `GET /api/v2/country-edition?cc=`.

**Architecture:** A dedicated live (unsealed) backend endpoint composes country-scoped threads (`fetch_threads(country_codes=[cc])` → `rank_threads`) + a country-scoped coverage-gaps query + a cache-first article-enrichment pass (warm-read `article_states`, fire-and-forget `enqueue_fetches`, **never blocks**). The frontend composes the three sections from those ingredients via a pure helper (reusing `splitEditionThreads`), renders with the existing `renderThreadCard`/`renderReceipt`, and fills excerpts progressively via the existing `useArticleStates` poll. **Design refinement vs the spec:** the 3-section split lives in the frontend (that is where the global edition already composes its sections — `BriefNewspaper.tsx` + `lib/briefEdition.ts`), so the backend returns ranked threads + gaps + enrichment rather than pre-composed `sections[]`. Same three adaptive sections, placed where the pattern already lives.

**Tech Stack:** Python 3 / FastAPI / asyncpg / Redis (backend); React + TypeScript + Vitest (frontend). No new dependencies. No engine writes. Reuses `daily_publication` enrichment pattern, `article_fetch`, `thread_ranking`, `thread_intelligence`, `attention`/coverage-gaps SQL, `splitEditionThreads`, `renderReceipt`, `useArticleStates`.

**Spec:** `docs/superpowers/specs/2026-07-21-country-edition-enrichment-design.md`

---

## File Structure

**Backend**
- Create: `backend/app/services/country_edition.py` — pure assemblers (`gather_receipt_urls`, `build_article_enrichment`, `build_country_edition_payload`) + async orchestrator `fetch_country_edition` + the country coverage-gaps SQL. One responsibility: compose the country edition, read-only.
- Create: `backend/tests/test_country_edition.py` — pure-helper + no-db-path tests.
- Modify: `backend/app/routers/geo.py` — add `GET /api/v2/country-edition` handler (no-prefix router already mounted).
- Modify: `backend/app/rate_limit.py:88-106` — add the endpoint to the `paid` bucket.

**Frontend**
- Create: `frontend-v2/src/lib/countryEdition.ts` — `CountryEdition`/`CountryGap`/`CountrySection` types, pure `composeCountrySections`, `fetchCountryEdition`.
- Create: `frontend-v2/src/lib/countryEdition.test.ts` — `composeCountrySections` vitest.
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx` — fetch the edition; switch `editionArticles`/`liveArticleStates` on `countryFilter`; replace the country render stub (`1673-1758`) with the 3 adaptive sections + enrichment strip.

---

## Task 1: Backend pure helpers (`country_edition.py`)

**Files:**
- Create: `backend/app/services/country_edition.py`
- Test: `backend/tests/test_country_edition.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_country_edition.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.country_edition'`.

- [ ] **Step 3: Write the pure helpers**

Create `backend/app/services/country_edition.py`:

```python
"""L1 country edition — on-demand, live (unsealed).

Composes country-scoped narrative threads + a country-scoped coverage-gaps
band + cache-first article enrichment for the Brief's country door. Read-only;
never writes engine substrate. Mirrors the daily_publication enrichment pattern
but NEVER blocks — this is a live serving endpoint, so it warm-reads the article
cache, enqueues the misses fire-and-forget, and returns immediately; the client
polls for the progressive fill.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app import db
from app.services.thread_intelligence import fetch_threads
from app.services.thread_ranking import rank_threads

logger = logging.getLogger(__name__)

CONTRACT = "country-edition-v0"
ENRICHMENT_CONTRACT = "country-edition-enrichment-v0"

_MAX_THREADS = 24
_RECEIPTS_PER_THREAD = 4
_MAX_RECEIPT_URLS = 48

# Country-scoped coverage gaps = the "Under the Radar" band. Categories getting
# real domestic signal in this country but with ZERO rows clearing the gate —
# the domestic stories not yet surfacing. Mirrors briefing.coverage_gaps but
# joins signals_v2 for the country predicate and uses a lower floor (per-country
# volume is smaller than global). Tunable via ATLAS_COUNTRY_GAP_MIN.
_COUNTRY_GAPS_SQL = """
    SELECT t.slug, t.label,
           COUNT(*)::int AS raw_signals,
           COUNT(*) FILTER (WHERE a.gate_kept)::int AS verified,
           COUNT(*) FILTER (WHERE a.gate_score IS NOT NULL)::int AS scored
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s ON s.id = a.signal_id
    WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.country_code = $2
    GROUP BY t.slug, t.label
    HAVING COUNT(*) >= $3
       AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
    ORDER BY raw_signals DESC
    LIMIT 6
"""


def gather_receipt_urls(
    threads: list[dict],
    *,
    per_thread: int = _RECEIPTS_PER_THREAD,
    cap: int = _MAX_RECEIPT_URLS,
) -> list[str]:
    """Distinct http receipt URLs across the ranked threads (capped per thread
    and per edition), preserving order. Same cap discipline as the seal."""
    urls: list[str] = []
    for thread in threads:
        for ev in (thread.get("evidence_samples") or [])[:per_thread]:
            url = str(ev.get("url") or ev.get("source_url") or "")
            if url.startswith("http"):
                urls.append(url)
    return list(dict.fromkeys(urls))[:cap]


def build_article_enrichment(urls: list[str], states: list[dict]) -> dict:
    """Assemble the enrichment block from a warm article_states read. `pending`
    counts URLs still fetching (None/pending/queued) — the client polls those."""
    by_url = {s["url"]: s for s in states}
    ok_count = sum(1 for s in states if s.get("status") == "ok")
    pending_urls = [
        u for u in urls
        if by_url.get(u, {}).get("status") in (None, "pending", "queued")
    ]
    return {
        "contract": ENRICHMENT_CONTRACT,
        "yield": {
            "ok": ok_count,
            "attempted": len(urls),
            "pending": len(pending_urls),
        },
        "pending_urls": pending_urls,
        "articles": {
            s["url"]: {
                "status": s.get("status"),
                "via": s.get("via"),
                "excerpt": s.get("excerpt"),
                "outlet": s.get("outlet"),
                "fetched_at": s.get("fetched_at"),
            }
            for s in states
        },
        "note": (
            "server-fetched page text per receipt; partial yield is normal "
            "(paywalls/bot walls); pending = still fetching, poll for the fill"
        ),
    }


def build_country_edition_payload(
    *,
    country: str,
    country_name: str,
    ranked_threads: list[dict],
    enrichment: dict,
    coverage_gaps: list[dict],
    generated_at: datetime,
    window_hours: int,
) -> dict:
    """The country-edition-v0 envelope. Pure — no I/O."""
    return {
        "contract": CONTRACT,
        "country": country,
        "country_name": country_name,
        "generated_at": generated_at.isoformat(),
        "window_hours": window_hours,
        "threads": ranked_threads,
        "coverage_gaps": coverage_gaps,
        "article_enrichment": enrichment,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/country_edition.py backend/tests/test_country_edition.py
git commit -m "feat(country-edition): pure assemblers (urls/enrichment/payload) + TDD"
```

---

## Task 2: Backend async orchestrator (`fetch_country_edition`)

**Files:**
- Modify: `backend/app/services/country_edition.py` (append)
- Test: `backend/tests/test_country_edition.py` (append)

- [ ] **Step 1: Write the failing test (no-db honest path + orchestration)**

Append to `backend/tests/test_country_edition.py`:

```python
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
    # Stub the two engine calls + article cache; assert the edition wires them.
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: FAIL — `AttributeError: module 'app.services.country_edition' has no attribute 'fetch_country_edition'`.

- [ ] **Step 3: Implement the orchestrator**

Append to `backend/app/services/country_edition.py`:

```python
import os


async def fetch_country_edition(country_code: str, *, hours: int = 24) -> dict:
    """Compose the live country edition. Never blocks: warm-reads the article
    cache and enqueues the misses fire-and-forget."""
    cc = country_code.upper()
    generated_at = datetime.now(timezone.utc)

    if db.pool is None:
        return build_country_edition_payload(
            country=cc,
            country_name=cc,
            ranked_threads=[],
            enrichment=build_article_enrichment([], []),
            coverage_gaps=[],
            generated_at=generated_at,
            window_hours=hours,
        )

    gap_min = int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))
    async with db.pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT name FROM countries_v2 WHERE code = $1", cc
        )
        country_name = rec["name"] if rec else cc
        gap_rows = await conn.fetch(_COUNTRY_GAPS_SQL, hours, cc, gap_min)

    threads = await fetch_threads(
        hours=hours,
        limit=_MAX_THREADS,
        country_codes=[cc],
        attach_evidence=True,
    )
    ranked = rank_threads(threads)

    urls = gather_receipt_urls(ranked)
    states: list[dict] = []
    if urls:
        try:
            from app.services.article_fetch import article_states, enqueue_fetches
            states = await article_states(urls)
            by_url = {s["url"]: s for s in states}
            missing = [
                u for u in urls
                if by_url.get(u, {}).get("status") in (None, "pending")
            ]
            if missing:
                await enqueue_fetches(missing)      # fire-and-forget, NO wait
                states = await article_states(urls)  # re-read; warm ones may flip
        except Exception as exc:  # enrichment never breaks the edition
            logger.warning(
                "country-edition enrichment skipped: %s: %s",
                type(exc).__name__, str(exc)[:200],
            )

    enrichment = build_article_enrichment(urls, states)
    coverage_gaps = [dict(r) for r in gap_rows]

    logger.info(
        "country-edition cc=%s threads=%d gaps=%d enrich ok=%d/%d pending=%d",
        cc, len(ranked), len(coverage_gaps),
        enrichment["yield"]["ok"], enrichment["yield"]["attempted"],
        enrichment["yield"]["pending"],
    )
    return build_country_edition_payload(
        country=cc,
        country_name=country_name,
        ranked_threads=ranked,
        enrichment=enrichment,
        coverage_gaps=coverage_gaps,
        generated_at=generated_at,
        window_hours=hours,
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: PASS (10 tests). If `pytest-asyncio` is not auto-mode, the `@pytest.mark.asyncio` marker matches the repo's existing async tests (e.g. `tests/test_dossier_synthesis.py`) — no config change needed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/country_edition.py backend/tests/test_country_edition.py
git commit -m "feat(country-edition): async orchestrator — threads+gaps+cache-first enrichment"
```

---

## Task 3: Backend router + rate-limit + cache

**Files:**
- Modify: `backend/app/routers/geo.py` (add handler; `app`, `json`, `Query` already imported at lines 3/7/9)
- Modify: `backend/app/rate_limit.py:88-106` (paid bucket)
- Test: `backend/tests/test_country_edition.py` (append handler test)

- [ ] **Step 1: Write the failing handler test**

Append to `backend/tests/test_country_edition.py`:

```python
@pytest.mark.asyncio
async def test_country_edition_handler_uppercases_and_delegates(monkeypatch):
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: FAIL — `AttributeError: module 'app.routers.geo' has no attribute 'get_country_edition'`.

- [ ] **Step 3: Add the handler to `geo.py`**

Append (at the end of `backend/app/routers/geo.py`, alongside the other `@router.get(...)` handlers):

```python
@router.get("/api/v2/country-edition")
async def get_country_edition(cc: str, hours: int = Query(24, ge=1, le=24)):
    """L1 country edition — country-scoped threads + coverage-gaps band +
    cache-first article enrichment. Live/on-demand (unsealed). 120s cache."""
    from app.services.country_edition import fetch_country_edition

    cc = cc.upper()
    cache_key = f"country-edition:{cc}:{hours}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    result = await fetch_country_edition(cc, hours=hours)

    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 120, json.dumps(result, default=str))
        except Exception:
            pass
    return result
```

Note: `geo.py` line 3 is `import json` — use `json.dumps`/`json.loads` (the flows endpoint's `_json` alias is a separate import; `json` is valid here).

- [ ] **Step 4: Register the paid bucket**

In `backend/app/rate_limit.py`, inside `_RULE_SPECS` (lines 88-106), add this row right after the `research/plan` row (the endpoint spawns outbound fetches like `articles/fetch`, so it belongs in `paid`):

```python
    (r"^/api/v2/country-edition$", "paid", None),
```

- [ ] **Step 5: Run the handler test**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: PASS (11 tests).

- [ ] **Step 6: Verify the router imports cleanly**

Run: `cd backend && .venv/bin/python -c "import app.routers.geo as g; print(hasattr(g, 'get_country_edition'))"`
Expected: `True`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/geo.py backend/app/rate_limit.py backend/tests/test_country_edition.py
git commit -m "feat(country-edition): GET /api/v2/country-edition (paid bucket, 120s cache)"
```

---

## Task 4: Frontend lib — types + `composeCountrySections` + fetch

**Files:**
- Create: `frontend-v2/src/lib/countryEdition.ts`
- Test: `frontend-v2/src/lib/countryEdition.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/countryEdition.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { composeCountrySections, type CountryGap } from './countryEdition'

const worldA = { label: 'Election dispute', category: 'election-legitimacy' }
const worldB = { label: 'Flood disaster', category: 'weather-and-climate' }
const gap: CountryGap = {
  slug: 'labor', label: 'Labor strike', raw_signals: 12, verified: 0, scored: 12,
}

describe('composeCountrySections', () => {
  it('returns the three kinds in order and drops nothing', () => {
    const [today, radar, culture] = composeCountrySections([worldA, worldB], [gap])
    expect([today.kind, radar.kind, culture.kind]).toEqual([
      'country_today', 'under_radar', 'culture_sport_life',
    ])
    // every thread lands in exactly one of today/culture (split is total)
    expect(today.threads.length + culture.threads.length).toBe(2)
    expect(radar.gaps).toHaveLength(1)
    expect(radar.threads).toHaveLength(0)
  })

  it('thin country: sections with no content are honest-empty, never invented', () => {
    const [today, radar, culture] = composeCountrySections([worldA], [])
    expect(radar.present).toBe(false)
    expect(radar.empty_reason).toBeTruthy()
    expect(radar.gaps).toHaveLength(0)
    // culture may or may not be present depending on classification; if empty,
    // it must be honest-empty (present=false ⇒ empty_reason set)
    if (!culture.present) expect(culture.empty_reason).toBeTruthy()
    expect(today.present || today.empty_reason).toBeTruthy()
  })

  it('zero threads and zero gaps: all three honest-empty', () => {
    const [today, radar, culture] = composeCountrySections([], [])
    expect(today.present).toBe(false)
    expect(radar.present).toBe(false)
    expect(culture.present).toBe(false)
    for (const s of [today, radar, culture]) expect(s.empty_reason).toBeTruthy()
  })

  it('present flag matches content presence', () => {
    const [today, radar] = composeCountrySections([worldA], [gap])
    expect(today.present).toBe(today.threads.length > 0)
    expect(radar.present).toBe(radar.gaps.length > 0)
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/countryEdition.test.ts`
Expected: FAIL — cannot resolve `./countryEdition`.

- [ ] **Step 3: Implement the lib**

Create `frontend-v2/src/lib/countryEdition.ts`:

```ts
// L1 country edition — client contract + pure section composer + fetch.
//
// The country door is a full edition: three adaptive/honest sections composed
// from country-scoped threads + a country coverage-gaps band. Section splitting
// reuses the global edition's deterministic classifier (splitEditionThreads).
// Adaptive by construction: a section renders only when it has content; empty
// sections carry an honest reason and are never invented to fill.

import { splitEditionThreads, type EditionThreadLike } from './briefEdition'

export interface CountryGap {
  slug: string
  label: string
  raw_signals: number
  verified: number
  scored: number
}

export interface CountryEditionArticle {
  status?: string
  via?: string
  excerpt?: string | null
  outlet?: string | null
  fetched_at?: string | null
}

export interface CountryEditionEnrichment {
  contract?: string
  yield?: { ok: number; attempted: number; pending: number }
  pending_urls?: string[]
  articles?: Record<string, CountryEditionArticle>
  note?: string
}

export interface CountryEdition {
  contract: 'country-edition-v0'
  country: string
  country_name: string
  generated_at: string
  window_hours: number
  // Thread rows are TopThread-compatible (fetch_threads output). Kept loose
  // here; the page maps them via its existing TopThread renderers.
  threads: Array<Record<string, unknown>>
  coverage_gaps: CountryGap[]
  article_enrichment: CountryEditionEnrichment | null
}

export type CountrySectionKind =
  | 'country_today'
  | 'under_radar'
  | 'culture_sport_life'

export interface CountrySection<T> {
  kind: CountrySectionKind
  present: boolean
  threads: T[]
  gaps: CountryGap[]
  empty_reason: string | null
}

const EMPTY_REASONS: Record<CountrySectionKind, string> = {
  country_today: 'poca actividad en las últimas 24 h',
  under_radar: 'nada bajo el radar hoy',
  culture_sport_life: 'sin cultura, deporte ni vida en 24 h',
}

/**
 * Partition country threads + gaps into the three adaptive sections.
 * - country_today  = the "world" (serious/crisis-relevant) country threads
 * - under_radar    = country coverage-gaps (domestic signal, 0 gate-kept)
 * - culture_sport_life = culture/sport/life country threads
 * Splitting reuses splitEditionThreads (category-first, label fallback).
 */
export function composeCountrySections<T extends EditionThreadLike>(
  threads: readonly T[],
  gaps: readonly CountryGap[],
): [CountrySection<T>, CountrySection<T>, CountrySection<T>] {
  const { world, culture } = splitEditionThreads(threads)
  const gapList = Array.from(gaps)
  return [
    {
      kind: 'country_today',
      present: world.length > 0,
      threads: world,
      gaps: [],
      empty_reason: world.length > 0 ? null : EMPTY_REASONS.country_today,
    },
    {
      kind: 'under_radar',
      present: gapList.length > 0,
      threads: [],
      gaps: gapList,
      empty_reason: gapList.length > 0 ? null : EMPTY_REASONS.under_radar,
    },
    {
      kind: 'culture_sport_life',
      present: culture.length > 0,
      threads: culture,
      gaps: [],
      empty_reason: culture.length > 0 ? null : EMPTY_REASONS.culture_sport_life,
    },
  ]
}

/** Fetch the live country edition. Returns null on any failure (honest degrade). */
export async function fetchCountryEdition(
  cc: string,
  hours = 24,
): Promise<CountryEdition | null> {
  try {
    const resp = await fetch(`/api/v2/country-edition?cc=${cc}&hours=${hours}`)
    if (!resp.ok) return null
    const data = await resp.json()
    if (data?.contract !== 'country-edition-v0') return null
    return data as CountryEdition
  } catch {
    return null
  }
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend-v2 && npx vitest run src/lib/countryEdition.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/countryEdition.ts frontend-v2/src/lib/countryEdition.test.ts
git commit -m "feat(country-edition): client contract + composeCountrySections + fetch (TDD)"
```

---

## Task 5: Frontend — wire the edition into BriefNewspaper

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

This task has no unit test of its own (React page wiring); it is covered by the `composeCountrySections` vitest (Task 4) plus a build gate and a browser check. Keep each edit surgical at the cited anchors.

- [ ] **Step 1: Add imports**

Near the existing edition imports (top of `BriefNewspaper.tsx`, alongside `import { TranslatableHeadline } ...` at line 16 and the `articleEnrichment` imports), add:

```tsx
import {
    composeCountrySections,
    fetchCountryEdition,
    type CountryEdition,
    type CountrySection,
} from '../lib/countryEdition'
```

- [ ] **Step 2: Add country-edition state + fetch effect**

Immediately after the existing country fetch effect (the `useEffect` at `465-515` that sets `countryDetail`/`countryThreads`), add a parallel effect that loads the edition:

```tsx
const [countryEdition, setCountryEdition] = useState<CountryEdition | null>(null)

useEffect(() => {
    if (!countryFilter) { setCountryEdition(null); return }
    let cancelled = false
    setCountryEdition(null)
    fetchCountryEdition(countryFilter, hours).then(ed => {
        if (!cancelled) setCountryEdition(ed)
    })
    return () => { cancelled = true }
}, [countryFilter, hours])
```

- [ ] **Step 3: Switch the excerpt sources on `countryFilter`**

The current bindings (BriefNewspaper `778` and `787-797`) drive `renderReceipt`'s excerpt lookup for the GLOBAL edition. Make them country-aware so `renderReceipt` fills country excerpts with zero change to `renderReceipt` itself.

Find (near line 778):
```tsx
const editionArticles = dailyEdition?.package?.article_enrichment?.articles ?? null
```
(the exact RHS may read from the sealed package — keep whatever it currently is, just rename it) and replace the block so the effective names `editionArticles` / `liveArticleStates` select the country sources when a country is active:

```tsx
// Global excerpt sources (unchanged behavior when no country is selected).
const dailyEditionArticles = dailyEdition?.package?.article_enrichment?.articles ?? null

// Country excerpt sources: warm map from the endpoint + a live poll on the
// still-pending receipt URLs (progressive fill — same machinery as the seal).
const countryEditionArticles = countryEdition?.article_enrichment?.articles ?? null
const countryPendingUrls = useMemo(
    () => countryEdition?.article_enrichment?.pending_urls ?? [],
    [countryEdition],
)
useEffect(() => { enqueueUrls(countryPendingUrls) }, [countryPendingUrls])
const countryLiveStates = useArticleStates(countryPendingUrls)

// renderReceipt reads these two; select country sources when a country is open.
const editionArticles = countryFilter ? countryEditionArticles : dailyEditionArticles
const liveArticleStates = countryFilter ? countryLiveStates : globalLiveArticleStates
```

Where the existing global live-poll binding at `797` (`const liveArticleStates = useArticleStates(liveReceiptUrls)`) must be **renamed** to `globalLiveArticleStates`:

```tsx
const globalLiveArticleStates = useArticleStates(liveReceiptUrls)
```

(Only the binding name changes; `liveReceiptUrls`, `enqueueUrls(liveReceiptUrls)`, and `renderReceipt`'s `liveArticleStates.get(...)` usage are unchanged — `renderReceipt` now reads the switched `liveArticleStates`.)

`useMemo`, `useArticleStates`, `enqueueUrls` are already imported/used in this file (recon: `787-797`).

- [ ] **Step 4: Add the section + gaps renderers**

Add these two render helpers near `renderThreadCard` (define after it, ~line 972, so `renderThreadCard`/`renderReceipt` are in scope):

```tsx
const renderCountryGaps = (gaps: CountrySection<TopThread>['gaps']) => (
    <ul className="brief-coverage-gaps">
        {gaps.map(g => (
            <li key={g.slug} className="brief-coverage-gap">
                <span className="brief-gap-label">{g.label}</span>
                <span className="brief-gap-meta">
                    {g.raw_signals} signals · 0 cleared the gate
                </span>
            </li>
        ))}
    </ul>
)

const COUNTRY_SECTION_META: Record<
    CountrySection<TopThread>['kind'],
    { title: string; kicker: string }
> = {
    country_today: { title: 'Today', kicker: 'The country now' },
    under_radar: { title: 'Under the Radar', kicker: 'Domestic signal, not yet surfacing' },
    culture_sport_life: { title: 'Culture, Sport & Life', kicker: 'Where the rest of us live' },
}

const renderCountrySection = (
    sec: CountrySection<TopThread>,
    country: string,
) => {
    const meta = COUNTRY_SECTION_META[sec.kind]
    return (
        <section key={sec.kind} className={`brief-country-section brief-country-section-${sec.kind}`}>
            <span className="reader-section-kicker">{meta.kicker}</span>
            <h3 className="brief-section-title">{meta.title}</h3>
            {!sec.present ? (
                <p className="brief-empty-note">{sec.empty_reason}</p>
            ) : sec.kind === 'under_radar' ? (
                renderCountryGaps(sec.gaps)
            ) : (
                <div className="brief-cards">
                    {sec.threads.map((t, i) => renderThreadCard(t, { country, wide: i === 0 }))}
                </div>
            )}
        </section>
    )
}
```

Note: `sec.threads` is typed `TopThread[]` because we call `composeCountrySections<TopThread>(...)` in Step 5. `TopThread` (defined at `98`) satisfies `EditionThreadLike` (it has `label`, `category`/`parent_domain`).

- [ ] **Step 5: Replace the country render stub with the 3 sections**

Replace the country render body (the `{countryFilter && ( <section className="brief-panel brief-panel-country"> ... )}` block at `1673-1758`). Keep the existing vitals instrument + masthead (they read `countryDetail`), and swap the single flat thread list for the three composed sections plus the enrichment strip:

```tsx
{/* ===== COUNTRY EDITION ===== */}
{countryFilter && (
    <section className="brief-panel brief-panel-country">
        {countryDetail && (
            <div className="brief-instrument brief-instrument-country">
                <div className="brief-vital">
                    <div className="k">Signals</div>
                    <div className="v">{countryDetail.totalSignals.toLocaleString()}</div>
                    <div className="sub">in the last 24h</div>
                </div>
                <div className="brief-vital">
                    <div className="k">Threads</div>
                    <div className="v">{countryEdition?.threads.length ?? countryThreads?.length ?? 0}</div>
                    <div className="sub">country-scoped narrative threads</div>
                </div>
                <div className={`brief-vital ${moodClass(countryDetail.sentiment)}`}>
                    <div className="k">Country mood</div>
                    <div className="v">{moodLabel(countryDetail.sentiment)}</div>
                    <div className="sub">window aggregate</div>
                </div>
            </div>
        )}

        <span className="reader-section-kicker brief-sub-kicker">Country edition</span>
        <h2 className="brief-section-title">
            <Flag code={countryFilter} /> {resolveCountryName(countryFilter, countryDetail?.name)}
        </h2>

        {(() => {
            const enr = countryEdition?.article_enrichment
            if (!enr?.yield || enr.yield.attempted === 0) return null
            // Live pending: URLs not yet settled in the poll.
            const stillPending = (enr.pending_urls ?? []).filter(u => {
                const s = countryLiveStates.get(u)
                return !s || s.status === 'pending' || s.status === 'queued'
            }).length
            return (
                <p className="brief-country-enrich" aria-live="polite">
                    {`full text ${enr.yield.ok}/${enr.yield.attempted} receipts`}
                    {stillPending > 0 ? ` · enriqueciendo ${stillPending} más…` : ''}
                </p>
            )
        })()}

        {!countryEdition ? (
            <p className="brief-country-note">
                Assembling this country's edition for the last {hours}h…
            </p>
        ) : countryEdition.threads.length === 0 && countryEdition.coverage_gaps.length === 0 ? (
            <div className="brief-country-note">
                <p>No coherent narrative thread cleared the quality gate for this country in the current window.</p>
                <button className="brief-theme-link" onClick={() => goToAtlas(`country=${countryFilter}`)}>
                    Open country in Atlas →
                </button>
            </div>
        ) : (
            composeCountrySections<TopThread>(
                (countryEdition.threads as unknown as TopThread[]),
                countryEdition.coverage_gaps,
            ).map(sec => renderCountrySection(sec, countryFilter))
        )}
    </section>
)}
```

- [ ] **Step 6: Type-check + build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (no TS errors). If `TopThread` is missing a field `composeCountrySections` needs, it only needs `label` + optional `category`/`parent_domain` — both present on `TopThread` (line 98). Fix any type friction with the `as unknown as TopThread[]` bridge already shown (the endpoint's `threads` are `Record<string,unknown>`).

- [ ] **Step 7: Add minimal CSS (only if the new classes have no styles)**

The classes `brief-country-section`, `brief-coverage-gaps`, `brief-coverage-gap`, `brief-gap-label`, `brief-gap-meta`, `brief-country-enrich` may be new. Check `BriefNewspaper.css` (or the relevant stylesheet) for `brief-coverage-gaps` (the global radar band likely already styles a sibling). If absent, add:

```css
.brief-country-section { margin-top: 1.5rem; }
.brief-country-enrich { font-size: 0.8rem; opacity: 0.75; margin: 0.25rem 0 0.75rem; }
.brief-coverage-gaps { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.4rem; }
.brief-coverage-gap { display: flex; justify-content: space-between; gap: 0.75rem;
    padding: 0.4rem 0.6rem; border-left: 2px solid var(--r-sec, currentColor); opacity: 0.9; }
.brief-gap-meta { font-size: 0.78rem; opacity: 0.7; white-space: nowrap; }
```

Run: `cd frontend-v2 && npm run build`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/pages/BriefNewspaper.css
git commit -m "feat(country-edition): 3 adaptive sections + progressive enrichment in the Brief country door"
```

---

## Task 6: Verify end-to-end + deploy

**Files:** none (verification + deploy)

- [ ] **Step 1: Backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/test_country_edition.py -q`
Expected: PASS (11 tests). Also run the neighbors that touch shared code: `.venv/bin/python -m pytest tests/test_daily_publication_artifact.py -q` — expected still green.

- [ ] **Step 2: Frontend suite + build**

Run: `cd frontend-v2 && npx vitest run src/lib/countryEdition.test.ts && npm run build`
Expected: vitest PASS + build green. Then the full suite: `npx vitest run` — expected no new failures.

- [ ] **Step 3: Deploy backend (Fly)**

Run: `./scripts/deploy-fly-api.sh`
Expected: deploy completes, health check passes.

- [ ] **Step 4: Prod smoke — thin, rich, non-English**

```bash
# Thin (Colombia): expect country_today present, under_radar/culture adaptive.
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/country-edition?cc=CO' \
  | jq '{contract, country_name, threads: (.threads|length), gaps: (.coverage_gaps|length), yield: .article_enrichment.yield}'
# Rich (US): expect more threads + gaps.
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/country-edition?cc=US' \
  | jq '{country_name, threads: (.threads|length), yield: .article_enrichment.yield}'
# Non-English (Turkey): excerpts should be source-language; check an article excerpt.
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/country-edition?cc=TR' \
  | jq '.article_enrichment.articles | to_entries[0].value.excerpt'
```
Expected: `contract == "country-edition-v0"`, `country_name` resolved (not the raw code), honest zero yields allowed (paywalls), non-English excerpts render in source language. Re-run CO after ~2 min — `pending` should drop and `ok` rise as the enqueue lands (progressive fill).

- [ ] **Step 5: Browser check (Vercel or local preview)**

Open the Brief, search a country. Verify: three sections render; thin sections show the honest-empty line (never fabricated); excerpts appear under receipts and grow on re-render (progressive); the "enriqueciendo N más…" strip counts down; state-media receipts carry the tier chip (renderReceipt already handles `is_state_media`). Confirm no console errors.

- [ ] **Step 6: Final commit / push**

```bash
git push origin v3-intel-layer
```

---

## Deferred follow-up (NOT in this plan — separate greenlight)

**Coverage-check on the country lead.** The spec §2/§3 mention a cross-read coverage check. It reuses `article_read.cross_read` (a paid LLM pass) on the lead thread's ≥2 readable bodies, same rule as the seal (`daily_publication.py:865-890`). Deferred to keep the on-demand paid-LLM surface minimal for the MVP — the excerpts already deliver the source-text depth. When greenlit: add a `coverage_check` computation to `fetch_country_edition` (lead = `ranked[0]`), attach to the payload, and render it with the existing coverage-check box (`BriefNewspaper.tsx:1493-1517`).

**Richer under-the-radar.** Current `under_radar` = country-scoped coverage-gaps (categories with domestic signal but 0 gate-kept). A country-scoped attention-eclipse (`attention_eclipse._ECLIPSE_SQL` + a country predicate) is a more nuanced signal but needs the cross-story global framing reworked for one country — a follow-up.
```
