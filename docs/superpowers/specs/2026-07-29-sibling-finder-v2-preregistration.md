# Sibling-finder v2 — pre-registration (gates frozen BEFORE any run)

**Date:** 2026-07-29 · **Status: PRE-REGISTERED, AWAITING GREENLIGHT (Pedro)**
**Trigger:** the Story Lens T11 gate NO-GO
(`docs/research/gold/2026-07-29-story-lens-navloss-check.md`). The lens MECHANISM
is complete and verified (synthesized sibling rows render with receipts); the
DATA is the blocker: the cos-only walk resolves onto false neighbors (Berlin
Pride's top sibling "Austrian Arrested for Fraud" at 0.853; 18/18 flagged
`is_blob` by the lens's own honesty machinery) while live same-event fragments
visible in the same panel are ABSENT from the neighborhood — argmax dispersion,
now user-visible. Spec §12's risk fired exactly as written.

## The claim under test

A candidate UNION — whitened-cos kNN ∪ rare-shared-entity ∪ country+time
proximity — with union-aware scoring can surface TRUE same-event siblings on the
current shredded field, where cos-only cannot. (This is the spec §6 union the v1
plan narrowed to walk-only; the narrowing is now measured as the gap.)

Ranking-with-receipts stays the frame: NOTHING merges, no transitive closure —
the K2 collapse class that killed these signals as merge gates cannot occur.
Bases already exist measured: rarity formula `0.30 + 0.68·norm_rarity`
(constellation_walk), entity DF machinery (dossier), country footprints
(story.py). ~80% reuse.

## Pre-registered gates (frozen now; movement after seeing results = invalid)

- **G1 (recall on witnesses):** for each witness family — Berlin Pride, Caspian,
  and ≥1 fresh family harvested at run time by the label-similarity rule — the
  v2 finder must place ≥3 TRUE same-event fragments (hand-verified against
  member receipts) in the top-8 siblings of at least one family anchor.
  Baseline: v1 places 0 (gate artifact).
- **G2 (false-neighbor rate):** hand-check the top-5 siblings of 10 random
  active anchors (the gate's protocol): ≤2/50 rows may be judged
  unrelated-story-presented-as-kin. Baseline: gate observed cross-domain false
  neighbors at the TOP of both flagships.
- **G3 (blob honesty, both directions):** re-measure `is_blob` incidence on v2
  output. If >50% of true-positive siblings still flag `is_blob`, the flagger is
  over-firing on the shredded field and needs its own calibration — REPORT, do
  not silently tune it to pass G1/G2.
- **K1 (kill):** if no operating point satisfies G1 AND G2 simultaneously, the
  finder is NOT shippable on this field — the identity layer must heal first
  (consolidation arc). Record and stop; do not ship a lens over false receipts.

## Method constraints

- Measure-first harness (read-only, M1) over the live field BEFORE touching
  story_siblings.py; the false side measured in the same pass as recall (the
  5-for-5 lesson).
- Frozen thresholds recorded in the harness artifact before scoring.
- Witness families reconstructed per the entity-overlap spec §2.5 protocol.
- No engine writes at any stage; the endpoint change (if GO) is additive to the
  candidate generation only — the Sibling contract and every lens surface are
  already built for it.

## Cost

M1 compute only (embeddings already stored; entity DF queries bounded). No paid
LLM in the measurement. Est. one session for harness+measurement, one for the
endpoint change if GO.
