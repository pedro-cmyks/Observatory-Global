# Thread-First Focus Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Atlas focus surfaces thread-first by patching `/api/v2/threads` quality metadata, preventing raw person/entity fields from reaching UI, and preparing country/entity focus to show active Narrative Threads.

**Architecture:** Keep the existing UI layout and focus context while improving the data contract underneath it. `/api/v2/threads` remains the canonical thread contract; `theme` focus remains a compatibility bridge until `thread` focus is introduced. Entity and country focus should become lenses over active threads rather than isolated summary panels.

**Tech Stack:** FastAPI, asyncpg SQL, pytest, React + Vite + TypeScript, existing `FocusContext`, `FocusDataContext`, `NarrativeThreads`, and `FocusSummaryPanel`.

---

## Files

- Modify: `backend/app/services/thread_intelligence.py`  
  Add thread quality metadata: `lex_pct`, method mix, raw entity quality flags,
  source quality flags, and geography quality flags. Hold raw `top_entities`
  from being treated as people.
- Modify: `backend/tests/test_thread_intelligence.py`  
  Lock the quality metadata contract and entity-safety behavior.
- Modify: `backend/tests/test_threads_router.py`  
  Confirm router responses preserve additive fields and cache shape.
- Modify: `frontend-v2/src/contexts/FocusContext.tsx`  
  Later task only: introduce `thread` and `entity` as explicit focus types while
  preserving `theme` and `person` compatibility.
- Modify: `frontend-v2/src/components/FocusSummaryPanel.tsx`  
  Later task only: rename generic sections toward thread-aware language and
  avoid implying that entity mentions are validated people.
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`  
  Later task only, blocked until audit gates pass: consume `/api/v2/threads`.
- Add: `docs/research/thread-quality/YYYY-MM-DD-thread-quality-snapshot.md`  
  Save repeatable audit snapshots.

---

## Task 1: Patch Thread Contract Quality Metadata

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`

- [ ] **Step 1: Add failing test for quality metadata**

Add a test row that includes method counts, lex counts, unresolved geography,
aggregator source, and raw entities. Assert the assembled thread exposes:

```python
assert thread["quality"]["lex_pct"] == 0.25
assert thread["quality"]["method_mix"]["lex"] == 5
assert "raw_entity_field_untyped" in thread["quality"]["entity_flags"]
assert "unresolved_country_code" in thread["quality"]["geo_flags"]
assert "aggregator_dominant" in thread["quality"]["source_flags"]
assert thread["top_entities"] == ["el nino", "pacific ocean"]
assert thread["top_people"] == []
```

Run:

```bash
cd backend && poetry run pytest tests/test_thread_intelligence.py -k quality -v
```

Expected: fail because `quality` and `top_people` do not exist yet.

- [x] **Step 2: Extend SQL with evidence-derived lex/theme counts**

In `THREADS_SQL`, add counts from `signal_topic_assignments.evidence`.
Current v2 writes rows with `method='lexicon'`, so lexical support cannot be
derived from the method column. The correct source is JSON evidence:

```sql
COUNT(*) FILTER (
    WHERE COALESCE((evidence->>'lex_count')::int, 0) > 0
)::int AS lex_count,
COUNT(*) FILTER (
    WHERE COALESCE((evidence->>'lex_count')::int, 0) = 0
      AND COALESCE((evidence->>'theme_hits')::int, 0) > 0
)::int AS theme_count
```

Expose both through `topic_agg` and final `SELECT`.

- [ ] **Step 3: Add source/geography/entity flag helpers**

Add small pure helpers:

```python
AGGREGATOR_DOMAINS = {"zazoom.it", "yahoo.com", "rediff.com", "tvguide.co.uk"}

def _quality_flags_for_sources(top_sources: list[str], source_count: int) -> list[str]:
    if not top_sources:
        return ["no_sources"]
    flags: list[str] = []
    if top_sources[0].lower() in AGGREGATOR_DOMAINS:
        flags.append("aggregator_dominant")
    if source_count <= 2:
        flags.append("thin_source_diversity")
    return flags

def _quality_flags_for_geo(country_codes: list[str], country_names: list[str]) -> list[str]:
    unresolved = [code for code, name in zip(country_codes, country_names) if code == name]
    return ["unresolved_country_code"] if unresolved else []

def _quality_flags_for_entities(raw_entities: list[str]) -> list[str]:
    return ["raw_entity_field_untyped"] if raw_entities else []
```

- [ ] **Step 4: Assemble additive `quality` object**

In `assemble_thread`, compute:

```python
lex_count = int(_record_get(row, "lex_count") or 0)
theme_count = int(_record_get(row, "theme_count") or 0)
lex_pct = round(lex_count / signal_count, 4) if signal_count else 0.0
quality = {
    "lex_pct": lex_pct,
    "method_mix": {"lex": lex_count, "theme": theme_count},
    "source_flags": _quality_flags_for_sources(top_sources, source_count),
    "geo_flags": _quality_flags_for_geo(country_codes, country_names),
    "entity_flags": _quality_flags_for_entities(top_entities),
}
```

Return both:

```python
"top_entities": top_entities,
"top_people": [],
"quality": quality,
```

`top_people` must stay empty until entity typing exists.

- [ ] **Step 5: Run focused tests**

Run:

```bash
cd backend && poetry run pytest tests/test_thread_intelligence.py tests/test_threads_router.py -v
```

Expected: pass.

---

## Task 2: Add Repeatable Thread Quality Audit Script

**Files:**
- Add: `backend/scripts/thread_quality_report.py`
- Add: `backend/tests/test_thread_quality_report.py`

- [ ] **Step 1: Write failing test for report formatting**

Create a unit test around pure formatting functions. Expected output fields:

```python
["topic_slug", "signal_count", "lex_pct", "grade", "source_flags", "geo_flags", "entity_flags"]
```

Run:

```bash
cd backend && poetry run pytest tests/test_thread_quality_report.py -v
```

Expected: fail because the script does not exist.

- [ ] **Step 2: Implement script with read-only DB access**

Script behavior:

```bash
python backend/scripts/thread_quality_report.py --hours 24 --limit 15 --out docs/research/thread-quality/2026-05-24-thread-quality-snapshot.md
```

It should:

- query `/api/v2/threads` or the same SQL helper;
- include top thread metrics;
- include quality flags;
- include 8 evidence headlines per thread;
- write Markdown only when `--out` is provided;
- print a compact table to stdout.

- [ ] **Step 3: Run script against production only after local tests pass**

Use Fly `DATABASE_URL` without printing secrets. Save one snapshot under:

```text
docs/research/thread-quality/2026-05-24-thread-quality-snapshot.md
```

Expected: snapshot includes the known weak topics:

- `gender-violence-rights`;
- `transport-corridor-disruption`.

---

## Task 3: Update Focus Model Types Without UI Swap

**Files:**
- Modify: `frontend-v2/src/contexts/FocusContext.tsx`
- Modify: `frontend-v2/src/components/FocusIndicator.tsx`
- Modify: focused frontend tests if present.

- [ ] **Step 1: Add failing TypeScript test or build expectation**

Change `FocusType` expectation to include:

```ts
export type FocusType = 'thread' | 'theme' | 'entity' | 'person' | 'country' | 'source' | null
```

Run:

```bash
cd frontend-v2 && npm run build
```

Expected before implementation: fail if any exhaustive labels are missing.

- [ ] **Step 2: Add thread/entity compatibility fields**

Extend `GlobalFilter` conservatively:

```ts
thread: string | null
entity: string | null
```

Keep `theme` and `person` as compatibility fields. `setPerson` should still
work, but internally it should set both `person` and `entity` once entity focus
is ready.

- [ ] **Step 3: Update labels**

In `FocusIndicator.tsx`, label:

```ts
thread: 'Thread',
entity: 'Entity',
person: 'Person'
```

Do not remove `person` yet.

- [ ] **Step 4: Build frontend**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: pass.

---

## Task 4: Thread-Aware Focus Summary Copy

**Files:**
- Modify: `frontend-v2/src/components/FocusSummaryPanel.tsx`
- Modify: `frontend-v2/src/components/FocusSummaryPanel.css` only if layout needs stable dimensions.

- [ ] **Step 1: Rename generic sections without changing endpoints**

Keep current `/api/v2/focus` data, but update labels:

- `Related Topics` -> `Related Threads / Topics`
- `Top Sources` -> `Sources Driving This Focus`
- `Recent Coverage` -> `Evidence`

This is copy-only and should not claim typed entity quality yet.

- [ ] **Step 2: Add entity quality note when focus type is person**

If `focus.type === 'person'`, show a small method note:

```tsx
<p className="focus-method-note">
  Entity mentions are untyped until the next Atlas entity pass; evidence below is mention-based.
</p>
```

Use CSS that does not resize the panel unpredictably.

- [ ] **Step 3: Build frontend**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: pass.

---

## Task 5: Re-Run Quality Audit And Decide M3b

**Files:**
- Modify: `docs/research/2026-05-24-thread-quality-audit.md`
- Modify: `docs/STATUS.md`

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd backend && poetry run pytest tests/test_thread_intelligence.py tests/test_threads_router.py tests/test_briefing_performance_shape.py -v
```

Expected: pass.

- [ ] **Step 2: Run frontend build if any frontend files changed**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: pass.

- [ ] **Step 3: Generate fresh audit snapshot**

Run the new report script and compare against the gates in:

```text
docs/research/2026-05-24-thread-quality-audit.md
```

- [ ] **Step 4: Decide M3b**

If top-10 threads fail the audit gates, keep `NarrativeThreads.tsx` on
`/api/v2/narratives`. If gates pass, create a new plan for the frontend swap.

---

## Self-Review

- Spec coverage: the plan implements thread-first focus by first fixing the
  thread contract, then adding repeatable audit, then preparing focus types and
  copy without forcing a UI swap.
- Placeholder scan: no `TBD`/`TODO` placeholders remain.
- Type consistency: `thread`, `entity`, `person`, `country`, and `theme` are
  treated as compatibility states, not mutually exclusive product concepts.
