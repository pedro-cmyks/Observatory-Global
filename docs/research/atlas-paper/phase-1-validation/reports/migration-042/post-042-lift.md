# Migration 042 — measured lift on reviewed gold

Date: 2026-05-27
Status: empirical result (null lift on existing precision)

## Setup

- Restored 64 reviewed gold signals (batches 01 + 02, sample
  date 2026-05-25) from local archive
  `/Users/pedro/AtlasArchive` into in-memory state.
- Loaded two atlas_topics snapshots:
  - `backend/data/atlas_topics_snapshot_pre_042.json` — taxonomy as of
    migrations 040 + 041.
  - `backend/data/atlas_topics_snapshot_post_042.json` — taxonomy
    after migration 042 (423 new multilingual terms added).
- Re-classified each restored signal in-Python using the same scoring
  formula as `backfill_lexicon_topics.py`:
  `confidence = 0.55 + 0.10*min(lex_count,3) + 0.05*min(theme_hits,4) + cross_bonus`.
- Re-evaluated outcome per row using the same logic as the LLM
  baseline comparison: correct iff the new top-2 predictions match
  the gold judgement of the original Atlas assignment.

Script: `backend/scripts/restore_and_reclassify_reviewed.py`.

## Result

| Metric | Pre-042 | Post-042 | Delta |
|---|---:|---:|---:|
| Labeled (excludes 3 unclear) | 61 | 61 | 0 |
| Correct | 36 | 36 | 0 |
| Incorrect | 25 | 25 | 0 |
| Precision | 0.5902 | 0.5902 | 0 |
| Wilson 95% CI | [0.4650, 0.7046] | [0.4650, 0.7046] | unchanged |
| Prediction set changes | — | 0 / 61 | 0 |
| Signals hitting new mig-042 terms | — | 0 / 61 | 0 |

Migration 042 produced **zero measurable effect on the existing
reviewed gold sample**. Per-topic precision matches pre-042 exactly:

| Topic | n | Precision (pre + post) |
|---|---:|---:|
| `armed-conflict-escalation` | 15 | 66.67% |
| `corruption-investigation` | 12 | 83.33% |
| `currency-debt-stress` | 11 | 63.64% |
| `agriculture-crop-risk` | 8 | 25.00% |
| `constitutional-institutional-crisis` | 8 | 62.50% |
| `cyberattack-infrastructure` | 7 | 28.57% |

## Why the null result is informative

The 25 incorrect gold rows are false positives: Atlas v2 wrongly
assigned a topic. Adding more lexicon terms is an **additive** change.
It can only:

1. Catch additional headlines that previously matched nothing
   (recall lift on new signals).
2. Reorder top-2 ranking when a new term raises confidence for a
   different topic.

It cannot remove the original false-positive assignment because the
original matching terms (e.g., bare `harvest` for
agriculture-crop-risk, bare `data breach` for
cyberattack-infrastructure) are still in the lexicon. Precision on
already-bad assignments stays bad.

This validates the earlier root-cause audit finding
(`docs/research/topic-quality/2026-05-25-narrative-classification-root-cause-audit.md`)
that precision improvements require **removing** noisy terms, not
**adding** precise ones. Migrations 040 and 041 took that path; mig
042 took the recall-expansion path.

## Production recall lift (small but real)

To confirm migration 042 is not inert in production, a spot-check on
22 sampled new terms against the last 24h of `signals_v2`:

| Term | Lang | New matches in 24h |
|---|---|---:|
| `corruption probe` | en | 16 |
| `crisis migratoria` | es | 3 |
| `escalada de violencia` | es | 2 |
| `ofensiva militar` | es | 1 |
| (other 18 sampled terms) | — | 0 |

So the migration does add real new matches in production (mostly via
a single high-productivity EN term, with a thin multilingual tail).
But the scale is small: 22 new matches in 24h across the 22 sampled
terms (likely ~50-100 new matches if extrapolated to all 423 added
terms).

## Conclusions for Paper 1

1. **Vocab expansion alone does not improve precision.** It is a
   recall instrument. Precision improvements require negative
   filters or removal of broad existing terms.
2. **Most LLM-generated specific phrases never appear in real
   headlines.** Of 22 sample terms checked in 24h production data,
   18 had zero matches. Specific multi-word phrases (like
   `récolte menacée par la sécheresse`) score high on conceptual
   confidence but score zero on real-world appearance.
3. **Distillation strategy correction.** Future LLM-distillation
   passes should ask the model to propose **single high-precision
   words** observed in real headline patterns, not aspirational
   multi-word phrases. The current vocab mining prompt skews toward
   verbose phrasings.
4. **For Paper 1 results section.** Report mig 042 as a
   recall-oriented intervention with measured null effect on
   precision and small effect on recall. Pair with mig 040 + 041
   results that did move precision (by removing broad terms). The
   contrast is the methodology paper's most defensible distillation
   finding: **distillation strategy must target the failure mode
   (precision vs recall), and asking the LLM for "good terms" is not
   enough**.

## Next-session actions

1. Add a negative-filter migration (043) using the 150 negative
   monitors from `migration-042-proposal.md` as candidate
   noise-removal targets. Test precision lift on reviewed gold.
2. Generate a second vocab-mining round with a tighter prompt:
   "single 1-2 word terms only, must be plausible in news
   headlines". Compare productivity vs mig 042.
3. Expand benchmark sample beyond N=61 toward the N>=150 target
   stated in the methodology outline.
