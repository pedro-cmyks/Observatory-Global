# Open Issues Triage For Living Threads

**Date:** 2026-05-24.
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
| #168 public attention threads and semantic links | canon | Reframe as voice lanes and related public-attention threads, not peer reporting. |
| #173 Evidence Route panel | canon | Becomes the analyst path: thread -> evidence -> workspace -> dossier. |
| #177 Signal Stream relevance/noise | canon | Upgrade to thread evidence ranking and evidence roles. |
| #183 sentiment source badge + heat panel | canon | Product rule: one Atlas sentiment; provenance can stay secondary. |
| #193 app windows to processed history | canon | Keep open until deployed visual smoke tests pass. |
| #203 Path B encoder classifier | canon | Shadow/benchmark only; 85% minimum precision, 90% target. |
| #204 Path C taxonomy revision | canon | Evolves into living-thread taxonomy review, not quarterly fixed-topic expansion only. |

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
| #202 Path A lex expansion | close-after-merge | Complete after PR #206 merges; future lex work feeds anchors, not UI taxonomy. |

## Close After Verification Or Merge

| Issue | Triage | Close condition |
|---|---|---|
| #191 processed historical sync | close-after-merge | Close if maintainers accept local hot/cold automation and compact sync as complete umbrella. |
| #192 processed-only historical tables | close-after-merge | Close if guardrail is accepted as implemented. |
| #202 Path A lex expansion | close-after-merge | Close after PR #206 merge and issue comment references final metrics. |

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
| #185 corpus-mine vocab | parking | Useful but no longer the main topic route after Path A. |
| #196 AISStream TLS degradation | parking | Provider health item. |

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
