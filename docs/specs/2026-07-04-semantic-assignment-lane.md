# Semantic assignment lane — spec (2026-07-04, status: PROPOSED)

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
