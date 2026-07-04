# The 3-day route (2026-07-04 night) — plan while the strong model lasts

Pedro's framing: the strong model is available ~3 more days; prepare the full
route so nothing depends on it afterward. Three questions answered with data:

## Q1 — "¿La información pasada no sirve para pruebas?" → SÍ SIRVE, y cambia el plan

Measured tonight:
- Hot DB (`signals_v2`): only **7 days** (retention trims hard; jun-28→jul-05).
- **Archive**: `/Volumes/Ext/Atlas/Archive` — signals partitioned
  `year=/month=/day=/source_family=` from **~May 19** + 167 incremental
  batches (~3.9M rows represented). Raw headlines, NO assignments/scores.
- Hot decision-band for election-legitimacy: 39 rows → the "wait 2 weeks for
  the accumulator" estimate was actually OPTIMISTIC for thin topics.

**Conclusion: the archive is the gold mine.** ~6-7 weeks of headlines covering
the whole Peru electoral arc (June), sanctions cycles, agriculture season —
thousands of hard-topic candidates. Mining it compresses "2 weeks of
accumulator" into ~1 day of compute+API:

`archive_gold_miner.py` (to build, Day 1):
1. Stream archive partitions (jsonl) → headline + lang + country.
2. Apply the lexicon matcher offline (atlas_topics lexicons from prod; pure
   substring matching — same rule as theme-hint-lex-v2, no DB writes).
3. Sample per hard topic (stratified by matched-term count; target 400-600
   per topic), dedup vs everything ever labeled.
4. Label with the boundary-wired annotators (candidate-v2 includes/excludes,
   DeepSeek + gpt-4o-mini, unanimity) — ~$3-6 total.
5. Merge into the accumulated corpus → **200+ positives/topic within Day 1-2.**
Caveat logged honestly: archive rows lack gate scores → stratify by lexicon
evidence instead (fine — labels don't depend on scores); distribution is
May-June (the frozen 5k corpus is May-28 anyway, same era).

## Q2 — F3 status with current data

`unified-v2` recurring build: **ALIVE** — 8,110 members, 77 topics, newest
build tonight 22:50. The engine runs; F4 (serving cutover) is what's parked.
Current data is thin post-collapse (47 bootstrap-restored actives; tonight's
snapshots re-add persistence) — F3 itself needs nothing from us.

## Q3 — The route

**Day 1 (next session, strong model): GOLD BLITZ.**
- Build + run `archive_gold_miner.py` (above). Validate label quality on a
  50-row eyeball. Target: every hard topic ≥200 positives.
- Nightly accumulator keeps running on top (live-fresh complement).

**Day 2 (strong model): THE ONE ENGINE SESSION** — everything today's work
converged toward, now unblocked by Day-1 gold:
1. Gate retrain with **variance-aware calibration** (bootstrap CI-lower
   operating point per topic; deploy only if hard-topic recall improves at
   held precision — the round-1 doc's deploy gate).
2. **τ_sem calibration + semantic assignment lane** (spec
   `2026-07-04-semantic-assignment-lane.md`) — same gold, same session.
3. **F4 prep**: the new-topic labeling pass (§6 step 5) + read-path
   parametrization, gated on the same gold. Flip only if the A/B holds.
4. Root-cause the identity-collapse (why resurrection didn't centroid-match)
   — fold into the F4 work (v2's design is less identity-brittle).

**Day 3 (strong model): VERIFY + HANDOFF.**
- Browser-verify every surface against the retrained engine (the eval
  fixture: election-legitimacy detail should show a real verified set).
- Write `docs/state/handoff-playbooks.md`: mechanical runbooks a smaller
  model (or Codex headless) can execute without judgment calls — accumulator
  monitoring, retrain-rerun recipe, threshold re-emit, deploy commands,
  reversal paths. Everything judgment-heavy lands in Days 1-2.

**After the strong model (small-model-safe backlog):**
- #247 C1/C2 (panel-header/badge consolidation — specs already written).
- #236 mobile: universe finger-nav pass (spec'd expectations, mechanical CSS/
  gesture work). Label bug chip (task_50ac0d82) if not done.
- Weekly telemetry read (2026-07-11) — recipe in the telemetry doc.
- Watchdog/cron monitoring — freshness watchdog already automates recovery.

## Open-item inventory (what remains, one line each)

- Engine: gate retrain @200pos · semantic lane · F4 cutover+labeling ·
  identity-continuity root-cause · #229 clustering recall (structural) ·
  #204 typer-prompt A/B + 2 hazard categories (κ phase).
- Product: #247 C1/C2 · #236 mobile (universe gestures) · #233 draggable
  panels · Workbench Phase 3 (report from pins) · #217 credibility tiers ·
  #161 DOC 2.0 enrichment.
- Ops: dev-session telemetry tagging · #243 checklist leftovers · #241
  HNSW insert bottleneck.
- Paper: P1 gets the variance-finding + two-tier §; P7 gets the eval; PR3
  ledger already reconciled.
