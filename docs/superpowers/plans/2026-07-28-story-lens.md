# Story Lens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opening a story opens its measured neighborhood — a lens mode that reconfigures the console around one thread (siblings with receipts, topic-scoped stream, verdicts on a banner, pinnable snapshot), so the gold-eval NAV-LOSS defect (10/10) falls.

**Architecture:** One new thin backend endpoint (`GET /api/v2/story/{thread_id}/siblings`) wrapping the EXISTING pure kinship math in `constellation_walk.py`; a user-driven frontend mode cloned from the Eclipse machinery (provider + body class + portaled banner); third ordering branch in NarrativeThreads; a lens tab model in the stream reusing the `topic=` filter; Pin Story rides the existing Workbench store with a new snapshot MERGE primitive.

**Tech Stack:** FastAPI + asyncpg + numpy (backend), React + vanilla CSS + vitest (frontend-v2), pytest (backend). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-28-story-lens-design.md` (D1–D7, §5–§13).

---

## Rails (every task)

- Controller commits; pathspec-only commits (`git commit -- <files>`); subagents NEVER `git add -A` (concurrent sessions share this branch).
- The lens NEVER writes to the engine — read-only endpoints + Workbench localStorage only (spec §11).
- Honest empties with a reason, never blank/500 (mig-087 lesson); degraded payloads NEVER cached.
- `topic_members` scoping verbatim everywhere: `role='evidence' AND engine_version='v1-compat' AND quarantined IS NOT TRUE` (2026-07-27 bug class).
- Frontend: vanilla CSS, `data-tip=` not `title=`, `getThemeLabel` for theme codes, `npm run build` (not tsc) before declaring green.
- Backend tests: pure-service tests (plain pytest, no fixtures) + source-contract tests for routers (regex over the router file) — there is NO db test fixture; see `backend/tests/test_attention_eclipse.py` and `backend/tests/test_query_thread_router_contract.py`.
- Pre-existing failures to NOT treat as regressions: 2 tests in `test_query_thread_router_contract.py` (broken since the search merge, verified at `be37a543`).

## File structure

| File | Responsibility |
|---|---|
| `backend/app/services/story_siblings.py` (create) | Pure ranking: seed → ranked siblings with kinship/weight/fold/blob, zero SQL |
| `backend/tests/test_story_siblings.py` (create) | Pure tests, synthetic vectors |
| `backend/app/routers/story.py` (create) | GET /api/v2/story/{thread_id}/siblings: SQL + whitening + service + country receipts + Redis cache |
| `backend/tests/test_story_router_contract.py` (create) | Source-contract test (registration, scoping strings, cache version) |
| `backend/app/main_v2.py` (modify) | include_router |
| `backend/app/rate_limit.py` (modify) | paid-bucket rule |
| `frontend-v2/src/lib/storyLens.ts` (create) | Pure: types, lens sets, roles, topic param, auto flag |
| `frontend-v2/src/lib/storyLens.test.ts` (create) | vitest |
| `frontend-v2/src/contexts/StoryLensContext.tsx` (create) | enter/exit, fetch, body class |
| `frontend-v2/src/components/StoryLensBanner.tsx` + `storyLens.css` (create) | Portaled banner: label, counts, verdicts, Pin, ✕ |
| `frontend-v2/src/components/NarrativeThreads.tsx` (modify) | Lens ordering branch + reason chips |
| `frontend-v2/src/lib/streamTabs.ts` + `components/SignalStream.tsx` (modify) | Lens tab model `Story | All` |
| `frontend-v2/src/components/AnomalyPanel.tsx` (modify) | Lens country in the scope chain |
| `frontend-v2/src/components/{SignalStream,ThemeDetail,SignalDetailPanel}.tsx` (modify) | Tier chips on chipless L2 receipt rows |
| `frontend-v2/src/lib/workbench.ts` + `contexts/WorkspaceContext.tsx` + `lib/capturePayloads.ts` (modify) | `mergePinSnapshot`, `PinSnapshot.siblings`, lens-aware threadPin |
| `frontend-v2/src/components/DossierView.tsx` (modify) | Render frozen neighborhood |
| `frontend-v2/src/App.tsx` + `main.tsx` (modify) | Provider mount, banner mount, auto-enter, deep link |

---

### Task 1: Pure sibling ranking service

**Files:**
- Create: `backend/app/services/story_siblings.py`
- Test: `backend/tests/test_story_siblings.py`

The math already exists in `backend/app/services/constellation_walk.py` (`build_knn_graph`, `max_product_walk`, `dedup_reached`, `blob_connector_flags`, `WalkParams` — read it first, lines 103–204, 225–239, 329–440). This service only orchestrates it for a SINGLE seed and shapes receipts.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_story_siblings.py
"""Pure tests for the story-lens sibling ranker (no DB, synthetic vectors)."""
import numpy as np

from app.services.story_siblings import rank_siblings


def _unit(v):
    a = np.asarray(v, dtype=np.float64)
    return a / np.linalg.norm(a)


def _matrix():
    # 6 unit vectors in 4-dim: seed cluster {0,1,2} tight, {3} mid, {4,5} far pair
    rows = [
        _unit([1.0, 0.05, 0.0, 0.0]),   # 0 seed
        _unit([1.0, 0.10, 0.0, 0.0]),   # 1 near seed (hermano)
        _unit([1.0, 0.12, 0.01, 0.0]),  # 2 near seed AND near 1 (dedup fold candidate)
        _unit([0.5, 0.8, 0.0, 0.0]),    # 3 mid distance
        _unit([0.0, 0.0, 1.0, 0.05]),   # 4 far
        _unit([0.0, 0.0, 1.0, 0.10]),   # 5 far, near 4
    ]
    return np.vstack(rows)


KEYS = [f"dynamic-topic-{i}" for i in range(6)]
LABELS = [f"Topic {i}" for i in range(6)]
CATS = [None] * 6


def test_seed_excluded_and_nearest_first():
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS)
    ids = [s.topic_key for s in sibs]
    assert "dynamic-topic-0" not in ids
    assert ids[0] in ("dynamic-topic-1", "dynamic-topic-2")
    weights = [s.weight for s in sibs]
    assert weights == sorted(weights, reverse=True)


def test_same_event_fold():
    # 1 and 2 are near-duplicates (cos > 0.999) -> one is folded under the other
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS)
    ids = [s.topic_key for s in sibs]
    assert not ("dynamic-topic-1" in ids and "dynamic-topic-2" in ids)
    rep = next(s for s in sibs if s.topic_key in ("dynamic-topic-1", "dynamic-topic-2"))
    assert set(rep.folded) & {"dynamic-topic-1", "dynamic-topic-2"}


def test_cap_respected():
    sibs = rank_siblings(0, _matrix(), KEYS, LABELS, CATS, cap=1)
    assert len(sibs) == 1


def test_every_sibling_carries_a_receipt():
    for s in rank_siblings(0, _matrix(), KEYS, LABELS, CATS):
        assert s.reasons, "ranking without a receipt is forbidden (spec §6)"
        assert s.reasons[0]["basis"] == "whitened_cos"
        assert s.kinship in ("hermano", "primo")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_story_siblings.py -q`
Expected: FAIL with `ModuleNotFoundError: app.services.story_siblings`

- [ ] **Step 3: Write the service**

```python
# backend/app/services/story_siblings.py
"""Story-lens sibling ranking — a single-seed view over the constellation walk.

Ranking-with-receipts, NEVER merging: the transitive-collapse failure that
killed these signals as merge gates (recall-229 record) cannot occur here
because nothing is written and no closure is taken. Every sibling carries
the measured WHY.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from app.services.constellation_walk import (
    WalkParams,
    blob_connector_flags,
    build_knn_graph,
    dedup_reached,
    max_product_walk,
)

DEFAULT_CAP = 12


@dataclass(frozen=True)
class Sibling:
    topic_key: str
    label: str
    weight: float          # accumulated walk weight (rank key)
    degree: int            # hops from the anchor
    kinship: str           # 'hermano' (direct edge) | 'primo' (walked)
    through_blob: bool
    folded: tuple = ()     # same-event topic_keys folded under this rep
    reasons: tuple = ()    # ({'basis': str, 'value': str}, ...)


def rank_siblings(
    seed: int,
    whitened: np.ndarray,
    keys: Sequence[str],
    labels: Sequence[str],
    categories: Sequence[Optional[str]],
    params: WalkParams = WalkParams(),
    cap: int = DEFAULT_CAP,
) -> list[Sibling]:
    """Rank the measured neighborhood of one topic.

    whitened: unit-norm rows (apply_whitening output) aligned with keys/labels.
    """
    n = len(keys)
    if n < 2 or seed < 0 or seed >= n:
        return []
    graph = build_knn_graph(whitened, k=params.k)
    blobs = blob_connector_flags(graph, categories, params)
    reached = max_product_walk([seed], graph, params, blob_flags=blobs)
    ranked = sorted(
        (idx for idx in reached if idx != seed),
        key=lambda idx: -reached[idx].acc_weight,
    )
    reps, fold_map = dedup_reached(ranked, whitened, tau=params.dedup_tau)
    out: list[Sibling] = []
    for idx in reps:
        if len(out) >= cap:
            break
        node = reached[idx]
        reasons = [
            {"basis": "whitened_cos", "value": f"{node.via_weight:.2f}"},
            {"basis": "kinship", "value": f"{node.kinship} · {node.degree}º"},
        ]
        out.append(
            Sibling(
                topic_key=keys[idx],
                label=labels[idx],
                weight=float(node.acc_weight),
                degree=int(node.degree),
                kinship=node.kinship,
                through_blob=bool(node.through_blob),
                folded=tuple(keys[j] for j in fold_map.get(idx, [])),
                reasons=tuple(reasons),
            )
        )
    return out
```

NOTE for the implementer: check `ReachedNode`'s actual field names in `constellation_walk.py:144-171` (`index, degree, kinship, acc_weight, via_parent, via_weight, origin_seed, through_blob`) and `dedup_reached`'s return `(reps, fold_map)` (lines 419–440) — if names differ, the walk file wins; adjust the service, not the walk.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_story_siblings.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
git add backend/app/services/story_siblings.py backend/tests/test_story_siblings.py
git commit -m "feat(story-lens): pure sibling ranker over the constellation walk" -- backend/app/services/story_siblings.py backend/tests/test_story_siblings.py
```

---

### Task 2: Siblings endpoint

**Files:**
- Create: `backend/app/routers/story.py`
- Test: `backend/tests/test_story_router_contract.py`
- Modify: `backend/app/main_v2.py` (include_router block, after line ~207)
- Modify: `backend/app/rate_limit.py` (`_RULE_SPECS`, lines 86–120)

Template: `backend/app/routers/attention_eclipse.py` (Redis pattern lines 61, 144–151, 165–176, 266–271) and the walk endpoint `backend/app/routers/dossier.py:1003-1119` (topics SQL 955–959, whitening 1067–1072). Read both before writing.

- [ ] **Step 1: Write the failing contract test**

```python
# backend/tests/test_story_router_contract.py
"""Source-contract tests for the story siblings router (no DB fixture exists;
mirror tests/test_query_thread_router_contract.py's approach)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = (ROOT / "app" / "routers" / "story.py").read_text()
MAIN = (ROOT / "app" / "main_v2.py").read_text()
RATE = (ROOT / "app" / "rate_limit.py").read_text()


def test_registered_in_main():
    assert re.search(r"from app\.routers import .*\bstory\b", MAIN) or "routers.story" in MAIN
    assert "app.include_router(story.router)" in MAIN


def test_paid_bucket_rule():
    assert re.search(r"story/\[?\^?/?\]?\+?/siblings", RATE) or "/api/v2/story/" in RATE


def test_full_path_and_contract():
    assert '@router.get("/api/v2/story/{thread_id}/siblings")' in ROUTER
    assert "story-siblings-v1" in ROUTER


def test_membership_scoping_verbatim():
    # country receipts must scope topic_members exactly (2026-07-27 bug class)
    assert "role = 'evidence'" in ROUTER
    assert "engine_version = 'v1-compat'" in ROUTER
    assert "quarantined IS NOT TRUE" in ROUTER


def test_honest_degrade_never_cached():
    assert "db.pool is None" in ROUTER
    assert "setex" in ROUTER
    # the degraded branch returns before any setex call
    degraded = ROUTER.index("db.pool is None")
    assert ROUTER.index("setex") > degraded


def test_statement_timeout_set():
    assert "SET statement_timeout" in ROUTER
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_story_router_contract.py -q`
Expected: FAIL with `FileNotFoundError` (story.py missing)

- [ ] **Step 3: Write the router**

```python
# backend/app/routers/story.py
"""Story Lens — measured neighborhood of one thread.

GET /api/v2/story/{thread_id}/siblings
Read-only. Ranking-with-receipts (spec 2026-07-28-story-lens-design.md §6).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter

from app import db
from app.services.story_siblings import DEFAULT_CAP, rank_siblings
from app.services.constellation_walk import WalkParams
from app.services.whitening import apply_whitening, load_whitening

logger = logging.getLogger(__name__)
router = APIRouter()

_CACHE_TTL_S = 300
_TOPIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Mirror _WALK_TOPICS_SQL (dossier.py:955-959); if it differs, the walk's wins.
_TOPICS_SQL = """
    SELECT id, label, category, label_status, centroid_vec
    FROM dynamic_topics
    WHERE state = 'active'
      AND (is_umbrella IS NOT TRUE)
      AND centroid_vec IS NOT NULL
"""

# Country footprints for the anchor + top siblings only (bounded ANY list).
_COUNTRIES_SQL = """
    SELECT tm.topic_id, s.country_code, COUNT(*) AS n
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = ANY($1::text[])
      AND tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - INTERVAL '7 days'
      AND s.country_code IS NOT NULL
    GROUP BY tm.topic_id, s.country_code
"""


def _redis_client():
    # Call-time import: a top-level import of main_v2 is a circular-import trap
    # (documented in attention_eclipse.py:50-60).
    from app.main_v2 import app

    return getattr(app.state, "redis", None)


def _normalize_thread_id(raw: str) -> str | None:
    if not raw or not _TOPIC_ID_RE.match(raw):
        return None
    if raw.startswith("dynamic-topic-") or raw.startswith("cluster-") or raw.startswith("emergent-cluster-"):
        return raw
    # atlas 'slug--cc[-cc]' — topic_members carries the bare slug
    return raw.split("--")[0]


def _empty(reason: str) -> dict:
    return {
        "contract": "story-siblings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor": None,
        "siblings": [],
        "notes": [reason],
    }


@router.get("/api/v2/story/{thread_id}/siblings")
async def get_story_siblings(thread_id: str) -> dict:
    topic_key = _normalize_thread_id(thread_id)
    if topic_key is None:
        return _empty("invalid_thread_id")

    cache_key = f"story_sib:v1:{topic_key}"
    redis = _redis_client()
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache read failed: %s", exc)

    if db.pool is None:
        return _empty("database unavailable")

    try:
        whitening = load_whitening()
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings whitening unavailable: %s", exc)
        return _empty("whitening_unavailable")

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 15000")
        rows = await conn.fetch(_TOPICS_SQL)

        keys, labels, cats, statuses, vecs = [], [], [], [], []
        for r in rows:
            v = r["centroid_vec"]
            if v is None or len(v) != 768:
                continue
            keys.append(f"dynamic-topic-{r['id']}")
            labels.append(r["label"] or f"dynamic-topic-{r['id']}")
            cats.append(r["category"])
            statuses.append(r["label_status"])
            vecs.append([float(x) for x in v])

        if topic_key not in keys:
            return _empty("seed_not_found_or_no_centroid")

        seed = keys.index(topic_key)
        whitened = apply_whitening(np.asarray(vecs, dtype=np.float64), whitening)
        siblings = rank_siblings(
            seed, whitened, keys, labels, cats, WalkParams.from_env(), cap=DEFAULT_CAP
        )

        # Country receipts for anchor + reps (one bounded query).
        want = [topic_key] + [s.topic_key for s in siblings]
        foot: dict[str, list[tuple[str, int]]] = {}
        try:
            crows = await conn.fetch(_COUNTRIES_SQL, want)
            for cr in crows:
                foot.setdefault(cr["topic_id"], []).append((cr["country_code"], cr["n"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings country footprint failed: %s", exc)

    def _countries(tk: str) -> list[str]:
        return [cc for cc, _n in sorted(foot.get(tk, []), key=lambda t: -t[1])[:3]]

    anchor_countries = _countries(topic_key)
    status_by_key = dict(zip(keys, statuses))

    sib_payload = []
    for s in siblings:
        reasons = list(s.reasons)
        shared = sorted(set(_countries(s.topic_key)) & set(anchor_countries))
        if shared:
            reasons.append({"basis": "shared_country", "value": ",".join(shared)})
        sib_payload.append(
            {
                "id": s.topic_key,
                "label": s.label,
                "weight": round(s.weight, 4),
                "degree": s.degree,
                "kinship": s.kinship,
                "through_blob": s.through_blob,
                "is_blob": s.is_blob,
                "via_parent": s.via_parent_label,
                "folded": list(s.folded),
                "label_status": status_by_key.get(s.topic_key),
                "countries": _countries(s.topic_key),
                "reasons": reasons,
            }
        )

    payload = {
        "contract": "story-siblings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor": {
            "id": topic_key,
            "label": labels[seed],
            "label_status": statuses[seed],
            "countries": anchor_countries,
        },
        "siblings": sib_payload,
        "notes": [],
    }

    if redis is not None:
        try:
            await redis.setex(cache_key, _CACHE_TTL_S, json.dumps(payload, default=str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache write failed: %s", exc)
    return payload
```

- [ ] **Step 4: Register router + rate limit**

In `backend/app/main_v2.py`, in the routers import + `include_router` block (lines ~173–207), add:

```python
from app.routers import story  # with the existing router imports
app.include_router(story.router)  # in the include block
```

In `backend/app/rate_limit.py` `_RULE_SPECS` (lines 86–120), add one tuple next to the other paid rules:

```python
(r"^/api/v2/story/[^/]+/siblings$", "paid", None),
```

(Match the tuple arity of neighboring entries exactly — if entries are 2-tuples, drop the trailing None.)

- [ ] **Step 5: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_story_router_contract.py tests/test_story_siblings.py -q`
Expected: all pass

- [ ] **Step 6: Live smoke (real prod-shaped DB via local backend if available)**

Run: `cd backend && .venv/bin/python -c "import app.routers.story"` (import sanity)
Optional if a local server is running: `curl -s localhost:8000/api/v2/story/dynamic-topic-1/siblings | head -c 400`
Expected: JSON with `"contract": "story-siblings-v1"` (or an honest empty note)

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/story.py backend/tests/test_story_router_contract.py backend/app/main_v2.py backend/app/rate_limit.py
git commit -m "feat(story-lens): siblings endpoint — ranking with receipts, never merging" -- backend/app/routers/story.py backend/tests/test_story_router_contract.py backend/app/main_v2.py backend/app/rate_limit.py
```

---

### Task 3: Pure frontend lens lib

**Files:**
- Create: `frontend-v2/src/lib/storyLens.ts`
- Test: `frontend-v2/src/lib/storyLens.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend-v2/src/lib/storyLens.test.ts
import { describe, expect, it } from 'vitest'
import {
  buildLensSets,
  lensTopicParam,
  threadLensRole,
  type StoryLensData,
} from './storyLens'

const data: StoryLensData = {
  contract: 'story-siblings-v1',
  generated_at: '2026-07-28T00:00:00Z',
  anchor: { id: 'dynamic-topic-1', label: 'Anchor', label_status: 'entailed', countries: ['IR'] },
  siblings: [
    { id: 'dynamic-topic-2', label: 'Sib A', weight: 0.7, degree: 1, kinship: 'hermano', through_blob: false, is_blob: false, via_parent: null, folded: ['dynamic-topic-9'], label_status: null, countries: ['IR'], reasons: [{ basis: 'whitened_cos', value: '0.70' }] },
    { id: 'dynamic-topic-3', label: 'Sib B', weight: 0.4, degree: 2, kinship: 'primo', through_blob: false, is_blob: true, via_parent: 'Sib A', folded: [], label_status: 'failed', countries: [], reasons: [{ basis: 'whitened_cos', value: '0.40' }] },
  ],
  notes: [],
}

describe('buildLensSets / threadLensRole', () => {
  it('classifies anchor, sibling (incl. folded ids), and outsiders', () => {
    const sets = buildLensSets(data)
    expect(threadLensRole(undefined, 'dynamic-topic-1', sets)).toBe('anchor')
    expect(threadLensRole(undefined, 'dynamic-topic-2', sets)).toBe('sibling')
    expect(threadLensRole(undefined, 'dynamic-topic-9', sets)).toBe('sibling')
    expect(threadLensRole(undefined, 'dynamic-topic-99', sets)).toBeNull()
  })
  it('matches through anchor_topics union like the eclipse role does', () => {
    const sets = buildLensSets(data)
    expect(threadLensRole(['dynamic-topic-2'], 'thread-x', sets)).toBe('sibling')
  })
})

describe('lensTopicParam', () => {
  it('joins anchor + siblings, capped, never empty string', () => {
    expect(lensTopicParam(data)).toBe('dynamic-topic-1,dynamic-topic-2,dynamic-topic-3')
    expect(lensTopicParam(data, 2)).toBe('dynamic-topic-1,dynamic-topic-2')
    expect(lensTopicParam(null)).toBeNull()
    expect(lensTopicParam({ ...data, anchor: null, siblings: [] })).toBeNull()
  })
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend-v2 && npx vitest run src/lib/storyLens.test.ts`
Expected: FAIL (module missing)

- [ ] **Step 3: Implement**

```ts
// frontend-v2/src/lib/storyLens.ts
// Story Lens pure model — mirrors lib/attentionEclipse.ts + lib/eclipseSets.ts.

export interface StoryLensReason { basis: string; value: string }

export interface StoryLensSibling {
  id: string
  label: string
  weight: number
  degree: number
  kinship: 'hermano' | 'primo'
  through_blob: boolean
  is_blob: boolean
  via_parent: string | null
  folded: string[]
  label_status?: string | null
  countries: string[]
  reasons: StoryLensReason[]
}

export interface StoryLensData {
  contract: string
  generated_at: string
  anchor: { id: string; label: string; label_status?: string | null; countries: string[] } | null
  siblings: StoryLensSibling[]
  notes: string[]
}

export interface StoryLensState {
  active: boolean
  anchorId: string | null
}

// One-line kill switch (TIME_IS_VIEW precedent in lib/timeRanges.ts).
export const STORY_LENS_AUTO = true

// Mirrors TOPIC_PARAM_MAX in lib/streamTabs.ts (backend _TOPIC_FILTER_MAX = 12).
export const LENS_TOPIC_CAP = 12

export interface LensSets {
  anchor: Set<string>
  siblings: Set<string>
}

export function buildLensSets(d: StoryLensData | null | undefined): LensSets {
  const anchor = new Set<string>()
  const siblings = new Set<string>()
  if (d?.anchor) anchor.add(d.anchor.id)
  for (const s of d?.siblings ?? []) {
    siblings.add(s.id)
    for (const f of s.folded ?? []) siblings.add(f)
  }
  return { anchor, siblings }
}

export type LensRole = 'anchor' | 'sibling' | null

// Union match [threadId, ...anchorTopics] — copy of eclipseSets.threadEclipseRole.
export function threadLensRole(
  anchorTopics: string[] | undefined,
  threadId: string,
  sets: LensSets,
): LensRole {
  const ids = [threadId, ...(anchorTopics ?? [])]
  if (ids.some((id) => sets.anchor.has(id))) return 'anchor'
  if (ids.some((id) => sets.siblings.has(id))) return 'sibling'
  return null
}

// Comma-joined topic ids for /api/v2/signals?topic= — null (never '') when empty.
export function lensTopicParam(
  d: StoryLensData | null | undefined,
  cap: number = LENS_TOPIC_CAP,
): string | null {
  if (!d?.anchor) return null
  const ids = [d.anchor.id, ...d.siblings.map((s) => s.id)].slice(0, cap)
  return ids.length ? ids.join(',') : null
}

export function siblingReasonText(s: StoryLensSibling): string {
  const first = s.reasons[0]
  return first ? `${first.basis} ${first.value}` : s.kinship
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend-v2 && npx vitest run src/lib/storyLens.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/storyLens.ts frontend-v2/src/lib/storyLens.test.ts
git commit -m "feat(story-lens): pure lens model (sets, roles, topic param)" -- frontend-v2/src/lib/storyLens.ts frontend-v2/src/lib/storyLens.test.ts
```

---

### Task 4: Lens context + portaled banner + CSS

**Files:**
- Create: `frontend-v2/src/contexts/StoryLensContext.tsx`
- Create: `frontend-v2/src/components/StoryLensBanner.tsx`
- Create: `frontend-v2/src/components/storyLens.css`
- Modify: `frontend-v2/src/main.tsx` (provider next to EclipseProvider, lines ~107–124; css import next to eclipse.css line ~70)
- Modify: `frontend-v2/src/App.tsx` (mount `<StoryLensBanner />` inside App's JSX so it sits INSIDE WorkspaceProvider — React context flows through the component tree, the portal only moves the DOM)

Clone source: `frontend-v2/src/contexts/EclipseModeContext.tsx` (75 lines) + `frontend-v2/src/components/EclipseChrome.tsx` + `frontend-v2/src/components/eclipse.css`. Read all three first.

- [ ] **Step 1: Context**

```tsx
// frontend-v2/src/contexts/StoryLensContext.tsx
// User-driven lens mode — EclipseModeContext's shell without the poll/tier machinery.
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { StoryLensData, StoryLensState } from '../lib/storyLens'

interface StoryLensValue {
  state: StoryLensState
  data: StoryLensData | null
  error: string | null
  loading: boolean
  enter: (threadId: string) => void
  exit: () => void
}

const StoryLensContext = createContext<StoryLensValue | undefined>(undefined)

export const StoryLensProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<StoryLensState>({ active: false, anchorId: null })
  const [data, setData] = useState<StoryLensData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    document.body.classList.toggle('story-lensed', state.active)
    return () => document.body.classList.remove('story-lensed')
  }, [state.active])

  const enter = useCallback((threadId: string) => {
    setState({ active: true, anchorId: threadId })
    setData(null)
    setError(null)
    setLoading(true)
    fetch(`/api/v2/story/${encodeURIComponent(threadId)}/siblings`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json: StoryLensData) => {
        setData(json)
        if (!json.anchor) setError(json.notes?.[0] ?? 'neighborhood unavailable')
      })
      .catch(() => setError('neighborhood unavailable'))
      .finally(() => setLoading(false))
  }, [])

  const exit = useCallback(() => {
    setState({ active: false, anchorId: null })
    setData(null)
    setError(null)
  }, [])

  return (
    <StoryLensContext.Provider value={{ state, data, error, loading, enter, exit }}>
      {children}
    </StoryLensContext.Provider>
  )
}

export const useStoryLens = (): StoryLensValue => {
  const ctx = useContext(StoryLensContext)
  if (!ctx) throw new Error('useStoryLens must be used within StoryLensProvider')
  return ctx
}
```

- [ ] **Step 2: Banner (portal) + CSS**

```tsx
// frontend-v2/src/components/StoryLensBanner.tsx
// Portaled to document.body: in-root fixed chrome is occluded by the command
// bar AND dimmed by mode filters (measured 2026-07-27, eclipse.css header).
import { createPortal } from 'react-dom'
import { useStoryLens } from '../contexts/StoryLensContext'
import { LabelReviewChip } from '../lib/labelReviewChip'
import './storyLens.css'

export function StoryLensBanner() {
  const { state, data, error, loading, exit } = useStoryLens()
  if (!state.active) return null
  const anchor = data?.anchor ?? null
  const label = anchor?.label ?? state.anchorId ?? ''
  return createPortal(
    <div className="sl-banner" role="status">
      <span className="sl-banner-mark">◈ STORY</span>
      <span className="sl-banner-label" data-tip={label}>{label}</span>
      {anchor?.label_status ? (
        <LabelReviewChip labelStatus={anchor.label_status} variant="chip" className="sl-banner-court" />
      ) : null}
      {data ? (
        <span className="sl-banner-counts">
          {data.siblings.length} hermanos · {anchor?.countries.length ?? 0} países
        </span>
      ) : null}
      {loading ? <span className="sl-banner-note">measuring…</span> : null}
      {error ? <span className="sl-banner-note sl-banner-degraded">⚠ {error}</span> : null}
      <button type="button" className="sl-banner-exit" onClick={exit} aria-label="Exit story lens" data-tip="Exit story lens">
        ✕
      </button>
    </div>,
    document.body,
  )
}
```

```css
/* frontend-v2/src/components/storyLens.css
   Calm scoping — cyan, NOT eclipse red. DARKEN never grayscale (eclipse lesson). */
:root { --story-cyan: #2aa7ad; }

body.story-lensed { padding-top: 28px; }
/* If the eclipse ribbon is also up, stack below it. */
body.eclipsed.story-lensed { padding-top: 56px; }
body.eclipsed.story-lensed .sl-banner { top: 28px; }

.sl-banner {
  position: fixed; top: 0; left: 0; right: 0; height: 28px;
  z-index: 100000; display: flex; align-items: center; gap: 10px;
  padding: 0 12px; font-size: 11px; letter-spacing: 0.06em;
  background: linear-gradient(90deg, #0e2e33, #0a1a20);
  color: #cfeff1; border-bottom: 1px solid var(--story-cyan);
}
.sl-banner-mark { color: var(--story-cyan); font-weight: 700; }
.sl-banner-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 38vw; }
.sl-banner-counts { color: #8fc7cb; }
.sl-banner-note { color: #8fa2bd; }
.sl-banner-degraded { color: #e2a23a; }
.sl-banner-exit { margin-left: auto; background: none; border: 1px solid #2aa7ad55; color: #cfeff1; cursor: pointer; border-radius: 3px; line-height: 1; padding: 1px 6px; }
.sl-banner-exit:hover { border-color: var(--story-cyan); }
```

- [ ] **Step 3: Mounts**

`frontend-v2/src/main.tsx`: import `StoryLensProvider` and nest it directly inside `EclipseProvider` (wrapping the same `<Routes>` block, lines ~107–124). Do NOT mount the banner here.
`frontend-v2/src/App.tsx`: import and render `<StoryLensBanner />` once, near the top of App's returned JSX (it must sit inside WorkspaceProvider for the Task 9 pin button).

- [ ] **Step 4: Build + tests**

Run: `cd frontend-v2 && npm run build && npx vitest run`
Expected: build green, suite green

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/contexts/StoryLensContext.tsx frontend-v2/src/components/StoryLensBanner.tsx frontend-v2/src/components/storyLens.css frontend-v2/src/main.tsx frontend-v2/src/App.tsx
git commit -m "feat(story-lens): lens context + portaled banner with verdicts" -- frontend-v2/src/contexts/StoryLensContext.tsx frontend-v2/src/components/StoryLensBanner.tsx frontend-v2/src/components/storyLens.css frontend-v2/src/main.tsx frontend-v2/src/App.tsx
```

---

### Task 5: NarrativeThreads — lens ordering + reason chips

**Files:**
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx` (eclipse ordering 201–216 & 355–393; #234 sibling relation 305–354; section labels 488–523; row class 525)
- Modify: `frontend-v2/src/components/NarrativeThreads.css` (lens row classes)

Precedence (explicit, from the existing mutually-exclusive branches at lines 363–367): **eclipse > story-lens > person-match > #234 sibling relation.** Preserve the N5 hover-freeze: all ordering flows through `freezeThreadOrder(liveOrdered, frozenOrder)` (lines 363–374).

- [ ] **Step 1: Derive lens sets**

Next to the eclipseSets memo (~line 209):

```tsx
const storyLens = useStoryLens()
const lensSets = useMemo(
  () => (storyLens.state.active && storyLens.data ? buildLensSets(storyLens.data) : null),
  [storyLens.state.active, storyLens.data],
)
const lensReasonById = useMemo(() => {
  const m = new Map<string, string>()
  for (const s of storyLens.data?.siblings ?? []) {
    const txt = siblingReasonText(s)
    m.set(s.id, txt)
    for (const f of s.folded ?? []) m.set(f, txt)
  }
  return m
}, [storyLens.data])
```

Imports: `useStoryLens` from `../contexts/StoryLensContext`; `buildLensSets, threadLensRole, siblingReasonText` from `../lib/storyLens`.

- [ ] **Step 2: Ordering branch**

In the ordering block (~363–367), insert the lens branch AFTER eclipse, BEFORE person/sibling:

```tsx
const lensRank = (n: Narrative): number => {
  if (!lensSets) return 2
  const role = threadLensRole(n.anchor_topics, n.thread_id, lensSets)
  return role === 'anchor' ? 0 : role === 'sibling' ? 1 : 2
}
// liveOrdered: eclipseSets branch first (unchanged); else if lensSets:
//   [...displayedNarratives].sort((a, b) => lensRank(a) - lensRank(b))  (stable re-GROUP, keep backend order within groups)
// else: existing person/sibling logic (unchanged)
```

- [ ] **Step 3: Section labels + row class + reason chip**

Mirror the eclipse section-label pattern (488–523): when `lensSets` is active, first anchor row gets label `◈ The story`, first sibling row gets `◈ Measured neighborhood`. Row class (line ~525): append `sl-row-anchor` / `sl-row-sibling` by role. On sibling rows render the receipt chip (reuse the #234 chip markup at 539–544):

```tsx
{lensRole === 'sibling' && lensReasonById.get(n.thread_id) ? (
  <span className="narrative-sibling-reason" data-tip={`Measured relation: ${lensReasonById.get(n.thread_id)}`}>
    ↔ {lensReasonById.get(n.thread_id)}
  </span>
) : null}
```

Blob honesty (T1 review #5): when the sibling's `is_blob` is true, append a `⚠ grab-bag` marker to the reason chip text (`data-tip`: "Flagged as a possible multi-story blob — relation may be inflated") — a flagged topic never renders as an unmarked peer.

CSS in `NarrativeThreads.css`:

```css
.narrative-row.sl-row-anchor { border-left: 2px solid var(--story-cyan, #2aa7ad); }
.narrative-row.sl-row-sibling { border-left: 2px solid rgba(42, 167, 173, 0.4); }
.sl-section-label { color: var(--story-cyan, #2aa7ad); font-size: 10px; letter-spacing: 0.1em; padding: 6px 8px 2px; }
```

- [ ] **Step 4: Build + full vitest**

Run: `cd frontend-v2 && npm run build && npx vitest run`
Expected: green

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/NarrativeThreads.tsx frontend-v2/src/components/NarrativeThreads.css
git commit -m "feat(story-lens): threads panel — anchor pinned + measured neighborhood with reason chips" -- frontend-v2/src/components/NarrativeThreads.tsx frontend-v2/src/components/NarrativeThreads.css
```

---

### Task 6: Stream `Story | All` tabs

**Files:**
- Modify: `frontend-v2/src/lib/streamTabs.ts` (model at 37–75, topic param 85–104, row class 108–112)
- Modify: `frontend-v2/src/lib/streamTabs.test.ts` (or create alongside if tests live elsewhere — check for an existing streamTabs test first)
- Modify: `frontend-v2/src/components/SignalStream.tsx` (tab state 139–183, fetches ~227/~333, filter skips 425 & 454, tab bar 479–497)

- [ ] **Step 1: Failing tests**

Add to the streamTabs test file:

```ts
import { streamTabModel, resolveStreamTab } from './streamTabs'

describe('story lens tab model', () => {
  it('eclipse wins over lens', () => {
    const m = streamTabModel(true, true)
    expect(m.eclipse).toBe(true)
  })
  it('lens model serves story|all with story default', () => {
    const m = streamTabModel(false, true)
    expect(m.lens).toBe(true)
    expect([...m.primary]).toEqual(['story', 'all'])
    expect(m.defaultTab).toBe('story')
  })
  it('mode flip falls back to the new default', () => {
    const lens = streamTabModel(false, true)
    expect(resolveStreamTab('notable', lens)).toBe('story')
  })
})
```

- [ ] **Step 2: Run to verify fails** — `npx vitest run src/lib/streamTabs.test.ts` (path per repo). Expected: FAIL.

- [ ] **Step 3: Implement**

In `streamTabs.ts`: add `'story'` to the `StreamTab` union; add `lens?: boolean` to `StreamTabModel`; `LENS_TABS = ['story', 'all'] as const`; change the signature to `streamTabModel(eclipseActive: boolean, lensActive = false)` — eclipse branch unchanged and FIRST, then:

```ts
if (lensActive) {
  return { eclipse: false, lens: true, primary: LENS_TABS, secondary: [], defaultTab: 'story' }
}
```

`streamRowEclipseClass`: return `'sl-row-scoped'` for `'story'`. Existing callers pass one arg — the default keeps them compiling.

In `SignalStream.tsx` (component has NO props — context is the wiring):

```tsx
const storyLens = useStoryLens()
const lensActive = storyLens.state.active && !!storyLens.data?.anchor
const tabModel = streamTabModel(eclipseActive, lensActive)
const topicParam = useMemo(() => {
  if (eclipseActive) return eclipseTopicParam(streamFilter, eclipseData)
  if (tabModel.lens && streamFilter === 'story') return lensTopicParam(storyLens.data)
  return null
}, [eclipseActive, tabModel.lens, streamFilter, eclipseData, storyLens.data])
```

Line 425 skip-condition: `if ((tabModel.eclipse || tabModel.lens) && streamFilter !== 'all') return true`. Line 454 already keys on `topicParam` — no change (a topic scope is the measured selector; keyword/noise re-filtering on top would be silent filtering). Tab bar: add `stream-filter-bar--lens` class variant and label the `story` tab `STORY`; `setStreamLevel` guard at 490 extends to `!tabModel.eclipse && !tabModel.lens`.

- [ ] **Step 4: Build + tests** — `cd frontend-v2 && npm run build && npx vitest run`. Expected: green.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/streamTabs.ts frontend-v2/src/components/SignalStream.tsx
git commit -m "feat(story-lens): stream Story|All tabs over the topic= filter" -- frontend-v2/src/lib/streamTabs.ts frontend-v2/src/components/SignalStream.tsx
```

(Include the test file path in both commands wherever it lives.)

---### Task 7: Dock re-scope (AnomalyPanel)

**Files:**
- Modify: `frontend-v2/src/components/AnomalyPanel.tsx` (scope chain lines 36–46)

- [ ] **Step 1: Extend the canonical scope chain**

```tsx
const storyLens = useStoryLens()
const lensCountry =
  !activeCountry && storyLens.state.active
    ? storyLens.data?.anchor?.countries?.[0] ?? null
    : null
const scopeCountry = activeCountry ?? lensCountry ?? relationCountry
```

(`filter.country` still wins — an explicit country focus outranks the lens; `relationCountry` stays the fallback. All three PA fetch effects and `visibleConflicts` already key on `scopeCountry`.) Add the lens to the scope badge text if one renders (mirror the "TRUMP → US" badge pattern).

- [ ] **Step 2: Build** — `cd frontend-v2 && npm run build`. Expected: green.

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/components/AnomalyPanel.tsx
git commit -m "feat(story-lens): dock public-attention re-scopes to the story's dominant country" -- frontend-v2/src/components/AnomalyPanel.tsx
```

---

### Task 8: Honesty chips on chipless L2 receipt rows

**Files:**
- Modify: `frontend-v2/src/components/CountryBrief.tsx` (line ~899 — bare `<span class="source-name">`, NO tier reference in the whole file; **eval batch 3 root-caused this as THE hole**: irna.ir / arabic.rt.com / radio.gov.pk render unmarked here)
- Modify: `frontend-v2/src/components/SignalStream.tsx` (signal-footer, line ~619)
- Modify: `frontend-v2/src/components/ThemeDetail.tsx` (`renderArticle` meta block 542–556 ONLY — note batch 3 confirmed ThemeDetail's Top Sources ALREADY renders the backend credibility tier including `⚑ state` for aa.com.tr; do not double-chip that list)
- Modify: `frontend-v2/src/components/SignalDetailPanel.tsx` (header 197–199; semantic-neighbor meta ~371)
- Modify: matching CSS files

This is the gold-eval defect fix: `resolveTierChip` (in `frontend-v2/src/lib/sourceProvenance.ts:67-96`, NOT sourceTiers.ts) is imported today only by WorkbenchPanel/Briefing/BriefNewspaper — irna.ir/rt.com render unmarked in the console.

- [ ] **Step 1: Chip pattern (copy of BriefNewspaper.tsx:831-838)**

At each site, with the data those rows actually carry (`source` only — NO origin, NO is_state_media; LOCAL honestly downgrades to UNKNOWN):

```tsx
const tc = resolveTierChip(sig.source, undefined)
{tc.tier !== 'unknown' ? (
  <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>{tc.label}</span>
) : null}
```

Render the chip beside the existing source name; suppress `unknown` (absence over noise — the chip carries signal only when the classifier knows). Do NOT touch ThemeDetail's Top Sources list itself (1324–1335) — it already renders the RICHER backend credibility tier; double-chipping is forbidden.

- [ ] **Step 2: CSS** (in each component's css, or once in `App.css`):

```css
.l2-tier-chip { font-size: 9px; letter-spacing: 0.08em; padding: 0 4px; border-radius: 3px; border: 1px solid currentColor; margin-left: 6px; }
.l2-tier-chip--state { color: #e23a1a; }
.l2-tier-chip--wire { color: #2aa7ad; }
.l2-tier-chip--major { color: #8fa2bd; }
```

- [ ] **Step 3: Build + vitest** — `cd frontend-v2 && npm run build && npx vitest run`. Expected: green.

- [ ] **Step 4: Browser spot-check** (dev server): find an RT/IRNA/TASS row in the stream → ⚑ STATE chip renders; a Reuters row → WIRE.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/SignalStream.tsx frontend-v2/src/components/ThemeDetail.tsx frontend-v2/src/components/SignalDetailPanel.tsx
git commit -m "fix(honesty): state/wire tier chips on L2 receipt rows — the eval's resolveTierChip gap" -- frontend-v2/src/components/SignalStream.tsx frontend-v2/src/components/ThemeDetail.tsx frontend-v2/src/components/SignalDetailPanel.tsx
```

(Add the CSS file(s) touched to both lists.)

---

### Task 9: Pin Story

**Files:**
- Modify: `frontend-v2/src/lib/workbench.ts` (PinSnapshot 11–25; near updatePinSnapshot 321–332)
- Test: `frontend-v2/src/lib/workbench.test.ts` (extend; check existing test file name first)
- Modify: `frontend-v2/src/contexts/WorkspaceContext.tsx` (fetchPanelSnapshot's updatePinSnapshot call, ~line 110)
- Modify: `frontend-v2/src/lib/capturePayloads.ts` (threadPin 16–23) + its test
- Modify: `frontend-v2/src/components/StoryLensBanner.tsx` (Pin button)
- Modify: `frontend-v2/src/components/DossierView.tsx` (render frozen neighborhood, pin block 700–764)

- [ ] **Step 1: Failing tests for the merge primitive**

```ts
// in the workbench test file
import { addPin, createInvestigation, mergePinSnapshot, getInvestigation } from './workbench'

it('mergePinSnapshot merges fields instead of replacing (race-proof)', () => {
  const inv = createInvestigation('Lens test')
  addPin(inv.id, { anchorId: 'theme-x', anchorType: 'theme', label: 'X', snapshot: { capturedAt: '2026-07-28T00:00:00Z', summary: 'seed' } })
  mergePinSnapshot(inv.id, 'theme-x', { siblings: [{ id: 'dynamic-topic-2', label: 'Sib', weight: 0.7, reason: 'whitened_cos 0.70' }] })
  mergePinSnapshot(inv.id, 'theme-x', { summary: 'enriched', evidence: [{ headline: 'h' }] })
  const pin = getInvestigation(inv.id)!.pins.find((p) => p.anchorId === 'theme-x')!
  expect(pin.snapshot?.summary).toBe('enriched')
  expect(pin.snapshot?.siblings?.length).toBe(1)          // survived the second write
  expect(pin.snapshot?.capturedAt).toBe('2026-07-28T00:00:00Z') // earliest capture wins
})
```

- [ ] **Step 2: Run to verify fails**, then implement:

In `workbench.ts` — extend the type and add the merge:

```ts
// PinSnapshot gains (keep O(1KB): top-8, no per-sibling evidence — sync is whole-blob LWW):
siblings?: Array<{ id: string; label: string; weight: number; reason: string }>
```

```ts
export function mergePinSnapshot(
  investigationId: string,
  anchorId: string,
  partial: Partial<PinSnapshot>,
): Investigation | null {
  const inv = getInvestigation(investigationId)
  if (!inv) return null
  const pin = inv.pins.find((p) => p.anchorId === anchorId)
  if (!pin) return null
  const existing = pin.snapshot
  pin.snapshot = {
    ...(existing ?? { capturedAt: new Date().toISOString() }),
    ...partial,
    capturedAt: existing?.capturedAt ?? partial.capturedAt ?? new Date().toISOString(),
  }
  inv.updatedAt = new Date().toISOString()
  persist()  // use this module's actual store-write helper (writeStore/save — check the file)
  return inv
}
```

In `WorkspaceContext.tsx` ~line 110: swap `updatePinSnapshot(...)` → `mergePinSnapshot(...)` (enrichment is a superset write; merging kills the last-writer-wins race that would drop lens siblings).

In `capturePayloads.ts`, extend threadPin backward-compatibly:

```ts
export function threadPin(id: string, label: string, opts?: { lens?: boolean }): PinPayload {
  return {
    id: `theme-${id}`,
    type: 'theme',
    title: label,
    urlParams: `?theme=${encodeURIComponent(id)}${opts?.lens ? '&lens=story' : ''}`,
  }
}
```

- [ ] **Step 3: Banner Pin button** (in `StoryLensBanner.tsx`):

```tsx
const { pinItem, isPinned } = useWorkspace()
const pinId = state.anchorId ? `theme-${state.anchorId}` : null
const onPin = () => {
  if (!state.anchorId || !data?.anchor) return
  pinItem(threadPin(state.anchorId, data.anchor.label, { lens: true }))
  const invId = getActiveInvestigationId()
  if (invId) {
    mergePinSnapshot(invId, `theme-${state.anchorId}`, {
      siblings: data.siblings.slice(0, 8).map((s) => ({
        id: s.id, label: s.label, weight: s.weight, reason: siblingReasonText(s),
      })),
    })
  }
}
// render: <button className="sl-banner-pin" onClick={onPin} data-tip="Freeze this neighborhood into an investigation">{pinId && isPinned(pinId) ? '◆ pinned' : '◇ Pin story'}</button>
```

- [ ] **Step 4: DossierView** — in the pin snapshot block (700–764), after evidence:

```tsx
{pin.snapshot?.siblings?.length ? (
  <div className="dossier-pin-neighborhood">
    <div className="dossier-pin-neighborhood-title">MEASURED NEIGHBORHOOD (frozen)</div>
    {pin.snapshot.siblings.map((s) => (
      <div key={s.id} className="dossier-pin-neighborhood-row">
        {s.label} <span className="dossier-pin-neighborhood-reason">↔ {s.reason}</span>
      </div>
    ))}
  </div>
) : null}
```

- [ ] **Step 5: Build + full vitest** — `cd frontend-v2 && npm run build && npx vitest run`. Expected: green.

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/lib/workbench.ts frontend-v2/src/contexts/WorkspaceContext.tsx frontend-v2/src/lib/capturePayloads.ts frontend-v2/src/components/StoryLensBanner.tsx frontend-v2/src/components/DossierView.tsx
git commit -m "feat(story-lens): Pin story — merge-safe snapshot with frozen neighborhood receipts" -- frontend-v2/src/lib/workbench.ts frontend-v2/src/contexts/WorkspaceContext.tsx frontend-v2/src/lib/capturePayloads.ts frontend-v2/src/components/StoryLensBanner.tsx frontend-v2/src/components/DossierView.tsx
```

(Add the two test files touched to both lists.)

---

### Task 10: Entry — auto-enter + deep link + exit wiring

**Files:**
- Modify: `frontend-v2/src/App.tsx` (thread-open handler `handleThemeSelect`; entrySource pattern lines 368–376; thread close/clear paths)

- [ ] **Step 1: Auto-enter on thread open** (spec D7: opening a story opens the mode). In `handleThemeSelect` (after the existing open logic), for thread-shaped ids only:

```tsx
// v1 lens anchors are DYNAMIC topics only — the siblings endpoint returns
// unsupported_anchor_type for atlas 'slug--cc' and emergent-cluster ids
// (no dynamic_topics centroid; T2 quality review issue 3, recorded decision).
const isLensAnchor = (id: string) => id.startsWith('dynamic-topic-')
if (STORY_LENS_AUTO && isLensAnchor(themeId)) storyLens.enter(themeId)
```

(Atlas and emergent-cluster threads keep today's open behavior — never a lens that is guaranteed empty. Widening the anchor set is a v1.1 item alongside country/person anchors. The banner label comes from the endpoint payload; no label needed at enter time.)

- [ ] **Step 2: Exit wiring.** Wherever the thread detail closes or focus fully clears (ThemeDetail close handler + FocusIndicator `onClear` path in App), call `storyLens.exit()`. Entering a DIFFERENT thread re-enters (enter replaces state wholesale — already handled).

- [ ] **Step 2b: Sticky lens during re-anchor (T6 quality-review issue 1).** Clicking a sibling row re-enters with a new anchor; `enter()` nulls `data` synchronously, so `hasLensContent` goes false for the fetch-latency window and SignalStream tears down to the CATEGORY model (streamFilter rewritten to 'notable', full unscoped refetch) then flips back — two stream resets per re-anchor. Fix in SignalStream's `lensActive` derivation: hold the lens model while a re-enter is in flight — `storyLens.state.active && (hasLensContent(storyLens.data) || storyLens.loading)` — and make `topicParam` return the PREVIOUS non-null lens param while loading (keep a ref), so the tab bar and scope never flicker mid-walk. Also apply the same `|| loading` hold to NarrativeThreads' `lensOn` ONLY if the ordering flicker proves visible in the T11 walkthrough (ordering is cheaper to re-run than a network refetch — decide by observation, not preemptively).

- [ ] **Step 3: Deep link.** Next to the `entry=eclipse` effect (368–376), add a reactive effect on `location.search`:

```tsx
useEffect(() => {
  const p = new URLSearchParams(location.search)
  const theme = p.get('theme')
  if (p.get('lens') === 'story' && theme && !storyLens.state.active) storyLens.enter(theme)
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [location.search])
```

`?lens=` survives focus writes (`mergeFocusIntoParams` only owns theme/country/person) — which is exactly why every EXIT path must STRIP it: the pre-existing theme deep-link effect re-fires `handleThemeSelect` on any unrelated URL write while `theme=` persists, and a surviving `lens=` would silently resurrect an explicitly-dismissed lens (found live in T10 verification; fixed via stripLensParam on every exit + the isSameThemeReopen guard — the referenced 'spec-review issue 4').

- [ ] **Step 4: Build + full vitest** — `cd frontend-v2 && npm run build && npx vitest run`. Expected: green.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "feat(story-lens): open-story enters the lens; deep link ?lens=story; clean exit" -- frontend-v2/src/App.tsx
```

---

### Task 11: Gate — browser verification + NAV-LOSS spot-check

**Files:**
- Create: `docs/research/gold/2026-07-XX-story-lens-navloss-check.md` (dated at run time)

- [ ] **Step 1: Full suites.** `cd backend && .venv/bin/python -m pytest -q tests/test_story_siblings.py tests/test_story_router_contract.py` and `cd frontend-v2 && npm run build && npx vitest run`. Expected: green (modulo the 2 documented pre-existing query_thread failures).

- [ ] **Step 2: Browser walkthrough** (dev server against real data, desktop + 375px):
1. Open a thread from search → banner appears with label + court chip when the anchor is court-flagged; console reconfigures.
2. Threads panel: anchor on top under `◈ The story`; siblings under `◈ Measured neighborhood`, each with an `↔` receipt chip.
3. Stream: `STORY | ALL` tabs; STORY scoped via `topic=` (verify the request in the network log); ALL restores.
4. Dock: Anomaly panel scoped to the anchor's dominant country.
5. Kill the siblings endpoint (devtools offline for that request) → banner shows `⚠ neighborhood unavailable`, console NEVER blanks.
6. Pin story → Workbench shows the pin; DossierView shows MEASURED NEIGHBORHOOD (frozen); reopening the pin deep-links back INTO the lens.
7. ✕ exits clean; `?lens=story&theme=…` in a fresh tab re-enters.
8. Eclipse co-active check: with eclipse ambient on, the lens banner stacks below the ribbon (56px padding), colors never mix (red vs cyan).

- [ ] **Step 3: NAV-LOSS spot-check — the acceptance number.** Re-run ≥5 gold UI queries (GQ-01 Berlin Pride class + the batch-1/2 NAV-LOSS witnesses) under rubric v2's N1 dimension: search → open one thread → are the other promised threads reachable WITH receipts from inside the lens? Record promised-vs-delivered per query in the artifact. **Ship criterion: NAV-LOSS falls from 10/10 baseline on the re-run set.**

- [ ] **Step 4: Commit the artifact**

```bash
git add docs/research/gold/2026-07-XX-story-lens-navloss-check.md
git commit -m "measure(story-lens): NAV-LOSS spot-check post-lens" -- docs/research/gold/2026-07-XX-story-lens-navloss-check.md
```

---

## Deferred (explicitly NOT in this plan)

- **Spec §8 bullet 5 — syndication collapsed with count in the lens-scoped stream** — NOT delivered in v1 (found by the final whole-implementation review as the one unrecorded gap; recorded here). The stream's lens tabs render rows as-is; syndication collapse rides the existing `_norm_headline` machinery server-side only. V1.1 candidate alongside the lanes.

- **Spec §10 item 3 reconciliation:** the TIMELINE lane needs NO new code — ThemeDetail (the lens's protagonist panel) already renders the combined activity timeline (C4b, shipped 2026-07-21); the VOICE lane moves to v1.1 alongside the country anchor (voice-mix is country-keyed, so it lands naturally with the country-anchored shell). Atención + Anomalías ship in v1 via Task 7 (AnomalyPanel carries both).
- V1.1: physical-events + markets lanes; VOICE lane; country/person anchors on the shared shell.
- V2: article-body enrichment through the Brief's fetch machinery; universal PA→story resolution.
- Folding eclipse internals onto the shared shell (spec §11 boundary).
- Sibling tau calibration cadence (spec §14) — v1 ships on the walk's measured `WalkParams` defaults (rel_floor 0.35, hop_cap 3, dedup 0.85, all pre-measured in the chains work).
