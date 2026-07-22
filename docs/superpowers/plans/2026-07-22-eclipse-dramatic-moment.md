# Eclipse Dramatic Moment + Eclipse Lens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **All commits** append a trailer line: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Goal:** When one story genuinely eclipses the world's coverage, the app transforms — a rare one-time cinematic takeover, then a shadow-first "Eclipse Lens" that recolors threads, universe, and map around the eclipse and its shadow. Replaces the retired crisis-mode in spirit.

**Architecture:** Backend hardens the existing `/api/v2/attention/eclipse` read into a guarded, tiered measurement (`none|partial|total`) from two orthogonal axes (country-dominance × entropy-collapse). Frontend adds one `EclipseModeContext` that polls it, drives a `normal→takeover→ambient⇄muted` state machine (episode-deduped, auto-exiting), and feeds an eclipse/shadow classification to the recolored surfaces. Pure logic is unit-tested; visual integration is browser-verified.

**Tech Stack:** Python/FastAPI + asyncpg + Pydantic (backend, repo root `backend/`); React 18 + TypeScript + Vite + vanilla CSS (frontend `frontend-v2/`); pytest + vitest.

**Spec:** `docs/superpowers/specs/2026-07-22-eclipse-dramatic-moment-design.md`
**Boundary — do NOT touch:** `docs/superpowers/specs/2026-07-22-under-the-radar-rescoped-coverage-gaps-design.md` (the dock tab → coverage-gaps).

---

## File structure

**Phase 1 — measurement (backend, repo root):**
- Modify `backend/app/services/attention_eclipse.py` — new pure fns (`field_entropy`, `entropy_collapse`, `country_dominance`, `eclipse_guards`, `classify_tier`); extend `assemble_eclipse` + `EclipseSelection` with `tier`/`intensity`/`axes`; dominant/shadow gain `countries`, dominant gains `identity_key`.
- Modify `backend/app/routers/attention_eclipse.py` — SQL adds `identity_key` + `array_agg(country_code)`; two new queries (country-dominance, 7-day entropy baseline); pass axes into `assemble_eclipse`; response `attention-eclipse-v1`.
- Modify `backend/tests/test_attention_eclipse.py` — pure-fn + tier tests.

**Phase 2 — the moment core (frontend):**
- Modify `frontend-v2/src/lib/attentionEclipse.ts` — types (`EclipseTier`, `EclipseAxes`, new `EclipseData`/`EclipseItem`/`dominant` fields); pure helpers (`eclipseTier`, `episodeKey`, `nextEclipseMode`, `applyEclipseAction`).
- Create `frontend-v2/src/contexts/EclipseModeContext.tsx` — poll + state machine + localStorage.
- Create `frontend-v2/src/components/EclipseTakeover.tsx` + `EclipseTakeover.css` — Phase A portal overlay.
- Create `frontend-v2/src/components/eclipse.css` — ambient `.eclipsed` chrome + ribbon + map sigil.
- Modify `frontend-v2/src/main.tsx` — mount `EclipseProvider` + render `<EclipseTakeover/>`.
- Modify `frontend-v2/src/App.tsx` — `.app` eclipsed class, ribbon, map sigil, `entry=eclipse` effect.
- Modify `frontend-v2/src/components/AnomalyPanel.tsx` — eclipse row from context.
- Modify `frontend-v2/src/pages/BriefNewspaper.tsx` — masthead eclipse symbol + `entry=eclipse` on Open Console.
- Modify `frontend-v2/src/lib/attentionEclipse.test.ts` — pure-helper tests.

**Phase 3 — Eclipse Lens surfaces (frontend):**
- Create `frontend-v2/src/lib/eclipseSets.ts` + `eclipseSets.test.ts` — pure membership/coloring.
- Modify `frontend-v2/src/components/UniverseView.tsx` — fill override.
- Modify `frontend-v2/src/lib/countryHeatStates.ts` + `frontend-v2/src/App.tsx` + `frontend-v2/src/components/EqualEarthMap.tsx` — map `lens` discriminator.
- Modify `frontend-v2/src/components/NarrativeThreads.tsx` — shadow-first reframe.

**Phase 4 — deferred (own plan):** signal-stream Eclipse/Shadow tabs + `/api/v2/signals?topic=` filter. See §Phase 4.

**Calibration constants** (measure-first; start conservative; module-level so they are tunable): `MIN_TOPICS=40`, `MIN_TOTAL=2000`, `COHESION_FLOOR=0.55`, `MIN_DOM_LANGS=3`, `MIN_DOM_COUNTRIES=8`, `DOM_TAU=0.33`, `COLL_TAU=0.25`, `MIN_CC_SIGNALS=5`.

---

## Phase 1 — Measurement v2 (backend)

Run backend tests with the repo's venv: `cd backend && .venv/bin/python -m pytest`.

### Task 1: Pure — `field_entropy` + `entropy_collapse`

**Files:**
- Modify: `backend/app/services/attention_eclipse.py`
- Test: `backend/tests/test_attention_eclipse.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_attention_eclipse.py`:

```python
from app.services.attention_eclipse import field_entropy, entropy_collapse

def test_field_entropy_uniform_is_high_and_concentrated_is_low():
    uniform = field_entropy([10, 10, 10, 10])
    concentrated = field_entropy([97, 1, 1, 1])
    assert uniform > concentrated
    assert field_entropy([]) == 0.0
    assert field_entropy([0, 0]) == 0.0

def test_entropy_collapse_ratio_and_nulls():
    # field went from diverse (H=2.0) to concentrated (H=0.5) -> 0.75 collapse
    assert entropy_collapse(0.5, 2.0) == 0.75
    # no baseline -> None (honest cold start)
    assert entropy_collapse(0.5, None) is None
    assert entropy_collapse(0.5, 0.0) is None
    # H rose (less concentrated) -> clamp to 0
    assert entropy_collapse(2.5, 2.0) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "entropy" -v`
Expected: FAIL with `ImportError: cannot import name 'field_entropy'`.

- [ ] **Step 3: Write minimal implementation**

Add near the top of `backend/app/services/attention_eclipse.py` (after the existing imports; add `import math`):

```python
import math


def field_entropy(volumes: list[int]) -> float:
    """Shannon entropy (nats) of the coverage-share distribution. 0 for an empty
    or single-story field; higher = more diverse."""
    total = sum(v for v in volumes if v and v > 0)
    if total <= 0:
        return 0.0
    h = 0.0
    for v in volumes:
        if v and v > 0:
            p = v / total
            h -= p * math.log(p)
    return round(h, 6)


def entropy_collapse(h_now: float, h_baseline: float | None) -> float | None:
    """Fractional drop in field diversity vs a trailing baseline, clamped [0,1].
    None when there is no usable baseline (cold start) — never fabricated."""
    if h_baseline is None or h_baseline <= 0:
        return None
    return round(max(0.0, min(1.0, (h_baseline - h_now) / h_baseline)), 6)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "entropy" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_eclipse.py backend/tests/test_attention_eclipse.py
git commit -m "feat(eclipse): field_entropy + entropy_collapse pure signals"
```

### Task 2: Pure — `country_dominance`

**Files:**
- Modify: `backend/app/services/attention_eclipse.py`
- Test: `backend/tests/test_attention_eclipse.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.attention_eclipse import country_dominance

def test_country_dominance_fraction_and_zero_guard():
    assert country_dominance(30, 90) == 0.333333
    assert country_dominance(0, 0) == 0.0
    assert country_dominance(45, 45) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "country_dominance" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/attention_eclipse.py`:

```python
def country_dominance(n_led_by_dominant: int, n_qualifying_countries: int) -> float:
    """Fraction of qualifying countries whose #1 story IS the global dominant.
    The spatial 'eclipse spread' axis; robust to a single global black-hole."""
    if n_qualifying_countries <= 0:
        return 0.0
    return round(n_led_by_dominant / n_qualifying_countries, 6)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "country_dominance" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_eclipse.py backend/tests/test_attention_eclipse.py
git commit -m "feat(eclipse): country_dominance pure signal"
```

### Task 3: Pure — `eclipse_guards`

**Files:**
- Modify: `backend/app/services/attention_eclipse.py`
- Test: `backend/tests/test_attention_eclipse.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.attention_eclipse import eclipse_guards

def _dom(**kw):
    base = dict(field_size=200, total_coverage=20000, dom_is_junk=False,
               dom_is_roundup=False, dom_cohesion=0.8, dom_langs=10, dom_countries=40)
    base.update(kw)
    return base

def test_eclipse_guards_pass_on_healthy_field():
    ok, reasons = eclipse_guards(**_dom())
    assert ok is True and reasons == []

def test_eclipse_guards_reject_thin_field_and_blackhole():
    ok, reasons = eclipse_guards(**_dom(field_size=31))
    assert ok is False and any("thin_field" in r for r in reasons)
    ok2, r2 = eclipse_guards(**_dom(dom_cohesion=0.2))
    assert ok2 is False and any("cohesion" in r for r in r2)
    ok3, r3 = eclipse_guards(**_dom(dom_countries=3))
    assert ok3 is False and "dominant_narrow_breadth" in r3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "guards" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/attention_eclipse.py` (constants near the top, function below):

```python
# Measure-first calibration constants (tunable).
MIN_TOPICS = 40
MIN_TOTAL = 2000
COHESION_FLOOR = 0.55
MIN_DOM_LANGS = 3
MIN_DOM_COUNTRIES = 8
DOM_TAU = 0.33
COLL_TAU = 0.25


def eclipse_guards(*, field_size: int, total_coverage: int, dom_is_junk: bool,
                   dom_is_roundup: bool, dom_cohesion: float | None,
                   dom_langs: int, dom_countries: int,
                   min_topics: int = MIN_TOPICS, min_total: int = MIN_TOTAL,
                   cohesion_floor: float = COHESION_FLOOR,
                   min_dom_langs: int = MIN_DOM_LANGS,
                   min_dom_countries: int = MIN_DOM_COUNTRIES) -> tuple[bool, list[str]]:
    """Reject the measured false-positive modes: thin-substrate days, tiny windows,
    and over-merged/junk dominant buckets. Returns (passes, reason_codes)."""
    reasons: list[str] = []
    if field_size < min_topics:
        reasons.append(f"thin_field({field_size})")
    if total_coverage < min_total:
        reasons.append(f"low_total({total_coverage})")
    if dom_is_junk:
        reasons.append("dominant_junk")
    if dom_is_roundup:
        reasons.append("dominant_roundup")
    if dom_cohesion is not None and float(dom_cohesion) < cohesion_floor:
        reasons.append(f"dominant_low_cohesion({float(dom_cohesion):.2f})")
    if dom_langs < min_dom_langs or dom_countries < min_dom_countries:
        reasons.append("dominant_narrow_breadth")
    return (len(reasons) == 0, reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "guards" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_eclipse.py backend/tests/test_attention_eclipse.py
git commit -m "feat(eclipse): artifact guards (thin field / blackhole / narrow breadth)"
```

### Task 4: Pure — `classify_tier`

**Files:**
- Modify: `backend/app/services/attention_eclipse.py`
- Test: `backend/tests/test_attention_eclipse.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.attention_eclipse import classify_tier

def _axes(**kw):
    base = dict(guards_pass=True, guard_reasons=[], country_dominance=0.5,
               entropy_collapse=0.5, top1_share=0.3, hhi=0.2,
               dom_langs=10, dom_countries=40)
    base.update(kw)
    return base

def test_classify_tier_total_needs_both_axes():
    assert classify_tier(**_axes())["tier"] == "total"

def test_classify_tier_partial_on_one_axis():
    assert classify_tier(**_axes(entropy_collapse=0.0))["tier"] == "partial"
    assert classify_tier(**_axes(country_dominance=0.0))["tier"] == "partial"

def test_classify_tier_none_when_guards_fail_or_neither_axis():
    assert classify_tier(**_axes(guards_pass=False))["tier"] == "none"
    assert classify_tier(**_axes(country_dominance=0.0, entropy_collapse=0.0))["tier"] == "none"

def test_classify_tier_null_axes_do_not_crash():
    out = classify_tier(**_axes(entropy_collapse=None, country_dominance=0.5))
    assert out["tier"] == "partial"
    assert 0.0 <= out["intensity"] <= 1.0
    assert out["axes"]["entropy_collapse"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "classify_tier" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/attention_eclipse.py` (uses the already-imported `global_breadth_signal`):

```python
def classify_tier(*, guards_pass: bool, guard_reasons: list[str],
                  country_dominance: float | None, entropy_collapse: float | None,
                  top1_share: float, hhi: float, dom_langs: int, dom_countries: int,
                  dom_tau: float = DOM_TAU, coll_tau: float = COLL_TAU) -> dict:
    """Two-axis tier: total needs BOTH axes high (spread AND field-collapse), which
    is what filters a black-hole (high volume/entropy-collapse, LOW spread) from a
    genuine world eclipse. A missing (cold-start) axis is treated as not-lit."""
    dom_high = country_dominance is not None and country_dominance >= dom_tau
    coll_high = entropy_collapse is not None and entropy_collapse >= coll_tau
    if not guards_pass:
        tier = "none"
    elif dom_high and coll_high:
        tier = "total"
    elif dom_high or coll_high:
        tier = "partial"
    else:
        tier = "none"
    breadth = global_breadth_signal(dom_langs, dom_countries)
    cd = country_dominance or 0.0
    ec = entropy_collapse or 0.0
    intensity = (0.30 * min(1.0, top1_share / 0.30) + 0.15 * min(1.0, hhi / 0.30)
                 + 0.20 * breadth + 0.20 * cd + 0.15 * ec)
    return {
        "tier": tier,
        "intensity": round(max(0.0, min(1.0, intensity)), 6),
        "axes": {
            "country_dominance": country_dominance,
            "entropy_collapse": entropy_collapse,
            "top1_share": round(top1_share, 6),
            "hhi": round(hhi, 6),
        },
        "guard_reasons": guard_reasons,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "classify_tier" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_eclipse.py backend/tests/test_attention_eclipse.py
git commit -m "feat(eclipse): two-axis tier classifier (none/partial/total)"
```

### Task 5: Wire tier into `assemble_eclipse` + carry `countries`/`identity_key`

**Files:**
- Modify: `backend/app/services/attention_eclipse.py` (`EclipseCandidate`, `EclipseSelection`, `assemble_eclipse`, dominant build in `select_under_radar`)
- Test: `backend/tests/test_attention_eclipse.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.attention_eclipse import assemble_eclipse

def _row(topic_id, attention, **kw):
    base = dict(topic_id=topic_id, label=topic_id, attention=attention, langs=12,
                countries=40, velocity=0.0, surprise=0.0, category="armed-conflict",
                crisis_relevant=True, mean_cohesion=0.8, is_junk=False,
                is_roundup=False, identity_key=f"key-{topic_id}",
                country_codes=["US", "GB", "FR"])
    base.update(kw)
    return base

def test_assemble_eclipse_total_tier_with_axes_and_footprint():
    rows = [_row("dominant", 5000)] + [_row(f"s{i}", 20, countries=9, langs=4,
              country_codes=["BR", "AR"]) for i in range(60)]
    sel = assemble_eclipse(rows, country_dominance=0.5, entropy_collapse=0.5,
                           field_size=len(rows), total_coverage=sum(r["attention"] for r in rows))
    assert sel.tier == "total"
    assert sel.eclipse is True                      # back-compat: eclipse == (tier==total)
    assert sel.dominant["identity_key"] == "key-dominant"
    assert sel.dominant["countries"] == ["US", "GB", "FR"]
    assert sel.axes["country_dominance"] == 0.5

def test_assemble_eclipse_guard_blocks_blackhole():
    # one huge low-cohesion bucket over a thin field -> guards fail -> none
    rows = [_row("blob", 5000, mean_cohesion=0.2)] + [_row(f"s{i}", 20) for i in range(5)]
    sel = assemble_eclipse(rows, country_dominance=0.9, entropy_collapse=0.9,
                           field_size=len(rows), total_coverage=6000)
    assert sel.tier == "none"
    assert sel.eclipse is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -k "assemble_eclipse" -v`
Expected: FAIL — `assemble_eclipse` has no `country_dominance` kwarg / `EclipseSelection` has no `tier`.

- [ ] **Step 3: Write minimal implementation**

(a) `EclipseCandidate` (after `is_roundup: bool = False`): add
```python
    identity_key: str | None = None
    country_codes: list[str] = Field(default_factory=list)
```

(b) `EclipseSelection`: add fields
```python
    tier: Literal["none", "partial", "total"] = "none"
    intensity: float = 0.0
    axes: dict[str, Any] = Field(default_factory=dict)
```

(c) In `select_under_radar`, extend `dominant_info` (the `dom` block) with:
```python
            "identity_key": dom.identity_key,
            "countries": list(dom.country_codes or []),
```

(d) Rewrite `assemble_eclipse` signature + tier wiring:
```python
def assemble_eclipse(rows: list[dict], *, eclipse_top1: float = 0.20,
                     min_langs: int = 3, min_countries: int = 8,
                     cohesion_floor: float = 0.55, display_limit: int = 8,
                     country_dominance: float | None = None,
                     entropy_collapse: float | None = None,
                     field_size: int | None = None,
                     total_coverage: int | None = None) -> EclipseSelection:
    conc = attention_concentration([int(r.get("attention", 0) or 0) for r in rows],
                                   eclipse_top1=eclipse_top1)
    candidates = [
        EclipseCandidate(
            topic_id=r["topic_id"], label=r.get("label") or r["topic_id"],
            attention=int(r.get("attention", 0) or 0),
            language_breadth=int(r.get("langs", 0) or 0),
            country_breadth=int(r.get("countries", 0) or 0),
            velocity=float(r.get("velocity") or 0.0),
            surprise=float(r.get("surprise") or 0.0),
            category=r.get("category"), crisis_relevant=r.get("crisis_relevant"),
            mean_cohesion=(None if r.get("mean_cohesion") is None else float(r["mean_cohesion"])),
            is_junk=bool(r.get("is_junk")), is_roundup=bool(r.get("is_roundup")),
            identity_key=r.get("identity_key"),
            country_codes=list(r.get("country_codes") or []),
        )
        for r in rows
    ]
    # tier is computed on the WINDOW (before the eclipse-gated under-radar selection),
    # so the under-radar list still keys on the legacy top1 gate for back-compat.
    dom = max(candidates, key=lambda c: c.attention) if candidates else None
    fsize = field_size if field_size is not None else len(candidates)
    tcov = total_coverage if total_coverage is not None else sum(c.attention for c in candidates)
    if dom is not None:
        guards_pass, guard_reasons = eclipse_guards(
            field_size=fsize, total_coverage=tcov, dom_is_junk=dom.is_junk,
            dom_is_roundup=dom.is_roundup, dom_cohesion=dom.mean_cohesion,
            dom_langs=dom.language_breadth, dom_countries=dom.country_breadth)
    else:
        guards_pass, guard_reasons = False, ["empty_field"]
    tinfo = classify_tier(
        guards_pass=guards_pass, guard_reasons=guard_reasons,
        country_dominance=country_dominance, entropy_collapse=entropy_collapse,
        top1_share=conc["top1_share"], hhi=conc["hhi"],
        dom_langs=(dom.language_breadth if dom else 0),
        dom_countries=(dom.country_breadth if dom else 0))

    sel = select_under_radar(candidates, eclipse_on=(tinfo["tier"] == "total"),
                             min_langs=min_langs, min_countries=min_countries,
                             cohesion_floor=cohesion_floor, display_limit=display_limit)
    sel.tier = tinfo["tier"]
    sel.intensity = tinfo["intensity"]
    sel.axes = tinfo["axes"]
    sel.eclipse = tinfo["tier"] == "total"
    sel.window.update({
        "top1_share": conc["top1_share"], "top3_share": conc["top3_share"],
        "hhi": conc["hhi"], "eclipse_top1_threshold": eclipse_top1,
        "tier": tinfo["tier"], "field_size": fsize, "total_coverage": tcov,
        "guard_reasons": guard_reasons,
    })
    return sel
```
Note: `select_under_radar` still sets `sel.eclipse` internally via its `eclipse_on` param; we override it after. The under-radar `selected` list now surfaces only when `tier=='total'` (eclipse_on), preserving the Brief strip's existing behavior but now gated on the hardened tier.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -v`
Expected: PASS (all — new + existing). If an existing test asserted `sel.eclipse` from the raw 20% gate, update it to pass `country_dominance`/`entropy_collapse` or assert on `sel.window["top1_share"]` instead.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attention_eclipse.py backend/tests/test_attention_eclipse.py
git commit -m "feat(eclipse): assemble_eclipse emits tier/intensity/axes + dominant footprint"
```

### Task 6: Router — new SQL (identity_key, country footprint, country-dominance, entropy baseline) + `attention-eclipse-v1`

**Files:**
- Modify: `backend/app/routers/attention_eclipse.py`

This task is DB-integration wiring (no new unit test — the logic is tested in Tasks 1–5; verify with a live smoke in Step 4).

- [ ] **Step 1: Extend `_ECLIPSE_SQL`**

In `_ECLIPSE_SQL` (`attention_eclipse.py:31-60`): add `identity_key` and a country array. Change the `agg` CTE to also aggregate country codes, and the final SELECT to include `dt.identity_key`:

```python
_ECLIPSE_SQL = """
WITH win AS (
  SELECT tm.topic_id, tm.signal_id
  FROM topic_members tm
  WHERE tm.role = 'evidence'
    AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
),
agg AS (
  SELECT w.topic_id,
         COUNT(*) AS attention,
         COUNT(DISTINCT NULLIF(lower(s.source_lang), ''))
           FILTER (WHERE lower(s.source_lang) NOT IN ('xx','un','und','(null)')) AS langs,
         COUNT(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL) AS countries,
         (array_agg(DISTINCT s.country_code) FILTER (WHERE s.country_code IS NOT NULL)) AS country_codes
  FROM win w JOIN signals_v2 s ON s.id = w.signal_id
  GROUP BY w.topic_id
  HAVING COUNT(*) >= 3
)
SELECT a.topic_id, a.attention, a.langs, a.countries, a.country_codes,
       dt.label AS dyn_label, dt.category, dt.crisis_relevant,
       dt.mean_cohesion, dt.is_junk, dt.is_roundup, dt.identity_key,
       mv.velocity, mv.surprise
FROM agg a
LEFT JOIN dynamic_topics dt ON a.topic_id = 'dynamic-topic-' || dt.id::text
LEFT JOIN LATERAL (
  SELECT velocity, surprise FROM topic_movement
  WHERE topic_id = a.topic_id AND engine_version = 'movement-kalman-v1'
  ORDER BY window_end DESC LIMIT 1
) mv ON TRUE
"""
```

- [ ] **Step 2: Add the country-dominance + entropy-baseline SQL constants**

Add below `_ECLIPSE_SQL`:

```python
# Per-country #1 story (by evidence volume), among countries with enough signal.
_CC_DOMINANCE_SQL = """
WITH win AS (
  SELECT tm.topic_id, tm.signal_id FROM topic_members tm
  WHERE tm.role='evidence' AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
),
per AS (
  SELECT w.topic_id, s.country_code, COUNT(*) AS c
  FROM win w JOIN signals_v2 s ON s.id = w.signal_id
  WHERE s.country_code IS NOT NULL
  GROUP BY w.topic_id, s.country_code
),
cc_tot AS (SELECT country_code, SUM(c) AS tot FROM per GROUP BY country_code),
cc_top AS (
  SELECT DISTINCT ON (country_code) country_code, topic_id
  FROM per ORDER BY country_code, c DESC
)
SELECT
  (SELECT COUNT(*) FROM cc_top t JOIN cc_tot g USING (country_code)
     WHERE g.tot >= $2 AND t.topic_id = $3) AS led,
  (SELECT COUNT(*) FROM cc_tot WHERE tot >= $2) AS qualifying
"""

# Daily field entropy over the trailing 7 full days (baseline for entropy-collapse).
_ENTROPY_BASELINE_SQL = """
WITH d AS (
  SELECT date_trunc('day', tm.assigned_at) AS day, tm.topic_id, COUNT(*) AS c
  FROM topic_members tm
  WHERE tm.role='evidence' AND tm.quarantined IS NOT TRUE
    AND tm.assigned_at >= date_trunc('day', NOW()) - INTERVAL '7 days'
    AND tm.assigned_at <  date_trunc('day', NOW())
  GROUP BY 1, 2 HAVING COUNT(*) >= 3
),
tot AS (SELECT day, SUM(c) AS t FROM d GROUP BY day)
SELECT d.day, -SUM((c::float / t) * ln(c::float / t)) AS h
FROM d JOIN tot USING (day) GROUP BY d.day
"""
```

- [ ] **Step 3: Rewrite the handler to compute axes and pass them in**

Replace the body of `get_attention_eclipse` after the `_ECLIPSE_SQL` fetch. Add `from statistics import median` at the top of the file. Full handler:

```python
@router.get("/api/v2/attention/eclipse")
async def get_attention_eclipse(
    hours: int = Query(24, ge=1, le=168),
    min_langs: int = Query(3, ge=1, le=20),
    min_countries: int = Query(8, ge=1, le=100),
    eclipse_top1: float = Query(0.20, ge=0.02, le=0.90),
    limit: int = Query(8, ge=1, le=30),
) -> dict:
    if db.pool is None:
        return {"contract": "attention-eclipse-v1", "eclipse": False, "tier": "none",
                "selected": [], "notes": ["database unavailable"]}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 45000")
        raw = await conn.fetch(_ECLIPSE_SQL, hours)

        rows = [{
            "topic_id": r["topic_id"], "label": r["dyn_label"] or r["topic_id"],
            "attention": r["attention"], "langs": r["langs"], "countries": r["countries"],
            "country_codes": list(r["country_codes"] or []),
            "velocity": r["velocity"], "surprise": r["surprise"],
            "category": r["category"], "crisis_relevant": r["crisis_relevant"],
            "mean_cohesion": r["mean_cohesion"], "is_junk": r["is_junk"],
            "is_roundup": r["is_roundup"], "identity_key": r["identity_key"],
        } for r in raw]

        # Axis 1 — country dominance (needs the current dominant topic id).
        cc_dominance: float | None = None
        if rows:
            dom_id = max(rows, key=lambda r: r["attention"])["topic_id"]
            drow = await conn.fetchrow(_CC_DOMINANCE_SQL, hours, MIN_CC_SIGNALS, dom_id)
            if drow:
                cc_dominance = country_dominance(int(drow["led"] or 0), int(drow["qualifying"] or 0))

        # Axis 2 — entropy collapse vs the trailing 7-day baseline.
        collapse: float | None = None
        base_rows = await conn.fetch(_ENTROPY_BASELINE_SQL)
        baselines = [float(b["h"]) for b in base_rows if b["h"] is not None]
        if len(baselines) >= 3:
            h_now = field_entropy([r["attention"] for r in rows])
            collapse = entropy_collapse(h_now, median(baselines))

    sel = assemble_eclipse(rows, eclipse_top1=eclipse_top1, min_langs=min_langs,
                           min_countries=min_countries, display_limit=limit,
                           country_dominance=cc_dominance, entropy_collapse=collapse,
                           field_size=len(rows),
                           total_coverage=sum(r["attention"] for r in rows))

    by_id = {row.topic_id: row for row in sel.ledger}
    dom_cc = {r["topic_id"]: r["country_codes"] for r in rows}
    selected = [{
        "topic_id": tid, "label": by_id[tid].label,
        "attention": by_id[tid].components["attention"],
        "attention_share": by_id[tid].attention_share,
        "consequence": by_id[tid].consequence,
        "language_breadth": by_id[tid].components["language_breadth"],
        "country_breadth": by_id[tid].components["country_breadth"],
        "countries": dom_cc.get(tid, []),
        "velocity": by_id[tid].components["velocity"], "lane": by_id[tid].lane,
        "reason_codes": by_id[tid].reason_codes,
    } for tid in sel.selected_ids]

    notes: list[str] = []
    if sel.tier != "total":
        notes.append(
            f"tier={sel.tier} (top story = {sel.window.get('top1_share', 0)*100:.1f}% of coverage; "
            f"country_dominance={sel.axes.get('country_dominance')}, "
            f"entropy_collapse={sel.axes.get('entropy_collapse')})"
        )
    notes.append("attention = coverage-volume share, a proxy for attention (not audience eyeballs)")

    return {
        "contract": "attention-eclipse-v1", "hours": hours,
        "eclipse": sel.eclipse, "tier": sel.tier, "intensity": sel.intensity,
        "axes": sel.axes, "dominant": sel.dominant, "window": sel.window,
        "selected": selected,
        "labeled_out": [
            {"topic_id": r.topic_id, "label": r.label, "status": r.status,
             "attention_share": r.attention_share, "lane": r.lane,
             "reason_codes": r.reason_codes}
            for r in sel.ledger if r.status in ("labeled_out", "dominant") and r.consequence >= 0.5
        ][:12],
        "method": sel.method, "notes": notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
```

Also update the imports at the top of the router:
```python
from statistics import median
from app.services.attention_eclipse import (
    assemble_eclipse, country_dominance, entropy_collapse, field_entropy, MIN_CC_SIGNALS,
)
```
And add `MIN_CC_SIGNALS = 5` to the constants block in `attention_eclipse.py` (Task 3 added the others; add this one there too).

- [ ] **Step 4: Verify — full backend suite + live smoke**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -v`
Expected: PASS.

Live smoke (dev backend must be running against the DB):
Run: `curl -s 'http://localhost:8000/api/v2/attention/eclipse?hours=24' | python -m json.tool | head -40`
Expected: JSON with `"contract": "attention-eclipse-v1"`, a `"tier"` field (likely `"none"` on a diffuse day — the measured 3% top-1), `"axes"` populated (`country_dominance` a float, `entropy_collapse` a float or `null` on cold start), and `dominant.identity_key` / `dominant.countries` present. To force a demo total eclipse for later frontend work, temporarily lower thresholds via a scratch call is NOT supported (guards are server-side) — instead use the frontend fixture in Task 12.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/attention_eclipse.py backend/app/services/attention_eclipse.py
git commit -m "feat(eclipse): attention-eclipse-v1 endpoint — tier + axes + footprints"
```

---

## Phase 2 — The moment core (frontend)

Run frontend tests: `cd frontend-v2 && npx vitest run <file>`; build check: `cd frontend-v2 && npm run build`.

### Task 7: Types + pure state helpers in `attentionEclipse.ts`

**Files:**
- Modify: `frontend-v2/src/lib/attentionEclipse.ts`
- Test: `frontend-v2/src/lib/attentionEclipse.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend-v2/src/lib/attentionEclipse.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { eclipseTier, episodeKey, nextEclipseMode, applyEclipseAction,
         type EclipseData, type EclipseModeState } from './attentionEclipse'

const total = (idk = 'k1'): EclipseData => ({
  eclipse: true, tier: 'total', dominant: { topic_id: 't', identity_key: idk },
  window: {}, selected: [],
})

describe('eclipse pure helpers', () => {
  it('eclipseTier falls back to boolean when tier absent', () => {
    expect(eclipseTier({ eclipse: true, dominant: {}, window: {}, selected: [] })).toBe('total')
    expect(eclipseTier({ eclipse: false, dominant: {}, window: {}, selected: [] })).toBe('none')
    expect(eclipseTier(null)).toBe('none')
  })
  it('episodeKey only for total, keyed on identity_key', () => {
    expect(episodeKey(total('abc'))).toBe('abc')
    expect(episodeKey({ eclipse: false, tier: 'partial', dominant: {}, window: {}, selected: [] })).toBeNull()
  })
  it('nextEclipseMode arms takeover once, then ambient, auto-exits', () => {
    const s0: EclipseModeState = { mode: 'normal', seenEpisode: null }
    const s1 = nextEclipseMode(s0, 'total', 'k1')
    expect(s1.mode).toBe('takeover')
    // same episode again -> never re-takeover
    const s2 = nextEclipseMode({ mode: 'ambient', seenEpisode: 'k1' }, 'total', 'k1')
    expect(s2.mode).toBe('ambient')
    // tier drops -> auto-exit
    const s3 = nextEclipseMode({ mode: 'ambient', seenEpisode: 'k1' }, 'none', null)
    expect(s3).toEqual({ mode: 'normal', seenEpisode: null })
    // new episode re-arms
    const s4 = nextEclipseMode({ mode: 'muted', seenEpisode: 'k1' }, 'total', 'k2')
    expect(s4.mode).toBe('takeover')
  })
  it('applyEclipseAction transitions', () => {
    expect(applyEclipseAction({ mode: 'takeover', seenEpisode: 'k' }, 'enter').mode).toBe('ambient')
    expect(applyEclipseAction({ mode: 'ambient', seenEpisode: 'k' }, 'mute').mode).toBe('muted')
    expect(applyEclipseAction({ mode: 'muted', seenEpisode: 'k' }, 'restore').mode).toBe('ambient')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/attentionEclipse.test.ts`
Expected: FAIL — `eclipseTier`/`nextEclipseMode` not exported.

- [ ] **Step 3: Write minimal implementation**

In `frontend-v2/src/lib/attentionEclipse.ts`: extend the types and add helpers.

Extend `EclipseItem` (add after `country_breadth`): `countries?: string[]`.
Replace `EclipseData` and add the new types + helpers:

```ts
export type EclipseTier = 'none' | 'partial' | 'total'

export interface EclipseAxes {
  country_dominance: number | null
  entropy_collapse: number | null
  top1_share: number
  hhi: number
}

export interface EclipseData {
  eclipse: boolean
  tier?: EclipseTier
  intensity?: number
  axes?: EclipseAxes
  dominant: { topic_id?: string; label?: string; attention?: number; share?: number;
              lane?: string; identity_key?: string; countries?: string[] }
  window: { top1_share?: number; hhi?: number; tier?: EclipseTier; [k: string]: unknown }
  selected: EclipseItem[]
}

export function eclipseTier(d: EclipseData | null | undefined): EclipseTier {
  if (!d) return 'none'
  if (d.tier) return d.tier
  return d.eclipse ? 'total' : 'none'
}

export function episodeKey(d: EclipseData | null | undefined): string | null {
  if (!d || eclipseTier(d) !== 'total') return null
  return d.dominant?.identity_key ?? d.dominant?.topic_id ?? null
}

export type EclipseMode = 'normal' | 'takeover' | 'ambient' | 'muted'
export interface EclipseModeState { mode: EclipseMode; seenEpisode: string | null }

/** Fold a fresh poll into the mode. Total+new episode arms the takeover exactly
 * once; a non-total tier auto-exits to normal; a re-seen episode never re-takes-over. */
export function nextEclipseMode(state: EclipseModeState, tier: EclipseTier,
                                episode: string | null): EclipseModeState {
  if (tier !== 'total') return { mode: 'normal', seenEpisode: null }
  if (episode && state.seenEpisode === episode) {
    if (state.mode === 'muted' || state.mode === 'ambient') return state
    return { mode: 'ambient', seenEpisode: episode }
  }
  return { mode: 'takeover', seenEpisode: episode }
}

export type EclipseAction = 'enter' | 'mute' | 'restore' | 'dismiss'
export function applyEclipseAction(state: EclipseModeState, action: EclipseAction): EclipseModeState {
  switch (action) {
    case 'mute': return { ...state, mode: 'muted' }
    case 'enter':
    case 'restore':
    case 'dismiss': return { ...state, mode: 'ambient' }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/attentionEclipse.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/attentionEclipse.ts frontend-v2/src/lib/attentionEclipse.test.ts
git commit -m "feat(eclipse): tier types + pure mode state machine helpers"
```

### Task 8: `EclipseModeContext` (poll + state machine)

**Files:**
- Create: `frontend-v2/src/contexts/EclipseModeContext.tsx`

- [ ] **Step 1: Implement the provider**

```tsx
/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { type EclipseData, type EclipseModeState, type EclipseAction,
         eclipseTier, episodeKey, nextEclipseMode, applyEclipseAction } from '../lib/attentionEclipse'

const STORAGE_KEY = 'atlas.eclipse.v1'
const POLL_MS = 4 * 60 * 1000

interface EclipseModeValue {
  data: EclipseData | null
  tier: 'none' | 'partial' | 'total'
  mode: EclipseModeState['mode']
  act: (a: EclipseAction) => void
}

const Ctx = createContext<EclipseModeValue | undefined>(undefined)

function loadState(): EclipseModeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) { const p = JSON.parse(raw); if (p && p.seenEpisode !== undefined) return { mode: 'normal', seenEpisode: p.seenEpisode } }
  } catch { /* ignore */ }
  return { mode: 'normal', seenEpisode: null }
}

export const EclipseProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [data, setData] = useState<EclipseData | null>(null)
  const [state, setState] = useState<EclipseModeState>(loadState)
  const stateRef = useRef(state)
  stateRef.current = state

  // Persist only the seenEpisode marker (mode is session-derived).
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ seenEpisode: state.seenEpisode })) } catch { /* ignore */ }
    document.body.classList.toggle('eclipsed', state.mode === 'ambient')
  }, [state])

  const poll = useCallback(async () => {
    try {
      const r = await fetch('/api/v2/attention/eclipse?hours=24')
      if (!r.ok) return
      const payload = (await r.json()) as EclipseData
      setData(payload)
      const tier = eclipseTier(payload)
      setState(prev => nextEclipseMode(prev, tier, episodeKey(payload)))
    } catch { /* diffuse day / offline — leave state */ }
  }, [])

  useEffect(() => {
    poll()
    const id = setInterval(poll, POLL_MS)
    return () => clearInterval(id)
  }, [poll])

  const act = useCallback((a: EclipseAction) => setState(prev => applyEclipseAction(prev, a)), [])

  return (
    <Ctx.Provider value={{ data, tier: eclipseTier(data), mode: state.mode, act }}>
      {children}
    </Ctx.Provider>
  )
}

export const useEclipseMode = (): EclipseModeValue => {
  const v = useContext(Ctx)
  if (!v) throw new Error('useEclipseMode must be used within EclipseProvider')
  return v
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend-v2 && npx tsc --noEmit -p tsconfig.app.json 2>&1 | grep EclipseModeContext || echo "clean"`
Expected: `clean`.

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/contexts/EclipseModeContext.tsx
git commit -m "feat(eclipse): EclipseModeContext — poll + episode-deduped state machine"
```

### Task 9: `EclipseTakeover` overlay (Phase A) + CSS

**Files:**
- Create: `frontend-v2/src/components/EclipseTakeover.tsx`
- Create: `frontend-v2/src/components/EclipseTakeover.css`

- [ ] **Step 1: Implement the overlay**

`EclipseTakeover.tsx`:
```tsx
import { createPortal } from 'react-dom'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { decodeEntities } from '../lib/attentionEclipse'
import './EclipseTakeover.css'

export function EclipseTakeover() {
  const { data, mode, act } = useEclipseMode()
  if (mode !== 'takeover' || !data) return null
  const label = decodeEntities(data.dominant?.label ?? 'one story')
  const share = Math.round((data.dominant?.share ?? data.window?.top1_share ?? 0) * 100)
  const cd = data.axes?.country_dominance
  const nCountries = cd != null ? Math.round(cd * 100) : null

  return createPortal(
    <div className="eclipse-takeover" role="dialog" aria-label="Attention eclipse" aria-modal="true">
      <div className="eclipse-takeover-disc-wrap"><div className="eclipse-takeover-disc" /></div>
      <div className="eclipse-takeover-content">
        <div className="eclipse-takeover-eyebrow">Total eclipse of attention</div>
        <h1 className="eclipse-takeover-headline">{`“${label}”`}</h1>
        <div className="eclipse-takeover-stats">
          {`${share}% of the world's coverage`}
          {nCountries != null && ` · leading in ${nCountries}% of countries`}
        </div>
        <div className="eclipse-takeover-honesty">
          Coverage-volume concentration — a proxy for attention, not audience eyeballs. Ranked, not certified.
        </div>
        <div className="eclipse-takeover-actions">
          <button className="eclipse-btn eclipse-btn-primary" onClick={() => act('enter')}>Enter the eclipse ▸</button>
          <button className="eclipse-btn eclipse-btn-ghost" onClick={() => act('enter')}>The stories in its shadow →</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
```
(Both actions call `act('enter')` in v1 — they land in the same ambient Eclipse Lens where the shadow threads are foregrounded. A future refinement can make the second action scroll/focus the shadow list.)

- [ ] **Step 2: Implement the CSS (reduced-motion aware)**

`EclipseTakeover.css`:
```css
.eclipse-takeover {
  position: fixed; inset: 0; z-index: 100000;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; color: #e7eaf0;
  background: radial-gradient(circle at 50% 42%, rgba(8,6,14,.55) 0%, rgba(3,3,7,.99) 60%);
  animation: eclipse-veil-in .7s ease both;
}
@keyframes eclipse-veil-in { from { opacity: 0 } to { opacity: 1 } }
.eclipse-takeover-disc-wrap { position: relative; margin-bottom: 30px; animation: eclipse-disc-in 1.15s cubic-bezier(.2,.7,.2,1) both; }
@keyframes eclipse-disc-in { from { transform: scale(.2); opacity: 0 } to { transform: scale(1); opacity: 1 } }
.eclipse-takeover-disc {
  width: 132px; height: 132px; border-radius: 50%;
  background: radial-gradient(circle at 50% 45%, #04040a 58%, #0b0912 100%);
  box-shadow: 0 0 0 2px rgba(255,86,54,.7), 0 0 34px 8px rgba(255,120,60,.6),
              0 0 90px 26px rgba(255,80,40,.32), inset 0 0 20px rgba(0,0,0,.95);
}
.eclipse-takeover-disc::after {
  content: ''; position: absolute; inset: -14px; border-radius: 50%;
  box-shadow: 0 0 34px 8px rgba(255,150,90,.5); animation: eclipse-corona 3.4s ease-in-out infinite;
}
@keyframes eclipse-corona { 0%,100% { transform: scale(1); opacity: .5 } 50% { transform: scale(1.14); opacity: .92 } }
.eclipse-takeover-content { max-width: 640px; padding: 0 24px; animation: eclipse-text-in 1s ease .5s both; }
@keyframes eclipse-text-in { from { opacity: 0; transform: translateY(14px) } to { opacity: 1; transform: translateY(0) } }
.eclipse-takeover-eyebrow { font-size: .72rem; letter-spacing: .34em; text-transform: uppercase; color: #ffb38a; margin-bottom: 14px; }
.eclipse-takeover-headline { font-family: Georgia, 'Times New Roman', serif; font-size: 2.5rem; line-height: 1.1; color: #fff; margin: 0 0 16px; }
.eclipse-takeover-stats { font-size: .95rem; color: #cdd6e4; margin-bottom: 10px; }
.eclipse-takeover-honesty { font-size: .72rem; color: #7f8aa0; margin-bottom: 26px; }
.eclipse-takeover-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.eclipse-btn { border: none; border-radius: 8px; padding: 11px 20px; font-size: .85rem; cursor: pointer; }
.eclipse-btn-primary { background: #ff5636; color: #fff; }
.eclipse-btn-ghost { background: transparent; color: #ffb38a; border: 1px solid rgba(255,150,90,.4); }
@media (prefers-reduced-motion: reduce) {
  .eclipse-takeover, .eclipse-takeover-disc-wrap, .eclipse-takeover-content, .eclipse-takeover-disc::after { animation: none !important; }
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend-v2 && npx tsc --noEmit -p tsconfig.app.json 2>&1 | grep -i eclipsetakeover || echo "clean"`
Expected: `clean`.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/EclipseTakeover.tsx frontend-v2/src/components/EclipseTakeover.css
git commit -m "feat(eclipse): full-screen takeover overlay (reduced-motion aware)"
```

### Task 10: Ambient chrome CSS + mount provider + overlay

**Files:**
- Create: `frontend-v2/src/components/eclipse.css`
- Modify: `frontend-v2/src/main.tsx`

- [ ] **Step 1: Ambient chrome CSS**

`eclipse.css`:
```css
/* Global desaturation while the Eclipse Lens is engaged. Toggled on <body> by
   EclipseModeContext (mode === 'ambient'). Scoped narrowly so it never touches
   the takeover overlay (which is its own full-color layer). */
body.eclipsed #root { filter: grayscale(.9) brightness(.62) contrast(1.05); transition: filter 1s ease; }
body.eclipsed .eclipse-takeover { filter: none; }

.eclipse-ribbon {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 14px; font-size: .66rem; letter-spacing: .1em; text-transform: uppercase;
  background: linear-gradient(90deg, rgba(120,22,10,.96), rgba(60,12,7,.9)); color: #ffd9c8;
}
.eclipse-ribbon b { color: #fff; }
.eclipse-ribbon .eclipse-ribbon-x { margin-left: auto; background: none; border: none; color: #ffd9c8; cursor: pointer; font-size: .7rem; }

.eclipse-map-sigil {
  position: absolute; right: 16px; bottom: 16px; width: 40px; height: 40px; border-radius: 50%;
  z-index: 500; border: none; cursor: pointer; background: #07060a;
  box-shadow: 0 0 0 2px rgba(255,86,54,.85), 0 0 18px 4px rgba(255,90,40,.55);
}
.eclipse-map-sigil::after { content: ''; position: absolute; inset: 8px; border-radius: 50%; background: radial-gradient(circle at 50% 42%, #0a0812, #05050a); }
```

- [ ] **Step 2: Mount the provider + overlay in `main.tsx`**

In `frontend-v2/src/main.tsx`: import and wrap. Add imports:
```tsx
import { EclipseProvider } from './contexts/EclipseModeContext'
import { EclipseTakeover } from './components/EclipseTakeover'
import './components/eclipse.css'
```
Wrap the existing inner tree (inside `AuthProvider`, around `AppBriefKeepAlive`/`Routes`) with `<EclipseProvider>`, and render `<EclipseTakeover />` as a sibling so the portal host exists once, e.g.:
```tsx
<AuthProvider>
  <EclipseProvider>
    <WarmCacheRouteReset />
    <AppBriefKeepAlive />
    <Routes>{/* …unchanged… */}</Routes>
    <InstallPrompt />
    <EclipseTakeover />
  </EclipseProvider>
</AuthProvider>
```
(Keep the exact existing children; only add the `EclipseProvider` wrapper and the `<EclipseTakeover />` line. Match the real JSX at `main.tsx:94-122`.)

- [ ] **Step 3: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (exit 0).

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/eclipse.css frontend-v2/src/main.tsx
git commit -m "feat(eclipse): mount EclipseProvider + takeover portal + ambient chrome css"
```

### Task 11: Ribbon + map sigil + `entry=eclipse` wiring in `App.tsx`

**Files:**
- Modify: `frontend-v2/src/App.tsx`

- [ ] **Step 1: Consume the context + render ribbon and sigil**

In `AppContent` (`App.tsx`), near the other context hooks (e.g. by `useCrisis()` at `:1152`), add:
```tsx
import { useEclipseMode } from './contexts/EclipseModeContext'
// …
const { mode: eclipseMode, data: eclipseData, act: eclipseAct } = useEclipseMode()
```
On the outer `.app` div (`App.tsx:1461`), add the eclipsed class alongside crisis:
```tsx
<div className={`app ${crisisEnabled ? 'crisis-mode' : ''} ${eclipseMode === 'ambient' ? 'eclipsed-console' : ''}`}>
```
Immediately under the `<header className="command-bar">…</header>` block (after it closes, ~`App.tsx:1511`), render the ribbon when ambient:
```tsx
{eclipseMode === 'ambient' && eclipseData && (
  <div className="eclipse-ribbon">
    ◑ Eclipsed · <b>{`“${eclipseData.dominant?.label ?? 'one story'}”`}</b> is eclipsing the world
    <button className="eclipse-ribbon-x" onClick={() => eclipseAct('mute')} data-tip="Exit the eclipse view">✕ exit eclipse</button>
  </div>
)}
```
In the map panel container (the `.terminal-panel.radar` wrapper that holds `<EqualEarthMap/>`, near `App.tsx:1723`), add the muted-state sigil:
```tsx
{eclipseMode === 'muted' && (
  <button className="eclipse-map-sigil" onClick={() => eclipseAct('restore')}
          data-tip="An eclipse is active — re-enter the eclipse view" aria-label="Re-enter eclipse view" />
)}
```
(The map wrapper must be `position: relative` — add it inline if not already.)

- [ ] **Step 2: Fire the takeover on `entry=eclipse`**

The takeover is normally armed by the poll. For the Brief→L2 hand-off, ensure entering with `?entry=eclipse` forces an immediate poll so the takeover arms without waiting up to 4 min. Near the `entrySource` read (`App.tsx:367`), add an effect:
```tsx
useEffect(() => {
  if (entrySource === 'eclipse') {
    // context poll is authoritative; nudge it by dispatching a manual refresh event
    window.dispatchEvent(new Event('atlas:eclipse-refresh'))
  }
}, [entrySource])
```
And in `EclipseModeContext` (Task 8), listen for that event to re-poll immediately:
```tsx
useEffect(() => {
  const h = () => poll()
  window.addEventListener('atlas:eclipse-refresh', h)
  return () => window.removeEventListener('atlas:eclipse-refresh', h)
}, [poll])
```

- [ ] **Step 3: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/App.tsx frontend-v2/src/contexts/EclipseModeContext.tsx
git commit -m "feat(eclipse): ambient ribbon + muted map sigil + entry=eclipse refresh"
```

### Task 12: Browser-verify the moment (fixture-driven)

**Files:** none (verification only). Uses the dev server + Browser pane preview tools.

- [ ] **Step 1: Start the dev server**

Use `preview_start` with the frontend-v2 dev server (`.claude/launch.json` name, or `npm run dev` in `frontend-v2/`). Navigate to `/app`.

- [ ] **Step 2: Inject a total-eclipse fixture**

Because a real total eclipse is rare, stub the fetch in the browser to return a fixture. In the Browser pane console (`javascript_tool`), before the provider polls, install a fetch shim:
```js
const _f = window.fetch;
window.fetch = (u, o) => (String(u).includes('/attention/eclipse')
  ? Promise.resolve(new Response(JSON.stringify({
      contract:'attention-eclipse-v1', eclipse:true, tier:'total', intensity:0.8,
      axes:{country_dominance:0.47, entropy_collapse:0.5, top1_share:0.31, hhi:0.2},
      dominant:{topic_id:'dynamic-topic-999', label:'US airstrikes — 4th consecutive night',
                share:0.31, identity_key:'demo-ep-1', countries:['US','IR','IL']},
      window:{top1_share:0.31, hhi:0.2, tier:'total'},
      selected:[{topic_id:'dynamic-topic-101', label:'Sudan famine declaration — Darfur',
                 attention:310, attention_share:0.004, consequence:0.7, language_breadth:9,
                 country_breadth:9, countries:['SD','TD'], velocity:0.1, lane:'general', reason_codes:[]}]
    }), {status:200, headers:{'Content-Type':'application/json'}}))
  : _f(u, o));
localStorage.removeItem('atlas.eclipse.v1');
window.dispatchEvent(new Event('atlas:eclipse-refresh'));
```

- [ ] **Step 3: Verify the sequence**

- `read_page` / `computer screenshot`: the **takeover overlay** appears (disc + "US airstrikes…" + stats + two buttons).
- Click **"Enter the eclipse ▸"** → overlay dismisses; `read_page` shows the **ribbon** ("◑ Eclipsed · …") under the command bar and the console is **desaturated** (`javascript_tool`: `getComputedStyle(document.querySelector('#root')).filter` contains `grayscale`).
- Click **✕ exit eclipse** → ribbon gone, desaturation gone, **map sigil** present (`read_page` finds `.eclipse-map-sigil`).
- Click the **sigil** → ribbon + desaturation return.
- `read_console_messages`: **no errors**.
- Reduced-motion: `resize_window` won't set it; instead `javascript_tool` check that the takeover CSS has the `prefers-reduced-motion` block (visual confirm only).

- [ ] **Step 4: Remove the shim**

`javascript_tool`: `window.fetch = _f` (or reload). Confirm on real data the app is normal (tier `none` → no takeover).

- [ ] **Step 5: Commit (verification note only, no code)**

No commit (verification task). If any defect found, fix in the owning task and re-verify.

### Task 13: Partial/total eclipse row in `AnomalyPanel`

**Files:**
- Modify: `frontend-v2/src/components/AnomalyPanel.tsx`

- [ ] **Step 1: Consume the context + render a global eclipse row**

In `AnomalyPanel.tsx`, add:
```tsx
import { useEclipseMode } from '../contexts/EclipseModeContext'
// … inside the component, near other hooks:
const { data: eclipseData, tier: eclipseTierNow } = useEclipseMode()
```
In the right column, between the THEME SPIKES block (ends ~`AnomalyPanel.tsx:239`) and the PUBLIC ATTENTION label (`:242`), add a section rendered only when a (partial or total) eclipse exists — mirroring the theme-spike row markup:
```tsx
{eclipseTierNow !== 'none' && eclipseData?.dominant?.label && (
  <div className="ap-eclipse-section">
    <div className="col-label">ATTENTION ECLIPSE{eclipseTierNow === 'total' ? ' · TOTAL' : ' · PARTIAL'}</div>
    <div className="ap-row ap-row--trend">
      <span className="ap-src-tag">◑</span>
      <span className="ap-keyword">{eclipseData.dominant.label}</span>
      <span className="ap-multiplier">{Math.round((eclipseData.dominant.share ?? 0) * 100)}% of coverage</span>
    </div>
  </div>
)}
```
(The eclipse is window-global, so this row does NOT re-scope on `scopeCountry` — unlike the other AnomalyPanel sections. Reuse existing `.ap-row`/`.col-label` styles; no new CSS required.)

- [ ] **Step 2: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Browser-verify (reuse the Task 12 fixture)**

With the fixture active and `tier:'total'` (or set `tier:'partial'` in the shim), open the Anomaly dock tab → `read_page` shows the "ATTENTION ECLIPSE · TOTAL/PARTIAL" row with the dominant label + share. Set `tier:'none'` → row absent.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/AnomalyPanel.tsx
git commit -m "feat(eclipse): partial/total eclipse row in AnomalyPanel (global, context-driven)"
```

### Task 14: Brief masthead eclipse symbol + `entry=eclipse` on Open Console

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

- [ ] **Step 1: Masthead symbol**

In `BriefNewspaper.tsx`, the eclipse payload already exists (`eclipse` state, `:322`). In the masthead right cluster (`brief-masthead-right`, near the live chip `:1149`), add a marker gated on a total eclipse:
```tsx
{eclipse?.eclipse && (eclipse.tier === 'total' || eclipse.tier === undefined) && (
  <button className="brief-eclipse-mark" onClick={() => goToAtlas(undefined, 'eclipse')}
          data-tip="A total attention eclipse is active — enter the console" aria-label="Enter the eclipse">◑</button>
)}
```
Add minimal CSS near the masthead styles (same file's stylesheet or inline): a small red-rimmed circular glyph. If the Brief has a dedicated CSS file, add:
```css
.brief-eclipse-mark { border: none; background: #07060a; color: #ffd9c8; width: 24px; height: 24px;
  border-radius: 50%; cursor: pointer; box-shadow: 0 0 0 2px rgba(255,86,54,.8), 0 0 10px rgba(255,90,40,.5); }
```

- [ ] **Step 2: `entry=eclipse` when a total eclipse is active**

`goToAtlas` (`:596-603`) currently always sets `entry='brief'`. Add an optional override so the eclipse mark routes with `entry=eclipse`:
```tsx
const goToAtlas = (params?: Record<string, string>, sectionName?: string) => {
  const next = new URLSearchParams(params)
  next.set('entry', sectionName === 'eclipse' ? 'eclipse' : 'brief')
  track('brief_section_click', { section: sectionName ?? 'unknown' })
  navigate(`/app?${next.toString()}`)
}
```
(Preserve the exact existing body of `goToAtlas` — only change the `entry` value derivation. Confirm the real signature at `:596`.)

- [ ] **Step 3: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Browser-verify**

Navigate to `/brief` with the Task-12 fetch shim active (also stubs the Brief's `/attention/eclipse` fetch) → `read_page` shows the `◑` masthead mark → click it → URL becomes `/app?entry=eclipse` → the takeover fires on the console.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/pages/BriefNewspaper.tsx
git commit -m "feat(eclipse): Brief masthead eclipse mark + entry=eclipse hand-off"
```

---

## Phase 3 — The Eclipse Lens surfaces

### Task 15: Pure — `eclipseSets.ts` (membership + coloring)

**Files:**
- Create: `frontend-v2/src/lib/eclipseSets.ts`
- Test: `frontend-v2/src/lib/eclipseSets.test.ts`

- [ ] **Step 1: Write the failing test**

`eclipseSets.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { buildEclipseSets, eclipseTopicColor, countryLens, threadEclipseRole } from './eclipseSets'
import type { EclipseData } from './attentionEclipse'

const data: EclipseData = {
  eclipse: true, tier: 'total',
  dominant: { topic_id: 'dynamic-topic-1', countries: ['US', 'IR'] },
  window: {},
  selected: [{ topic_id: 'dynamic-topic-9', label: 's', attention: 10, attention_share: 0.01,
               consequence: 0.5, language_breadth: 3, country_breadth: 4, velocity: 0,
               lane: 'general', reason_codes: [], countries: ['SD', 'US'] }],
}

describe('eclipseSets', () => {
  it('builds eclipse/shadow topic + country sets, dominant wins shared country', () => {
    const s = buildEclipseSets(data, ['dynamic-topic-2'])
    expect(s.eclipseTopics.has('dynamic-topic-1')).toBe(true)
    expect(s.eclipseTopics.has('dynamic-topic-2')).toBe(true)   // neighbor
    expect(s.shadowTopics.has('dynamic-topic-9')).toBe(true)
    expect(s.eclipseCountries.has('US')).toBe(true)
    expect(s.shadowCountries.has('US')).toBe(false)             // dominant footprint wins
    expect(s.shadowCountries.has('SD')).toBe(true)
  })
  it('colors and roles', () => {
    const s = buildEclipseSets(data)
    expect(eclipseTopicColor('dynamic-topic-1', s)).toContain('eclipse')
    expect(eclipseTopicColor('dynamic-topic-9', s)).toContain('shadow')
    expect(eclipseTopicColor('unknown', s)).toBeNull()
    expect(countryLens('IR', s)).toBe('eclipse')
    expect(countryLens('SD', s)).toBe('shadow')
    expect(countryLens('BR', s)).toBeNull()
    expect(threadEclipseRole(['dynamic-topic-9'], 'theme-x', s)).toBe('shadow')
    expect(threadEclipseRole([], 'dynamic-topic-1', s)).toBe('eclipse')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/eclipseSets.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `eclipseSets.ts`**

```ts
import type { EclipseData } from './attentionEclipse'

export const ECLIPSE_COLOR = 'var(--eclipse-red, #e23a1a)'
export const SHADOW_COLOR = 'var(--eclipse-cyan, #2aa7ad)'

export interface EclipseSets {
  eclipseTopics: Set<string>
  shadowTopics: Set<string>
  eclipseCountries: Set<string>
  shadowCountries: Set<string>
}

/** neighborIds = the dominant topic's universe neighbors (caller supplies via the
 * existing edge walk). Dominant footprint countries win over shadow when shared. */
export function buildEclipseSets(d: EclipseData | null | undefined, neighborIds: string[] = []): EclipseSets {
  const eclipseTopics = new Set<string>()
  const shadowTopics = new Set<string>()
  const eclipseCountries = new Set<string>()
  const shadowCountries = new Set<string>()
  const domId = d?.dominant?.topic_id
  if (domId) eclipseTopics.add(domId)
  for (const id of neighborIds) eclipseTopics.add(id)
  for (const cc of d?.dominant?.countries ?? []) eclipseCountries.add(cc)
  for (const item of d?.selected ?? []) {
    shadowTopics.add(item.topic_id)
    for (const cc of item.countries ?? []) shadowCountries.add(cc)
  }
  for (const cc of eclipseCountries) shadowCountries.delete(cc)
  return { eclipseTopics, shadowTopics, eclipseCountries, shadowCountries }
}

export function eclipseTopicColor(topicId: string, s: EclipseSets): string | null {
  if (s.eclipseTopics.has(topicId)) return ECLIPSE_COLOR
  if (s.shadowTopics.has(topicId)) return SHADOW_COLOR
  return null
}

export function countryLens(cc: string, s: EclipseSets): 'eclipse' | 'shadow' | null {
  if (s.eclipseCountries.has(cc)) return 'eclipse'
  if (s.shadowCountries.has(cc)) return 'shadow'
  return null
}

export function threadEclipseRole(anchorTopics: string[] | undefined, threadId: string,
                                  s: EclipseSets): 'eclipse' | 'shadow' | null {
  const ids = [threadId, ...(anchorTopics ?? [])]
  if (ids.some(id => s.eclipseTopics.has(id))) return 'eclipse'
  if (ids.some(id => s.shadowTopics.has(id))) return 'shadow'
  return null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend-v2 && npx vitest run src/lib/eclipseSets.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/eclipseSets.ts frontend-v2/src/lib/eclipseSets.test.ts
git commit -m "feat(eclipse): pure eclipse/shadow membership + coloring helpers"
```

### Task 16: Universe recolor by eclipse-set

**Files:**
- Modify: `frontend-v2/src/components/UniverseView.tsx`

- [ ] **Step 1: Compute the eclipse-set (dominant + neighbors) and override fill**

In `UniverseView.tsx`, consume the context and build the set using the existing edge walk (the `neighborIds` memo at `:189-198` is the pattern; here we seed by the dominant topic id):
```tsx
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { buildEclipseSets, eclipseTopicColor } from '../lib/eclipseSets'
// … inside the component:
const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
const eclipseSets = useMemo(() => {
  if (eclipseMode !== 'ambient' || !eclipseData?.dominant?.topic_id) return null
  const domId = eclipseData.dominant.topic_id
  const neighbors: string[] = []
  for (const e of edges) {
    if (e.a === domId) neighbors.push(e.b)
    else if (e.b === domId) neighbors.push(e.a)
  }
  return buildEclipseSets(eclipseData, neighbors)
}, [eclipseMode, eclipseData, edges])
```
At the node `<circle>` fill (`UniverseView.tsx:653`), override when a set is active (keep the existing opacity/visibility so shadow stays visible):
```tsx
fill: eclipseSets ? (eclipseTopicColor(n.id, eclipseSets) ?? 'var(--eclipse-cyan, #2aa7ad)') : categoryColor(n.category),
```
(When `eclipseSets` is active every node is eclipse-red, shadow-cyan, or — if it's neither dominant/neighbor nor a listed shadow topic — defaults to the shadow cyan so the whole field reads eclipse-vs-shadow. Non-eclipse-mode path is byte-identical.)

- [ ] **Step 2: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Browser-verify (Task-12 fixture + open universe)**

With the fixture active + mode `ambient`, open the Universe view → `computer screenshot`: the dominant node + its neighbors render red, the rest cyan; all nodes still visible. `read_console_messages`: no errors. Exit eclipse → universe returns to category colors.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/UniverseView.tsx
git commit -m "feat(eclipse): universe recolors eclipse-set red / shadow cyan in lens mode"
```

### Task 17: Map recolor via `lens` discriminator

**Files:**
- Modify: `frontend-v2/src/lib/countryHeatStates.ts`, `frontend-v2/src/App.tsx`, `frontend-v2/src/components/EqualEarthMap.tsx`

- [ ] **Step 1: Add `lens` to the heat-state type + fill branch**

In `lib/countryHeatStates.ts`, extend the per-country state shape with an optional `lens?: 'eclipse' | 'shadow'` and add two colors + a helper:
```ts
export const ECLIPSE_FILL = 'rgba(226,58,26,0.72)'
export const SHADOW_FILL = 'rgba(42,167,173,0.62)'
export function lensFillColor(lens: 'eclipse' | 'shadow' | undefined, heat: number): string | null {
  if (lens === 'eclipse') return ECLIPSE_FILL
  if (lens === 'shadow') return SHADOW_FILL
  return null // caller falls back to heatFillColor(heat)
}
```
(Add `lens?: 'eclipse' | 'shadow'` to whatever interface `computeCountryHeatStates` returns per country — around `countryHeatStates.ts:50-111`.)

- [ ] **Step 2: Tag countries in the App heat memo**

In `App.tsx`, after `heatStates` is computed (`:1177-1196`), when eclipse mode is `ambient`, tag each country by membership using `countryLens`:
```tsx
import { buildEclipseSets, countryLens } from './lib/eclipseSets'
// …
const eclipseHeatStates = useMemo(() => {
  if (eclipseMode !== 'ambient' || !eclipseData) return heatStates
  const sets = buildEclipseSets(eclipseData)
  const out = new Map(heatStates)
  for (const [cc, st] of out) {
    const lens = countryLens(cc, sets)
    if (lens) out.set(cc, { ...st, lens })
  }
  // ensure eclipse/shadow countries with no heat still render
  for (const cc of [...sets.eclipseCountries]) if (!out.has(cc)) out.set(cc, { heat: 0.15, intensity: 0.15, lens: 'eclipse' })
  for (const cc of [...sets.shadowCountries]) if (!out.has(cc)) out.set(cc, { heat: 0.12, intensity: 0.12, lens: 'shadow' })
  return out
}, [eclipseMode, eclipseData, heatStates])
```
Pass `eclipseHeatStates` (instead of `heatStates`) to `<EqualEarthMap heatStates={…}>` at `:1723`.

- [ ] **Step 3: Consume `lens` in the map fill**

In `EqualEarthMap.tsx`, at `heatEls` (`:587-592`), branch the fill:
```tsx
import { lensFillColor } from '../lib/countryHeatStates'
// … per-country path:
fill={lensFillColor((st as any).lens, heat) ?? heatFillColor(heat)}
```
(And the border at `:604` may keep `heatGlowColor(heat)` — opacity still encodes heat so "both stay visible".)

- [ ] **Step 4: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Browser-verify**

Fixture active + ambient → `computer screenshot` of the map: eclipse countries (US/IR/IL) render red, shadow countries (SD/TD) cyan, others normal heat. Exit eclipse → normal heat returns. `read_console_messages`: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/lib/countryHeatStates.ts frontend-v2/src/App.tsx frontend-v2/src/components/EqualEarthMap.tsx
git commit -m "feat(eclipse): map recolors eclipse/shadow countries via lens discriminator"
```

### Task 18: Narrative threads — shadow-first reframe

**Files:**
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`

- [ ] **Step 1: Classify + reorder in eclipse mode**

In `NarrativeThreads.tsx`, consume the context and build sets:
```tsx
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { buildEclipseSets, threadEclipseRole } from '../lib/eclipseSets'
// …
const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
const eclipseSets = useMemo(
  () => (eclipseMode === 'ambient' && eclipseData ? buildEclipseSets(eclipseData) : null),
  [eclipseMode, eclipseData])
```
At the ordering hook (`:336-344`, the `liveOrdered` sort), compose an eclipse-priority sort ahead of the existing relational one when a set is active:
```tsx
const liveOrdered = useMemo(() => {
  const base = [...displayedNarratives]
  if (eclipseSets) {
    const rank = (n: Narrative) => {
      const role = threadEclipseRole(n.anchor_topics, n.thread_id, eclipseSets)
      return role === 'eclipse' ? 0 : role === 'shadow' ? 1 : 2
    }
    return base.sort((a, b) => rank(a) - rank(b))
  }
  return base.sort((a, b) => Number(relate(b)) - Number(relate(a)))
}, [displayedNarratives, eclipseSets, relate])
```
(Preserve the existing `relate`/freeze wrapper for the non-eclipse path; only branch when `eclipseSets` is set. Match the real memo/vars at `:335-344`.)

- [ ] **Step 2: Per-row role tag + share-vs-dominant**

At the row render (`:438` map + count block `:509-533`), when `eclipseSets`, tag the row and show the relation. Add a class + a small label:
```tsx
const eclipseRole = eclipseSets ? threadEclipseRole(n.anchor_topics, n.thread_id, eclipseSets) : null
// row className gets: eclipseRole === 'eclipse' ? 'ecl-row-eclipse' : eclipseRole === 'shadow' ? 'ecl-row-shadow' : ''
// near narrative-count, when eclipseRole === 'shadow', render the dominant contrast:
{eclipseRole === 'shadow' && eclipseData?.dominant?.share != null && (
  <span className="ecl-share-vs" data-tip="Share of coverage vs the eclipsing story">
    {`${(shareOf(n) * 100).toFixed(1)}% vs ${Math.round((eclipseData.dominant.share) * 100)}%`}
  </span>
)}
```
where `shareOf(n)` reads the thread's share if present (from the eclipse `selected` item matched by topic id) — add a small lookup:
```tsx
const shadowShareById = useMemo(() => {
  const m = new Map<string, number>()
  for (const it of eclipseData?.selected ?? []) m.set(it.topic_id, it.attention_share)
  return m
}, [eclipseData])
const shareOf = (n: Narrative) => {
  for (const id of [n.thread_id, ...(n.anchor_topics ?? [])]) { const v = shadowShareById.get(id); if (v != null) return v }
  return 0
}
```
Add minimal CSS (in the component's CSS file): `.ecl-row-eclipse { border-left-color: #e23a1a !important; } .ecl-row-shadow { border-left-color: #2aa7ad !important; } .ecl-share-vs { font-size: .62rem; color: #39d0d8; }`.

- [ ] **Step 3: Build check**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Browser-verify**

Fixture active + ambient → `read_page` on the threads panel: the eclipse thread sorts to the top with a red accent; shadow threads follow with the "X% vs 31%" tag. Exit eclipse → normal ranking. `read_console_messages`: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/NarrativeThreads.tsx
git commit -m "feat(eclipse): shadow-first threads reframe with share-vs-dominant"
```

### Task 19: Full-suite gate + final browser pass

- [ ] **Step 1: Run all frontend tests + build**

Run: `cd frontend-v2 && npx vitest run && npm run build`
Expected: all vitest green, build succeeds.

- [ ] **Step 2: Run backend tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_attention_eclipse.py -v`
Expected: PASS.

- [ ] **Step 3: End-to-end browser pass (fixture)**

Brief `◑` mark → console takeover → Enter → ambient (desaturated + ribbon; universe red/cyan; map red/cyan; threads shadow-first) → ✕ exit → muted + map sigil → sigil → ambient → set fixture `tier:'none'` → auto-exit to normal. `read_console_messages`: clean throughout.

- [ ] **Step 4: Commit any fixes; done.**

---

## Phase 4 — deferred (own plan): signal-stream Eclipse/Shadow

Not in this plan. Requires a backend contract addition (`/api/v2/signals` has **no** topic linkage — `SignalStream.tsx` can't class a signal eclipse/shadow client-side). Scope for the follow-up plan:
- Backend: add a `topic=<id[,id]>` (or `eclipse=1`) filter to `/api/v2/signals` that returns member signals for the given topics (join `topic_members`), or a dedicated `/api/v2/attention/eclipse/signals` endpoint returning dominant + shadow member signals.
- Frontend: in eclipse mode, replace the category tabs (`SignalStream.tsx:436-459`) with **Eclipse / Shadow / All** (default Shadow); filter branch at `:388-411`; per-row eclipse/shadow styling at `:486`.
Write this plan after Phase 2 is live so the real signal payload shape is confirmed.

---

## Self-review

**Spec coverage:**
- §4 measurement v2 → Tasks 1–6 (entropy, country-dominance, guards, tier, assemble, router). ✓
- §5.1 EclipseModeContext → Task 8; §5.2 takeover → Task 9; §5.3 ambient/muted → Tasks 10–11; §5.4 entry flow → Tasks 11 + 14; §5.5 anomaly row → Task 13. ✓
- §6.1 threads → Task 18; §6.2 universe → Task 16; §6.3 map → Task 17. ✓
- §6.4 signal-stream → Phase 4 (deferred, explicit). ✓
- §8 reduced-motion → Task 9 CSS; auto-exit/dedup → Tasks 7–8; honesty line → Task 9. ✓
- §9 boundary (coverage-gaps) → untouched; only additive edits to shared files. ✓

**Placeholder scan:** no "TBD"/"handle edge cases"/"similar to" — every code step has real code. Calibration constants are concrete numbers with a measure-first note (not placeholders). ✓

**Type consistency:** `EclipseData`/`EclipseItem`/`EclipseTier`/`EclipseModeState` defined in Task 7 and used identically in Tasks 8/9/13/15–18; `buildEclipseSets`/`eclipseTopicColor`/`countryLens`/`threadEclipseRole` defined in Task 15 and consumed with matching signatures in 16–18; backend `assemble_eclipse(..., country_dominance, entropy_collapse, field_size, total_coverage)` defined in Task 5 and called with those kwargs in Task 6. ✓

**Known integration caveats (call out during execution, not placeholders):**
- Task 6 SQL runs against real tables; verify column names (`signals_v2.country_code`, `source_lang`, `dynamic_topics.identity_key`, `topic_members.role/quarantined/assigned_at`) match live schema before committing.
- Task 11/16/17/18 use approximate line anchors — confirm the exact current lines (the surrounding code is quoted in the spec's §6) before editing.
