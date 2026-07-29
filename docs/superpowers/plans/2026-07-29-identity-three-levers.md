# Identity heals: the three measured levers — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Measure-first: every lever has a pre-registered gate BEFORE its write lands.

**Goal:** Act on the three instruments the 2026-07-29 measurements produced — court verdicts ENFORCED where they are ignored, umbrellas COVERED where they are unjudged, blobs CONFIRMED by membership where entropy is blind — so the served field stops presenting court-failed fusions as top stories. This is the direct prerequisite for `STORY_LENS_AUTO=true`.

**Evidence base (do not re-derive):**
- Court audit `docs/research/label-court/2026-07-29-court-blindspot-audit.md`: PASS stamp has ZERO blind spot (0/30); the failure is enforcement (66% of active topics court-FAILED and serving) + coverage (the 14 biggest served rows, incl. 10 umbrellas, carry NO verdict).
- Blob calibration `docs/research/recall-229/2026-07-29-blob-flagger-calibration.md`: (tau 2.6, indeg 4) → 22.1% flagged, precision 0.78 (CI wide); entropy AUC 0.564 vs in-degree 0.702; within-category fusions are invisible to entropy BY CONSTRUCTION; `confirm_blob_candidates` (membership multimodality) is the measured discriminator.
- Finder-v2 `docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.md`: the walk works on clean fragments (6/6); the served anchors are the disease (dt-466 class).

**Rails:** pathspec-only commits; every write behind an env kill-switch, default OFF; degraded/thin surfaces stay honest-empty, never blank; no gate moved after seeing results; ALW runner re-sync on any cron-executed script change.

---

## Lever A — court enforcement in serving (damp, not gate)

### A0 · Measure the enforcement modes (read-only, gates everything)
Harness `backend/scripts/measure_court_enforcement.py` over the live field, simulating `/threads` top-40 (global + 5 country doors incl. 2 thin ones) under:
- mode-0 baseline (today), mode-1 rank damp (court-failed × configurable factor, lifestyle-damp precedent), mode-2 top-N exclusion of `failed` with below-fold tray.
Report per mode: entailed/partial/failed share of top-40, rows-served delta, thin-country coverage delta, WHICH stories move (labels).
**Pre-registered gate GA:** adopt the strongest mode that raises top-40 entailed-share by ≥20pp while (a) no country door loses >25% of its served rows and (b) the global top-40 never drops below 30 rows. **Kill:** if every mode violates (a)/(b), enforcement waits for relabel/court-recovery — record and stop Lever A.

### A1 · Implement the adopted mode
`thread_ranking.rank_threads` gains a court term behind `ATLAS_COURT_ENFORCE=off` (default), factor from A0. Meta carries the damp count (stamped_counts already serves the census — extend with `court_damped`). Tests: pure ranking tests freezing damp-off byte-equivalence + the damp ordering. Flip on only after A2.

### A2 · Two-night watch + flip
Enable on Fly, watch two mornings (top-40 entailed-share + thin doors vs A0's simulation). Matches simulation → stays on; deviates materially → off + artifact.

## Lever B — umbrella verdicts (the front-page lane gets judged)

### B1 · The umbrella court question
Extend `label_court.py` with a FAMILY question for umbrellas (~10-30 rows/night, valley-priced DeepSeek): "does this umbrella label honestly cover its children's labels+receipts?" → `label_status` on the umbrella row (entailed/partial/failed). Reuses the existing court plumbing/ledger; kill-switch `ATLAS_COURT_UMBRELLAS=off`.
**Pre-registered gate GB:** hand-check 10 umbrella verdicts (blind, receipts-first protocol) — ≥8/10 agreement before the cron flag flips on. ALW runner sync required.

### B2 · Serve it
Umbrella rows already ride the same serializers (`label_status` flows once written — verify `assemble_dynamic_thread` covers umbrellas; LabelReviewChip renders wherever threads render). The 10 unjudged front-page rows get verdicts within one cron cycle.

## Lever C — blobs confirmed by membership, not entropy

### C1 · Candidate-set calibration (env only)
Set `ATLAS_WALK_BLOB_ENTROPY_TAU=2.6` + `ATLAS_WALK_BLOB_INDEG_MIN=4` on Fly (WalkParams.from_env already reads them — verify names). Consumers checked by the calibration chip: the walk endpoint + story siblings; the over-merge detector does NOT consume blob_connector_flags (its own overmerge.py lane) — re-verify before setting.

### C2 · `is_blob` through the confirmer
`story.py`: for the ≤12 candidate siblings only, run `confirm_blob_candidates` (bounded member fetch, `_WALK_BLOB_MEMBERS_SQL` pattern) and set `is_blob` from CONFIRMED multimodality; entropy+indeg stays the cheap candidate filter. Budgeted: ≤12 topics × ≤200 members per request, off-connection, cached with the payload.
**Pre-registered gate GC:** on the finder-v2 G1 true-positive set (11 rows), confirmed-blob rate ≤3/11 (was 6/11) while dt-466 and the calibration sample's hand-labeled blobs stay flagged ≥7/9. **Kill:** if the confirmer can't separate on those witnesses, the chip keeps entropy flags AND gains a "candidate" qualifier in the tooltip — never silently better-looking.

## Order
A0 → C1 (parallel, both cheap) → C2 → B1 → A1 → GB hand-check + A2 watch → B2 verify. Story lens flip (`STORY_LENS_AUTO=true`) is NOT in this plan — it re-gates on a fresh NAV-LOSS run after A+B+C land.
