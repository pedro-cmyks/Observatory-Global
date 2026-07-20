# M4 over-merge blob detector — precision fix, measured audit, court impact

**Date:** 2026-07-20 · **Run:** `m4-20260720-s42` · **Engine:** `v1-compat`
(serving default) · **Artifact:** `docs/research/overmerge/2026-07-20-overmerge-audit.json`
· **Commits:** `06b110ee` (country-dominant veto), `93005c9b` (judge gates both bands)

## 0. What this is

The 2026-07-20 merge sprint drove label-court failure 47.9% → 24.3% by collapsing
duplicate identities, but left a residual of **OVER-MERGE blob-topics** that fuse
2+ distinct stories under a vague umbrella label ("Diverse Local Incidents Across
Regions", "Multiple Global Incidents: Deaths in Iraq, Peru, Mexico"). They evade
every existing guard: the **label court** passes them (a vague label trivially
entails a diverse set), **flag_junk_topics** passes them (each member is a real
news item), and the **M2 radial floor** passes them (the centroid falls *between*
the sub-clusters). The signal that catches them is **membership multimodality** —
2-means over the member embeddings; a topic that splits into two well-separated
sub-clusters of substantial size is a fusion.

The detector (`app/services/overmerge.py` + `scripts/detect_overmerge.py`) was
built read-only. Verify then found it at **~54% precision on demotes** (bar ~85%).
This document records the minimal fix, the re-measured audit on live prod, the
reconciliation against the relabel-ledger vague-blob set, and the predicted court
impact.

## 1. The precision bug and the fix

**Root cause (measured).** The false positives were **~all single-country topics**
— dt-3504 Texas floods, dt-3681 Iran Hormuz, dt-514 Venezuela earthquake, dt-2873
German nursing reform, dt-3608 UK cabinet. The shared-actor veto (meant to spare a
mega-story whose sub-aspects share actors) computed a Jaccard over a **combined
country+person set** and was **person-swamped**: two halves of a single-country
story share the one country token, but each item names different people, so the
many distinct person tokens diluted the intersection below `tau_overlap=0.5`. The
story read as "distinct actors" and the demote fired. Confirmed on prod: the 8
named false positives are all `distinct_countries = 1` with high person density
(e.g. dt-3504 = 13/14 members carry persons), and all 169 baseline demotes had
`entity_overlap < 0.5`.

**Fix 1 — country-dominant veto** (`06b110ee`, `country_dominant_overlap`). Score
the country Jaccard and the person Jaccard **separately** and take the **max**.
Same-country halves → country Jaccard 1.0 → veto → KEEP. A genuine cross-country
fusion (Peru vs Ukraine) → 0 → demote proceeds. A single common wire-service person
keeps the person Jaccard low, so it never spuriously vetoes a real fusion. `decide`
contract untouched; 6 new pure tests.

Effect (no judge): **169 → 58 structural demotes**; 111 single-country FPs flipped
to KEEP. But hand-labelling the 58 exposed a second FP class the country signal
*cannot* reach: a single **global** story split by outlet-country/language — Sam
Neill's death across AU/NZ, one Kyiv strike reported RU/UA/TH, the ICC lawsuit
across US/IL. The outlet countries genuinely differ across the split, so
country_jaccard = 0 and the demote still fired.

**Fix 2 — the judge gates both bands** (`93005c9b`, `apply_judge_verdict`). The
structural+country stage produces a **candidate** set (borderline ∪ demote); the
DeepSeek "one story or two?" judge is the precision **gate**. A candidate becomes a
real demote *only* on a positive `two_stories` confirmation; `one_story` or an
unavailable/unparseable call KEEPS (precision-first — never demote a real story on
the absence of a positive confirmation). This is exactly what catches the
cross-country-same-story residual: shown the two sides' headlines, the judge
returns `one_story`. **`--judge` is therefore required for a precision-safe demote
set** — without it, "demote" is an unconfirmed structural candidate.

49 pure tests green (`tests/test_overmerge.py`, `tests/test_detect_overmerge.py`).

## 2. Measured audit (live prod, judge-gated)

Population: **1,832** active non-umbrella non-junk topics (1,435 eligible ≥12
members). Taus: `tau_sep=1.8`, `tau_sep_low=1.3`, `tau_bal=0.20`, `tau_overlap=0.5`,
`min_members=12`, seed 42.

| stage | keep | borderline | demote |
|---|---|---|---|
| baseline (swamped `set_overlap`) | 1,462 | 201 | **169** (~54% precision) |
| + country-dominant veto | 1,729 | 45 | 58 |
| + judge gates both bands (final) | 1,743 | 0 | **89** |

The judge was called on **103** candidates (58 structural-demote + 45 borderline);
it confirmed **89** as two_stories and **rescued 14** as one_story. The 14 rescues
are precisely the residual FP class: Sam Neill (dt-3219/3234), Tate Brothers
(dt-3596), Ukrainian↔Russian strikes (dt-2727), India-condemns-Hormuz (dt-2614),
World Cup results (dt-537), Russian Black Sea shipping (dt-827). `unavailable_keep = 0`
(judge healthy this run).

**Multimodality distribution (1,435 eligible, gap_ratio = separation / intra_spread):**
p10 0.55 · p25 0.81 · p50 **1.20** · p75 1.69 · p90 2.38 · p95 2.93 · p99 4.13.
balance p50 0.33. mean_silhouette p50 0.25 / p99 0.60. The e5 gap_ratio is compressed
(most topics sit ~1.2), which is why `tau_sep=1.8` sits above the median and the raw
structural flag (`gap≥1.8 AND balance≥0.20`) fires on only 234 of 1,832 before the
veto and judge cut it to 89.

**Precision (hand-labelled all 89 confirmed demotes against their sub-cluster
headlines): ≈ 90–93%** (83–85 genuine two-story fusions). Representative TP: dt-244
Novosibirsk quake ∥ Venezuela quake; dt-2967 Ukraine defmin resigns ∥ Spahn resigns;
dt-2881 Brussels construction fire ∥ VW layoffs; dt-1416 Bangkok pub fire ∥ Ukraine
strikes; dt-424 Brussels fire ∥ China landslide; dt-79 celebrity son's death ∥
Milei-Kirchner; dt-892 two distinct Spanish legal cases. The ~6 borderline/possible-FP:
dt-1711 (UK/Spain/Israel heatwaves — distinct national events or one crisis?),
dt-2596 (Pakistan gold + rupee — one market roundup?), dt-534/dt-552 (distinct World
Cup matches within one tournament), dt-1723 (storms), dt-1221 (Vox internal politics).
Even counting all 6 as FP → 83/89 = **93.3%**, comfortably above the 85% bar.

**Verdict: PASS.** The fixed detector is precision-safe when run with `--judge`.

## 3. Reconciliation vs the relabel-ledger vague-blob set

Cross-ref against `docs/research/label-court/2026-07-20-relabel-ledger.jsonl`,
keyword-matching the "Mixed / Diverse / Multiple / Roundup / across regions / …"
new-labels (a deliberately **coarse** proxy — never used to decide, only to compare).

- **149** vague-labeled topics in the ledger; **127** still active + scanned.
- Of the 127: detector **FLAGS 10**, **KEEPS 117**.
- The detector ALSO flags **79 demotes that are NOT vague-labeled** — structural
  fusions the sprint's label-based relabel never touched (e.g. dt-666 "US Immigration
  Police Body Cameras", label garbage, content = Iran resistance ∥ Trump/Netanyahu
  Lebanon; dt-2930 "Andy Burnham UK PM", content = UK PM ∥ Ukraine PM).

**Why only 10 of 127?** The keyword proxy is noisy; the detector is deliberately
more precise. The 117 kept-vague break down (by keep reason):

| kept-vague reason | count | meaning |
|---|---|---|
| unimodal (`gap<1.3`) | 57 | one coherent story wearing a vague label = **keyword false positive** |
| shared actors (country veto) | 19 | same-country roundup **spared, precision-first** |
| below min_members (`<12`) | 23 | too small to fuse two substantial stories |
| unbalanced split | 18 | second sub-cluster is a sliver of strays |

Spot-check of the "unimodal" kept-vague confirms they are genuinely one story:
dt-2571 "Deadly Landslides… Multiple" = both sub-clusters the *same* Nagaland Mon
landslide; dt-2585 "African election updates across multiple regions" = both sides
one India-election/SIR cluster (label is simply wrong). **75 of the 117 kept-vague
are single-country.**

**Honest recall tradeoff.** The country veto's 19 "shared actors" keeps include
genuine **same-country roundups** (the mission's own "Indonesian News Roundup:
Multiple Events" class). Precision-first hard-keeps them: a wrongly-demoted real
story is worse than a known blob the next nightly can re-split. This is a real
recall sacrifice against the keyword set, made deliberately to clear the 85%
precision bar. **Future refinement** (not this pass): route same-country
wide-gap-balanced topics to the *judge* (borderline) instead of a hard KEEP, to
recover the same-country-roundup recall without spending precision.

Net: the detector finds a **largely disjoint** population from the keyword — 79 new
structural fusions the relabel missed, 10 keyword-vague confirmed — and spares 117
that are mostly one-story-with-a-bad-label (57) or single-country roundups (19).

## 4. Predicted label-court impact

Court over the 1,832 active non-umbrella non-junk topics **before** demoting:
entailed 760 · partial 700 · **failed 372 (20.3%)**.

The 89 demotes carry label_status: **partial 37 · entailed 25 · failed 27**. So
**62 of the 89 are court-PASSING** — they show green (entailed/partial) via a vague
label but are structural fusions. This is the thesis quantified: **the label court
cannot see 62 over-merges**; only the multimodality signal catches them.

Demoting all 89 (active → candidate) removes them from the active denominator:

| | active | failed | failed % |
|---|---|---|---|
| before | 1,832 | 372 | **20.3%** |
| after demoting 89 | 1,743 | 345 | **19.8%** |

The failed rate barely moves (−0.5 pp) because the detector removes **more passing
(62) than failing (27)** topics — as it should. The detector's value is **not**
lowering failed% (the court already scores these green); it is **removing 62
court-invisible fusions** from serving that the court, junk classifier, and M2 floor
all miss.

## 5. Reversal

Everything is reversible (demote = `active → candidate`, never delete; a split-back
next nightly resurrects the sub-stories). The write path is guarded (nightly +
heavy-lock) and writes a per-run ledger for exact undo:

```
python -m scripts.detect_overmerge --revert m4-20260720-s42
```

## 6. Status / next

- **Audit: PASS at ~93% precision (judge-gated).** This run was **read-only** — no
  DB writes. `--write` (the demote path) is implemented but GATED and is the next
  step, and MUST run with `--judge` (structural candidates alone are ~54% and unsafe).
- Durable stickiness against re-promotion (a `dynamic_topics` over-merge marker, like
  `is_junk`) is the follow-up so a demoted blob does not re-promote next nightly.
- Recall refinement: same-country roundups → judge instead of hard-keep (see §3).
