# Investigation Graph Slice 3 — Daily Publication and Shared Package

**Date:** 2026-07-12
**Status:** implementation complete; validation/deploy gate in progress
**Goal:** replace the L1 volume-ranked thread strip with a complete, reconciled
24-hour candidate ledger and serialize both system-selected L1 material and
analyst-selected L3 material through one deterministic publication package.

**History reconciliation:**
`docs/state/2026-07-12-spec-history-crosswalk.md` is load-bearing. This slice
extends existing relation/dossier contracts; it does not create a second graph,
who-says-what, corroboration, citation, or publication-synthesis brain.

## Canon reused — do not create a parallel ranking brain

- `docs/specs/2026-07-04-crisis-as-dynamics-reframe.md`: crisis is a measured
  dynamic state/lens; semantic category and `crisis_relevant` do not partition
  or rank reality.
- `docs/specs/2026-07-02-universe-view.md` §7.6: `topic_movement` is the shared
  movement field; Kalman velocity/surprise is preferred and relative
  `changed_10h` is the same-lineage fallback.
- `docs/state/2026-07-04-alignment.md`: the leading-indicator backtest was
  negative. Movement describes current change and must not be narrated as a
  forecast.
- `backend/app/services/thread_ranking.py`: retain its evidence-floor lesson,
  but do not copy its legacy volume/editorial-lane weighting into the daily
  edition. The daily adapter consumes the shared movement field and reports
  uncertainty/completion.

## Constraints

- Candidate traversal may use operational batches, but it must reconcile the
  full eligible universe and report completion. Display limits are not semantic
  omissions.
- Selection and relations are math/rules only. The LLM may write prose only
  after nodes, edges, receipts, readiness, and gaps are fixed.
- Contextual overlap never becomes a measured or causal relation.
- A failed lane remains named in the completion/degradation ledger.
- Existing Workbench investigations migrate losslessly; frozen pins remain
  authoritative for what the analyst saw.

## Task 1 — Graph and edge contract

**Implemented 2026-07-13.**

- Add deterministic `InvestigationEdge` and graph response contracts.
- Add pure adapters for the shipped `dossier-connections-v1`, exact
  `topic_members`, event bindings, voice/relationship, and history contracts.
  The graph assembler reconciles their outputs; it does not reimplement their
  relation math.
- Resolve exact membership/shared receipts before contextual country/time
  overlap; semantic proximity is accepted only with an explicit measured score
  and method. Correct the legacy dossier interpretation: shared coverage country
  is contextual, not a strong story edge.
- Reconcile every requested pair and every enabled engine in completion
  metadata.
- Expose `POST /api/v2/investigation/graph`.

## Task 2 — Shared deterministic `PublicationPackage`

**Implemented 2026-07-13.**

- Build numbered receipts from frozen node evidence.
- Wrap the existing dossier connection distributions, who-says-what/voice,
  corroboration, citation table, and synthesis contracts. Do not replace real
  public/press/tier data with counts inferred from generic evidence snapshots.
- Compute the 5W+H readiness ledger, relation spine, unknowns/gaps, method
  receipts, and reproducibility payload over those adapters.
- Prove identical node/edge inputs produce identical packages apart from an
  explicitly supplied `generated_at`.
- Expose `POST /api/v2/investigation/publication-package`.

## Task 3 — Complete daily candidate ledger

**Implemented offline/precomputed; selector backtest and L1 cutover remain
gated.**

- Traverse all eligible top-level active dynamic topics in the fixed edition
  window using cursor batches.
- Compute a **measured state vector** from change against each topic's own
  history: relative `changed_10h`, Kalman-smoothed velocity/surprise/uncertainty
  when available, persistence, source independence/diversity,
  coherence/noise, novelty, attention divergence, and gap/anomaly flags. Raw
  volume is an evidence-floor/confidence input, never importance. Category and
  harm-potential are descriptive lenses only and contribute zero importance
  weight.
- Select a finite visual spine from a Pareto frontier plus graph/diversity
  coverage, rather than declaring one handwritten scalar to be “investigative
  usefulness”. Sports, culture, politics, disasters, or finance may lead when
  their measured state and receipts warrant it. Preserve reason codes and the
  full measured vector for every selected/downranked/unresolved row.
- Backtest the selector on frozen daily universes against volume-only and the
  existing `rank_threads` order before wiring it into production L1.
- Label acceleration as a measured current state, never a prediction: the
  existing backtest found Kalman velocity did not lead future volume, so it
  cannot support forecasting language.
- Resolve full receipts only for selected nodes after the universe is
  reconciled.
- Expose `GET /api/v2/investigation/daily-publication?hours=24` with completion
  and selection ledgers.
- Build this contract offline after the sealed scoped snapshot and store one
  compact `atlas_daily_editions` row. Serving must read the artifact, never
  traverse candidates, receipts, or relations inside the request.

## Task 4 — L1 and L3 adapters

**L3 adapter/readiness implemented; L1 intentionally remains on the existing
Brief until the sealed artifact clears freshness, receipt and editorial gates.**

- L1 consumes the daily package/article and exposes its selection, receipts,
  readiness, gaps, and method instead of a generic volume paragraph.
- Workbench migrates to `atlas-investigation-v2`, resolves heterogeneous pins,
  requests the graph/package, and preserves the current dossier as an honest
  fallback while enrichment runs.
- The existing dossier synthesis/corroboration path remains canonical until the
  shared package adapter proves parity on NATO-Ankara.

## Task 5 — Editorial and operational gate

**In progress.** Focused suites and local Workbench truth smoke pass. Full
suite, controlled HNSW maintenance measurement, deploy and post-deploy L0-L3
comparison remain.

**2026-07-13 follow-up:** the frozen daily forcing case now verifies subject
geography on all 12 story nodes from independent receipt headlines, and the
shared package applies the broad typed-actor canon without promoting
shared-country context into a measured relation. The #238 complete-universe
rerun reached 1,488/1,488 topics with no failures. The next stored artifact must
be produced by the autonomous sealed pipeline; do not rewrite the current
edition with a later wall-clock timestamp merely to manufacture freshness.

- Run focused and full backend/frontend suites.
- Deploy API and frontend.
- Browser-smoke L0, L1, L2, L3; build one real investigation and export it.
- Grade the daily edition and Workbench dossier with the same rubric; record
  every remaining caveat and issue mapping before any closeout.
