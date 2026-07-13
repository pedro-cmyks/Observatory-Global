# Investigation Graph Slice 1 Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the thread and semantic discovery lanes reliable enough to serve as the measured substrate for the shared L1/L2/L3 Investigation Graph.

**Architecture:** Preserve the existing dynamic-topic-first, stories-only contract while removing the discarded atlas aggregate query from its hot path. Translate only database-owned client timeouts into Atlas's existing honest `503 db_busy` response, and split semantic retrieval into independently degraded centroid, taxonomy-anchor, and signal-headline components so one failure cannot erase useful results from the others.

**Tech Stack:** Python 3.11, FastAPI, asyncpg, pytest, Supabase Postgres, Fly.io.

## Global Constraints

- `dynamic_topics` and user-facing Narrative Threads are the same product object at different layers.
- Global and single-country thread lists are stories-only by default; category aggregates appear only behind the existing kill switches.
- A thin substrate yields a short or empty list, never category filler.
- Ranking and omission remain visible through reason codes and coverage gaps.
- LLMs do not decide graph topology or evidence truth.
- Production deploys use `scripts/deploy-fly-api.sh`, never a bare `fly deploy`.
- Do not modify the deprecated `frontend/` directory.

---

## File Map

- `backend/app/services/thread_intelligence.py` — dynamic/atlas/emergent thread query orchestration and database-timeout boundary.
- `backend/app/main_v2.py` — Atlas-wide response mapping for the explicit database-busy exception.
- `backend/app/services/research_anchor_discovery.py` — semantic discovery orchestration and component-specific coverage gaps.
- `backend/tests/test_thread_intelligence.py` — behavioral query-count and fallback tests.
- `backend/tests/test_db_busy_degradation.py` — real-app response contract for database-owned client timeouts.
- `backend/tests/test_research_semantic.py` — semantic sub-lane isolation tests.
- `docs/state/2026-07-12-investigation-graph-slice-1-reliability.md` — measured local and production delivery record.

### Task 1: Remove discarded atlas work from the stories-only thread path

**Files:**
- Modify: `backend/app/services/thread_intelligence.py:1877-2005`
- Test: `backend/tests/test_thread_intelligence.py`

**Interfaces:**
- Consumes: `fetch_threads(hours, limit, topic_slug, country_codes, person, attach_evidence, conn)` and the existing `ATLAS_THREADS_CATEGORY_ROWS` / `ATLAS_COUNTRY_CATEGORY_ROWS` flags.
- Produces: the same `list[dict[str, Any]]` contract, with atlas aggregation queried only for atlas-only or explicitly category-enabled requests.

- [ ] **Step 1: Add a failing test for the stories-only query budget**

```python
def test_fetch_threads_stories_only_skips_discarded_atlas_query():
    class FakeConn:
        def __init__(self):
            self.fetch_calls = []

        async def fetch(self, query, *args, **kwargs):
            self.fetch_calls.append(query)
            if "FROM dynamic_topics dt" in query:
                return []
            if "FROM emergent_clusters" in query:
                return []
            raise AssertionError("stories-only path queried atlas category aggregates")

    result = asyncio.run(fetch_threads(hours=24, limit=10, conn=FakeConn()))
    assert result == []
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd backend && .venv/bin/pytest tests/test_thread_intelligence.py::test_fetch_threads_stories_only_skips_discarded_atlas_query -q`

Expected: FAIL with `stories-only path queried atlas category aggregates`.

- [ ] **Step 3: Add a failing category-kill-switch test**

```python
def test_fetch_threads_category_kill_switch_still_fetches_atlas(monkeypatch):
    monkeypatch.setenv("ATLAS_THREADS_CATEGORY_ROWS", "on")
    calls = []

    class FakeConn:
        async def fetch(self, query, *args, **kwargs):
            calls.append(query)
            return []

    asyncio.run(fetch_threads(hours=24, limit=10, conn=FakeConn()))
    assert any("signal_topic_assignments" in query for query in calls)
```

- [ ] **Step 4: Run the kill-switch test and verify its current behavior is protected**

Run: `cd backend && .venv/bin/pytest tests/test_thread_intelligence.py::test_fetch_threads_category_kill_switch_still_fetches_atlas -q`

Expected: PASS before and after the refactor; this is the characterization guardrail.

- [ ] **Step 5: Refactor `_merged` to decide the product mode before querying atlas**

```python
        category_rows = _category_rows_enabled(single_country=single_country)
        if atlas_only:
            return await _fetch_threads_with_conn(...)

        dynamic = await _fetch_dynamic_threads_with_conn(...)
        if category_rows:
            atlas = await _fetch_threads_with_conn(...)
            return _merge_category_rows(dynamic, atlas, limit=limit)
        if dynamic:
            return dedupe_same_event_threads(rank_threads(dynamic))[:limit]
```

Keep the global emergent fallback and country honest-empty behavior unchanged. Extract only small helpers needed to make the mode decision and category merge explicit; do not change ranking.

- [ ] **Step 6: Run focused and neighboring tests**

Run: `cd backend && .venv/bin/pytest tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py tests/test_thread_person_filter.py -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit the hot-path correction**

```bash
git add backend/app/services/thread_intelligence.py backend/tests/test_thread_intelligence.py
git commit -m "fix(threads): skip discarded atlas query"
```

### Task 2: Map database-owned client timeouts to honest 503 responses

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/app/main_v2.py:68-98`
- Test: `backend/tests/test_db_busy_degradation.py`
- Test: `backend/tests/test_thread_intelligence.py`

**Interfaces:**
- Produces: `DatabaseBusyError`, raised only when an awaited asyncpg thread query raises built-in `TimeoutError`.
- Produces: HTTP `503`, JSON `{"reason":"db_busy", ...}`, and `Retry-After: 10` through the existing app handler.

- [ ] **Step 1: Add a failing service-boundary test**

```python
def test_fetch_threads_translates_database_command_timeout():
    class TimedOutConn:
        async def fetch(self, query, *args, **kwargs):
            raise TimeoutError("command timeout")

    with pytest.raises(DatabaseBusyError):
        asyncio.run(fetch_threads(hours=24, limit=10, conn=TimedOutConn()))
```

- [ ] **Step 2: Run it and verify RED**

Run: `cd backend && .venv/bin/pytest tests/test_thread_intelligence.py::test_fetch_threads_translates_database_command_timeout -q`

Expected: FAIL because `DatabaseBusyError` is not yet defined/exported.

- [ ] **Step 3: Implement the narrow exception boundary**

```python
class DatabaseBusyError(RuntimeError):
    """A database command timed out after connection acquisition."""


async def _database_fetch(awaitable):
    try:
        return await awaitable
    except TimeoutError as exc:
        raise DatabaseBusyError("database command timed out") from exc
```

Apply the translation at the `fetch_threads` database-owned execution boundary. Do not register generic `TimeoutError` globally and do not relabel embedding, HTTP, or other external timeouts.

- [ ] **Step 4: Add a failing real-app response test**

```python
@app.get("/__test__/database-busy-error")
async def _raise_database_busy_error():
    raise DatabaseBusyError("database command timed out")


def test_explicit_database_busy_error_returns_503():
    response = client.get("/__test__/database-busy-error")
    assert response.status_code == 503
    assert response.json()["reason"] == "db_busy"
    assert response.headers["retry-after"] == "10"
```

- [ ] **Step 5: Register `DatabaseBusyError` with the existing handler**

```python
from app.services.thread_intelligence import DatabaseBusyError

app.add_exception_handler(DatabaseBusyError, _handle_db_busy)
```

- [ ] **Step 6: Verify both positive and negative timeout contracts**

Run: `cd backend && .venv/bin/pytest tests/test_db_busy_degradation.py tests/test_thread_intelligence.py -q`

Expected: PASS, including `test_generic_timeout_is_not_mislabeled_as_database_contention`.

- [ ] **Step 7: Commit the degradation contract**

```bash
git add backend/app/main_v2.py backend/app/services/thread_intelligence.py backend/tests/test_db_busy_degradation.py backend/tests/test_thread_intelligence.py
git commit -m "fix(api): expose thread database timeouts honestly"
```

### Task 3: Isolate semantic discovery components

**Files:**
- Modify: `backend/app/services/research_anchor_discovery.py:250-372`
- Test: `backend/tests/test_research_semantic.py`

**Interfaces:**
- Consumes: one query embedding plus optional async fetchers for story centroids, atlas anchors, and signal matches.
- Produces: all successful anchors/evidence plus a `lane_degraded` gap containing `lane="semantic"` and `component` for each failed component.

- [ ] **Step 1: Add a failing signal-headline isolation test**

```python
def test_signal_timeout_preserves_centroid_anchors_and_names_component_gap():
    async def no_threads(**kwargs):
        return []
    async def centroids():
        return TOPICS
    async def broken_signals(**kwargs):
        raise TimeoutError("ANN timeout")

    plan = asyncio.run(discover_anchors(
        parse_research_intent("Iran climate water drought"), hours=24,
        fetch_threads_fn=no_threads, fetch_attention_fn=None,
        embed_query_fn=lambda _: QUERY_VEC,
        fetch_centroids_fn=centroids,
        fetch_signal_matches_fn=broken_signals,
    ))

    assert any(a.get("match_basis") == "member_centroid" for a in plan["anchors"])
    assert any(
        gap.get("component") == "signal_headline"
        for gap in plan["coverage_gaps"]
    )
```

- [ ] **Step 2: Run it and verify RED**

Run: `cd backend && .venv/bin/pytest tests/test_research_semantic.py::test_signal_timeout_preserves_centroid_anchors_and_names_component_gap -q`

Expected: FAIL because the broad semantic `try` currently reports only a generic gap.

- [ ] **Step 3: Add failing centroid and taxonomy isolation tests**

Add two tests proving: (a) a centroid fetch timeout preserves atlas and signal results, and (b) an atlas-anchor timeout preserves centroid and signal results. Each test must assert the exact failed component (`story_centroid` or `topic_description`) in `coverage_gaps`.

- [ ] **Step 4: Run both tests and verify RED**

Run: `cd backend && .venv/bin/pytest tests/test_research_semantic.py -k "timeout_preserves" -q`

Expected: the new isolation tests FAIL for the missing component boundaries.

- [ ] **Step 5: Implement a component-specific gap helper and independent try blocks**

```python
def _semantic_component_gap(component: str, exc: Exception) -> dict[str, Any]:
    return {
        "gap_type": "lane_degraded",
        "lane": "semantic",
        "component": component,
        "note": f"Semantic {component.replace('_', ' ')} unavailable ({exc.__class__.__name__}).",
    }
```

After query embedding succeeds, wrap `fetch_centroids_fn`, `fetch_atlas_anchors_fn`, and `fetch_signal_matches_fn` independently. Append successful results immediately. Keep the existing thin-centroid visible gap and lexical-only behavior when the query embedder is absent.

- [ ] **Step 6: Run semantic and full research tests**

Run: `cd backend && .venv/bin/pytest tests/test_research_semantic.py tests/test_research_anchor_discovery.py tests/test_research_ranking.py tests/test_research_walkthrough_fixture.py -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit semantic fault isolation**

```bash
git add backend/app/services/research_anchor_discovery.py backend/tests/test_research_semantic.py
git commit -m "fix(research): isolate semantic retrieval failures"
```

### Task 4: Verify, deploy, and record production evidence

**Files:**
- Create: `docs/state/2026-07-12-investigation-graph-slice-1-reliability.md`
- Modify only if required by measured regressions: files from Tasks 1-3 with a new failing test first.

**Interfaces:**
- Produces: a deployed API whose 24h and 168h thread lists are non-erroring and whose research plans preserve partial results with explicit gaps.

- [ ] **Step 1: Run the focused suite and repository backend gate**

Run: `cd backend && .venv/bin/pytest tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py tests/test_db_busy_degradation.py tests/test_research_semantic.py tests/test_research_anchor_discovery.py tests/test_research_ranking.py tests/test_research_walkthrough_fixture.py -q`

Expected: all tests PASS.

Run: `cd backend && .venv/bin/pytest -q`

Expected: all tests PASS or pre-existing unrelated failures recorded verbatim before proceeding.

- [ ] **Step 2: Measure the local live query path**

Run the existing local API or a read-only service script against the configured database and record wall times and result counts for:

```text
/api/v2/threads?hours=24&limit=10
/api/v2/threads?hours=168&limit=24
/api/v2/research/plan?query=NATO%20summit%20Ankara&hours=24
```

Acceptance: thread requests do not execute `THREADS_SQL` in stories-only mode; each endpoint returns an honest success or explicit `503 db_busy`, never raw 500.

- [ ] **Step 3: Deploy the API through the repository wrapper**

Run: `scripts/deploy-fly-api.sh`

Expected: Fly deployment succeeds and health checks pass.

- [ ] **Step 4: Smoke production**

Use production API requests and the browser to verify:

```text
GET /api/v2/threads?hours=24&limit=10 -> 200 with threads array
GET /api/v2/threads?hours=168&limit=24 -> 200 with threads array
Research "NATO summit Ankara", 24h -> real pin candidates or a component-specific gap, never a generic whole-lane timeout caused by signal ANN
Iran thread -> opens with its existing evidence/deep-history contract intact
```

- [ ] **Step 5: Write the delivery record**

Record commit SHAs, test counts, deployment identity, endpoint status/latency/counts, research-plan gap components, and any remaining limitations in `docs/state/2026-07-12-investigation-graph-slice-1-reliability.md`. The conclusion must grade the slice `pass`, `pass_with_caveats`, or `fail` against the acceptance criteria.

- [ ] **Step 6: Commit and push the verified slice**

```bash
git add docs/state/2026-07-12-investigation-graph-slice-1-reliability.md
git commit -m "docs(state): record investigation substrate reliability"
git push origin v3-intel-layer
```

## Self-Review

- Spec coverage: this slice covers only the reliability precondition for the approved Investigation Graph. Typed graph persistence, node resolution, temporal slices, Workbench UI, and shared `PublicationPackage` remain separate executable plans because each is an independently reviewable subsystem.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: all tasks preserve `fetch_threads -> list[dict]`; semantic failures add only the backward-compatible optional `component` field; `DatabaseBusyError` maps through the existing response helper.
