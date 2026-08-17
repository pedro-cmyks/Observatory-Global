# Daily Reader — Tranches 1+2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure where `/api/v2/briefing`'s 21.7s goes (Tranche 1), then recompose the Brief into the day-anatomy — near/changed/odd/world segments over data already served, no profile, no lead (Tranche 2).

**Architecture:** T1 instruments the existing `_fetch_section` chokepoint (every briefing section already flows through it) and produces a measured artifact — the fix is chosen AFTER the numbers exist, in its own plan. T2 is three pure frontend libs (place, last-read, composer) + one integration pass in BriefNewspaper behind a one-line kill-switch. Empty segments vanish; "El mundo" wraps the three existing sections untouched (the §6.2 firewall by construction).

**Tech Stack:** FastAPI/asyncpg (backend), React + vitest pure libs (frontend), no new tables, no new endpoints.

**Spec:** `docs/superpowers/specs/2026-08-17-daily-reader-design.md`. Tranches 3–6 (composition change, lead rule, interest profile, corrected edition) get their own plans — the lead rule needs 14 days of history that starts accumulating only after T2 ships, and the perf fix needs T1's numbers.

**Shared-branch rule:** every commit is pathspec-only (`git add <files>`, never `git add -A`) — parallel agents share this worktree.

---

## Tranche 1 — profile the 21.7s (measurement only, no behavior change)

### Task 1: Per-section timing in `_fetch_section` + `?profile=1`

**Files:**
- Modify: `backend/app/routers/briefing.py` (handler at `:151`, `_fetch_section` at `:93`)
- Test: `backend/tests/test_briefing_profile.py` (create)

The handler runs ~20 sequential `_fetch_section` calls on one connection behind a 900s Redis cache. We time each section at the chokepoint, log one line always, and expose `meta.section_timings` only when `?profile=1` (which also bypasses the cache read AND write, so profiled payloads never poison the cache).

- [ ] **Step 1: Write the failing test**

```python
"""Timing instrumentation for the briefing profiler (spec §9, T1).

The dict passed as `timings` collects {section_name: elapsed_ms}. It must
record for BOTH the fetchrow and fetch paths, and record even when the
section degrades (a degraded section that took 14.9s is exactly what we
are hunting).
"""
import asyncio
import pytest

from app.routers.briefing import _fetch_section


class FakeConn:
    def __init__(self, delay_s=0.0, fail=False):
        self.delay_s = delay_s
        self.fail = fail

    async def _go(self):
        await asyncio.sleep(self.delay_s)
        if self.fail:
            raise RuntimeError("boom")
        return [{"x": 1}]

    async def fetch(self, query, *args, timeout=None):
        return await self._go()

    async def fetchrow(self, query, *args, timeout=None):
        rows = await self._go()
        return rows[0]


@pytest.mark.asyncio
async def test_timings_recorded_for_fetch_path():
    timings, degraded = {}, []
    await _fetch_section(FakeConn(delay_s=0.01), degraded, "top_countries",
                         "SELECT 1", timings=timings)
    assert "top_countries" in timings
    assert timings["top_countries"] >= 10  # ms


@pytest.mark.asyncio
async def test_timings_recorded_even_when_section_degrades():
    timings, degraded = {}, []
    await _fetch_section(FakeConn(delay_s=0.01, fail=True), degraded,
                         "heat_countries", "SELECT 1", timings=timings)
    assert "heat_countries" in timings
    assert "heat_countries" in degraded  # existing degradation contract intact


@pytest.mark.asyncio
async def test_timings_none_is_the_default_and_changes_nothing():
    degraded = []
    rows = await _fetch_section(FakeConn(), degraded, "s", "SELECT 1")
    assert rows == [{"x": 1}]
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_briefing_profile.py -q`
Expected: FAIL — `TypeError: _fetch_section() got an unexpected keyword argument 'timings'`

- [ ] **Step 3: Implement the instrumentation**

In `_fetch_section` (read the real signature at `briefing.py:93` first; it takes `conn, degraded_segments, name, query, *args` plus row/timeout kwargs). Add `timings: dict | None = None` as a keyword-only param and wrap the entire body:

```python
async def _fetch_section(conn, degraded_segments, name, query, *args,
                         timings: dict | None = None, **kw):
    import time
    _t0 = time.perf_counter()
    try:
        ...existing body unchanged...
    finally:
        if timings is not None:
            timings[name] = round((time.perf_counter() - _t0) * 1000, 1)
```

(`finally`, not on the success path — a degraded section must still report its cost.)

In `get_briefing` (`:151`):

```python
async def get_briefing(hours: int = Query(24, ge=1, le=8760),
                       profile: bool = Query(False)):
    cache_key = f"briefing_data:{hours}"
    cache_ttl = 900 if hours <= 24 else 1800
    timings: dict[str, float] = {}
    if not profile and hasattr(app.state, "redis") and app.state.redis:
        ...existing cache read unchanged...
```

Thread `timings=timings` into EVERY `_fetch_section` call in the handler (~20 call sites — mechanical). The non-`_fetch_section` awaits (`fetch_threads` :614, `fetch_rising` :631, `fetch_gap` :636, `fetch_extended_receipts_by_slug` :316, the `to_regclass` probes) get manual brackets:

```python
_t0 = time.perf_counter()
top_threads = await fetch_threads(...)
timings["top_threads"] = round((time.perf_counter() - _t0) * 1000, 1)
```

Before the return: always log, attach only under profile, and never cache a profiled payload:

```python
total_ms = round(sum(timings.values()), 1)
logger.info("briefing sections total=%sms breakdown=%s", total_ms,
            dict(sorted(timings.items(), key=lambda kv: -kv[1])))
if profile:
    result["meta_profile"] = {"section_timings_ms": timings,
                              "sections_total_ms": total_ms}
if not profile and hasattr(app.state, "redis") and app.state.redis:
    ...existing cache write unchanged...
```

(Key is `meta_profile`, top-level — the payload has no `meta` object today; do not invent nesting the frontend might collide with.)

- [ ] **Step 4: Run the tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_briefing_profile.py tests/test_briefing*.py -q`
Expected: new tests PASS, existing briefing tests stay green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/briefing.py backend/tests/test_briefing_profile.py
git commit -m "perf(briefing): per-section timings + ?profile=1 (cache-bypassed) — instrument before choosing a fix"
```

### Task 2: Run the profile against prod, write the artifact

**Files:**
- Create: `docs/research/perf/2026-08-17-briefing-profile.md`

- [ ] **Step 1: Deploy the instrumentation**

Run: `./scripts/deploy-fly-api.sh` (from repo root). Expected: machine healthy.

- [ ] **Step 2: Capture cold and warm profiles**

```bash
# COLD (profile=1 bypasses cache read — this IS the 21.7s path)
curl -s -m 60 'https://atlas-api-pedro.fly.dev/api/v2/briefing?hours=24&profile=1' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); import pprint; pprint.pprint(d['meta_profile'])"
# Run 3× — one sample is not a measurement. Then the warm control:
time curl -s -o /dev/null 'https://atlas-api-pedro.fly.dev/api/v2/briefing?hours=24'
```

Expected shape: `sections_total_ms` ≈ the observed wall time; a sorted breakdown naming the top sections.

- [ ] **Step 3: Write the artifact**

`docs/research/perf/2026-08-17-briefing-profile.md` MUST contain: the 3 cold runs' tables (median per section, sorted), the warm control, the serialization sum-check (does Σ sections ≈ wall? if wall ≫ Σ, the cost is outside the sections — name where), and a **top-3 contributors** section with each one's SQL line range. NO fix proposal in the artifact — numbers only.

- [ ] **Step 4: Commit**

```bash
git add docs/research/perf/2026-08-17-briefing-profile.md
git commit -m "perf: briefing profile artifact — where the 21.7s actually goes"
```

### Task 3: STOP — decision gate

- [ ] **Step 1: Present the artifact's top-3 to Pedro with ONE recommended fix family** (spec §9 candidates: precompute-and-serve-artifact like `/universe` mig-091 · compute/serve split · plan-level index work). The fix is its own plan with G-VELOCIDAD (<3s cold) as its bar. **Do not build the fix inside this plan.**

---

## Tranche 2 — the day anatomy over today's data (no profile, no lead)

### Task 4: `readerPlace.ts` — declared place, never silently inferred

**Files:**
- Create: `frontend-v2/src/lib/readerPlace.ts`
- Test: `frontend-v2/src/lib/readerPlace.test.ts`

Spec §6: place is a DECLARED fact, country-grain only. Locale may *propose* the initial value but the proposal is flagged so the UI always shows it as changeable — a wrongly inferred, hidden place is the VE-chip defect class.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { loadReaderPlace, saveReaderPlace, PLACE_KEY } from './readerPlace'

describe('readerPlace', () => {
    beforeEach(() => localStorage.clear())

    it('proposes from locale region when nothing is stored, flagged as proposed', () => {
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })

    it('a stored choice wins over locale and is not "proposed"', () => {
        saveReaderPlace('VE')
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'VE', proposed: false })
    })

    it('no locale region and nothing stored → honest null, never a guess', () => {
        expect(loadReaderPlace('es')).toEqual({ country: null, proposed: false })
        expect(loadReaderPlace(undefined)).toEqual({ country: null, proposed: false })
    })

    it('clearing returns to the locale proposal', () => {
        saveReaderPlace('VE'); saveReaderPlace(null)
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })

    it('stored garbage is ignored, not served', () => {
        localStorage.setItem(PLACE_KEY, 'not-a-country-code')
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })
})
```

- [ ] **Step 2: Run to fail** — `cd frontend-v2 && npx vitest run src/lib/readerPlace.test.ts`. Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

```ts
// Reader place — a DECLARED fact, country-grain only (spec §6, 2026-08-17).
// Locale may PROPOSE the initial value; `proposed: true` obliges the UI to
// show it as changeable. Never inferred silently: a wrong hidden place is
// the same defect class as the VE chip on a Colombian story.
export const PLACE_KEY = 'atlas.reader.place.v1'

export interface ReaderPlace {
    country: string | null
    proposed: boolean
}

const CC = /^[A-Z]{2}$/

export function loadReaderPlace(locale?: string): ReaderPlace {
    try {
        const stored = localStorage.getItem(PLACE_KEY)
        if (stored && CC.test(stored)) return { country: stored, proposed: false }
    } catch { /* storage unavailable → fall through to proposal */ }
    const region = locale?.split('-')[1]?.toUpperCase()
    if (region && CC.test(region)) return { country: region, proposed: true }
    return { country: null, proposed: false }
}

export function saveReaderPlace(cc: string | null): void {
    try {
        if (cc && CC.test(cc.toUpperCase())) localStorage.setItem(PLACE_KEY, cc.toUpperCase())
        else localStorage.removeItem(PLACE_KEY)
    } catch { /* best-effort */ }
}
```

- [ ] **Step 4: Run to pass** — same command. Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/readerPlace.ts frontend-v2/src/lib/readerPlace.test.ts
git commit -m "feat(reader): declared place — country-grain, proposed-from-locale but never silent"
```

### Task 5: `lastRead.ts` — the last-read mark

**Files:**
- Create: `frontend-v2/src/lib/lastRead.ts`
- Test: `frontend-v2/src/lib/lastRead.test.ts`

Tranche-2 scope: the mark labels "desde tu última lectura · hace Nh" on the changed segment. The §8 multi-cut delta consumes it later; writing it now starts the clock. Epoch-ms compare, never ISO strings (the accounts-v1 lesson).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { touchLastRead, hoursSince, LAST_READ_KEY } from './lastRead'

describe('lastRead', () => {
    beforeEach(() => localStorage.clear())

    it('first visit: returns null previous, stores now', () => {
        expect(touchLastRead(1_000_000)).toBeNull()
        expect(localStorage.getItem(LAST_READ_KEY)).toBe('1000000')
    })

    it('second visit: returns the previous mark, advances the store', () => {
        touchLastRead(1_000_000)
        expect(touchLastRead(70_600_000)).toBe(1_000_000)
    })

    it('hoursSince rounds to one decimal; null previous → null, never 0', () => {
        expect(hoursSince(1_000_000, 69_400_000)).toBe(19)
        expect(hoursSince(null, 69_400_000)).toBeNull()
    })

    it('garbage in storage reads as first visit', () => {
        localStorage.setItem(LAST_READ_KEY, 'NaNope')
        expect(touchLastRead(5_000)).toBeNull()
    })
})
```

- [ ] **Step 2: Run to fail** — `npx vitest run src/lib/lastRead.test.ts`. Expected: FAIL.

- [ ] **Step 3: Implement**

```ts
// Last-read mark (spec §7/§8, 2026-08-17). Epoch-ms integers, NEVER ISO
// strings — Postgres re-serialization made lexicographic ISO compare a real
// bug in accounts-v1. A null previous mark is a first visit and is reported
// as null, never as "0 hours ago".
export const LAST_READ_KEY = 'atlas.reader.lastread.v1'

export function touchLastRead(nowMs: number): number | null {
    let prev: number | null = null
    try {
        const raw = localStorage.getItem(LAST_READ_KEY)
        if (raw != null) {
            const n = Number(raw)
            prev = Number.isFinite(n) && n > 0 ? n : null
        }
        localStorage.setItem(LAST_READ_KEY, String(nowMs))
    } catch { /* storage unavailable → behaves as first visit */ }
    return prev
}

export function hoursSince(prevMs: number | null, nowMs: number): number | null {
    if (prevMs == null) return null
    return Math.round(((nowMs - prevMs) / 3_600_000) * 10) / 10
}
```

- [ ] **Step 4: Run to pass.** Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/lastRead.ts frontend-v2/src/lib/lastRead.test.ts
git commit -m "feat(reader): last-read mark — epoch-ms, first visit is null not zero"
```

### Task 6: `dayAnatomy.ts` — the pure composer

**Files:**
- Create: `frontend-v2/src/lib/dayAnatomy.ts`
- Test: `frontend-v2/src/lib/dayAnatomy.test.ts`

The §3 anatomy as a pure function over data the Brief ALREADY fetches. Tranche-2 mapping (uses only served measurements — nothing invented):

| Segment | Source already in the Brief |
|---|---|
| `near` | country-edition threads for the declared place |
| `changed` | rising rows + threads whose `temporal_signature ∈ {new, resurrected}` |
| `odd` | coverage-gap rows (measured absence) + eclipse tier ≠ none |
| `world` | the three existing sections, untouched, always present |

Rules: fixed order `near → changed → odd → world`; an empty segment is ABSENT from the output (never rendered hollow); `world` is always present — it is the shared edition, and its presence is the §6.2 firewall.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest'
import { composeDayAnatomy, changedRowsFromThreads, READER_ANATOMY } from './dayAnatomy'

const base = { nearCount: 0, changedCount: 0, oddCount: 0 }

describe('composeDayAnatomy', () => {
    it('fixed order, empty segments absent, world always last and always present', () => {
        expect(composeDayAnatomy({ nearCount: 2, changedCount: 1, oddCount: 3 })
            .map(s => s.id)).toEqual(['near', 'changed', 'odd', 'world'])
        expect(composeDayAnatomy({ ...base, changedCount: 1 })
            .map(s => s.id)).toEqual(['changed', 'world'])
        expect(composeDayAnatomy(base).map(s => s.id)).toEqual(['world'])
    })

    it('world survives even a fully empty day — the shared edition is the firewall', () => {
        const segs = composeDayAnatomy(base)
        expect(segs).toHaveLength(1)
        expect(segs[0].id).toBe('world')
    })

    it('carries counts through for the kicker labels', () => {
        expect(composeDayAnatomy({ ...base, nearCount: 2 })[0]).toEqual({ id: 'near', count: 2 })
    })
})

describe('changedRowsFromThreads', () => {
    const t = (id: string, sig: string | null) =>
        ({ thread_id: id, label: id, temporal_signature: sig })

    it('keeps only new and resurrected — continuous/recurrent/null are not "changes"', () => {
        const rows = changedRowsFromThreads([
            t('a', 'new'), t('b', 'recurrent'), t('c', 'resurrected'),
            t('d', 'continuous'), t('e', null),
        ])
        expect(rows.map(r => r.thread_id)).toEqual(['a', 'c'])
    })

    it('empty input → empty output, no fabrication', () => {
        expect(changedRowsFromThreads([])).toEqual([])
    })
})

describe('kill switch', () => {
    it('exists and is a boolean (one-line revert per spec discipline)', () => {
        expect(typeof READER_ANATOMY).toBe('boolean')
    })
})
```

- [ ] **Step 2: Run to fail** — `npx vitest run src/lib/dayAnatomy.test.ts`. Expected: FAIL.

- [ ] **Step 3: Implement**

```ts
// The day anatomy (spec §3, 2026-08-17): one lead, then fixed layers —
// near → changed → odd → world. Tranche 2 builds the LAYERS only (no lead,
// no profile). Two structural rules live here, not in the component:
//   * an empty segment is ABSENT — never rendered hollow, never apologized;
//   * `world` is ALWAYS present: it is the shared edition, and its
//     unconditional presence is the §6.2 firewall (personalization adds
//     segments, never subtracts from the shared edition).
export const READER_ANATOMY = true // kill switch: false → pre-anatomy Brief render

export type SegmentId = 'near' | 'changed' | 'odd' | 'world'

export interface DaySegment {
    id: SegmentId
    count: number
}

export interface DayCounts {
    nearCount: number
    changedCount: number
    oddCount: number
}

export function composeDayAnatomy(c: DayCounts): DaySegment[] {
    const out: DaySegment[] = []
    if (c.nearCount > 0) out.push({ id: 'near', count: c.nearCount })
    if (c.changedCount > 0) out.push({ id: 'changed', count: c.changedCount })
    if (c.oddCount > 0) out.push({ id: 'odd', count: c.oddCount })
    out.push({ id: 'world', count: 0 }) // always — see header comment
    return out
}

export interface SignedThread {
    thread_id: string
    label: string
    temporal_signature: string | null
}

// "Changed" per the temporal signature the engine already measures (mig 085).
// recurrent/continuous are the steady state, not a change; null is unmeasured.
export function changedRowsFromThreads<T extends SignedThread>(threads: T[]): T[] {
    return threads.filter(t =>
        t.temporal_signature === 'new' || t.temporal_signature === 'resurrected')
}
```

- [ ] **Step 4: Run to pass.** Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/dayAnatomy.ts frontend-v2/src/lib/dayAnatomy.test.ts
git commit -m "feat(reader): day-anatomy composer — empty segments vanish, world unconditional (the firewall)"
```

### Task 7: uiCopy keys for the anatomy chrome

**Files:**
- Modify: `frontend-v2/src/lib/uiCopy.ts`
- Test: existing catalogue tests cover new keys automatically (same-placeholders / same-digits / no-copied-es rules)

- [ ] **Step 1: Add the keys** (read `uiCopy.ts` first and follow its exact entry shape; these are the entries, adapt syntax to the file's convention):

```ts
'anatomy.kicker.near':    { en: 'Near you · {place}',            es: 'Cerca de ti · {place}' },
'anatomy.kicker.changed': { en: 'What changed',                  es: 'Qué cambió' },
'anatomy.kicker.changedSince': { en: 'What changed · since your last read, {h}h ago',
                                 es: 'Qué cambió · desde tu última lectura, hace {h}h' },
'anatomy.kicker.odd':     { en: 'What is odd',                   es: 'Qué está raro' },
'anatomy.kicker.world':   { en: 'The world',                     es: 'El mundo' },
'anatomy.place.change':   { en: 'change',                        es: 'cambiar' },
'anatomy.place.proposed': { en: 'guessed from your device — tap to change',
                            es: 'propuesto por tu dispositivo — toca para cambiar' },
```

(`changedSince` is used when `hoursSince` returns non-null; plain `changed` otherwise. The proposed-place string is the §6 "never silent" obligation made visible.)

- [ ] **Step 2: Run the catalogue tests** — `npx vitest run src/lib/uiCopy.test.ts`. Expected: PASS (placeholders match, digits match, no es≡en copies).

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/lib/uiCopy.ts
git commit -m "i18n(reader): anatomy kickers + declared-place strings, es/en"
```

### Task 8: BriefNewspaper integration

**Files:**
- Modify: `frontend-v2/src/components/BriefNewspaper.tsx`
- Modify: `frontend-v2/src/components/BriefNewspaper.css` (or the stylesheet the section headers already use — follow the file)

No pure logic here — every decision was made in Tasks 4–6; this task is wiring. **Read before writing:** locate (a) the masthead block that mounts `ReaderLanguagePicker`, (b) the render sites of the three sections (grep `splitEditionThreads` usage and the section kickers), (c) the Gap box and Rising renders, (d) the country-edition fetch (`/api/v2/country-edition?cc=`) used by the country door.

- [ ] **Step 1: Wire the shell.** Under `READER_ANATOMY` (import from `dayAnatomy.ts`):
  - On mount: `touchLastRead(Date.now())` once (store the returned prev in a ref — calling it twice per visit would eat the mark), `loadReaderPlace(navigator.language)`.
  - If place.country: fetch the country edition for it (same warm-cache fetch the country door uses) → `near` items (top 3 threads, compact rows reusing the existing thread-row renderer).
  - `changed` = existing Rising rows + `changedRowsFromThreads(top_threads)`.
  - `odd` = existing Gap box rows (+ eclipse row when the masthead symbol's tier ≠ none).
  - `composeDayAnatomy` with the three counts decides which kickers render. `world` wraps the EXISTING three sections **unmoved and unfiltered** — their render code does not change, they gain only the "El mundo" kicker above them.
  - Masthead: place control next to `ReaderLanguagePicker` — a native `<select>` of countries (reuse the country list the search aliases use), showing the `anatomy.place.proposed` hint when `proposed: true`.
  - `READER_ANATOMY = false` must reproduce the current Brief byte-for-byte (wrappers not applied, no fetch added).

- [ ] **Step 2: Segment CSS.** Kickers reuse the existing section-kicker classes (the i18n pass just touched them — match `.brief-*` conventions in the stylesheet; dashed top rule for `odd`, no new palette).

- [ ] **Step 3: Build + full suite.**

Run: `cd frontend-v2 && npx vitest run && npm run build` (node@24 PATH as usual)
Expected: full suite green (1939+ tests), build clean.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/BriefNewspaper.tsx frontend-v2/src/components/BriefNewspaper.css frontend-v2/src/lib/dayAnatomy.ts
git commit -m "feat(brief): the day anatomy — near/changed/odd kickers over today's data, world untouched (kill-switch READER_ANATOMY)"
```

### Task 9: Verification gate (browser + firewall audit)

- [ ] **Step 1: Browser walkthrough** (preview via launch.json, desktop + 375px):
  - Place CO declared → `Cerca de ti · Colombia` renders with country-edition rows; place cleared + no locale region → segment absent, **no hole, no apology**.
  - Second visit → `Qué cambió · desde tu última lectura, hace Nh`; first visit → plain kicker, never "hace 0h".
  - Empty odd/changed days (stub the data in dev if today is full) → kickers vanish.
  - ES and EN chrome both render; zero horizontal overflow at 375px.
- [ ] **Step 2: G-NO-BURBUJA precondition audit (mechanical, not eyeballed):** with anatomy ON and place set, diff the item lists of the three world subsections against `READER_ANATOMY=false` — **must be identical**. Any missing item is a firewall breach and a STOP.
- [ ] **Step 3: G-SIN-OPINIÓN spot check:** every kicker and hint string added is chrome or a measured count — no adjective of value anywhere in the new strings.
- [ ] **Step 4: Full gate + push.** Backend suite too (Task 1 touched briefing): `cd backend && .venv/bin/python -m pytest -q`. Then push both refs (`eclipse-dramatic-moment`, `eclipse-dramatic-moment:v3-intel-layer`, retry loops for SSH flake) and deploy Fly if Task 1 wasn't deployed yet.
- [ ] **Step 5: Close the loop.** Note in the plan header what shipped; the next plan (perf fix per Task 3's decision, or Tranche 3's composition witness) starts from Pedro's call.

---

## Self-review notes

- **Spec coverage:** §3 anatomy → T6+T8; §6 place → T4; §7/§8 mark → T5 (multi-cut delta explicitly deferred to its own tranche); §9 → T1–T3 (measurement only, fix out of scope by design); §12 G-NO-BURBUJA/G-SIN-OPINIÓN partials → T9; G-VELOCIDAD belongs to the fix plan; G-NO-FABRICA/G-COMPOSICIÓN belong to Tranches 3–4. Lead, profile inference, suggestions, corrected edition: out of scope here, per §13 order.
- **Types:** `ReaderPlace{country,proposed}` (T4) consumed in T8; `changedRowsFromThreads` generic over `SignedThread` matches `Narrative.temporal_signature: string | null` in NarrativeThreads.tsx; `composeDayAnatomy(DayCounts) → DaySegment[]` consumed in T8.
- **Honesty:** no step invents data the payload doesn't carry; the only new fetch (country edition) is an existing endpoint on the warm-cache path.
