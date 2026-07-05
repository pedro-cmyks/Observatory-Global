# Semantic assignment lane — spec (2026-07-04, status: SHIPPED — see §Execution)

## Execution status (2026-07-04 night, Day-2 session)

SHIPPED, with three measured deviations from the proposal below:

1. **e5 anchor-cosine FAILED calibration** (the §Threshold-discipline risk was
   real): pos/neg medians 0.789/0.765, AUC 0.735, cross-fire 3169/3186
   positives firing foreign anchors. Text-rich anchors do NOT fix the e5
   headline-space noise floor. → Lane runs in **OpenAI text-embedding-3-small
   space** (the same space that won the gate bake-off), embedding headlines at
   pass time (~$0.001/cycle at 1h windows); `signal_embeddings` (e5) is NOT
   used and the `atlas_topic_anchors` pgvector table was dropped unbuilt.
2. **Rule is ARGMAX + tau, not absolute cosine** (absolute cross-fires ~100%);
   and taus are **wild-calibrated** — the gold-corpus floor transfers badly
   (lexicon-pool base rate 40-80% vs wild ~0; gold taus admitted 29.6% of
   random corpus). tau_T = wild junk quantile (clearance <= 0.05%/topic),
   lane ON iff gold recall at that tau >= 0.10 → **24/30 lanes on**
   (`docs/research/semantic-lane/2026-07-04-tau-sem-wild.md`). Scripts:
   `calibrate_semantic_lane.py` (engines e5|openai), `sem_lane_wildcheck.py`,
   `calibrate_tau_wild.py`.
3. **method='embedding'** (mig-019 CHECK has no 'semantic'), lane identity =
   `model_version='sem-assign-v0'`.

Live results (first cycle, 6h window): 2.43% wild clearance, 357 candidates,
gate kept 65 (18.2% vs lexicon 32.4% — sem_assign_report.py is the ledger).
**Acceptance case hit: election-legitimacy lexicon kept 0/18; semantic lane
added 2 VERIFIED (Peru Sánchez-IACHR appeal 0.997, Armenia vote-annulment
court 0.994) and surfaced a literal India-SIR headline into the candidate
universe.** Cron: runner Step 2b (sem_assign_pass --write + gate --lane
semantic each 30-min cycle; flag ATLAS_SEM_LANE_ENABLED, config synced to
~/AtlasLocalWorker/config/). Caveat held honestly: gate features for the
lane carry matched_terms=0 + confidence=cosine (mild OOD) — keep reading the
per-lane keep-rates before trusting them as precision.

## Problem (measured)

Atlas-topic assignment is lexicon-only (`theme-hint-lex-v2`: lexicon terms +
per-topic GDELT hints, hints now pruned by mig 067). The gate arc exposed the
recall ceiling this leaves: genuinely on-topic stories that no lexicon term
matches never become candidates at all — the India-SIR class ("Opposition
seeks SIR suspension", "9M voters purged") scored 0.90+ under the gate when
sampled semantically, but 'SIR'/'special intensive revision' is in no lexicon,
so those signals were never assigned to election-legitimacy in the first
place. The lexicon defines the candidate universe; the gate can only grade
what it's given.

## Proposal

A SECOND candidate-generation lane, semantic, feeding the SAME gate:

1. **Anchor embeddings per atlas topic**: embed
   `"{label}. {candidate-v2 definition} {includes}"` with e5-base (the
   substrate model — signal vectors already exist in `signal_embeddings`).
   Cached in a small table (`atlas_topic_anchors`, 768-dim, rebuilt when the
   taxonomy text changes).
2. **Nightly pass** (M1, numpy, $0 inference): for embedded signals in the hot
   window, cosine(signal_vec, anchor_vec) ≥ τ_sem → INSERT assignment with
   `method='semantic'`, `model_version='sem-assign-v0'` (same PK family as
   lexicon rows; the two lanes coexist, dedup by (signal, topic)).
3. **Gate grades both lanes identically** — semantic candidates flow through
   the same scope-gate scoring + two-tier serving. No serving change at all;
   the lane only widens the candidate universe.

## Threshold discipline (measure-first)

- τ_sem must be MEASURED, not guessed: score the 5k gold corpus signals
  against their assigned topics' anchors; pick τ at a fixed candidate-
  precision floor (~60% — the gate does the precision work downstream, the
  lane only needs to beat the lexicon's candidate quality, measured this week
  at ~30% gate-keep).
- Known risk from the 2026-06-29 ablations: e5 headline-space similarity has
  a HIGH noise floor (centroid↔centroid p50 0.94). Anchors are TEXT-rich
  (definition+includes), not centroids — expect better separation, but verify
  on gold before any write.

## Acceptance

- Offline: on the gold corpus, the semantic lane recovers ≥N (target 15%+)
  of positives the lexicon lane misses, at candidate precision ≥ the floor.
- Online: election-legitimacy (the fixture case) gains assigned candidates
  containing India-SIR-class headlines; two-tier serving shows them under
  verified/extended after gate scoring.
- Ledger honesty: assignments carry `method='semantic'` so every consumer can
  distinguish lanes; a `sem_assign_report.py` prints per-topic added-candidate
  counts + gate keep-rates per lane.

## Sequencing

After the gold accumulator reaches its targets (~2 weeks) — the same gold
powers τ_sem calibration AND the gate retrain, one measurement session for
both. Est. build: 1 session (anchor table + nightly script + report), no
frontend.
