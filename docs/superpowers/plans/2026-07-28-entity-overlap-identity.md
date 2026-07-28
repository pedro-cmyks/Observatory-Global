# Entity-overlap identity — implementation plan

**STATUS: CLOSED at GO/NO-GO 0 (2026-07-29) — see the spec header for the verdict.**
Phases B–F are dead as designed. What survives the measurements: (a) the M0/M4 infrastructure
numbers (fingerprint build 14.8s, 146MB/30d) if a future non-transitive consumer wants them;
(b) the finding that DP-3 (`used_t` removal) should be re-examined UNDER THE EXISTING
label+cos gate — the shipping rule already halves witness fragmentation and the structural
one-cluster-per-night cap is now the visible remaining constraint; (c) day-over-day answer
persistence as the metric any successor must move.

**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` (read first —
measurements M0–M7, kill rules K1–K5, stages 0–5 are defined THERE; this plan sequences them).
**Baseline:** gold answer rate **7–14%** (n=14, two runs); GQ-05 story coverage **6.4%**;
fragments/event 33 (GQ-05) & 9 (Caspian); false-absorption witnesses topics 784 & 52.
**Added metric (2026-07-28 rerun finding):** **day-over-day answer persistence** — a gold query
answered on day N must stay answered on day N+1 while the story remains in-corpus (GQ-02 witness:
a 26-receipt thread on 07-27 became a Klopp-appointment thread on 07-28). Post-fix gold runs span
**≥2 consecutive days**.

## Rails (apply to every task)
- Measure before code; thresholds are frozen at go/no-go 0, never moved after.
- Every merge/attach carries a reason code + ledger row; kill-switch per stage; reversible.
- The falsifier: `detect_overmerge` demotes >281/night ⇒ revert the stage that moved it.
- Controller commits; subagents never `git add -A`; runners re-sync to ALW only at go-live.

---

## Phase A — Stage 0: measure (read-only, gates everything)

**T-A1** Build `backend/scripts/measure_evidence_fingerprint.py` with modes
`--coverage` (M0), `--sweep` (M1), `--false-density` (M2), `--retention` (M4),
`--judge-dryrun` (M6). M1+M2 emit ONE table (spec rule: no operating point chosen on recall
without its false-side number beside it). Witness families: Caspian 9, Berlin Pride 22,
GQ-05 33 (reconstructed per spec §2.5) + ≥3 fresh families found by the label-similarity rule.

**T-A2** Build `backend/scripts/calibrate_evidence_rarity.py` (M3): df distributions per lane
over ≥7 snapshots, `df_max`, the nlp_persons noise floor (hand-label 200 df=1 entities),
domain-lane discrimination, fit `w_E/w_U/w_H`.

**T-A3** Run M0–M4 + M6 → dated artifacts under `docs/research/recall-229/`.
**GO/NO-GO 0:** an operating point must satisfy K2 (largest merge component ≤2% of topics) AND
bring ≥2 of 3 witness families to ≤3 components. Freeze `(MERGE_TAU_COS, lane, rarity gate)` into
this plan by edit. NO-GO ⇒ escalate lanes per K3 or close the spec. *Seed candidate from the spec's
pre-measurement: `cos≥0.86 + ent≥1` (1 component on Berlin Pride, 2.7% false).*

## Phase B — Stage 1: fingerprints (write-only, gates nothing)

**T-B1** Migration 092: `cluster_evidence_fingerprints` + `topic_evidence_fingerprints`,
`reason_code`/`evidence` on members, the absorption ledger. Frozen `entity_dfs` at build time.
Follow the 082-style revoke convention for any client-readable table (and note the RLS audit
finding — new tables ship with RLS ON).

**T-B2** `backend/scripts/build_evidence_fingerprints.py`, wired into `run-scoped-snapshot.sh`
**immediately after the snapshot write** (before signals age out — the §2.4 evaporation curve is
the whole reason). Backfill the ~8 resolvable days. ALW re-sync required (runner edit).

**T-B3 GO/NO-GO 1:** coverage of new clusters ≥95% · build wall-clock in budget (§8) · zero
serving change · `detect_overmerge` baseline unmoved (nothing gates yet, so ANY movement = the
writer has a side effect).

## Phase C — Stage 2: DP-1 same-snapshot evidence merge (the days-scale win)

**T-C1** `merge_duplicates`: label-string gate → evidence gate, SAME-SNAPSHOT topics only
(evidence 97.5% available there), behind `ATLAS_IDENTITY_EVIDENCE_MERGE=off` default. Frozen
operating point from go/no-go 0. Reason codes + ledger from day one.
`labels_compatible(None,None)` ceases to matter here — evidence, not strings.

**T-C2** Tests: witness fixtures (the 9 Caspian labels as the canonical reconvergence case);
env-off ⇒ byte-identical decisions; env-on ⇒ Caspian ≤3 components on the fixture; a
false-construction pair (disjoint countries, dissimilar labels, no shared evidence) never merges.

**T-C3** Flip on in ALW, watch TWO nights. **GO/NO-GO 2:** fragments/event ≤3 on ≥2 witness
families IN PRODUCTION · K1 quiet both nights · K2 holds on the live merge graph ·
`merge.fingerprint_missing` published and falling. Then re-run the gold eval **two consecutive
days** (answer rate + the new persistence metric).

## Gated phases (tasks written only after their gate opens)
- **Phase D — Stage 3 (`used_t` removal + absorption guard):** opens on GO 2. Moves the primary
  metric; most able to manufacture black holes — lands only on a merge gate proven in prod.
  Gate: GQ-05 coverage ≥25% & rising, 0 new false absorptions, K1 quiet, K5.
- **Phase E — Stage 4 (anchor-evidence guard):** opens when M5 becomes measurable (≥14 nights of
  fingerprints + fresh false-witness set harvested from detect_overmerge demotions). If the guard
  cannot reject the absorptions without rejecting the true continuations, ship neither.
- **Phase F — Stage 5 (shadow A/B ≥7 nights → env flip):** the standing cutover pattern.

## Boundaries
Untouched: HDBSCAN/min_kept/precision gate, whitening, MATCH_THRESHOLD, detect_overmerge logic
(it must remain a valid control), serving, label court, umbrellas. Spec §7 is authoritative.
