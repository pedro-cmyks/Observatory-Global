# Consolidation, Serving Stability, and C7 Design

**Date:** 2026-07-12  
**Status:** Pedro-approved execution design  
**Canonical branch:** `v3-intel-layer` (this is Atlas main; legacy `main` is not the production line)

## Goal

Close the current consolidation debt, make the shared Supabase serving path fail honestly and predictably, restore reproducible local verification, and deliver the first read-only C7 voice-asymmetry detector without adding persistent tables or cron.

## Sequence

1. Consolidate the useful clean branches into `v3-intel-layer` and close obsolete GitHub PRs.
2. Harden P1.1 before merging it: a live lock owner may never be evicted by a waiting job, and generic application timeouts may never be mislabeled as database contention.
3. Bound the cold `/api/v2/threads` query before correlated member aggregation.
4. Remove default-confidence theater and make Brief resilient with stale-while-revalidate plus a visible unavailable state.
5. Rebuild corrupted dependency installations, run the complete verification surface, and update canonical docs/issues.
6. Produce C7 as a read-only detector and review artifact; persistence, cron, ranking promotion, and public UI remain separate decisions after measured validation.

## P1.1 concurrency contract

- One heavy local job owns `/tmp/atlas-heavy-job.lock` at a time.
- The lock record includes PID, job, start time, and owner TTL.
- A dead PID can be reclaimed immediately.
- A live PID is never deleted by a contender. If it exceeds its owner TTL, the contender logs `OVERDUE_ACTIVE`, refuses to acquire, and leaves recovery to an operator or the owning process.
- Waiting and skip callers use the owner's TTL, never their own TTL, when evaluating the existing lock.
- The API maps explicit asyncpg cancellation/connection failures to `503 {reason: "db_busy"}`.
- Built-in `TimeoutError` remains a generic server failure unless a database boundary explicitly converts it to a database-busy exception. This prevents upstream HTTP/LLM timeouts from being falsely attributed to Supabase.

## Bounded threads query

The dynamic-topic list first materializes at most `min(max(limit * 8, 80), 400)` eligible topics ordered by `last_seen DESC, id DESC`. Correlated latest-snapshot metrics, country arrays, and evidence samples execute only for that bounded candidate set. The final result remains ranked by current signal volume and recency and still returns at most the requested limit.

No new index is added without a live `EXPLAIN (ANALYZE, BUFFERS)` showing it is necessary. Existing indexes on dynamic-topic state/member joins are checked first. The acceptance target is a warm production request below two seconds and no cold timeout at the existing 15-second client cap.

## Honest confidence contract

- `avg_confidence` is nullable for dynamic topics when `noise_rate` is absent.
- The thread response exposes `confidence_measured: boolean` and `confidence_source: "noise_rate" | "assignment" | null`.
- The frontend renders a confidence bar only for a measured value. Missing/default values render `unscored`, not `90% confidence`.
- Acceleration uses a neutral accent unless `crisis_relevant` is true.

## Brief resilience contract

- A fresh session cache paints immediately.
- A stale session cache may paint immediately with an explicit `cached` notice while a live refresh runs.
- Refresh success replaces stale data and clears the notice.
- Refresh failure keeps stale data visible and labels it unavailable; without cache, the page renders a retryable error instead of a blank body.
- The AI insight remains a separate best-effort request and never blocks the brief.

## C7 voice-asymmetry pilot

C7 asks: "Which substantial Atlas stories are heavily narrated from a narrow set of outside voices, with weak or absent voice from the story's subject geography or primary languages?"

### Inputs

- Active `dynamic_topics` and their member `signals_v2` rows.
- Signal volume, distinct sources, source languages, source-origin countries, and subject-country candidates already carried by topic members.
- `voice_mix.primary_langs()` for the conservative subject-country language map.

### Eligibility

- At least 20 attributable member signals.
- At least 3 distinct sources.
- A usable subject country; otherwise emit `insufficient_subject_geo` and do not score.
- At least 50% of member signals must have a known language or source origin; otherwise emit `insufficient_attribution` and do not rank.

### Measurements and reason codes

- `dominant_origin_share`: largest outlet-origin share among attributable origins.
- `subject_voice_share`: outlet-origin share owned by the subject country.
- `primary_language_share`: share of language-known signals in the subject country's mapped primary languages.
- `outside_voice_concentration`: normalized origin concentration.
- `voice_asymmetry_score` from 0–100: volume-gated blend of dominant outside origin, missing subject voice, and missing primary-language coverage. It is a corpus-coverage signal, never a claim about real-world truth.
- Ranked hits must expose reason codes such as `dominant_outside_origin`, `subject_voice_absent`, `primary_language_absent`, `high_unattributed_share`, and `thin_public_lane`.

### Outputs and guardrails

- `backend/scripts/voice_asymmetry_report.py` produces JSON and Markdown.
- The report is explicitly `read_only: true`, `model_version: voice-asymmetry-v0`, and labels ordering as "first seen by Atlas" only.
- No database writes, migration, cron, rank mutation, alert, or public badge.
- A live artifact is written under `docs/research/voice-asymmetry/` and reviewed for obvious false positives before C7 is considered a product candidate.

## Verification and delivery

- Frontend: full Vitest, ESLint, and production build.
- Backend: full pytest after repairing the local environment; targeted P1, thread, Brief-contract, and C7 tests run during TDD.
- Shell lock behavior: acquire, skip, wait/give-up, dead-PID reclaim, and live-overdue non-reclaim.
- Production smoke after push: health, signals, threads, briefing, universe, delight, archive search.
- GitHub: close obsolete PRs #144 and #118 with explanatory comments; remove the obsolete remote head for #118; update issue comments where delivered work changed status.
- Preserve every dirty external worktree. Clean host-owned worktrees are not removed by this execution pass.

