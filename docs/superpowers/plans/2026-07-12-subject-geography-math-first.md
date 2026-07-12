# Subject Geography Math-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a complete-universe, deterministic, read-only subject-geography report for #238 with transparent candidates, abstention, structural evaluation, and ablations.

**Architecture:** A focused Python module separates pure signal extraction/scoring from database pagination and report rendering. It reuses Atlas's existing multilingual headline patterns, persisted e5 embeddings, NER JSON, topic membership, and archive story units; all database access is read-only and cursor-exhaustive. Evaluation uses deterministic fixtures and invariants rather than LLM labels.

**Tech Stack:** Python 3.12, pytest, asyncpg/PostgreSQL/Supabase, NumPy-free pure scoring, persisted pgvector/e5 metrics, JSON/Markdown artifacts.

**Execution status (2026-07-12): COMPLETE.** Tasks 1-4 were implemented in
commits `903e6d40`, `e7a3e89d`, `f48feeb4`, and `2ec206b4`. The live run
exhausted all 1,442 active/candidate topics in 29 cursor batches with no failures.
GitHub #238 contains the measured receipt; map follow-ups are #255 and #256.

## Global Constraints

- No semantic top-N/topic ceiling or silent omission.
- Bounded cursor batches are operational controls; a full run must reach cursor exhaustion.
- No LLM calls for inference, classification, evaluation, adjudication, or gold generation.
- Coverage geography and outlet origin remain separate from subject geography.
- Read-only only: no migrations, persistence, lifecycle, ranking, API, UI, or cron changes.
- Every candidate exposes components, provenance, uncertainty, and reason codes.
- Missing evidence degrades or abstains; it never copies coverage geography into subject geography.
- Do not touch deprecated `frontend/`.

---

### Task 1: Pure subject-country evidence and scoring

**Files:**
- Create: `backend/scripts/subject_geography_report.py`
- Create: `backend/tests/test_subject_geography_report.py`

**Interfaces:**
- Consumes: `SignalSubjectInput`, existing `_COUNTRY_PATTERNS` and `_NATIVE_COUNTRY_PATTERNS` from `app.services.ingest_rss`.
- Produces: `extract_headline_country_evidence()`, `score_subject_candidates()`, and `SubjectCandidate` dictionaries used by every later task.

- [ ] **Step 1: Write failing extraction/scoring tests**

```python
def test_multilingual_headlines_build_a_country_distribution():
    signals = [
        _signal(1, "Venezuela earthquake death toll rises", "en"),
        _signal(2, "Sube el balance del terremoto en Venezuela", "es"),
        _signal(3, "Землетрясение в Венесуэле", "ru"),
    ]
    result = score_subject_candidates(signals)
    assert result["primary_country"] == "VE"
    assert result["candidate_distribution"]["VE"] == 1.0
    assert result["reason_codes"] == ["headline_geo_consensus"]

def test_coverage_country_never_creates_subject_candidate():
    result = score_subject_candidates([
        _signal(1, "Central bank changes interest rate", "en", coverage_country="US")
    ])
    assert result["primary_country"] is None
    assert result["candidate_distribution"] == {}
    assert "insufficient_subject_evidence" in result["reason_codes"]

def test_ambiguous_multi_country_headlines_abstain():
    result = score_subject_candidates([
        _signal(1, "Iran and Israel resume negotiations", "en"),
        _signal(2, "Israel and Iran trade accusations", "en"),
    ])
    assert result["primary_country"] is None
    assert result["entropy"] > 0
    assert "ambiguous_subject_geo" in result["reason_codes"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_subject_geography_report.py -q`

Expected: collection fails because `scripts.subject_geography_report` does not exist.

- [ ] **Step 3: Implement pure dataclasses, extraction, entropy, margin, scoring, and abstention**

Required public interfaces are `SignalSubjectInput(signal_id, headline,
language, coverage_country, source_family, published_at, ner_places,
embedding_similarity)`,
`extract_headline_country_evidence(headline) -> list[dict[str, object]]`, and
`score_subject_candidates(signals, disabled_components=frozenset()) ->
dict[str, object]`.

The extractor must return every matched country, not the first match. Exact Latin/native pattern evidence is deduplicated per signal. Scoring must calculate support, normalized distribution, Shannon entropy, top-two margin, source-family breadth, temporal stability, and explicit abstention.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_subject_geography_report.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/scripts/subject_geography_report.py backend/tests/test_subject_geography_report.py
git commit -m "feat(research): add deterministic subject geography scorer"
```

### Task 2: Cursor-exhaustive complete-universe loader

**Files:**
- Modify: `backend/scripts/subject_geography_report.py`
- Modify: `backend/tests/test_subject_geography_report.py`

**Interfaces:**
- Consumes: `score_subject_candidates()`.
- Produces: `iter_topic_batches()`, `load_topic_signals()`, `run_complete_universe()`, and completion metadata.

- [ ] **Step 1: Write failing cursor and completion tests**

```python
async def test_cursor_batches_reach_exhaustion_without_topic_ceiling():
    db = FakeDB(topic_pages=[[{"id": 1}, {"id": 2}], [{"id": 3}], []])
    rows, meta = await run_complete_universe(db, batch_size=2)
    assert [r["dynamic_topic_id"] for r in rows] == [1, 2, 3]
    assert meta["complete_universe"] is True
    assert meta["rows_discovered"] == meta["rows_processed"] == 3
    assert meta["last_cursor"] == 3

async def test_failed_batch_is_resumable_and_never_claims_complete():
    db = FakeDB(topic_pages=[[{"id": 1}], RuntimeError("timeout")])
    rows, meta = await run_complete_universe(db, batch_size=1, max_retries=0)
    assert meta["complete_universe"] is False
    assert meta["last_cursor"] == 1
    assert meta["failures"][0]["reason"] == "timeout"
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: failures because the loader interfaces are absent.

- [ ] **Step 3: Implement read-only SQL and cursor exhaustion**

The topic query must use `WHERE id > $cursor ORDER BY id LIMIT $batch_size` with lifecycle states provided explicitly. Member loading must union latest emergent-cluster samples and `topic_members` unified-v2 evidence, dedupe by signal ID, and fetch headline/language/coverage/source/NER plus centroid similarity when the persisted embedding exists. No SQL may contain a total-topic limit.

Required completion shape:

```python
{
    "complete_universe": bool,
    "rows_discovered": int,
    "rows_processed": int,
    "rows_emitted": int,
    "last_cursor": int | None,
    "batches": int,
    "retries": int,
    "failures": list[dict],
    "by_lifecycle_state": dict[str, int],
    "by_quality_lane": dict[str, int],
}
```

- [ ] **Step 4: Verify SQL shape and loader behavior**

Run: `cd backend && .venv/bin/python -m pytest tests/test_subject_geography_report.py -q`

Expected: cursor, degradation, SQL-shape, and Task 1 tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/scripts/subject_geography_report.py backend/tests/test_subject_geography_report.py
git commit -m "feat(research): exhaust full topic universe for subject geo"
```

### Task 3: Structural evaluation, proxy comparison, and ablations

**Files:**
- Modify: `backend/scripts/subject_geography_report.py`
- Modify: `backend/tests/test_subject_geography_report.py`

**Interfaces:**
- Consumes: per-topic candidate ledgers from Task 2.
- Produces: `evaluate_known_fixtures()`, `evaluate_invariants()`, `run_ablations()`, and per-topic disagreement ledgers.

- [ ] **Step 1: Write failing invariant and ablation tests**

```python
def test_leave_one_source_family_out_does_not_flip_stable_subject():
    result = evaluate_invariants(_stable_venezuela_topic())
    assert result["leave_one_source_family_out"]["stable"] is True

def test_archive_and_coverage_are_labeled_proxies_not_gold():
    row = compare_proxies(subject={"VE": 0.9}, coverage=["US", "BR"], archive=["VE"])
    assert row["coverage_relation"] == "subject_missing_from_coverage"
    assert row["archive_relation"] == "agrees_with_candidate"
    assert row["truth_status"] == "not_gold"

def test_ablation_reports_candidate_and_abstention_delta():
    report = run_ablations([_stable_venezuela_topic()])
    assert "headline_geo_support" in report["components"]
    assert "primary_changed" in report["components"]["headline_geo_support"]
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: failures because the evaluation interfaces are absent.

- [ ] **Step 3: Implement deterministic evaluation**

Evaluation must include known fixtures, cross-language consistency, adjacent-snapshot stability, leave-one-source-family-out, component ablations, and comparison against coverage/`archive_story_units.top_cc`. When no fixture resolves truth, use `disagreement`, never `error` or `accuracy`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_subject_geography_report.py -q`

Expected: all scorer, loader, invariant, and ablation tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add backend/scripts/subject_geography_report.py backend/tests/test_subject_geography_report.py
git commit -m "feat(research): evaluate subject geo with structural invariants"
```

### Task 4: CLI, artifacts, live complete-universe run, and issue evidence

**Files:**
- Modify: `backend/scripts/subject_geography_report.py`
- Modify: `backend/tests/test_subject_geography_report.py`
- Create: `docs/research/subject-geography/2026-07-12-complete-universe.json`
- Create: `docs/research/subject-geography/2026-07-12-complete-universe.md`
- Create: `docs/research/subject-geography/2026-07-12-ablation.json`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: resumable CLI and canonical evidence artifacts for #238 Stage 1.

- [ ] **Step 1: Write failing renderer/CLI contract tests**

```python
def test_report_declares_read_only_no_llm_and_completion():
    report = build_report([], completion={"complete_universe": True})
    assert report["read_only"] is True
    assert report["no_llm_classification"] is True
    assert report["complete_universe"] is True

def test_markdown_never_calls_proxy_error_without_fixture():
    md = render_markdown(_proxy_disagreement_report())
    assert "proxy disagreement" in md.lower()
    assert "ground truth error" not in md.lower()
```

- [ ] **Step 2: Run focused tests and verify RED**

- [ ] **Step 3: Implement CLI and renderers**

Required flags:

```text
--states active,candidate
--batch-size 50
--hours 336
--resume-cursor INT
--output-json PATH
--output-md PATH
--output-ablation PATH
```

`--batch-size` controls database pressure only. There is no `--limit` flag.

- [ ] **Step 4: Run unit and affected regression tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_subject_geography_report.py tests/test_geo_tagging_native.py tests/test_thread_intelligence.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run the complete universe against the configured read-only database**

Run from `backend/` with `DATABASE_URL` loaded from `/Users/pedro/AtlasLocalWorker/.env`:

```bash
.venv/bin/python -m scripts.subject_geography_report \
  --states active,candidate \
  --batch-size 50 \
  --hours 336 \
  --output-json ../docs/research/subject-geography/2026-07-12-complete-universe.json \
  --output-md ../docs/research/subject-geography/2026-07-12-complete-universe.md \
  --output-ablation ../docs/research/subject-geography/2026-07-12-ablation.json
```

Expected: exit 0, `complete_universe=true`, discovered=processed, no DB writes.

- [ ] **Step 6: Inspect obvious cases and verify artifact integrity**

Run:

```bash
jq '{complete_universe, rows_discovered, rows_processed, by_lifecycle_state, summary}' \
  docs/research/subject-geography/2026-07-12-complete-universe.json
git diff --check
```

- [ ] **Step 7: Commit artifacts and update GitHub #238 with measured results**

```bash
git add backend/scripts/subject_geography_report.py backend/tests/test_subject_geography_report.py docs/research/subject-geography
git commit -m "docs(research): publish complete-universe subject geo report"
```

### Task 5: Delivery verification and adjacent issue separation

**Files:**
- Modify: `STATUS.md`
- Modify: `SESSION_LOG.md`

**Interfaces:**
- Produces: canonical delivery state plus separate GitHub tracking for event hover/enrichment and movement-binding freshness.

- [ ] **Step 1: Create one scoped GitHub issue for structured event receipts**

The issue must record current truth: country hover exists; hazard/conflict/anomaly marker hover does not; hazards currently open USGS/GDACS; use official detail APIs and cached backend receipts, not HTML scraping; retain authoritative external links.

- [ ] **Step 2: Create or reopen a scoped operational issue for binding freshness**

Record evidence: disaster ingestion fresh through 2026-07-12, but `movement-v1`/`disaster-v1` bindings are stale because the 2026-07-12 scoped runner hit `TimeoutError`/`QueryCanceledError`. Keep this separate from #238.

- [ ] **Step 3: Update status docs with Stage 1 result and remaining #238 stages**

- [ ] **Step 4: Run fresh final verification**

```bash
cd backend
.venv/bin/python -m pytest tests/test_subject_geography_report.py tests/test_geo_tagging_native.py tests/test_thread_intelligence.py -q
cd ../
git diff --check
git status --short --branch
```

- [ ] **Step 5: Commit, push canonical `v3-intel-layer`, and verify remote parity**

```bash
git add STATUS.md SESSION_LOG.md
git commit -m "docs(status): record subject geography Stage 1"
git push origin v3-intel-layer
git rev-list --left-right --count origin/v3-intel-layer...v3-intel-layer
```

Expected parity: `0 0`.
