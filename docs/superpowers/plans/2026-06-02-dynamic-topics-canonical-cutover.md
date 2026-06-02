# Dynamic Topics Canonical Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the user-facing narrative topic source from raw latest `emergent_clusters` toward quality-gated `dynamic_topics`, while preserving fallbacks and product contracts.

**Architecture:** Backend-first cutover. Add dynamic-topic thread assembly and briefing rows from `dynamic_topics` joined to `dynamic_topic_members`/`emergent_clusters`; keep `emergent_clusters` and static `atlas_topics` as fallbacks. Do not change frontend shape unless backend contract smokes show a field gap.

**Tech Stack:** FastAPI, asyncpg SQL, existing `/api/v2/threads` and `/api/v2/briefing` contracts, pytest shape/unit tests, local Supabase DB via `DATABASE_URL`.

---

## File Structure

- Modify `backend/app/services/thread_intelligence.py`: add `dynamic-topic-` thread prefix, dynamic topic list/detail fetchers, and merge dynamic topics before raw emergent clusters.
- Modify `backend/app/routers/briefing.py`: prefer active `dynamic_topics` for `top_atlas_topics`; fallback to latest `emergent_clusters`; fallback to static `signal_topic_assignments`.
- Modify `backend/tests/test_threads_emergent_augment_shape.py`: add shape guardrails for dynamic topic thread source and fallback ordering.
- Add or modify `backend/tests/test_briefing_performance_shape.py`: freeze briefing preference order and dynamic topic response fields.
- Update `docs/research/topic-quality/2026-06-02-dynamic-topics-shadow-result.md`, `STATUS.md`, `SESSION_LOG.md`, and Obsidian MOCs after implementation.

---

### Task 1: Freeze Dynamic Topic Thread Contract

**Files:**
- Modify: `backend/tests/test_threads_emergent_augment_shape.py`
- Modify: `backend/app/services/thread_intelligence.py`

- [x] **Step 1: Write failing shape tests**

Add tests requiring:

```python
def test_dynamic_topic_thread_prefix_constant():
    source = _src()
    assert 'DYNAMIC_TOPIC_THREAD_PREFIX = "dynamic-topic-"' in source


def test_dynamic_topic_fetcher_reads_active_dynamic_topics():
    source = _src()
    assert "async def _fetch_dynamic_threads_with_conn(" in source
    block = source[source.index("async def _fetch_dynamic_threads_with_conn("):source.index("async def _fetch_emergent_threads_with_conn(")]
    assert "to_regclass('dynamic_topics')" in block
    assert "dynamic_topic_members" in block
    assert "dt.state = 'active'" in block
    assert "dt.noise_rate" in block


def test_fetch_threads_prefers_dynamic_then_emergent_then_atlas():
    source = _src()
    block = source[source.index("async def fetch_threads("):source.index("async def fetch_thread_detail(")]
    assert "_fetch_dynamic_threads_with_conn" in block
    assert "_fetch_emergent_threads_with_conn" in block
    assert "dynamic + emergent + atlas" in block
```

- [x] **Step 2: Run test to verify RED**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_threads_emergent_augment_shape.py -q
```

Expected: fails because dynamic prefix/fetcher do not exist.

- [x] **Step 3: Implement minimal dynamic topic list/detail assembly**

In `backend/app/services/thread_intelligence.py`, add:

```python
DYNAMIC_TOPIC_THREAD_PREFIX = "dynamic-topic-"
```

Add `_fetch_dynamic_threads_with_conn(conn, hours, limit)` that:

- guards `to_regclass('dynamic_topics')` and `to_regclass('dynamic_topic_members')`,
- selects active dynamic topics whose `last_seen` is inside the requested window,
- joins member rows to latest/sample `emergent_clusters`,
- returns thread dictionaries with the same keys as `assemble_emergent_thread`,
- sets `source = "dynamic_topics"`,
- uses `thread_id = f"dynamic-topic-{dt.id}"`,
- uses `anchor_topics = [dt.identity_key]`,
- uses `signal_count = dt.agg_n_signals`,
- uses `avg_confidence = 1 - noise_rate` when present.

Add `_fetch_dynamic_thread_detail(conn, dynamic_topic_id)` with the same shape and sample evidence from member cluster sample IDs.

- [x] **Step 4: Update `fetch_threads` merge order**

When unfiltered:

```python
dynamic = await _fetch_dynamic_threads_with_conn(...)
emergent = [] if dynamic else await _fetch_emergent_threads_with_conn(...)
combined = dynamic + emergent + atlas
```

Sort by `signal_count`, trim to limit. Filtered atlas calls keep atlas-only behavior.

- [x] **Step 5: Update detail dispatch**

In `fetch_thread_detail`, dispatch `dynamic-topic-<id>` to `_fetch_dynamic_thread_detail`.

- [x] **Step 6: Run focused tests**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_threads_emergent_augment_shape.py backend/tests/test_thread_intelligence.py backend/tests/test_threads_router.py -q
```

Expected: pass.

---

### Task 2: Prefer Dynamic Topics in Briefing Watchlist

**Files:**
- Modify: `backend/tests/test_briefing_performance_shape.py`
- Modify: `backend/app/routers/briefing.py`

- [x] **Step 1: Write failing briefing shape test**

Add a source-shape test requiring:

```python
def test_briefing_prefers_dynamic_topics_before_emergent_clusters():
    source = BRIEFING.read_text(encoding="utf-8")
    dynamic_pos = source.index("FROM dynamic_topics")
    emergent_pos = source.index("FROM emergent_clusters")
    assert dynamic_pos < emergent_pos
    assert "'dynamic_topics'" in source
    assert "dt.state = 'active'" in source
    assert "noise_rate" in source
```

- [x] **Step 2: Run test to verify RED**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_briefing_performance_shape.py -q
```

Expected: fails because briefing does not query `dynamic_topics`.

- [x] **Step 3: Implement dynamic `top_atlas_topics` query**

Before the current `emergent_clusters` branch, add `has_dynamic_topics` guards for `dynamic_topics` and `dynamic_topic_members`. Query active topics:

```sql
SELECT
  ('dynamic-topic-' || dt.id::text) AS slug,
  dt.label,
  NULL::text AS parent_domain,
  dt.agg_n_signals::bigint AS signal_count,
  CASE WHEN dt.noise_rate IS NULL THEN NULL ELSE (1 - dt.noise_rate)::float END AS avg_confidence,
  dt.agg_n_signals::bigint AS high_confidence_count,
  dt.agg_n_signals::bigint AS gated_signal_count,
  dt.agg_n_signals::bigint AS gate_scored_count,
  'dynamic_topics' AS source_table,
  'dynamic-topics-v1' AS model_version,
  NULL::text AS description,
  NULL::int AS velocity,
  ARRAY[]::text[] AS top_country_codes,
  dt.mean_cohesion AS cohesion,
  NULL::float AS vendor_agreement,
  dt.noise_rate
FROM dynamic_topics dt
WHERE dt.state = 'active'
  AND dt.last_seen > NOW() - ($1::int * INTERVAL '1 hour')
ORDER BY dt.agg_n_signals DESC
LIMIT 10
```

Keep existing emergent and static fallbacks unchanged.

- [x] **Step 4: Preserve response shape**

Add optional `noise_rate` to the serialized `top_atlas_topics` rows.

- [x] **Step 5: Run focused tests**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_briefing_performance_shape.py backend/tests/test_threads_emergent_augment_shape.py -q
```

Expected: pass.

---

### Task 3: Live Contract Smokes

**Files:**
- No code unless smoke fails.
- Update docs after results.

- [x] **Step 1: Run backend local/live dry smokes**

With `DATABASE_URL` loaded:

```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import asyncio, os, asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch("SELECT id, label, state, agg_n_signals, noise_rate FROM dynamic_topics ORDER BY agg_n_signals DESC LIMIT 5")
        print([dict(r) for r in rows])
    finally:
        await conn.close()
asyncio.run(main())
PY
```

Expected: active dynamic topics exist and have non-null state.

- [x] **Step 2: Run API contract smokes against local service if already running**

If backend server is running:

```bash
curl -s 'http://127.0.0.1:8000/api/v2/threads?hours=24&limit=5' | jq '.threads[0] | {thread_id,label,source,signal_count}'
curl -s 'http://127.0.0.1:8000/api/v2/briefing?hours=24' | jq '{top_atlas_topics_source, first: .top_atlas_topics[0] | {slug,label,source_table,signal_count,noise_rate}}'
```

Expected: `source` / `source_table` is `dynamic_topics` when active rows exist; otherwise fallback is explicit.

- [x] **Step 3: Run dynamic-topic Watchlist click smoke**

Also validate:

```bash
curl -s 'http://127.0.0.1:8017/api/v2/theme/dynamic-topic-10?hours=24' \
  | jq '{theme,label,source,total,signalSample,warnings}'
```

Result: `source=dynamic_topics`, `total=287`, `signalSample=141`, warnings
include `dynamic_topic_member_preview_sample`.

- [x] **Step 4: Run targeted tests**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest \
  backend/tests/test_threads_emergent_augment_shape.py \
  backend/tests/test_threads_router.py \
  backend/tests/test_thread_intelligence.py \
  backend/tests/test_briefing_performance_shape.py \
  backend/tests/test_project_dynamic_topics.py \
  -q
```

Expected: pass.

---

### Task 4: Documentation and Commit

**Files:**
- Modify: `STATUS.md`
- Modify: `SESSION_LOG.md`
- Modify: `docs/maps/Narrative Intelligence.md`
- Modify: `docs/maps/Data Operations.md` only if cron/deploy state changed
- Modify: `docs/research/topic-quality/2026-06-02-dynamic-topics-shadow-result.md`
- Modify: `docs/state/PROJECT_INVENTORY.md` after regeneration

- [x] **Step 1: Update docs with cutover result**

Record:

- backend contracts now prefer `dynamic_topics`,
- product read path still has fallbacks,
- active row counts from smoke,
- exact test commands and results,
- whether frontend changed.

- [x] **Step 2: Regenerate inventory**

```bash
python3 scripts/project_inventory.py
```

- [x] **Step 3: Final verification**

```bash
git diff --check
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_threads_emergent_augment_shape.py backend/tests/test_briefing_performance_shape.py backend/tests/test_project_dynamic_topics.py -q
```

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md CLAUDE.md STATUS.md SESSION_LOG.md \
  backend/app/services/thread_intelligence.py \
  backend/app/routers/briefing.py backend/app/routers/themes.py \
  backend/tests/test_threads_emergent_augment_shape.py \
  backend/tests/test_briefing_performance_shape.py \
  backend/tests/test_theme_insight_shape.py \
  docs/maps/Narrative\ Intelligence.md \
  docs/research/topic-quality/2026-06-02-dynamic-topics-shadow-result.md \
  docs/state/PROJECT_INVENTORY.md \
  docs/superpowers/plans/2026-06-02-dynamic-topics-canonical-cutover.md
git commit -m "feat(phase6): read product threads from dynamic topics"
```

---

## Self-Review

- Spec coverage: plan covers `/api/v2/threads`, `/api/v2/threads/{id}`, `/api/v2/briefing.top_atlas_topics`, fallback behavior, tests, live smokes, docs.
- Placeholder scan: no TODO/TBD steps; fallback behavior and SQL are explicit.
- Type consistency: dynamic thread prefix is `dynamic-topic-`; source labels are `dynamic_topics`; model version is `dynamic-topics-v1`.
