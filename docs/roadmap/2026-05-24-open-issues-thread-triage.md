# Open Issues Triage For Living Threads

**Date:** 2026-05-24.
**Updated:** 2026-05-25 after PR #211, frontend thread-focus deploy,
production-cycle canon, and narrative-intelligence framework.
**Basis:** open GitHub issues reviewed with `gh issue list --state open --limit 120`.

## Triage Labels

| Label | Meaning |
|---|---|
| `canon` | Still aligned with the current Atlas route. |
| `evolve` | Keep the issue, but update wording/scope around living threads. |
| `close-after-merge` | Work is effectively done locally or in PR; close after merge/verification. |
| `parking` | Valid but not on the immediate route. |
| `blocked` | External provider, asset, or decision dependency. |
| `stale-review` | Likely superseded; review before doing work. |

## Canonical Route

These issues should drive the next roadmap phase:

| Issue | Triage | Direction |
|---|---|---|
| #207 Living Narrative Threads data contract | canon | Keep as umbrella until thread contract, focus path, evidence roles, and downstream surfaces are coherent. Backend and first visible frontend slice are live. |
| #168 public attention threads and semantic links | canon | Reframe as voice lanes and related public-attention threads, not peer reporting. |
| #173 Evidence Route panel | canon | Becomes the analyst path: thread -> evidence -> workspace -> dossier. |
| #177 Signal Stream relevance/noise | canon | Upgrade to thread evidence ranking and evidence roles. |
| #183 sentiment source badge + heat panel | canon | Product rule: one Atlas sentiment; provenance can stay secondary. |
| #193 app windows to processed history | canon | Keep open until deployed visual smoke tests pass. |
| #203 Path B encoder classifier | canon | Shadow/benchmark only; 85% minimum precision, 90% target. |
| #204 Path C taxonomy revision | active-now | First slice corrects mining/resource label after live evidence showed coal mine/resource-disaster dominance. |

## Evolve

These issues remain useful but should be updated before implementation:

| Issue | Triage | Needed evolution |
|---|---|---|
| #146 narrative threads explanation | evolve | Replace explanatory copy with natural thread behavior and confidence cues. |
| #160 Voice Mix endpoint/CountryBrief | evolve | Make Voice Mix a per-thread and per-country lane, not only country-level summary. |
| #167 Atlas topic intelligence | evolve | Clarify `atlas_topics` as internal anchors for living threads. |
| #172 silent-risk detector | evolve | Model as thread with high public attention and low reporting coverage. |
| #174 scope coherence | evolve | Scope should be country/topic/person/thread coherent. |
| #175 topic-detail empty states | evolve | Empty states should explain thread coverage, not only topic misses. |
| #176 entity drilldown hygiene | evolve | Entity pages should show which threads the entity participates in. |
| #178 stream inspection time | evolve | Include evidence freshness vs publication/render time in thread evidence. |
| #179 map legend | evolve | Legend should explain active thread/geography/source layers. |

## Close After Verification Or Merge

| Issue | Triage | Close condition |
|---|---|---|
| #191 processed historical sync | close-after-merge | Close if maintainers accept local hot/cold automation and compact sync as complete umbrella. |
| #192 processed-only historical tables | close-after-merge | Close if guardrail is accepted as implemented. |
| #202 Path A lex expansion | close-after-verification | Migrations 036-038 are live. Close after final issue comment records six-topic rollout metrics and states future lex work feeds internal anchors. |

## Parking Lot

These are still valid, but should not interrupt the living-thread route:

| Issue | Triage | Reason |
|---|---|---|
| #134 analytical use cases docs | parking | Useful after thread surfaces are real. |
| #140 visual use-case manual | parking | Best after thread/evidence route stabilizes. |
| #145 public-attention noise | parking | Important, but subordinate to source-lane modeling. |
| #147 map reset | parking | UI polish. |
| #148 see all publishers | parking | Useful source UX, not route-defining. |
| #150 non-anglophone sources | parking | Important data breadth; route is already known. |
| #151 financial overlays | parking | Separate feature lane. |
| #152 command bar collision | parking | UI polish. |
| #153 public attention sources research | parking | Current providers are enough for thread modeling. |
| #154 source quality/backlog audit | parking | Some conclusions have been absorbed; keep as background. |
| #156 NewsAPI dynamic queries | parking | Good ingestion improvement after thread layer. |
| #158 NewsData country-primary | parking | Good ingestion improvement after thread layer. |
| #159 Event Mentions propagation | parking | Research lane. |
| #161 GDELT DOC 2.0 | parking | Query-time enrichment lane. |
| #164 ADR-0004 NLP strategy | parking | Historical context; likely close after review if all action migrated. |
| #185 corpus-mine vocab | active-later | Feed this into Path B/C benchmark work; do not use it as visible taxonomy work. |
| #196 AISStream TLS degradation | parking | Provider health item. |
| #212 Equal Earth projection mode | parking | Product-architecture item for equal-area worldview; documented in ADR-0005, not part of current data sprint. |

## Blocked

| Issue | Triage | Blocker |
|---|---|---|
| #46 ACLED API access | blocked | External access. |
| #106 mascot | blocked | Brand/asset/product decision; not part of current intelligence route. |
| #180 ReliefWeb Fly fetch | blocked | Provider/network path; can be revisited under source lanes. |

## Stale Review

| Issue | Triage | Review question |
|---|---|---|
| #157 multilingual NLP quality/backlog | stale-review | Some multilingual NLP work has already landed; keep only if it now means benchmark quality. |
| #162 multilingual NLP swap | stale-review | Logs show multilingual XLM pipeline active; confirm remaining delta before doing work. |
| #163 NLP priority queue | stale-review | Worker split exists; validate whether queue/lag telemetry is still missing. |
| #166 analyst correction loop | stale-review | User rejected broad topic-correction UI for now; keep only controlled benchmark labels. |
| #184 NLP_WORKER_LIMIT bump | stale-review | Do not raise limits without fresh DB pressure evidence. |

## New Umbrella Issue

Opened as #207: `feat(threads): introduce living Narrative Threads data contract`.

It links:

- this triage;
- `docs/specs/2026-05-24-living-narrative-threads.md`;
- `docs/research/2026-05-24-app-panel-thread-audit.md`;
- #168, #173, #177, #183, #203, #204.

Do not create separate issues per panel until the first `/api/v2/threads` beta
contract exists.

## 2026-05-25 Production-Cycle Update

The first `/api/v2/threads` beta and visible Narrative Threads consumption are
now live. The route is no longer "build the thread endpoint"; it is:

1. close or update completed umbrella issues;
2. fix data/taxonomy quality before more visual polish;
3. batch visual feedback from recorded walkthroughs;
4. reserve immediate frontend changes for truth/contract mismatches.

Immediate active issue order:

1. #203 Path B encoder classifier: label and score the first benchmark sample
   before any promotion.
2. #204 Path C taxonomy revision: continue broader taxonomy repair after the
   mining/resource disaster first slice.
3. #193 processed historical routing: deployed visual smoke before closure.
4. #176 Entity Focus: thread participation and role hygiene.
5. #177 Signal Stream: evidence-role ranking for selected threads.

## 2026-05-25 Path C / Projection Update

- #212 opened for Equal Earth / equal-area projection exploration. It is
  relevant to Atlas's worldview but parked outside the active data backlog.
- #204 first slice started with
  `docs/research/2026-05-25-path-c-mining-resource-taxonomy-audit.md`.
- `backend/migrations/039_mining_resource_safety_label.sql` is the conservative
  first Path C migration: keep slug compatibility, correct the visible mining
  anchor label/description.

## 2026-05-25 All-Topic Quality Update

- `backend/scripts/topic_quality_audit.py` added as a repeatable read-only audit
  tool for all active atlas topics.
- Full 30-topic audit documented in
  `docs/research/topic-quality/2026-05-25-atlas-topic-quality-audit.md`.
- Migrations 040-041 applied a precision-first pass. Some topics intentionally
  became thin rather than noisy; this is a product-quality improvement, not a
  regression.
- #204 remains open for the broader Path C cycle, but the immediate dependency
  now shifts to #203 benchmark labels so sample precision can become a measured
  gate.

## 2026-05-25 Path B Benchmark Harness Update

- `backend/scripts/topic_benchmark_harness.py` added as the read-only sample and
  score harness.
- First label-ready sample:
  `docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl`.
- Harness documentation:
  `docs/research/topic-quality/2026-05-25-path-b-benchmark-harness.md`.
- First labeled score:
  `docs/research/topic-quality/benchmark-scores/2026-05-25-path-b-priority-topics-score.json`.
- Overall precision is `80.85%`, below the 85% floor. Next issue action for
  #203 is typed repair/design, not model promotion.
- Typed failures split into mechanical noise and hierarchy work. Broad concepts
  that fail a specific child anchor can still be valid parent/entity threads.
- Root cause audit:
  `docs/research/topic-quality/2026-05-25-narrative-classification-root-cause-audit.md`.
  Next issue action is model-level: distinguish domain, parent thread, child
  thread, entity thread, evidence, context signal, and noise before adding more
  topic-specific patches.
- Market/product quality review:
  `docs/research/topic-quality/2026-05-25-atlas-quality-models-market-and-product.md`.
  #203/#207 validation should become answerability-first: each metric should
  trace to one of the seven Atlas questions.

## 2026-05-25 Narrative Intelligence Framework Update

- External field review:
  `docs/research/topic-quality/2026-05-25-narrative-intelligence-field-review.md`.
- Active model framework:
  `docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`.
- Atlas should be treated as both model and visualizer. The model converts
  signals into evidence-backed parent/child/entity Narrative Threads; the
  visualizer exposes those threads through the globe, thread list, focus panels,
  source integrity, stream, and workspace.
- #203 next action: extend benchmark labels from binary topic relevance into
  semantic scope, evidence role, parent/child thread candidates, and supported
  Atlas questions.
- #207 next action: use a read-only Narrative Thread Graph report to test
  relations, movement drivers, evidence roles, and quality envelopes before
  adding persistent graph tables or deeper UI changes.
