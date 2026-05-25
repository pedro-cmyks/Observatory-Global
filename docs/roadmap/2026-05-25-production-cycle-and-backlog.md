# Atlas Production Cycle And Backlog Canon

**Date:** 2026-05-25
**Status:** Active operating canon
**Branch:** `v3-intel-layer`

## Decision

Atlas should not turn every visual observation into immediate frontend work.
The UI is an excellent detector of contract and data-quality problems, but the
current bottleneck is not visual polish. The current bottleneck is backlog
closure across data quality, living-thread contracts, taxonomy quality, entity
hygiene, source lanes, and historical routing verification.

The production cycle is now:

1. Close active data/product backlog.
2. Keep frontend changes limited to functional truth issues.
3. Batch visual feedback after recorded product review sessions.
4. Re-triage open issues before starting each major work block.

## Why This Changed

The latest Narrative Threads work exposed a useful failure mode:

- `/api/v2/threads` was live and returning living-thread data.
- `NarrativeThreads.tsx` still consumed `/api/v2/narratives`, so the visible
  panel kept showing older theme-style rows.
- After the frontend swap, clicking a living thread opened `ThemeDetail`, which
  queried `/api/v2/theme/{slug}` and showed `0 signals` even when the thread row
  showed hundreds of signals.

That was not primarily a design issue. It was a contract mismatch between the
panel, the focus route, and the backend data model.

The fix was functional, not cosmetic:

- `NarrativeThreads.tsx` now consumes `/api/v2/threads`.
- Thread labels are shortened for panel fit; country concentration stays in
  country chips and the thread focus.
- A new `ThreadFocusPanel` reads `/api/v2/threads/{thread_id}` so a selected
  thread shows consistent counts, countries, sources, movement, and evidence.

This pattern should guide future work: fix UI only when it is presenting false
or contradictory information. Defer pure visual refinement to batch review.

## Production Loop

### 1. Backlog Sprint

Pick one backlog lane and finish a small, measurable slice. The preferred lanes
for the current phase are:

- data quality and taxonomy;
- living-thread contract quality;
- entity hygiene;
- source lanes / Voice Mix;
- historical routing verification;
- NLP backlog and benchmark quality.

Do not open new UI-polish work during a backlog sprint unless the UI is
misrepresenting data.

### 2. Contract Smoke

Every shipped product/data change needs a contract smoke:

- frontend surface and endpoint agree on the same object model;
- counts shown in the row match counts shown in the focus/detail;
- empty states explain coverage truth rather than hiding a mismatch;
- long-window surfaces expose coverage/provenance when data is partial;
- cached responses do not preserve stale contract shapes.

### 3. Visual Review Batch

Visual review is a separate production cycle. Pedro records product walkthrough
videos, then the feedback is converted into a batch:

- functional contradiction;
- layout/readability issue;
- explanation/copy issue;
- nice-to-have polish;
- data-quality issue misread as UI.

Only the first category is allowed to interrupt a data backlog sprint.

### 4. Deploy And Verify

For frontend changes:

- run `cd frontend-v2 && npm run build`;
- deploy through Vercel on `v3-intel-layer`;
- verify the public bundle changed;
- smoke the target interaction with Playwright or Browser tooling.

For backend API-only changes:

- use `scripts/deploy-fly-api.sh`;
- verify `https://atlas-api-pedro.fly.dev/health`;
- smoke the touched endpoint against Fly;
- avoid bare `fly deploy` unless the NLP runtime intentionally changes.

## Current Backlog Priority

### Active Now

| Issue | Why it is active |
|---|---|
| #204 Path C taxonomy revision | Needed because live mining/resource thread currently captures coal mine disaster evidence under mining royalty/resource risk. |
| #203 Path B encoder classifier | Needs benchmark harness and precision gate before model promotion. |
| #207 Living Narrative Threads | Umbrella remains active until thread contract quality, frontend focus, evidence roles, and downstream surfaces are coherent. |
| #193 Processed history app windows | Still needs deployed app-wide smoke before closure. |
| #176 Entity drilldown hygiene | Entity Focus should become thread participation, not raw mention cards. |
| #177 Signal Stream relevance/noise | Stream should become evidence-role aware for selected threads. |
| #183 Atlas sentiment presentation | UI should expose one Atlas sentiment, with provenance secondary. |

### Close Or Update Soon

| Issue | Action |
|---|---|
| #202 Path A lex expansion | Close after documenting final migrations 036-038 and metrics. Future lex work feeds anchors, not visible taxonomy. |
| #191 processed historical sync | Likely close if local hot/cold automation remains accepted. |
| #192 processed-only historical tables | Likely close if Supabase-lightweight guardrail remains accepted. |
| #146 narrative threads explanation | Update wording to living-thread confidence/coverage, not old topic explanation. |
| #175 topic detail empty states | Reframe around thread coverage/focus consistency after `ThreadFocusPanel`. |

### Parking / Batch Later

These should not interrupt the current data backlog unless they become visible
truth issues: #134, #140, #147, #148, #152, #173, #178, #179.

### Map Projection / Worldview

Issue #212 tracks Equal Earth / equal-area projection exploration. This is a
separate but Atlas-relevant product architecture item: Atlas should not treat
Mercator distortion as neutral truth. It is documented in
`docs/adrs/ADR-0005-equal-area-projection-mode.md`.

Keep it parked for now. It should enter a visual review batch after the current
data-quality backlog, unless projection work becomes necessary to fix a concrete
map contract problem.

### Provider / Source Lane

These belong to the source-lane/Voice Mix block: #160, #168, #172, #180, #158,
#156, #150, #145.

## Next Work Block

Start with **Path C taxonomy quality** because it is the clearest current
product/data mismatch:

1. Audit live top `/api/v2/threads?hours=24&limit=20`.
2. Flag threads where label and evidence disagree.
3. First candidate: split or rename `mining-royalty-risk` because the current
   high-confidence cluster is coal mine disaster, not royalty/concession risk.
4. First audit result: the cluster is real but the label is wrong. It is mining
   safety / resource-disaster coverage, currently dominated by a China coal mine
   explosion.
5. First conservative migration: `backend/migrations/039_mining_resource_safety_label.sql`
   keeps slug `mining-royalty-risk` stable but changes the human-facing label
   and description toward `Mining and resource safety crisis`.
6. Defer a true split until Path B labels or a larger Path C sample shows
   independent royalty/concession volume.

Audit doc:
`docs/research/2026-05-25-path-c-mining-resource-taxonomy-audit.md`.

Second Path C slice:

- Added `backend/scripts/topic_quality_audit.py`.
- Audited all 30 active topics in
  `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.md`.
- Applied migrations 040-041 to reduce visible false positives. The quality
  rule is now explicit: smaller precise topics are better than large noisy
  topics.
- Proposed future thread/data quality indicator with components for evidence
  support, sample precision, source breadth, geo coherence, and movement
  integrity.

Next quality dependency:

- #203 Path B benchmark harness now exists as
  `backend/scripts/topic_benchmark_harness.py`.
- First label-ready sample:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl`
  with 103 rows across seven priority topics.
- The next step is labeling and scoring the sample. Manual sample precision is
  now a measurable gate before broader taxonomy/model promotion.

## Guardrails

- Do not trust GDELT themes as proof of significance.
- Do not optimize recall by accepting noisy broad terms.
- Do not expose raw NER entities as validated people.
- Do not add user-facing correction UI yet.
- Do not let visual polish displace data quality work.
- Do not close historical routing issues until deployed frontend smoke passes.
