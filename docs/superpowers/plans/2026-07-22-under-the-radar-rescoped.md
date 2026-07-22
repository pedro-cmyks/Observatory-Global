# Under the Radar — re-scoped coverage gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the L2 dock's mislabeled "UNDER THE RADAR" tab (today an attention-eclipse detector that is empty on diffuse days) into a coverage-gap lens that re-scopes to the active focus — closing the only dock panel that ignores focus.

**Architecture:** Extract the duplicated coverage-gap SQL (`briefing.py` global + `country_edition.py` country) into one canonical service, expose it as `GET /api/v2/attention/coverage-gaps?country=&hours=`, and consume it from a new dock component that derives its country scope from the shared `useFocusRelation` idiom already used by AnomalyPanel/MarketsPanel. The gap card markup is extracted from BriefNewspaper so Brief and dock render identically from one component.

**Tech Stack:** Python 3 / FastAPI / asyncpg (backend), React 18 + TypeScript + vanilla CSS (frontend), pytest + vitest.

**Spec:** `docs/superpowers/specs/2026-07-22-under-the-radar-rescoped-coverage-gaps-design.md`

**Deviation from spec (documented):** no Redis cache in v1. The sibling attention routers (`attention_eclipse.py`, `attention_threads.py`) do not cache, the gap queries are small aggregates, and the client fetches once per scope change. Revisit if load shows need.

**Commands:**
- Backend tests: `cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py -v`
- Frontend tests: `cd frontend-v2 && npx vitest run src/lib/coverageGaps.test.ts`
- Frontend build: `cd frontend-v2 && npm run build`

**Two environment gotchas (measured 2026-07-22 — do not re-discover these):**
1. **Never `import app.routers.<name>` standalone.** It raises `AttributeError: partially initialized module 'app.routers.briefing' has no attribute 'router' (most likely due to a circular import)` — importing a router pulls `main_v2`, which re-imports the router. This is pre-existing and unrelated to this work. To check imports, use the entrypoint: `.venv/bin/python -c "import app.main_v2"`.
2. **Never run pytest across the whole `tests/` directory** (e.g. `pytest tests/ -k briefing`). Broad collection imports every test module and hangs. Always name the specific test files. Targeted runs are fast (18 tests in 0.74s).
3. `pytest.ini` wins over `pyproject.toml` in this repo, so asyncio mode is **STRICT** — every async test needs an explicit `@pytest.mark.asyncio` decorator.

---

### Task 1: Canonical coverage-gap service

**Files:**
- Create: `backend/app/services/coverage_gaps.py`
- Test: `backend/tests/test_coverage_gaps.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_coverage_gaps.py`:

```python
"""Coverage-gap service — the canonical 'what is a coverage gap' definition."""
import pytest

from app.services.coverage_gaps import (
    COUNTRY_GAPS_SQL,
    GLOBAL_GAP_FLOOR,
    GLOBAL_GAPS_SQL,
    country_gap_floor,
    fetch_coverage_gaps,
    gap_status,
)


class FakeConn:
    """Minimal asyncpg-conn stub: records the calls, returns canned rows."""

    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows


def test_gap_status_gate_pending_when_nothing_scored():
    assert gap_status(0) == "gate_pending"


def test_gap_status_none_verified_when_scored():
    assert gap_status(280) == "none_verified"


def test_country_gap_floor_defaults_to_8(monkeypatch):
    monkeypatch.delenv("ATLAS_COUNTRY_GAP_MIN", raising=False)
    assert country_gap_floor() == 8


def test_country_gap_floor_reads_env(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "15")
    assert country_gap_floor() == 15


@pytest.mark.asyncio
async def test_global_scope_uses_global_sql_and_floor():
    conn = FakeConn([
        {"slug": "telecom-shutdown", "label": "Telecom or internet shutdown",
         "raw_signals": 280, "verified": 0, "scored": 280},
    ])
    gaps = await fetch_coverage_gaps(conn, hours=24, with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == GLOBAL_GAPS_SQL
    assert args == (24, GLOBAL_GAP_FLOOR)
    assert gaps == [{
        "slug": "telecom-shutdown",
        "label": "Telecom or internet shutdown",
        "raw_signals": 280,
        "verified": 0,
        "scored": 280,
        "status": "none_verified",
        "extended_receipts": [],
    }]


@pytest.mark.asyncio
async def test_country_scope_uses_country_sql_with_cc_and_floor(monkeypatch):
    monkeypatch.setenv("ATLAS_COUNTRY_GAP_MIN", "8")
    conn = FakeConn([
        {"slug": "mining-safety", "label": "Mining and resource safety crisis",
         "raw_signals": 12, "verified": 0, "scored": 0},
    ])
    gaps = await fetch_coverage_gaps(conn, hours=24, country="CO", with_receipts=False)

    sql, args = conn.calls[0]
    assert sql == COUNTRY_GAPS_SQL
    assert args == (24, "CO", 8)
    assert gaps[0]["status"] == "gate_pending"


@pytest.mark.asyncio
async def test_empty_window_returns_empty_list():
    conn = FakeConn([])
    assert await fetch_coverage_gaps(conn, hours=24, with_receipts=False) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.coverage_gaps'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/services/coverage_gaps.py`:

```python
"""Canonical coverage-gap definition (the "Under the Radar" substrate).

A COVERAGE GAP = an Atlas category that received real signal in the window but
had ZERO rows clear the quality gate — "attention without verified coverage",
the wedge's "what is missing". Honest by construction: a raw-count floor avoids
thin-noise rows, and `gate_pending` (nothing scored yet) is labeled separately
from `none_verified` (scored, none admitted) — never conflated with "rejected".

This module is the ONE definition. Previously the SQL was duplicated in
`routers/briefing.py` (global) and `services/country_edition.py` (country);
both now import from here, as does GET /api/v2/attention/coverage-gaps.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Global floor: raw >= 20 in the window (thin-noise guard).
GLOBAL_GAP_FLOOR = 20

GLOBAL_GAPS_SQL = """
    SELECT t.slug, t.label,
           COUNT(*)::int AS raw_signals,
           COUNT(*) FILTER (WHERE a.gate_kept)::int AS verified,
           COUNT(*) FILTER (WHERE a.gate_score IS NOT NULL)::int AS scored
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
    GROUP BY t.slug, t.label
    HAVING COUNT(*) >= $2
       AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
    ORDER BY raw_signals DESC
    LIMIT 6
"""

# Country scope adds the signals_v2 join for the country predicate and uses a
# lower floor (per-country volume is smaller than global).
COUNTRY_GAPS_SQL = """
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

# The strongest rows the ~75%-precision extended model recovers from a gap's raw
# pool — read as leads, never as verified evidence.
EXTENDED_RECEIPTS_SQL = """
    SELECT s.headline, s.source_name AS source,
           s.source_url AS url,
           a.gate_score::float AS gate_score
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s ON s.id = a.signal_id
    WHERE t.slug = $1
      AND a.assigned_at > NOW() - ($2::int * INTERVAL '1 hour')
      AND a.gate_score >= $3
    ORDER BY a.gate_score DESC
    LIMIT 40
"""


def country_gap_floor() -> int:
    """Per-country raw floor. Tunable via ATLAS_COUNTRY_GAP_MIN (default 8)."""
    return int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))


def gap_status(scored: int) -> str:
    """`gate_pending` = not yet scored (NOT rejected); else `none_verified`."""
    return "gate_pending" if scored == 0 else "none_verified"


async def attach_extended_receipts(conn, gap_rows: list[dict], hours: int) -> dict[str, list]:
    """Best-effort extended receipts per gap slug, keyed by slug.

    Guarded PER GAP (the delight lesson): one failing query must never blank the
    whole section — a failure just means that gap carries no receipts.
    """
    out: dict[str, list] = {}
    if not gap_rows:
        return out
    from app.routers.themes import _extended_gate_thresholds
    from app.services.gap_receipts import GAP_RECEIPTS_K, pick_extended_receipts

    per_topic_ext, _global_ext = _extended_gate_thresholds()
    for gap_row in gap_rows:
        slug = gap_row["slug"]
        ext_thr = per_topic_ext.get(slug)
        if ext_thr is None:
            continue
        try:
            ext_rows = await conn.fetch(EXTENDED_RECEIPTS_SQL, slug, hours, float(ext_thr))
            out[slug] = pick_extended_receipts(
                [dict(r) for r in ext_rows], float(ext_thr), GAP_RECEIPTS_K
            )
        except Exception:
            logger.exception("gap receipts query failed for %s", slug)
    return out


async def fetch_coverage_gaps(
    conn,
    *,
    hours: int,
    country: str | None = None,
    global_floor: int = GLOBAL_GAP_FLOOR,
    country_floor: int | None = None,
    with_receipts: bool = True,
) -> list[dict]:
    """Assembled coverage gaps for one scope: global (country=None) or country."""
    if country:
        floor = country_gap_floor() if country_floor is None else country_floor
        rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, country, floor)
    else:
        rows = await conn.fetch(GLOBAL_GAPS_SQL, hours, global_floor)

    gaps = [{
        "slug": r["slug"],
        "label": r["label"],
        "raw_signals": r["raw_signals"],
        "verified": r["verified"],
        "scored": r["scored"],
        "status": gap_status(r["scored"]),
        "extended_receipts": [],
    } for r in rows]

    if with_receipts and gaps:
        by_slug = await attach_extended_receipts(conn, gaps, hours)
        for gap in gaps:
            gap["extended_receipts"] = by_slug.get(gap["slug"], [])
    return gaps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py -v`
Expected: PASS — 7 passed

If the async tests error with "async def functions are not natively supported", the repo's pytest lacks asyncio auto-mode; add `@pytest.mark.asyncio` (already present) and confirm `pytest-asyncio` is installed: `cd backend && .venv/bin/python -m pip show pytest-asyncio`. If missing, run the async assertions through `asyncio.run(...)` inside sync test functions instead.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/coverage_gaps.py backend/tests/test_coverage_gaps.py
git commit -m "feat(gaps): canonical coverage-gap service (one definition, global + country)"
```

---

### Task 2: `GET /api/v2/attention/coverage-gaps` endpoint

**Files:**
- Modify: `backend/app/routers/attention_threads.py` (append a new route at end of file)
- Test: `backend/tests/test_coverage_gaps.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_coverage_gaps.py`:

```python
@pytest.mark.asyncio
async def test_endpoint_returns_contract_and_global_scope(monkeypatch):
    from app.routers import attention_threads as at

    async def fake_fetch(conn, *, hours, country=None, **kw):
        return [{"slug": "cyber", "label": "Cyberattack on infrastructure",
                 "raw_signals": 189, "verified": 0, "scored": 189,
                 "status": "none_verified", "extended_receipts": []}]

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool())

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["contract"] == "coverage-gaps-v0"
    assert out["scope"] == "global"
    assert out["country"] is None
    assert out["gaps"][0]["slug"] == "cyber"


@pytest.mark.asyncio
async def test_endpoint_country_scope_uppercases_cc(monkeypatch):
    from app.routers import attention_threads as at
    seen = {}

    async def fake_fetch(conn, *, hours, country=None, **kw):
        seen["country"] = country
        return []

    monkeypatch.setattr(at, "fetch_coverage_gaps", fake_fetch)
    monkeypatch.setattr(at.db, "pool", _FakePool())

    out = await at.get_coverage_gaps(country="co", hours=24)
    assert seen["country"] == "CO"
    assert out["scope"] == "country"
    assert out["country"] == "CO"


@pytest.mark.asyncio
async def test_endpoint_degrades_when_db_unavailable(monkeypatch):
    from app.routers import attention_threads as at
    monkeypatch.setattr(at.db, "pool", None)

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["gaps"] == []
    assert "database unavailable" in out["notes"]


@pytest.mark.asyncio
async def test_endpoint_degrades_on_query_failure(monkeypatch):
    from app.routers import attention_threads as at

    async def boom(conn, *, hours, country=None, **kw):
        raise RuntimeError("statement timeout")

    monkeypatch.setattr(at, "fetch_coverage_gaps", boom)
    monkeypatch.setattr(at.db, "pool", _FakePool())

    out = await at.get_coverage_gaps(country=None, hours=24)
    assert out["gaps"] == []
    assert any("unavailable" in n for n in out["notes"])
```

Add this stub near `FakeConn` at the top of the same test file:

```python
class _FakeAcquire:
    async def __aenter__(self):
        class _C:
            async def execute(self, *a, **k):
                return None
        return _C()

    async def __aexit__(self, *a):
        return False


class _FakePool:
    def acquire(self):
        return _FakeAcquire()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py -v -k endpoint`
Expected: FAIL — `AttributeError: module 'app.routers.attention_threads' has no attribute 'get_coverage_gaps'`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routers/attention_threads.py`, add to the existing import block (after the `app.services.silent_risk` import):

```python
from app.services.coverage_gaps import fetch_coverage_gaps
```

Then append at the end of the file:

```python
@router.get("/api/v2/attention/coverage-gaps")
async def get_coverage_gaps(
    country: str | None = Query(None, min_length=2, max_length=2),
    hours: int = Query(24, ge=1, le=168),
) -> dict:
    """Coverage gaps for one scope — the "Under the Radar" substrate.

    Global (no country) mirrors the Brief's "What is missing"; with a country it
    is the domestic band. Same definition either way (services/coverage_gaps).
    Degrades to an empty list — a secondary lens must never 500 the dock.
    """
    cc = country.upper() if country else None
    scope = "country" if cc else "global"
    notes: list[str] = []
    gaps: list[dict] = []

    if db.pool is None:
        return {"contract": "coverage-gaps-v0", "scope": scope, "country": cc,
                "hours": hours, "gaps": [], "notes": ["database unavailable"],
                "generated_at": datetime.now(timezone.utc).isoformat()}

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 12000")
            gaps = await fetch_coverage_gaps(conn, hours=hours, country=cc)
    except Exception:
        logger.exception("coverage-gaps query failed scope=%s cc=%s", scope, cc)
        notes.append("coverage gaps temporarily unavailable")

    if not gaps and not notes:
        notes.append(
            "no coverage gaps in this window — every category with signal cleared the gate"
        )

    return {
        "contract": "coverage-gaps-v0",
        "scope": scope,
        "country": cc,
        "hours": hours,
        "gaps": gaps,
        "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
```

If `attention_threads.py` has no module logger, add near the top imports:

```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py -v`
Expected: PASS — all tests pass (11 total)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/attention_threads.py backend/tests/test_coverage_gaps.py
git commit -m "feat(api): GET /api/v2/attention/coverage-gaps (global + country scope)"
```

---

### Task 3: Refactor `briefing.py` onto the shared definition

**Files:**
- Modify: `backend/app/routers/briefing.py:287-336` (gap query + receipts loop), `briefing.py:831` (status line)

- [ ] **Step 1: Add the import**

In `backend/app/routers/briefing.py`, add to the imports at the top of the file:

```python
from app.services.coverage_gaps import (
    GLOBAL_GAP_FLOOR,
    GLOBAL_GAPS_SQL,
    fetch_extended_receipts_by_slug,
    gap_status,
)
```

> **Note (post-Task-1 review):** the receipts helper was renamed from
> `attach_extended_receipts(conn, gap_rows, hours)` to
> `fetch_extended_receipts_by_slug(conn, slugs, hours, timeout=None)` — it takes a
> list of slug STRINGS now, and it does not mutate anything (the caller attaches).
> `_fetch_section` takes a query STRING and runs `conn.fetch` itself, so it cannot
> wrap a coroutine — that is why the primary query below still goes through it
> (preserving `degraded_segments` registration) while the receipts call does not.

- [ ] **Step 2: Replace the inline gap SQL**

Replace lines 287-300 (the `coverage_gaps = await _fetch_section(...)` call with its inline SQL string) with:

```python
        coverage_gaps = await _fetch_section(
            conn, degraded_segments, "coverage_gaps",
            GLOBAL_GAPS_SQL, hours, GLOBAL_GAP_FLOOR,
        )
```

Keep the explanatory comment block above it (lines 282-286) unchanged.

- [ ] **Step 3: Replace the inline receipts loop**

Replace lines 302-336 (the `gap_receipts_by_slug` block, from the comment through the `except Exception: logger.exception(...)`) with:

```python
        # Gap-box extended receipts (measured 2026-07-16, docs/research/gap-pool):
        # the 2-3 most newsworthy hits in a gap category sit above its extended
        # (~75%) threshold and are recoverable now — max K=3, tier-labeled.
        # Guarded per gap inside the shared helper.
        gap_receipts_by_slug = await fetch_extended_receipts_by_slug(
            conn, [g["slug"] for g in coverage_gaps], hours
        )
```

- [ ] **Step 4: Use the shared status helper**

At `briefing.py:831`, replace the inline ternary:

```python
"status": "gate_pending" if scored == 0 else "none_verified",
```

with:

```python
"status": gap_status(scored),
```

(If the local variable is named differently in that comprehension, pass whatever holds the scored count — the expression must stay semantically identical.)

- [ ] **Step 5: Verify parity against production**

Check the module still imports cleanly — via the entrypoint, never the router directly (see gotcha 1 in the header):

```bash
cd backend && .venv/bin/python -c "import app.main_v2; print('ok')"
```
Expected: prints `ok` (a CORS warning line above it is normal)

Run the affected test files by name (never the whole `tests/` dir — see gotcha 2):
```bash
cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py tests/test_daily_publication_artifact.py -q
```
Expected: PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/briefing.py
git commit -m "refactor(briefing): coverage gaps read the shared canonical definition"
```

---

### Task 4: Refactor `country_edition.py` onto the shared definition

**Files:**
- Modify: `backend/app/services/country_edition.py:30-50` (delete `_COUNTRY_GAPS_SQL`), `country_edition.py:144,153` (call site)

- [ ] **Step 1: Add the import and delete the duplicate SQL**

In `backend/app/services/country_edition.py`, add to the imports:

```python
from app.services.coverage_gaps import COUNTRY_GAPS_SQL, country_gap_floor
```

Delete lines 30-50 (the `_COUNTRY_GAPS_SQL` comment block and constant).

- [ ] **Step 2: Update the call site**

Replace line 144:

```python
    gap_min = int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))
```

with:

```python
    gap_min = country_gap_floor()
```

Replace line 153:

```python
            gap_rows = await conn.fetch(_COUNTRY_GAPS_SQL, hours, cc, gap_min)
```

with:

```python
            gap_rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, cc, gap_min)
```

- [ ] **Step 3: Verify it imports and the country-edition tests pass**

Run (entrypoint import + named test files — see the header gotchas):
```bash
cd backend && .venv/bin/python -c "import app.main_v2; print('ok')" && .venv/bin/python -m pytest tests/test_country_edition.py tests/test_coverage_gaps.py -q
```
Expected: prints `ok`; all tests PASS

If `os` becomes unused in `country_edition.py` after this change, leave the import alone only if other code uses it — otherwise remove the now-dead `import os` line (check with `rg -n "os\." backend/app/services/country_edition.py`).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/country_edition.py
git commit -m "refactor(country-edition): coverage gaps read the shared canonical definition"
```

---

### Task 5: Frontend coverage-gaps lib

**Files:**
- Create: `frontend-v2/src/lib/coverageGaps.ts`
- Test: `frontend-v2/src/lib/coverageGaps.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend-v2/src/lib/coverageGaps.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import {
  coverageGapsUrl,
  maxGapRaw,
  parseCoverageGaps,
  type CoverageGap,
} from './coverageGaps'

const GAP: CoverageGap = {
  slug: 'telecom-shutdown',
  label: 'Telecom or internet shutdown',
  raw_signals: 280,
  verified: 0,
  scored: 280,
  status: 'none_verified',
  extended_receipts: [],
}

describe('coverageGapsUrl', () => {
  it('omits country when global', () => {
    expect(coverageGapsUrl(null, 24)).toBe('/api/v2/attention/coverage-gaps?hours=24')
  })

  it('includes country when scoped', () => {
    expect(coverageGapsUrl('CO', 24)).toBe('/api/v2/attention/coverage-gaps?country=CO&hours=24')
  })
})

describe('parseCoverageGaps', () => {
  it('accepts the v0 contract', () => {
    const parsed = parseCoverageGaps({
      contract: 'coverage-gaps-v0', scope: 'global', country: null, hours: 24, gaps: [GAP],
    })
    expect(parsed?.gaps).toHaveLength(1)
    expect(parsed?.scope).toBe('global')
  })

  it('rejects a foreign contract', () => {
    expect(parseCoverageGaps({ contract: 'something-else', gaps: [GAP] })).toBeNull()
  })

  it('rejects null / non-object payloads', () => {
    expect(parseCoverageGaps(null)).toBeNull()
    expect(parseCoverageGaps('nope')).toBeNull()
  })

  it('defaults a missing gaps array to empty', () => {
    const parsed = parseCoverageGaps({ contract: 'coverage-gaps-v0', scope: 'global' })
    expect(parsed?.gaps).toEqual([])
  })
})

describe('maxGapRaw', () => {
  it('is at least 1 so the bar never divides by zero', () => {
    expect(maxGapRaw([])).toBe(1)
  })

  it('returns the largest raw count', () => {
    expect(maxGapRaw([GAP, { ...GAP, slug: 'b', raw_signals: 33 }])).toBe(280)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/coverageGaps.test.ts`
Expected: FAIL — cannot resolve `./coverageGaps`

- [ ] **Step 3: Write minimal implementation**

Create `frontend-v2/src/lib/coverageGaps.ts`:

```ts
// Coverage gaps = the "Under the Radar" substrate. A category that got real
// signal in the window but had ZERO rows clear the quality gate — "attention
// without verified coverage". Served by GET /api/v2/attention/coverage-gaps,
// global or scoped to one country. Same definition the Brief renders.

export interface GapReceipt {
  headline: string
  source: string | null
  url: string | null
  gate_score: number
}

export interface CoverageGap {
  slug: string
  label: string
  raw_signals: number
  verified: number
  scored: number
  status: 'gate_pending' | 'none_verified'
  extended_receipts?: GapReceipt[]
}

export interface CoverageGapsData {
  contract: string
  scope: 'global' | 'country'
  country: string | null
  hours: number
  gaps: CoverageGap[]
  notes: string[]
}

export const COVERAGE_GAPS_CONTRACT = 'coverage-gaps-v0'

export function coverageGapsUrl(country?: string | null, hours = 24): string {
  const params = new URLSearchParams()
  if (country) params.set('country', country)
  params.set('hours', String(hours))
  return `/api/v2/attention/coverage-gaps?${params.toString()}`
}

/** Contract-validated parse. Returns null for anything we do not recognise —
 *  the caller renders an honest empty state rather than guessing. */
export function parseCoverageGaps(payload: unknown): CoverageGapsData | null {
  if (!payload || typeof payload !== 'object') return null
  const p = payload as Record<string, unknown>
  if (p.contract !== COVERAGE_GAPS_CONTRACT) return null
  return {
    contract: COVERAGE_GAPS_CONTRACT,
    scope: p.scope === 'country' ? 'country' : 'global',
    country: typeof p.country === 'string' ? p.country : null,
    hours: typeof p.hours === 'number' ? p.hours : 24,
    gaps: Array.isArray(p.gaps) ? (p.gaps as CoverageGap[]) : [],
    notes: Array.isArray(p.notes) ? (p.notes as string[]) : [],
  }
}

/** Shared denominator for the gap bars — at least 1 so we never divide by zero. */
export function maxGapRaw(gaps: CoverageGap[]): number {
  return Math.max(1, ...gaps.map(g => g.raw_signals))
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/coverageGaps.test.ts`
Expected: PASS — 8 tests

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/coverageGaps.ts frontend-v2/src/lib/coverageGaps.test.ts
git commit -m "feat(gaps): frontend coverage-gaps lib (url, contract parse, bar scale)"
```

---

### Task 6: Extract the shared `CoverageGapCard`

**Files:**
- Create: `frontend-v2/src/components/CoverageGapCard.tsx`
- Create: `frontend-v2/src/components/CoverageGapCard.css`
- Modify: `frontend-v2/src/pages/BriefNewspaper.css:1019-1195` and `:2090` (move the gap rules out)
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx:1647-1698` (render the card)

- [ ] **Step 1: Create the card component**

Create `frontend-v2/src/components/CoverageGapCard.tsx`:

```tsx
// One coverage gap, rendered identically wherever gaps appear: the L1 Brief's
// "What is missing" and the L2 dock's "Under the Radar" lens. Class names are
// the Brief's originals so the shipped visual is preserved byte-for-byte; the
// stylesheet moved here supplies console fallbacks for the reader-theme vars.
import { decodeEntities } from '../lib/decodeEntities'
import type { CoverageGap } from '../lib/coverageGaps'
import './CoverageGapCard.css'

interface Props {
  gap: CoverageGap
  /** Largest raw_signals in the set — the shared bar denominator. */
  maxRaw: number
  onOpen: (slug: string) => void
}

export function CoverageGapCard({ gap: g, maxRaw, onOpen }: Props) {
  return (
    <div className="brief-gap-cell">
      <button
        className="brief-gap"
        onClick={() => onOpen(g.slug)}
        data-tip="Category with real coverage in the last 24h where NOTHING cleared the quality gate — attention without verified evidence. 'gate pending' means not yet scored, not rejected."
      >
        <span className="brief-gap-label">{decodeEntities(g.label)}</span>
        <span className="brief-gap-cat">Coverage gap</span>
        <span className="brief-gauge">
          <span><span className="num raw">{g.raw_signals.toLocaleString()}</span><span className="lbl">raw signals</span></span>
          <span><span className="num ver">{g.verified}</span><span className="lbl">verified</span></span>
        </span>
        <span className="brief-gbar" aria-hidden="true" style={{ width: `${Math.max(8, Math.round((g.raw_signals / maxRaw) * 100))}%` }}>
          <i style={{ width: g.raw_signals > 0 ? `${Math.round((g.verified / g.raw_signals) * 100)}%` : '0%' }} />
        </span>
        <span className={`brief-gap-status brief-gap-status--${g.status}`}>
          <span className="d" />
          {g.status === 'gate_pending' ? 'gate pending — not yet scored' : `${g.verified} of ${g.raw_signals.toLocaleString()} admitted — none cleared the quality gate`}
        </span>
      </button>
      {(g.extended_receipts?.length ?? 0) > 0 && (
        <div className="brief-gap-receipts">
          <span className="brief-gap-receipts-label" data-tip="The strongest rows the ~75%-precision extended model recovers from this gap's raw pool (measured slice precision 29-43% — read as leads, not verified evidence).">
            UNVERIFIED · EXTENDED (~75% MODEL)
          </span>
          {g.extended_receipts!.map(r => (
            <a
              key={r.headline}
              className="brief-gap-receipt"
              href={r.url ?? undefined}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="brief-gap-receipt-headline">{decodeEntities(r.headline)}</span>
              <span className="brief-gap-receipt-meta">{r.source ?? 'source unknown'} · score {r.gate_score.toFixed(2)} ↗</span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Move the gap CSS into the card stylesheet**

Cut the rule block from `frontend-v2/src/pages/BriefNewspaper.css` lines **1019-1195** (every rule from `.brief-gapgrid {` through the end of `.brief-gap-status .d { ... }`) plus the single rule at line **2090** (`.brief-gap-meta { ... }`), and paste them verbatim into a new `frontend-v2/src/components/CoverageGapCard.css` under this header:

```css
/* Coverage-gap card — shared by the L1 Brief ("What is missing") and the L2
   dock ("Under the Radar"). Rules moved verbatim out of BriefNewspaper.css so
   both surfaces render one definition.

   The Brief supplies the reader-theme vars (--r-*, styles/readerTheme.css); the
   L2 console does not, so every reader var carries a console fallback
   (styles/variables.css). In the Brief the reader value wins and the visual is
   unchanged; in the console the fallback applies. */
```

Then, in the pasted rules only, apply exactly these substitutions:

| Find | Replace with |
|---|---|
| `var(--r-ink)` | `var(--r-ink, var(--color-text-primary))` |
| `var(--r-critical)` | `var(--r-critical, var(--color-accent-secondary))` |
| `var(--r-accent-2)` | `var(--r-accent-2, var(--color-accent-secondary))` |
| `var(--r-paper)` | `var(--r-paper, var(--color-bg-secondary))` |
| `var(--r-rule)` | `var(--r-rule, var(--color-border-subtle))` |

Leave any `--r-*` var not in this table alone if it already has a fallback; if you find one with no fallback and no row here, add `, var(--color-text-secondary)` as its fallback and note it in the commit body.

- [ ] **Step 3: Render the card from the Brief**

In `frontend-v2/src/pages/BriefNewspaper.tsx`, add the import near the other component imports:

```tsx
import { CoverageGapCard } from '../components/CoverageGapCard'
```

Replace the `{coverageGaps.map(g => ( ... ))}` block (lines 1651-1692, the entire `<div key={g.slug} className="brief-gap-cell">…</div>` expression) with:

```tsx
                                                {coverageGaps.map(g => (
                                                    <CoverageGapCard
                                                        key={g.slug}
                                                        gap={g}
                                                        maxRaw={maxGapRaw}
                                                        onOpen={(slug) => goToAtlas(`theme=${encodeURIComponent(slug)}`, 'gap_box')}
                                                    />
                                                ))}
```

Leave the surrounding `<div className="brief-gapgrid">`, the sub-kicker, the footref and the empty-state paragraph exactly as they are.

- [ ] **Step 4: Verify the build and the Brief visual is unchanged**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds with no TypeScript errors

Then start the preview and compare the Brief's "Under the Radar" panel against the pre-change screenshot:
```bash
cd frontend-v2 && npm run preview
```
Open `/brief`, go to the "Under the Radar" section, and confirm the gap cells render with the same layout, bar, colours and receipts as before.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/CoverageGapCard.tsx frontend-v2/src/components/CoverageGapCard.css frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/pages/BriefNewspaper.css
git commit -m "refactor(gaps): extract shared CoverageGapCard (Brief + dock render one component)"
```

---

### Task 7: The `UnderRadarLens` dock component

**Files:**
- Create: `frontend-v2/src/components/UnderRadarLens.tsx`
- Create: `frontend-v2/src/components/UnderRadarLens.css`

- [ ] **Step 1: Create the component**

Create `frontend-v2/src/components/UnderRadarLens.tsx`:

```tsx
// L2 Console "Under the Radar" lens — categories getting real signal that
// NOTHING has verified yet. Unlike the L1 Brief's global gap box, this
// RE-SCOPES to the active focus (#234): a focused country scopes directly, a
// focused person/thread scopes to its dominant country via the shared
// focus-relation context. Honest: when no relation resolves, it stays global.
import { useEffect, useState } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusRelation } from '../hooks/useFocusRelation'
import { resolveCountryName } from '../lib/countryNames'
import {
  type CoverageGap,
  coverageGapsUrl,
  maxGapRaw,
  parseCoverageGaps,
} from '../lib/coverageGaps'
import { CoverageGapCard } from './CoverageGapCard'
import './UnderRadarLens.css'

interface Props {
  onOpenTopic: (slug: string) => void
}

export function UnderRadarLens({ onOpenTopic }: Props) {
  const { filter } = useFocus()
  const relation = useFocusRelation()
  const activeCountry = filter.country
  const relationCountry = !activeCountry && relation.relationActive && relation.kind !== 'country'
    ? relation.dominantCountry : null
  const scopeCountry = activeCountry ?? relationCountry

  const [gaps, setGaps] = useState<CoverageGap[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let ignore = false
    setLoaded(false)
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 12000)
    fetch(coverageGapsUrl(scopeCountry, 24), { signal: ctrl.signal })
      .then(r => (r.ok ? r.json() : null))
      .then(payload => {
        const parsed = parseCoverageGaps(payload)
        if (!ignore) setGaps(parsed?.gaps ?? [])
      })
      .catch(() => { if (!ignore) setGaps([]) })
      .finally(() => { clearTimeout(timer); if (!ignore) setLoaded(true) })
    return () => { ignore = true; clearTimeout(timer); ctrl.abort() }
  }, [scopeCountry])

  const scopeName = scopeCountry ? resolveCountryName(scopeCountry) : null
  const denominator = maxGapRaw(gaps)

  return (
    <div className="under-radar-lens">
      <div className="url-scope-bar">
        <span className="url-scope-label">
          {scopeName ? `Gaps in ${scopeName}` : 'Gaps worldwide'}
        </span>
        {relationCountry && (
          <span className="url-scope-chip"
            data-tip={`Re-scoped to the focus's dominant country: ${resolveCountryName(relationCountry)}`}>
            {(relation.value || '').toUpperCase().slice(0, 14)} → {relationCountry}
          </span>
        )}
      </div>

      {gaps.length > 0 ? (
        <>
          <div className="url-gapgrid">
            {gaps.map(g => (
              <CoverageGapCard key={g.slug} gap={g} maxRaw={denominator} onOpen={onOpenTopic} />
            ))}
          </div>
          <p className="url-foot">
            Categories with real signal where nothing cleared the quality gate — attention
            without verified coverage. Leads, not certified evidence.
          </p>
        </>
      ) : (
        <div className="under-radar-empty">
          <p>
            {!loaded
              ? 'Checking what the pipeline sees but has not verified…'
              : scopeName
                ? `Nothing under the radar in ${scopeName} right now — every category with signal cleared the gate.`
                : 'Nothing under the radar — every category with signal cleared the gate this window.'}
          </p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend-v2/src/components/UnderRadarLens.css`:

```css
/* L2 console "Under the Radar" lens — terminal idiom, dock tab. The gap cells
   themselves are styled by CoverageGapCard.css (shared with the L1 Brief). */
.under-radar-lens {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px 10px;
    height: 100%;
    overflow-y: auto;
}

.url-scope-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.url-scope-label {
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-secondary, #9aa1ab);
}

.url-scope-chip {
    font-size: 0.68rem;
    letter-spacing: 0.04em;
    padding: 2px 6px;
    border-radius: 3px;
    border: 1px solid var(--color-border-subtle);
    color: var(--color-accent-secondary, #fbbf24);
    white-space: nowrap;
}

.url-gapgrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 8px;
}

.url-foot {
    margin: 0;
    font-size: 0.7rem;
    line-height: 1.4;
    color: var(--color-text-muted, #8a8f98);
}

.under-radar-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--color-text-muted, #8a8f98);
    font-size: 0.8rem;
    line-height: 1.5;
    padding: 18px;
    flex: 1;
}

.under-radar-empty p { margin: 0; }
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (the component is not mounted yet — this only proves it compiles)

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/UnderRadarLens.tsx frontend-v2/src/components/UnderRadarLens.css
git commit -m "feat(dock): UnderRadarLens — coverage gaps re-scoped to the active focus"
```

---

### Task 8: Wire the dock tab

**Files:**
- Modify: `frontend-v2/src/App.tsx:336` (tab union), `:2221-2227` (tab button), `:2270-2277` (mount)

- [ ] **Step 1: Rename the tab id in the state type**

At `frontend-v2/src/App.tsx:336`, replace:

```tsx
const [dockTab, setDockTab] = useState<'anomaly' | 'sources' | 'eclipse' | 'markets'>('anomaly')
```

with:

```tsx
const [dockTab, setDockTab] = useState<'anomaly' | 'sources' | 'radar' | 'markets'>('anomaly')
```

- [ ] **Step 2: Update the tab button**

Replace the button at lines 2221-2227 with:

```tsx
              <button
                className={`dock-tab ${dockTab === 'radar' ? 'active' : ''}`}
                onClick={() => { track('dock_tab', { tab: 'radar' }); setDockTab('radar') }}
                data-tip="Under the radar: categories getting real signal that nothing has verified yet — re-scopes to your active focus"
              >
                UNDER THE RADAR
              </button>
```

- [ ] **Step 3: Mount the new lens**

Replace the mount block at lines 2270-2277 with:

```tsx
            {dockTab === 'radar' && (
              <PanelErrorBoundary
                key={`radar-${filter.country ?? ''}-${filter.person ?? ''}-${filter.theme ?? ''}`}
                panelName="UNDER THE RADAR"
              >
                <UnderRadarLens
                  onOpenTopic={(slug) => handleResearchOpenThread(slug, slug)}
                />
              </PanelErrorBoundary>
            )}
```

- [ ] **Step 4: Swap the import**

Replace the `EclipseLens` import line in `App.tsx` with:

```tsx
import { UnderRadarLens } from './components/UnderRadarLens'
```

If `handleEclipseInvestigate` is now unused, leave it in place only if something else calls it — check with `rg -n "handleEclipseInvestigate" frontend-v2/src/App.tsx`. If it has no remaining callers, delete its definition. `EclipseLens.tsx` and `EclipseLens.css` stay on disk (the eclipse dramatic-moment follow-up repurposes them) — do not delete them.

- [ ] **Step 5: Verify the build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds with no unused-import or type errors

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "feat(dock): Under the Radar tab serves re-scoped coverage gaps (eclipse leaves the tab)"
```

---

### Task 9: Full verification

**Files:** none modified (verification only)

- [ ] **Step 1: Run the whole frontend test suite**

Run: `cd frontend-v2 && npx vitest run`
Expected: PASS — all suites green, including the new `coverageGaps.test.ts`

- [ ] **Step 2: Run the backend tests**

Run (named files only — broad `tests/` collection hangs, see header gotcha 2):
`cd backend && .venv/bin/python -m pytest tests/test_coverage_gaps.py tests/test_country_edition.py tests/test_gap_receipts.py tests/test_daily_publication_artifact.py -q`
Expected: PASS

- [ ] **Step 3: Smoke the endpoint against a running backend**

Start the backend locally (or deploy to Fly first), then:

```bash
curl -s 'http://localhost:8000/api/v2/attention/coverage-gaps?hours=24' | jq '{contract, scope, n:(.gaps|length)}'
curl -s 'http://localhost:8000/api/v2/attention/coverage-gaps?country=US&hours=24' | jq '{contract, scope, country, n:(.gaps|length)}'
```
Expected: `contract: "coverage-gaps-v0"`, `scope: "global"` then `"country"`, `n` a small integer (0 is a valid honest answer).

- [ ] **Step 4: Browser-verify the re-scope**

With the frontend preview running, open the L2 console and check, in order:
1. Open the UNDER THE RADAR tab with no focus → gap cells render (or the honest empty note), scope label reads "Gaps worldwide".
2. Click a country on the map → the tab re-fetches, scope label reads "Gaps in \<Country\>".
3. Focus a person → the chip `PERSON → CC` appears and the gaps change to that country's.
4. Clear the focus → returns to worldwide.
5. Console shows zero errors throughout.

- [ ] **Step 5: Browser-verify the Brief did not regress**

Open `/brief` → "Under the Radar" section → gap cells and their extended receipts look exactly as before the refactor.

- [ ] **Step 6: Commit any verification fixes**

```bash
git add -A
git commit -m "test: verify under-the-radar re-scope end to end"
```

---

## Self-review

**Spec coverage:**
- Spec §1 (shared service + endpoint) → Tasks 1, 2; callers refactored → Tasks 3, 4.
- Spec §2 (re-scope semantics, dominantCountry for person/thread, hours fixed 24) → Task 7.
- Spec §3 (UnderRadarLens, shared renderer, tab rename, empty states) → Tasks 6, 7, 8.
- Spec §4 (eclipse removal, EclipseLens kept on disk) → Task 8 Step 4.
- Spec §5 (error handling both sides) → Task 2 Step 3 (backend degrade), Task 7 Step 1 (frontend catch).
- Spec §6 (tests) → Tasks 1, 2, 5 + Task 9.
- Spec's Redis cache → intentionally deferred, documented in the header.

**Placeholder scan:** no TBD/TODO; every code step carries real code; the two conditional steps (unused `os` import, unused `handleEclipseInvestigate`) give the exact `rg` command to decide.

**Type consistency:** `CoverageGap` / `GapReceipt` defined in Task 5 are the types consumed in Tasks 6 and 7. `fetch_coverage_gaps(conn, *, hours, country, ...)` defined in Task 1 is called with the same keywords in Task 2. `maxGapRaw()` (lib fn, Task 5) vs `maxRaw` (card prop, Task 6) vs `maxGapRaw` (existing Brief local, Task 6 Step 3) are three distinct names — the Brief's local variable keeps its existing name and is passed as the `maxRaw` prop, which is correct and intentional.
