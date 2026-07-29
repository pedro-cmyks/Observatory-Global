# Blob-flagger calibration — `blob_entropy_tau` × `blob_indeg_min` sweep against a blind hand-labeled sample

**Date:** 2026-07-29 · **Harness:** `backend/scripts/measure_blob_flagger_calibration.py` (READ-ONLY) ·
**Raw artifact:** `2026-07-29-blob-flagger-calibration.json` ·
**Trigger:** finder-v2 G3 (`2026-07-29-sibling-finder-v2-measurement.md`) — `blob_connector_flags`
flags **626/1022 = 61.25%** of the active field at the shipped defaults (`tau=1.5`, `indeg_min=3`),
while the G2 rows showed an 80/60 flagged-share separation (false vs true neighbors).

> ## Verdict
> | question | answer |
> |---|---|
> | Does an operating point meet the pre-stated target (≤25% of field flagged, ≥70% precision on true blobs)? | **Nominally yes: `tau=2.6`, `indeg_min=4`** → 226/1022 = **22.1%** flagged · sample precision **0.78** (7/9) · recall **0.41** |
> | Is that precision statistically confirmable? | **No.** n=9 flagged sample rows → Wilson 95% **[0.45, 0.94]**. The point estimate clears 0.70; the CI does not. |
> | Is 2-hop category entropy a good topic-level blob discriminator? | **No — AUC 0.564** (blob vs clean, blind labels). In-degree alone does better (**0.702**); their product 0.751. |
> | Why did G3 see a real 80/60 separation then? | Different population. G3 measured flag share over **neighbor rows** (false vs true kin); this measures **topic-level blob-ness**. A flag correlates with sitting in a dense confusable *neighborhood* — not with the topic itself being a grab-bag. |
> | The structural blind spot | **8 of 10 blobs missed at the pick are within-category fusions** (Crime and Accidents ×4, Crime and Justice ×2, …). Category entropy is blind to same-category grab-bags **by construction** — and that is the dominant real blob class (femicide fusions, road-accident buckets, fraud dockets). |
> | Recommendation | Adopt (2.6, 4) as the **candidate-set calibration** (env-only, below) — it fixes the base rate and makes the confirmer affordable — but route the user-facing `is_blob` chip through `confirm_blob_candidates` (membership multimodality), which is the measured discriminator the spec already names. **Nothing changed in this session.** |

---

## 1. Setup

- **Field:** the exact population the story lens caches — `dynamic_topics` active, not umbrella,
  `centroid_vec` present → **1022 topics** (pulled read-only 2026-07-29; reproduces G3's 626/1022 =
  61.25% at current defaults exactly, so the harness is field-identical to the G3 measurement).
- **Features:** whitening + `build_knn_graph(k=6)` verbatim from `app.services` (the objects the
  endpoint calls). Per-node 2-hop category entropy and in-degree are threshold-independent, so each
  grid point is a pure 2-D threshold over precomputed features. Grid: tau 1.0–3.4 ×0.1, indeg_min
  {3,4,5,6,7,8,10,12} = 200 points.
- **Sample:** 40 topics = 8 entropy octiles × 5, seeded (`20260729`). Octiles are equal field mass →
  self-weighting; sample precision/recall estimate field precision/recall directly.
- **Blinding:** the judging worksheet carried ONLY id + label + up to 12 evidence headlines
  (`role='evidence'`, `engine_version='v1-compat'`, not quarantined, 7-day window — verbatim story.py
  scoping). Entropy/indeg/flag status lived in a separate meta file, not read until after all 40
  verdicts were written.
- **Judgment protocol (G2 reuse):** judged from **evidence headlines, not labels** (§4.1
  label↔evidence divergence). `blob` = members span ≥2 substantial distinct stories (a story with
  ≥~3 members counts as substantial; one stray in 12 does not) or no dominant story at all.
  `clean` = one event or one tight running story. `unsure` counts **against** the flagger.
- **Selection rule (frozen in the harness before judging):** among grid points with field flag rate
  ≤ 0.25 AND sample precision ≥ 0.70, maximize recall; ties → precision, then lower flag rate.

## 2. What the blind labels say about the field

| verdict | n | share |
|---|---|---|
| blob | 17 | 42.5% (Wilson 95% [0.29, 0.58]) |
| clean | 22 | 55.0% |
| unsure | 1 | 2.5% |

The field genuinely is badly fused — roughly **four in ten** active topics are grab-bags of ≥2
distinct stories. A 61% flag rate was over-firing, but not against a clean field. (Side observation,
same disease as finder-v2 §4: the sample caught the SW-Europe-wildfires story shredded into **three**
separate topics — dt-4019 German, dt-363 Ukrainian/Slavic, dt-5113 Arabic — each internally clean.)

## 3. Sweep result

Current defaults vs the rule's pick, on the same blind sample:

| point | field flagged | precision | recall |
|---|---|---|---|
| **current** `tau=1.5, indeg_min=3` | 626 = **61.25%** | 0.58 (14/24) [0.39–0.76] | 0.82 (14/17) |
| **pick** `tau=2.6, indeg_min=4` | 226 = **22.1%** | 0.78 (7/9) [0.45–0.94] | 0.41 (7/17) |

Feasible-set runners-up all sit at P=0.75/R=0.35 (e.g. `2.6/5`, `1.9/8`, `2.7/4` — full frontier in
the JSON). Best point **outside** the ≤25% constraint, for sensitivity: `tau=2.2, indeg_min=4` →
33.8% flagged, P=0.71, R=0.59 — the constraint costs ~0.18 recall.

## 4. The honest finding: the feature, not the threshold, is the ceiling

The task's premise ("the signal works, the threshold is wrong") is **half right**. The threshold IS
wrong (61% base rate). But re-thresholding cannot buy a good detector, because at the topic level
the feature barely separates:

| feature (blob vs clean, blind labels) | AUC |
|---|---|
| 2-hop category entropy | **0.564** |
| in-degree | **0.702** |
| entropy × log(1+indeg) | 0.751 |

- Blob entropy median 2.34 vs clean median 2.33 — the distributions sit on top of each other.
  In-degree (connector-ness) carries more topic-level signal than the entropy that was supposed to
  be the discriminator.
- **Misses at the pick are the worst real fusions:** dt-2018 (two fatal-accident stories fused,
  entropy **0.91** — both stories same category, so 2-hop entropy is *low*), dt-5000 (Spanish
  femicides fused, e=2.20, indeg 13), dt-2721 (sanctions bill + tariffs, e=2.34, indeg 16).
  8/10 misses are within-category fusions — invisible to category entropy by construction.
- **False positives at the pick are clean topics in noisy neighborhoods:** dt-2774 (Lake Como
  drowning, single event, e=3.04) and dt-6975 (Morant-Hitler row, single story, e=2.90).
- This **reconciles with G3's 80/60**: the flag genuinely correlates with *false-neighbor rows*
  because it measures the confusability of a topic's neighborhood — a property of the region the
  cosine walk is lost in, not of the topic. As a trail-brake correlate it carries signal; as a
  topic-level "grab-bag" chip it is close to a coin flip on entropy alone.

## 5. Consumers (checked before proposing anything)

`blob_connector_flags` callers (grep, this tree):

| caller | use | effect of (2.6, 4) |
|---|---|---|
| `app/routers/story.py:312` (story lens `/story/{id}/siblings`) | flags computed on the cached field, passed to `rank_siblings`; rows surface `is_blob` + `through_blob` → `storyLens.ts` ⚠ grab-bag chips. **No confirmer on this path** — the raw entropy flag reaches the UI. | chips drop ~61%→~22% of rows; walk penalties rarer → some sibling orderings shift. Lens ships DARK (`STORY_LENS_AUTO=false`), deep-link only — low blast radius. |
| `app/routers/dossier.py:1086` (`/dossier/walk`) | flags = CANDIDATES → bounded member-embedding fetch → `confirm_blob_candidates` (overmerge 2-means) gates the penalty; `is_blob`/`blob_basis` in payload. | candidate set 626→**226** — the confirmer becomes affordable over the full candidate set (it was the bounded-fetch bottleneck). |
| `app/services/story_siblings.py:83` (`rank_siblings`) | `BLOB_PENALTY` 0.5 on hops out of flagged nodes + `is_blob` field. | fewer penalized hops; acc_weights rise on affected trails. |
| `scripts/measure_sibling_finder_v2.py` | measurement only. | n/a |

**Over-merge detector coupling:** `overmerge.py` / `detect_overmerge` do **not** import the flagger —
the dependency is one-directional (the walk uses `overmerge.decide` as its confirmer). Re-thresholding
the entropy pass cannot touch the nightly over-merge lane. Both params already ride
`WalkParams.from_env()` (`story.py` cache build + `dossier.py:1075`), so the change is env-only.

## 6. Proposal (NOT applied — env or reviewed commit after this artifact)

```
ATLAS_WALK_BLOB_ENTROPY_TAU=2.6
ATLAS_WALK_BLOB_INDEG_MIN=4
```

equivalently `BLOB_ENTROPY_TAU 1.5 → 2.6`, `BLOB_INDEG_MIN 3 → 4` in `constellation_walk.py`
(defaults change also needs a pass over `test_constellation_walk.py`, whose synthetic fixtures assume
the current defaults).

Read this as **candidate-set calibration, not detector calibration**:

1. It meets the pre-stated base-rate target (22.1% ≤ 25%) and the precision target on point estimate
   (0.78 ≥ 0.70) — but n=9 means the precision claim is [0.45, 0.94]; treat 0.70+ as plausible, not
   established.
2. Recall on true blobs halves (0.82 → 0.41). Acceptable ONLY because the entropy pass is the cheap
   first pass, not the verdict: the walk's real discriminator (`confirm_blob_candidates` → membership
   multimodality) sits above it in the dossier path.
3. **The follow-up that actually fixes the chip** (separate chip, not this artifact): route the story
   lens's user-facing `is_blob` through the same confirmer the dossier walk already uses, and consider
   an in-degree-weighted score (`entropy × log(1+indeg)`, AUC 0.751) as the candidate rank if a
   bounded confirmer budget needs prioritizing. Within-category fusions need the multimodality signal
   — no category-entropy threshold can see them.

## Reproduction

```
set -a; . ~/AtlasLocalWorker/.env; set +a
cd backend
python -m scripts.measure_blob_flagger_calibration --pull    # field snapshot (read-only)
python -m scripts.measure_blob_flagger_calibration --prep    # features + sweep + blind worksheet
# hand-judge worksheet -> blob_calib_judgments.json
python -m scripts.measure_blob_flagger_calibration --report  # this artifact
```

Seed 20260729; grid, constraints and selection rule are frozen constants in the harness. The full
grid (200 points), per-topic features, verdicts and notes are in the JSON artifact.
