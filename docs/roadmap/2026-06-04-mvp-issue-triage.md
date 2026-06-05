# MVP Issue Triage

**Date:** 2026-06-04  
**Status:** Active MVP sprint triage  
**Basis:** 42 open GitHub issues from `gh issue list --state open --limit 100`
on 2026-06-04.

## Sprint Rule

The MVP sprint prioritizes product truth over polish:

1. Narrative Threads must be the visible topic model.
2. Thread volume should improve only where weak support and label anchors agree.
3. Side panels must not contradict the active country/topic/person/thread scope.
4. Empty states must explain coverage/quality gates, not look broken.
5. Paper/benchmark work remains relevant, but it should not block next week's
   MVP unless the product is making an unsupported methodological claim.

## Active Now

| Issue | Action | Reason |
|---|---|---|
| #207 Living Narrative Threads data contract | Keep open as umbrella | Threads/themes are now one product concept, but downstream surfaces still need consistency. |
| #174 Scope coherence across side panels | In progress | First slice labels Source Integrity as scoped vs global background; remaining work covers Public Attention, thread detail, and stale response guards. |
| #175 Topic-detail empty states | In progress | ThemeDetail now explains zero-result thread/topic detail as a coverage/quality gate and gives a return action; remaining work covers stale responses and other panels. |
| #193 Processed history app windows | Verify/deploy-smoke | 1w/1m should route to processed historical tables and expose coverage metadata. |
| #177 Signal Stream relevance/noise | Start after scope pass | Stream should rank evidence for the active thread, not just list recent signals. |
| #146 Narrative Threads explanation | Close after current fix | Country-scoped empty states now explain quality gates and provide a global reset. |

## Thread Volume Lane

This lane is active but conservative.

| Artifact | Status | MVP interpretation |
|---|---|---|
| `docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json` | Done | GDELT themes are useful diagnostics for support, contradiction, entropy, and bias. |
| `docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json` | Done | Weak recall can recover candidates only when compatible GDELT themes and label anchors agree. |
| Automatic promotion from GDELT | Not allowed | GDELT is a weak support signal, not the final classifier or paper-grade truth. |
| Next implementation | Pending | Add a reviewable candidate queue or diagnostics panel before adding any candidates to active threads. |

## Close Or Update Soon

| Issue | Action |
|---|---|
| #146 | Close after commit/push and issue comment. |
| #179 | Keep open; legend improvements landed, but active-layer/marker acceptance is only partially covered. |
| #178 | Reframe around evidence publication time vs UI render time in selected thread context. |
| #183 | Reframe under one Atlas sentiment with provenance details, not competing sentiment systems. |
| #196 | Verify provider degradation behavior; close only if AIS TLS path is handled as degraded. |

## Source And Coverage Lane

These are real, but should be batched after the thread/scope pass:

| Issues | Direction |
|---|---|
| #150, #153, #156, #158, #180 | Source breadth and provider reliability. |
| #160, #168, #172 | Voice Mix and public-attention threads. |
| #145 | Public-attention noise filters. |
| #159, #161 | GDELT propagation/query-time evidence research. |

## Paper And Model Refinement Lane

Keep these alive, but do not let them interrupt MVP fixes:

| Issues | Direction |
|---|---|
| #203, #204 | Benchmark/taxonomy refinement continues after MVP thread truth is stable. |
| #185 | Corpus-mined vocabulary can feed weak support and benchmark repair. |
| #154, #157, #162, #164, #166 | Model quality, NLP quality, and correction-loop work; refresh before implementation because several parts are now stale or partially superseded. |

## Parking

These are valid but not MVP blockers:

| Issues | Reason |
|---|---|
| #212 | Equal-area projection is product architecture, parked outside this sprint. |
| #173 | Evidence Route is important but depends on thread/scope consistency first. |
| #176 | Entity drilldown hygiene follows the scope pass. |
| #184 | Do not change worker capacity without fresh pressure evidence. |
| #140, #134 | Documentation/use-case manual after stable screenshots. |
| #147, #148, #151, #152 | Useful UX/features, not current truth blockers. |
| #106, #46 | Blocked by brand/provider access. |

## Current Closure Decision

#146 is the first close candidate in this sprint. The current implementation:

- fetches country-scoped threads from `/api/v2/threads?country_code=...`;
- explains that an empty country list means no coherent thread cleared the
  current quality gate, not that the country has no signals;
- provides a direct "Show global threads" reset;
- updates hover copy to point to the unified thread detail instead of the old
  topic breakdown.

## Next Implementation Order

1. Close #146.
2. Continue #174/#175 as a scope/empty-state pass. First slices are complete:
   Source Integrity now names country/theme/person scopes and explicitly labels
   unscoped metrics as global background when the center panel is focused.
   ThemeDetail now replaces zero-result stats/graphs with a coverage-gate empty
   state and a return-to-global/stream action.
3. Smoke #193 for 1w/1m processed-history routing.
4. Decide whether GDELT weak recall becomes a review queue or remains a research
   artifact for MVP.
5. Return to #177 evidence relevance once the selected scope is reliable.
