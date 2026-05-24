# Living Narrative Threads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first read-only Living Narrative Threads layer so Atlas surfaces natural, evidence-backed threads instead of exposing fixed topics as the product model.

**Architecture:** Add a backend thread assembler above existing hot-window topic, signal, country, source, and sentiment tables. Keep `atlas_topics` as internal anchors, expose `/api/v2/threads` as a beta read contract, then adapt Brief and NarrativeThreads to consume the thread shape while preserving existing theme-based fallbacks.

**Tech Stack:** FastAPI, PostgreSQL/Supabase SQL, React + Vite, existing Atlas topic assignment tables, existing briefing/narratives UI components.

---

## File Structure

- Create `backend/app/services/thread_intelligence.py`: pure data assembly helpers and scoring functions.
- Create `backend/app/routers/threads.py`: `/api/v2/threads` and `/api/v2/threads/{thread_id}` beta routes.
- Modify `backend/app/main_v2.py`: register the threads router.
- Create `backend/tests/test_thread_intelligence.py`: unit tests for labels, confidence bands, velocity, and evidence roles.
- Create `backend/tests/test_threads_router.py`: API-shape tests with monkeypatched service output.
- Modify `frontend-v2/src/types/threads.ts`: shared thread response types.
- Modify `frontend-v2/src/pages/BriefNewspaper.tsx`: read `top_threads` or fetch `/api/v2/threads` behind a safe fallback.
- Modify `frontend-v2/src/components/NarrativeThreads.tsx`: accept thread-shaped rows through an adapter while keeping theme rows as fallback.
- Add/update frontend smoke tests if the existing test harness is healthy.

## Task 1: Backend Thread Types And Pure Scoring

**Files:**
- Create: `backend/app/services/thread_intelligence.py`
- Test: `backend/tests/test_thread_intelligence.py`

- [ ] **Step 1: Write tests for thread confidence bands**

```python
from app.services.thread_intelligence import confidence_band


def test_confidence_band_high():
    assert confidence_band(evidence_count=80, source_count=12, geo_count=5, assignment_confidence=0.82) == "high"


def test_confidence_band_thin():
    assert confidence_band(evidence_count=6, source_count=2, geo_count=1, assignment_confidence=0.7) == "thin"


def test_confidence_band_degraded():
    assert confidence_band(evidence_count=100, source_count=1, geo_count=1, assignment_confidence=0.4) == "degraded"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: FAIL because `app.services.thread_intelligence` does not exist.

- [ ] **Step 3: Add the minimal confidence implementation**

```python
from __future__ import annotations


def confidence_band(
    *,
    evidence_count: int,
    source_count: int,
    geo_count: int,
    assignment_confidence: float,
) -> str:
    if assignment_confidence < 0.5 or source_count <= 1:
        return "degraded"
    if evidence_count >= 50 and source_count >= 6 and geo_count >= 2 and assignment_confidence >= 0.75:
        return "high"
    if evidence_count >= 10 and source_count >= 3 and assignment_confidence >= 0.6:
        return "medium"
    return "thin"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: PASS.

## Task 2: Thread Label And ID Contract

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`

- [ ] **Step 1: Add tests for deterministic labels and IDs**

```python
from app.services.thread_intelligence import build_thread_id, build_thread_label


def test_build_thread_id_is_stable():
    assert build_thread_id("fuel-subsidy-unrest", ["NG", "PE"]) == "fuel-subsidy-unrest--ng-pe"


def test_build_thread_label_uses_topic_and_geography():
    label = build_thread_label(
        anchor_label="Fuel subsidy unrest",
        top_countries=["Nigeria", "Peru"],
        changed_10h=42,
    )
    assert label == "Fuel subsidy unrest intensifies in Nigeria and Peru"
```

- [ ] **Step 2: Run the focused test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: FAIL for missing functions.

- [ ] **Step 3: Implement deterministic helpers**

```python
def build_thread_id(anchor_slug: str, country_codes: list[str]) -> str:
    suffix = "-".join(code.lower() for code in country_codes[:3] if code)
    return f"{anchor_slug}--{suffix}" if suffix else anchor_slug


def build_thread_label(*, anchor_label: str, top_countries: list[str], changed_10h: int) -> str:
    if len(top_countries) >= 2:
        place = f"{top_countries[0]} and {top_countries[1]}"
    elif top_countries:
        place = top_countries[0]
    else:
        place = "multiple regions"

    verb = "intensifies" if changed_10h > 0 else "continues"
    return f"{anchor_label} {verb} in {place}"
```

- [ ] **Step 4: Run the focused test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: PASS.

## Task 3: Read-Only Thread Assembler

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`

- [ ] **Step 1: Add a test for assembling thread dictionaries from rows**

```python
from app.services.thread_intelligence import assemble_thread


def test_assemble_thread_contract():
    row = {
        "topic_slug": "fuel-subsidy-unrest",
        "topic_label": "Fuel subsidy unrest",
        "signal_count": 120,
        "source_count": 18,
        "country_count": 3,
        "avg_confidence": 0.81,
        "changed_10h": 47,
        "sentiment_swing_10h": -0.24,
        "top_countries": ["NG", "PE"],
        "top_country_names": ["Nigeria", "Peru"],
        "top_sources": ["reuters.com", "elcomercio.pe"],
    }
    thread = assemble_thread(row)
    assert thread["thread_id"] == "fuel-subsidy-unrest--ng-pe"
    assert thread["anchor_topics"] == ["fuel-subsidy-unrest"]
    assert thread["confidence"] == "high"
    assert thread["why_now"] == "47 more signals in the last 10h, concentrated in Nigeria and Peru."
```

- [ ] **Step 2: Run the test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: FAIL for missing `assemble_thread`.

- [ ] **Step 3: Implement `assemble_thread`**

```python
def assemble_thread(row: dict) -> dict:
    country_codes = list(row.get("top_countries") or [])
    country_names = list(row.get("top_country_names") or [])
    changed_10h = int(row.get("changed_10h") or 0)
    label = build_thread_label(
        anchor_label=str(row["topic_label"]),
        top_countries=country_names,
        changed_10h=changed_10h,
    )
    confidence = confidence_band(
        evidence_count=int(row.get("signal_count") or 0),
        source_count=int(row.get("source_count") or 0),
        geo_count=int(row.get("country_count") or 0),
        assignment_confidence=float(row.get("avg_confidence") or 0),
    )
    place = " and ".join(country_names[:2]) if country_names else "multiple regions"
    return {
        "thread_id": build_thread_id(str(row["topic_slug"]), country_codes),
        "label": label,
        "summary": label,
        "anchor_topics": [row["topic_slug"]],
        "signal_count": int(row.get("signal_count") or 0),
        "source_count": int(row.get("source_count") or 0),
        "country_count": int(row.get("country_count") or 0),
        "changed_10h": changed_10h,
        "sentiment_swing_10h": row.get("sentiment_swing_10h"),
        "top_countries": country_codes,
        "top_country_names": country_names,
        "top_sources": list(row.get("top_sources") or []),
        "confidence": confidence,
        "why_now": f"{changed_10h} more signals in the last 10h, concentrated in {place}.",
        "subthreads": [],
        "related_threads": [],
        "evidence_samples": [],
    }
```

- [ ] **Step 4: Run the test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: PASS.

## Task 4: Beta Threads Router

**Files:**
- Create: `backend/app/routers/threads.py`
- Modify: `backend/app/main_v2.py`
- Create: `backend/tests/test_threads_router.py`

- [ ] **Step 1: Write router tests with monkeypatched service**

```python
from fastapi.testclient import TestClient

from app.main_v2 import app
from app.routers import threads


def test_threads_endpoint_returns_beta_contract(monkeypatch):
    monkeypatch.setattr(
        threads,
        "fetch_threads",
        lambda hours, limit: [{"thread_id": "fuel-subsidy-unrest--ng", "label": "Fuel subsidy unrest intensifies in Nigeria"}],
    )
    client = TestClient(app)
    res = client.get("/api/v2/threads?hours=24&limit=5")
    assert res.status_code == 200
    assert res.json()["threads"][0]["thread_id"] == "fuel-subsidy-unrest--ng"
    assert res.json()["beta"] is True
```

- [ ] **Step 2: Run router test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_threads_router.py -q`

Expected: FAIL because router is missing.

- [ ] **Step 3: Implement router**

```python
from fastapi import APIRouter, Query

from app.services.thread_intelligence import fetch_threads

router = APIRouter(prefix="/api/v2", tags=["threads"])


@router.get("/threads")
async def get_threads(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    return {"beta": True, "hours": hours, "threads": fetch_threads(hours=hours, limit=limit)}
```

In `backend/app/main_v2.py`, import and include the router:

```python
from app.routers import threads

app.include_router(threads.router)
```

- [ ] **Step 4: Run router test**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_threads_router.py -q`

Expected: PASS.

## Task 5: SQL Fetch Function

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`

- [ ] **Step 1: Add query-shape test**

```python
from app.services.thread_intelligence import THREADS_SQL


def test_threads_sql_uses_assignments_and_atlas_topics():
    assert "signal_topic_assignments" in THREADS_SQL
    assert "atlas_topics" in THREADS_SQL
    assert "model_version = 'theme-hint-lex-v2'" in THREADS_SQL
    assert "assigned_at >= now() - (%s * interval '1 hour')" in THREADS_SQL
```

- [ ] **Step 2: Run focused tests**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: FAIL until SQL constant exists.

- [ ] **Step 3: Implement SQL constant and fetch wrapper**

The SQL should aggregate by atlas topic for the first beta. It should include
`signal_count`, `source_count`, `country_count`, `avg_confidence`, top countries,
and top sources. Keep the first version read-only and bounded by `hours` and
`limit`.

- [ ] **Step 4: Add database integration only if local env has `DATABASE_URL`**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py -q`

Expected: PASS without requiring live database.

## Deferred Task 6: Frontend Thread Types And Adapter

Status 2026-05-24: deferred until live `/api/v2/threads?hours=24&limit=10`
output is manually reviewed. This avoids wiring the UI to a beta assembler
before validating that its top threads are coherent.

**Files:**
- Create: `frontend-v2/src/types/threads.ts`
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`

- [ ] **Step 1: Add shared type**

```ts
export interface LivingThread {
  thread_id: string
  label: string
  summary?: string
  anchor_topics: string[]
  signal_count: number
  source_count: number
  country_count: number
  changed_10h?: number
  sentiment_swing_10h?: number | null
  top_countries: string[]
  top_country_names?: string[]
  top_sources?: string[]
  confidence: 'high' | 'medium' | 'thin' | 'degraded'
  why_now?: string
}
```

- [ ] **Step 2: Add adapter without changing current behavior**

Create a function in `NarrativeThreads.tsx` that maps a legacy `Narrative` row
to the `LivingThread` shape. The first frontend PR should not remove legacy
fields or break current `/api/v2/narratives`.

- [ ] **Step 3: Run frontend build**

Run: `cd frontend-v2 && npm run build`

Expected: PASS.

## Task 7: Brief Beta Consumption

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`

- [ ] **Step 1: Fetch `/api/v2/threads` in parallel with briefing**

Only render thread beta data if the response is successful. If it fails, Brief
must behave exactly as it does today.

- [ ] **Step 2: Render top thread cards in place of top themes only when present**

Do not remove top theme fallback. Show `why_now`, signal count, top countries,
and confidence.

- [ ] **Step 3: Run frontend build**

Run: `cd frontend-v2 && npm run build`

Expected: PASS.

## Task 8: Verification And Issue Updates

**Files:**
- Modify: `STATUS.md`
- Modify: `docs/roadmap/2026-05-21-data-operating-roadmap.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Run focused backend tests**

Run: `cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_thread_intelligence.py tests/test_threads_router.py -q`

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend-v2 && npm run build`

Expected: PASS.

- [ ] **Step 3: Update docs**

Record the beta contract, fallback behavior, and any issues that should be
closed/evolved.

- [ ] **Step 4: Open PR**

Base branch should be `v3-intel-layer` unless this plan is stacked on a pending
topic-taxonomy PR.

Commit:

```bash
git add backend/app/services/thread_intelligence.py backend/app/routers/threads.py backend/app/main_v2.py backend/tests/test_thread_intelligence.py backend/tests/test_threads_router.py frontend-v2/src/types/threads.ts frontend-v2/src/components/NarrativeThreads.tsx frontend-v2/src/pages/BriefNewspaper.tsx STATUS.md docs/roadmap/2026-05-21-data-operating-roadmap.md AGENTS.md
git commit -m "feat(threads): add living narrative threads beta"
```

## Self-Review

- Spec coverage: the plan covers the thread contract, backend assembler, beta
  endpoints, Brief, NarrativeThreads, evidence/fallback guardrails, and docs.
- Placeholder scan: implementation steps define concrete behavior and should
  not ask the worker to invent behavior without a contract.
- Type consistency: frontend `LivingThread` fields match backend output keys.
