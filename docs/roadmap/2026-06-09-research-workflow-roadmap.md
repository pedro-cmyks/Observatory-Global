# Atlas Research Workflow Roadmap

**Date:** 2026-06-09
**Status:** active — phases 0.5 through 1.5 shipped; typed graph foundation next
**Spec:** `docs/specs/2026-06-09-research-thread-builder-workbench.md`
**Umbrella issue:** #213
**Supersedes triage framing in:** `docs/roadmap/2026-06-04-mvp-issue-triage.md`

## Position

The MVP truth pass shipped in `ca2130b` (#174 scope coherence, #175 query-thread
builder, #177 Signal Stream relevance, #146 country-scoped threads). Narrative
Threads are the visible topic model; `dynamic_topics` is their implementation
record. The product is now correct enough to build the next capability on top of:
a guided research workflow from natural search to a pinned Workbench
investigation.

#213 is the umbrella. It is not one feature; it sequences a large slice of the
existing backlog that all feeds the same workflow.

## Reconciliation with the MVP triage

The 2026-06-04 MVP triage parked several issues as "not current truth blockers."
The research-workflow spec **promotes** some of them because they are core to the
workflow, now that the truth pass is done. Where the two disagree, this roadmap
wins:

| Issue | MVP triage said | Now |
|---|---|---|
| #173 Evidence Route | Parked (depends on scope consistency) | Tier A core; scope consistency shipped. |
| #176 Entity hygiene | Parked (follows scope pass) | Tier A core; needed for who-says-what. |
| #152 Command-bar layout | Parked (not a truth blocker) | Tier E; front door for `Start investigation`. |
| #167 Atlas topic intelligence | Umbrella/future | Tier F: largely delivered by dynamic-topics; narrow to remnant. |
| #134 / #140 use-case docs | Parked until stable screenshots | Tier F: the Iran walkthrough becomes the showcase. |

Source/coverage and paper/model lanes from the MVP triage map onto Tiers B/C/D
unchanged in intent, just re-sequenced around the workflow.

## Two forcing cases

1. **Topic research** — Iran climate/water (broad multi-hop investigation).
2. **Claim verification** — Iran "rain theft" / weather-weapon viral claim
   (verify, not amplify; contradiction + unsupported-claim handling).

Both are automated acceptance fixtures, not manual smoke.

## Tiered backlog (see spec Backlog Alignment)

- **rw-tier-a-core:** #207 #173 #168 #172 #160 #176 #178
- **rw-tier-b-recall:** #161 #185 #150 #158 #162 #157
- **rw-tier-c-quality:** #154 #166 #180 #148 #153 #156 #159 #46
- **rw-tier-d-nlp:** #164 #163 #184
- **rw-tier-e-entry:** #152
- **rw-tier-f-fold:** #167 #134 #140 #204
- **Independent (not blocked):** #106 #147 #151 #179 #183 #196 #212

## Attack order

1. **Phase 0.5** — list/detail reconciliation fix (trust prerequisite). Own issue.
2. **Fixtures** — encode both forcing cases as automated acceptance tests.
3. **Phase 1a** — read-only anchors over existing thread/country/public-attention
   surfaces; prove the forcing cases return openable anchors. Tier A surfaces.
4. **#154 audit** — measure source quality/dominance; seed ranking weights.
5. **Phase 1b** — weighted ranking, reason codes, downranking ledger, trays.
6. **Phase 1.5** — `e5-base` semantic lane for cross-language / fringe-phrasing
   recall. Tier B (#161, #185, multilingual) feeds this.
7. **Phase 2** — Workbench pinning + sidebar/history (localStorage v1) + #152.
8. **Tier D** — NLP capacity backbone, continuous parallel track.

## Movement signal

The read-only Kalman state pilot (`kalman-state-v0-readonly`,
`backend/scripts/dynamic_topic_state_report.py`) is the `movement_signal`
provider for ranking. No separate issue; stays read-only. Promoting it from a
report to a callable feed is an optional follow-up.

## Definition of done for the workflow

The product is done when a broad natural query and a viral claim both produce
useful, openable anchors; the user can pin a route in Workbench without losing
it; who-says-what and frame differences are visible; evidence, context, weak
support, contradiction, and gaps are clearly separated; list and detail counts
agree; and the pinned route can become a report.

## Addendum 2026-07-12: Investigation Graph execution order

The original read-only research-plan phases are now live: list/detail
reconciliation, forcing fixtures, multi-lane anchors, usefulness ranking,
reason-code ledgers, and semantic retrieval. Workbench can store several pin
types, but its constellation resolves mostly thread/topic identifiers and does
not yet connect the heterogeneous Atlas surfaces truthfully.

Pedro approved the next canon in
`docs/superpowers/specs/2026-07-12-investigation-graph-l2-l3-design.md`:

1. reliability precondition — shipped and deployed in
   `docs/state/2026-07-12-investigation-graph-slice-1-reliability.md`;
2. typed node identity and heterogeneous `resolve-node` adapters;
3. immutable pin snapshot plus live reference;
4. measured/inferred/contextual/analyst edge envelopes with receipts;
5. Workbench graph/time slices and editorial composition;
6. shared publication package, used both by L1's complete 24h investigation
   and L3's analyst-built investigation;
7. blind editorial comparison for the prose provider over frozen evidence
   packages; LLM writes synthesis but never graph topology or evidence truth.

The first graph forcing case must combine at least two related Iran threads, a
structured conflict event, a country, and a person/entity. It fails if the only
explanation is a tautological geography edge such as `Iran ↔ Iran`.


## Addendum 2026-06-12: L4 markets layer (post-spec track)

After the research workflow ships its remaining phases, the L4 markets
layer is the next major track: `docs/research/2026-06-12-atlas-markets-layer-l4.md`
(evidence-gated plan, M0 = #226). Lives in a `markets/` folder in this repo,
consumes the Atlas API, never blocks the spec. Long-range product thesis:
Atlas as an API for processed narrative state.
