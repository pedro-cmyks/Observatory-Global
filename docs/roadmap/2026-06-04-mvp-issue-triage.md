# MVP Issue Triage

**Date:** 2026-06-04  
**Status:** Superseded for sequencing by
`docs/roadmap/2026-06-09-research-workflow-roadmap.md` (the MVP truth pass
shipped in `ca2130b`; #213 research workflow is the next sprint). Tier
assignments and the promote/park reconciliation live in that roadmap.  
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
| #174 Scope coherence across side panels | In progress | Source Integrity labels scoped vs global background; FocusData discards stale responses; Public Attention names global matching vs country origin. **CountryBrief now counts country-scoped Narrative Threads from `/api/v2/threads?country_code=...`, not the forced 12-item GDELT theme slice.** Remaining work is manual country -> person -> topic -> clear smoke and any panel-specific gaps found there. |
| #175 Topic-detail/Search empty states | Closed 2026-06-08/09 | ThemeDetail explains zero-result thread/topic detail as a coverage/quality gate. Search no longer shows curated concept-map suggestions or the old save-as-concept CTA. **Custom query-thread builder shipped in `ca2130b`** (`GET /api/v2/search/thread` + `query-thread::` token in SearchBar/ThemeDetail; direct match, no gate, THIN badge). Production smoke: search for `Colombia` and "Build a thread" opened `CUSTOM THREAD` with no `HTTP 404`. Organic search-demand tracking should be a separate future issue if needed. |
| #193 Processed history app windows | Closed | Briefing and `/api/v2/nodes` route long windows to processed history; `/app` shows a historical processed cue when the map is served from compact historical aggregates. |
| #177 Signal Stream relevance/noise | Closed 2026-06-08/09 | **Slice 1 shipped in `ca2130b`**: backend `lane`+`relevanceScore` on `/api/v2/signals` (+`lane` filter, `sort=relevance`); SignalStream analyst tabs exclude sports/entertainment, NOTABLE ranks analyst lane, lane badges + ranking tooltip. Production smoke returned signals with `lane=analyst` and `relevanceScore=1.0`. Dedicated public-attention/US-domestic/raw tabs and `signal_topic_assignments` (#167) domain labels should be narrower future issues if needed. |
| #146 Narrative Threads explanation | Close after current smoke | Country-scoped empty states explain quality gates and provide a global reset. CountryBrief now aligns its visible thread count with the Narrative Threads contract. |

## Thread Volume Lane

This lane is active but conservative.

| Artifact | Status | MVP interpretation |
|---|---|---|
| `docs/research/topic-quality/gdelt-weak-support/2026-06-04-live.json` | Done | GDELT themes are useful diagnostics for support, contradiction, entropy, and bias. |
| `docs/research/topic-quality/gdelt-weak-support/2026-06-04-recall-pilot.json` | Done | Weak recall can recover candidates only when compatible GDELT themes and label anchors agree. |
| Automatic promotion from GDELT | Not allowed | GDELT is a weak support signal, not the final classifier or paper-grade truth. |
| Next implementation | Pending | Add a reviewable candidate queue or diagnostics panel before adding any candidates to active threads. |

## Search And Query Threads

Search should not expose `INVESTIGATIVE CONCEPT MAP` as a fixed user-facing
taxonomy. That map is a legacy curated GDELT-bundle helper and can create false
related concepts for normal person/topic searches.

MVP direction:

1. Search returns direct evidence first: signal matches, people, countries,
   public attention, and supported themes.
2. A user query should become a temporary custom Narrative Thread when enough
   evidence exists.
3. A persistent concept list is allowed only if it grows from demand and
   evidence: repeated searches, query volume, multilingual variants, and signal
   support.
4. Curated concept suggestions stay hidden until they can be justified by that
   demand/evidence layer.

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

#146 remains the first close candidate in this sprint. The current implementation:

- fetches country-scoped threads from `/api/v2/threads?country_code=...`;
- explains that an empty country list means no coherent thread cleared the
  current quality gate, not that the country has no signals;
- provides a direct "Show global threads" reset;
- updates hover copy to point to the unified thread detail instead of the old
  topic breakdown;
- aligns CountryBrief's visible `threads` metric and Narrative Threads section
  with the same country-scoped thread source, so countries no longer show a
  forced `12 themes` count from local GDELT signal-theme slicing.

## Next Implementation Order

1. Browser-smoke #146/#174 locally: country click, CountryBrief `threads` metric,
   NarrativeThreads country rows, ThreadDetail open, clear country, and empty
   states.
2. Commit the local closeout batch once smoke passes.
3. Rotate secrets in a separate maintenance pass; the MVP batch itself was
   pushed/deployed/smoked in `ca2130b`.
4. Close #146 after commit/deploy/comment if production matches local behavior.
5. Continue only new narrower follow-ups from #174/#175 if fresh evidence shows
   a regression. Current slices are complete:
   Source Integrity now names country/theme/person scopes and explicitly labels
   unscoped metrics as global background when the center panel is focused.
   ThemeDetail now replaces zero-result stats/graphs with a coverage-gate empty
   state and a return-to-global/stream action. FocusData now rejects stale
   responses, Public Attention names its matching scope, and Search no longer
   shows curated concept-map suggestions.
6. Decide whether GDELT weak recall becomes a review queue or remains a research
   artifact for MVP.
7. Treat #177 as closed for this implementation slice. Open narrower follow-ups
   for dedicated public-attention / US-domestic / raw-firehose tabs, or for
   consuming `signal_topic_assignments` (#167) as domain labels.
8. Scope the Kalman/state-tracking pilot only after the MVP truth pass ships.
