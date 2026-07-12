# Consolidation, Stability, and C7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate Atlas on `v3-intel-layer`, harden shared-database behavior, restore trustworthy verification, and deliver a read-only C7 voice-asymmetry pilot.

**Architecture:** Merge only clean, reviewed work into the canonical branch. Keep heavy-job coordination local and fail-safe; bound serving SQL before member aggregation; express uncertainty in API/UI contracts; keep C7 pure/read-only until validation. Repair dependency installations without committing generated dependency directories.

**Tech Stack:** Bash, FastAPI/asyncpg, PostgreSQL/Supabase, React/TypeScript/Vitest, pytest, GitHub CLI.

## Global Constraints

- `v3-intel-layer` is the canonical production/main branch.
- Do not touch deprecated `frontend/`.
- Preserve dirty external worktrees and user changes.
- Math/data first; LLM only for grounded brief prose.
- C7 does not write DB state, add cron, or alter lifecycle/ranking.
- Apply behavior changes test-first and verify red before green.

---

### Task 1: Canonical synchronization and GitHub hygiene

**Files:**
- Modify: `docs/specs/2026-07-09-resume-roadmap.md`
- Modify: `CLAUDE.md`
- Modify: `STATUS.md`
- Modify: `SESSION_LOG.md`

**Interfaces:**
- Consumes: clean branch commits `2f174041`, `e2d1fd82`, `0c0f123e` after review.
- Produces: one truthful canonical state and closed obsolete PRs.

- [ ] Fast-forward `v3-intel-layer` to `origin/v3-intel-layer` and verify a clean checkout.
- [ ] Close PR #144 with a comment that `v3-intel-layer` is the canonical/default production branch and legacy `main` is not an active merge target.
- [ ] Close PR #118 as superseded by the current Wave 4–11 RSS implementation, then delete only its obsolete remote head branch.
- [ ] Inventory unmerged branches and preserve every dirty worktree.
- [ ] Update canonical docs after Tasks 2–7 so shipped ticks, remaining work, and verification evidence match reality.

### Task 2: Safe P1.1 mutex and honest DB-busy errors

**Files:**
- Create: `backend/tests/test_heavy_job_lock.py`
- Modify: `scripts/heavy-job-lock.sh`
- Modify: `backend/tests/test_db_busy_degradation.py`
- Modify: `backend/app/main_v2.py`
- Integrate: the remaining runner/frontend changes from `e2d1fd82`

**Interfaces:**
- Consumes: `atlas_heavy_lock(job, mode, ttl_min, wait_max_min)`.
- Produces: lock metadata with owner TTL and explicit asyncpg-only 503 mapping.

- [ ] Write a failing pytest that creates a live holder with `ttl=240`, invokes a `ttl=45` contender, and asserts the holder directory remains and the contender fails.
- [ ] Run `.venv/bin/pytest tests/test_heavy_job_lock.py -q`; expect failure because current code evaluates the contender TTL and removes the live lock.
- [ ] Change the lock record to persist `ttl=<owner ttl>` and make `_atlas_heavy_try_reclaim` read it. Dead PID reclaims; live overdue PID logs and returns failure without deleting.
- [ ] Run the lock test and the dead-PID/normal-release cases; expect pass.
- [ ] Add a failing API test whose route raises built-in `TimeoutError` and assert it is not returned as `503 db_busy`.
- [ ] Run the focused DB-busy test; expect failure under the global handler from `e2d1fd82`.
- [ ] Remove global built-in/asyncio `TimeoutError` registration while retaining explicit asyncpg cancellation/connection handlers.
- [ ] Run `tests/test_db_busy_degradation.py` and relevant router tests; expect pass.
- [ ] Merge the corrected P1.1 changes into `v3-intel-layer` and sync the six runner files plus `heavy-job-lock.sh` to `~/AtlasLocalWorker` only after byte-identity verification.

### Task 3: Bound the dynamic-thread serving query

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_threads_emergent_augment_shape.py`
- Modify: `backend/tests/test_thread_intelligence.py`

**Interfaces:**
- Consumes: `hours`, `limit`, optional `country_code`.
- Produces: the unchanged living-thread response contract from a bounded candidate CTE.

- [ ] Add a failing shape test asserting both global and country SQL contain a materialized `candidate_topics` CTE with `LEAST(GREATEST($2 * 8, 80), 400)` and that member aggregation selects from candidates.
- [ ] Run the focused tests; expect failure because `_DYNAMIC_TOPICS_SELECT` starts from all active topics.
- [ ] Refactor the shared SQL builder so eligibility predicates live inside `candidate_topics`, ordered by `last_seen DESC, id DESC`, then run existing correlated metrics only on the candidate rows.
- [ ] Preserve final ordering by `recent_n_signals DESC, last_seen DESC` and requested `LIMIT $2`.
- [ ] Run thread unit/shape/router tests.
- [ ] With the configured read-only production connection, run `EXPLAIN (ANALYZE, BUFFERS)` for global and one country query without printing credentials; record execution time and scan shape in the session log.
- [ ] Smoke `/api/v2/threads?hours=24&limit=20` twice and confirm contract/counts remain valid.

### Task 4: Honest confidence and neutral movement encoding

**Files:**
- Create: `frontend-v2/src/lib/threadConfidence.ts`
- Create: `frontend-v2/src/lib/threadConfidence.test.ts`
- Modify: `backend/app/services/thread_intelligence.py`
- Modify: `backend/tests/test_thread_intelligence.py`
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`

**Interfaces:**
- Produces: `confidence_measured`, `confidence_source`, nullable `avg_confidence`, and `threadConfidencePresentation()`.

- [ ] Write failing backend tests that a dynamic topic without `noise_rate` returns null confidence/unmeasured, while a topic with noise returns measured `1-noise_rate`.
- [ ] Write failing Vitest cases that unmeasured confidence renders `unscored`, measured confidence renders a whole percent, and acceleration is neutral unless crisis-relevant.
- [ ] Run both focused test files and confirm red.
- [ ] Implement nullable confidence metadata in the serializer and pure frontend presentation helper.
- [ ] Render the confidence bar only when measured; render `unscored` otherwise. Use a neutral accelerating sparkline color for non-crisis stories.
- [ ] Re-run focused and full frontend tests.

### Task 5: Brief stale-while-revalidate and visible failure state

**Files:**
- Modify: `frontend-v2/src/lib/briefingPrefetch.ts`
- Modify: `frontend-v2/src/lib/briefingPrefetch.test.ts`
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx`
- Modify: `frontend-v2/src/pages/BriefNewspaper.css`

**Interfaces:**
- Produces: cache reads carrying `{briefing, insight, isStale}` and visible refresh state.

- [ ] Add failing cache tests for fresh, stale-but-usable, and expired/malformed payloads.
- [ ] Add a failing page source/behavior test asserting stale data is not cleared before revalidation and a no-cache failure renders a retry action.
- [ ] Run focused tests and confirm red.
- [ ] Implement stale-while-revalidate: paint cached data first, fetch live in background, retain stale data on failure, and expose a labeled cached/unavailable notice.
- [ ] Add an explicit error body with retry when no cache exists.
- [ ] Run focused tests, full Vitest, and production build.

### Task 6: Reproducible tooling

**Files:**
- Modify only if required by evidence: `backend/pyproject.toml`, `frontend-v2/package-lock.json`, `frontend-v2/eslint.config.js`

**Interfaces:**
- Produces: complete pytest collection/execution and terminating ESLint.

- [ ] Capture the backend import failure and confirm the installed `anthropic` distribution lacks `_client.py`.
- [ ] Reinstall backend dependencies from `pyproject.toml` in `.venv`; verify `python -c 'import anthropic'` succeeds.
- [ ] Capture the ESLint process blocked reading `node_modules/ajv/lib/dotjs/items.js` and verify direct file hashing also blocks.
- [ ] Run `npm ci` to reconstruct `node_modules`; verify `eslint --version` and `npm run lint` terminate.
- [ ] Remove the duplicate `orjson` dependency entry from `backend/pyproject.toml` as a mechanical manifest cleanup.
- [ ] Run full backend pytest, frontend lint, tests, and build.

### Task 7: C7 read-only voice-asymmetry pilot

**Files:**
- Create: `backend/scripts/voice_asymmetry_report.py`
- Create: `backend/tests/test_voice_asymmetry_report.py`
- Create: `docs/research/voice-asymmetry/2026-07-12-c7-pilot.json`
- Create: `docs/research/voice-asymmetry/2026-07-12-c7-pilot.md`

**Interfaces:**
- Consumes: aggregated per-topic signal volume, sources, languages, origins, subject country.
- Produces: pure `score_topic_voice_asymmetry()` plus JSON/Markdown report.

- [ ] Write failing tests for a concentrated outside-voice hit, balanced/self-voice non-hit, insufficient subject geography, insufficient attribution, volume/source floors, and explicit reason codes.
- [ ] Run `tests/test_voice_asymmetry_report.py`; expect import failure because the module does not exist.
- [ ] Implement dataclasses/pure scoring with the thresholds in the design spec and no DB writes.
- [ ] Add a bounded loader over active dynamic topics and member signals, reusing `voice_mix.primary_langs()`.
- [ ] Add JSON/Markdown renderers and CLI flags `--hours`, `--limit`, `--output-json`, `--output-md`.
- [ ] Run unit tests, then run the live read-only pilot against the configured database.
- [ ] Inspect top hits for obvious false positives; document attribution gaps and do not promote C7 to UI/ranking.

### Task 8: Delivery, cleanup, and production verification

**Files:**
- Modify: `CLAUDE.md`
- Modify: `STATUS.md`
- Modify: `SESSION_LOG.md`
- Modify: `docs/specs/2026-07-09-resume-roadmap.md`

**Interfaces:**
- Produces: pushed canonical branch, matching documentation, clean GitHub state, and verified production.

- [ ] Reconcile roadmap ticks: P0 complete except real-analyst validation, P1.1 shipped, X.1–X.4 actual state, C7 pilot delivered/read-only.
- [ ] Add a concise current-state block to STATUS/SESSION_LOG and point old chronological material to CLAUDE/roadmap instead of rewriting history.
- [ ] Run `git diff --check` and review every changed file.
- [ ] Run full backend pytest; frontend lint, tests, and build; focused shell/P1/C7 tests.
- [ ] Commit coherent units, push `v3-intel-layer`, and wait for Vercel success.
- [ ] Deploy Fly only if backend runtime files changed, then smoke health, signals, threads, briefing, universe, delight, and archive search.
- [ ] Delete only clean branches whose commits are now ancestors of `v3-intel-layer` and obsolete remote branches explicitly approved here; preserve dirty/host-owned worktrees.
- [ ] Leave GitHub issue comments with commit/deploy evidence for affected open issues rather than silently closing umbrella work.

