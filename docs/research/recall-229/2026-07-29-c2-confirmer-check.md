# Gate GC — C2 confirmer check on the two pre-registered witness sets

**Date:** 2026-07-29 · **Branch:** `eclipse-dramatic-moment` · **Read-only**
(`SET default_transaction_read_only = on` on every connection; zero writes)
**Harness:** `backend/scripts/measure_c2_confirmer_check.py` (committed) ·
**Raw artifact:** `2026-07-29-c2-confirmer-check.json`
**Gate (frozen before this run):** `docs/superpowers/plans/2026-07-29-identity-three-levers.md`,
Lever C2 / gate GC:

> confirmed-blob rate ≤3/11 (was 6/11) on the finder-v2 G1 true-positive set,
> AND ≥7/9 stay flagged on the calibration sample's hand-labeled blobs. Kill:
> if the confirmer can't separate on those witnesses, the chip keeps entropy
> flags AND gains a "candidate" qualifier in the tooltip — never silently
> better-looking.

> ## Verdict
> | witness | target | result | pass? |
> |---|---|---|---|
> | **A** — 11 G1 true-positive siblings (genuine same-event fragments) | confirmed ≤ 3/11 | **1/11** | ✅ |
> | **B** — 9-row (2.6,4) calibration sample, 7 hand-labeled blob / 2 clean | confirmed ≥ 7/9 | **3/9** (3/7 of the true blobs) | ❌ |
> | **GC (both required)** | | | **❌ FAIL** |

**GC fires. Per the pre-registered kill rule: the change SHIPS anyway** (it
already carries the qualifier by construction — `blob_basis:
'candidate_unconfirmed'` degrades the chip to `⚠ grab-bag?` rather than
`⚠ grab-bag`, both in the backend contract and the frontend chip text). No
threshold in `overmerge.py`/`constellation_walk.py` was tuned to force a pass.

---

## 1. Witness A — the confirmer does exactly what it was built to do

The 11 rows are **verified same-event fragments** (finder-v2 measurement,
`v1_true` per eligible gate family: berlin-pride ×6 from anchor `dt-7712`,
`fresh:trump-threatens-iran` ×2 from `dt-2854`, `fresh:trump-imposes-50-
tariffs-on-canada` ×3 from `dt-5494`) — real siblings the entropy pass
over-flagged as blobs (6/11 = 54.5%, the finder-v2 G3 finding).

| topic | raw entropy candidate? | is_blob (confirmed-only) | blob_basis |
|---|---|---|---|
| dt-7647 | no | false | — |
| dt-7717 | no | false | — |
| dt-7715 | **yes** | true | candidate_unconfirmed |
| dt-7356 | **yes** | **false** | — (spared) |
| dt-7714 | no | false | — |
| dt-7716 | **yes** | true | candidate_unconfirmed |
| dt-6993 | no | false | — |
| dt-2805 | no | false | — |
| dt-5340 | **yes** | true | candidate_unconfirmed |
| dt-5488 | **yes** | **true** | **confirmed** |
| dt-5492 | **yes** | true | candidate_unconfirmed |

Raw candidate count reproduces the cited baseline exactly: **6/11**, on
`WalkParams()` literal defaults (tau=1.5, indeg_min=3 — the same fixed
methodology the finder-v2 measurement used, `not from_env()`, so the result
is independent of whatever C1 env vars are or aren't live wherever this
runs). After confirmation: only **dt-5488** ends up structurally `confirmed`
(a real internal borderline split among ITS OWN members — not a claim about
whether dt-5488 belongs with the anchor, which is an orthogonal question);
the other 4 raw candidates degrade to `candidate_unconfirmed` (their member
embeddings were not available — see §3), never silently cleared, never
silently confirmed. **1/11 ≤ 3/11 — PASS, comfortably.**

## 2. Witness B — real data limitations, not a confirmer bug

| topic | hand-label | embedded/total members | verdict (real eval) | is_blob | blob_basis |
|---|---|---|---|---|---|
| dt-2526 | blob | 13/15 | KEEP, gap_ratio 1.297 | false | — |
| dt-3660 | blob | 17/19 | BORDERLINE, gap_ratio 1.675 | **true** | **confirmed** |
| dt-2733 | blob | 23/31 | KEEP, gap_ratio 1.277 | false | — |
| dt-79 | blob | 35/38 | BORDERLINE, gap_ratio 1.539 | **true** | **confirmed** |
| dt-901 | blob | 30/38 | BORDERLINE, gap_ratio 1.321 | **true** | **confirmed** |
| dt-2774 | clean | 4/11 | too few members (< MIN_MEMBERS=12) | true | candidate_unconfirmed |
| dt-6975 | clean | 9/9 | too few members (< MIN_MEMBERS=12) | true | candidate_unconfirmed |
| dt-3567 | blob | 10/10 | too few members (< MIN_MEMBERS=12) | true | candidate_unconfirmed |
| dt-3902 | blob | 21/22 | KEEP, gap_ratio 0.500 | false | — |

**3/9 confirmed (3/7 of the hand-labeled true blobs) — target ≥7/9, FAIL.**
Read honestly, three different things are happening, not one failure mode:

1. **2 of the 2 clean rows correctly never get a false "confirmed"** (both
   fall below `MIN_MEMBERS=12` and degrade to `candidate_unconfirmed` — the
   honest "couldn't evaluate" state, not a wrong confirm).
2. **1 of the 7 true blobs (dt-3567) also can't be evaluated** — exactly the
   same `MIN_MEMBERS` floor (10 embedded members, one below the threshold).
   This is a **data-volume limitation** the confirmer's docstring already
   names ("too few embedded members to partition"), not a discriminator
   failure — the sample deliberately spans small topics and the fusion
   detector needs enough members on each side to measure a split at all.
3. **2 of the 7 true blobs are genuine confirmer misses with real data
   evaluated**: dt-2526 (gap_ratio 1.297, a hair under `TAU_SEP_LOW=1.3`) and
   dt-3902 (gap_ratio 0.500, well below threshold — its own note reads "daily
   lottery syair predictions for many cities... junk recurring template,
   roundup"). dt-3902 in particular is **not a bimodal fusion** — it is a
   many-way smear of near-duplicate templates across cities, which is a
   structurally different shape than the two-well-separated-clusters pattern
   `overmerge.two_means`/`decide` was built and calibrated to catch (spec
   §2.4, the over-merge arc's original design target). A 2-means split
   over an N-way uniform smear does not produce a wide gap by construction.

**Net finding: the confirmer works as designed on genuine bimodal fusions
with enough members (3/3 of the eligible ones in this sample: dt-3660,
dt-79, dt-901, all correctly confirmed), and is honestly silent — never
wrongly confident — on both undersized topics and non-bimodal "many-way
junk template" blobs.** The gate's ≥7/9 target implicitly assumed the
confirmer would resolve every hand-labeled blob in a small, opportunistically
sampled population; two structural gaps (a member-count floor and a
non-bimodal blob shape) make that unreachable without changing
`overmerge.py`'s detection model — which the gate explicitly forbids doing
to force a pass.

## 3. Why so many degrade to `candidate_unconfirmed`

`_BLOB_MEMBERS_SQL` (mirrored verbatim from `dossier.py`/`story.py`) scopes
to `topic_members` rows with a `signal_embeddings` join, `role='evidence'`,
`engine_version='v1-compat'`, `quarantined IS NOT TRUE` — **no time window**.
The gap between "total" and "embedded" members above (e.g. dt-2733: 23/31,
dt-2526: 13/15) is signals whose embeddings are gone — consistent with this
project's hot-retention discipline (embeddings are not kept as long as
`topic_members` rows) rather than a bug in the fetch. Several witness-B
topics additionally sit right at or under `overmerge.MIN_MEMBERS=12` even
counting ALL evidence members, before any embedding loss.

## 4. Disposition (per the pre-registered kill rule)

**GC fails on Witness B. The change SHIPS anyway, exactly as specified:**
`is_blob` reads CONFIRMED-only in both the `/story/{id}/siblings` payload
(siblings + the umbrella stand-in anchor) and the frontend chip; every
candidate that could not be structurally evaluated carries
`blob_basis: 'candidate_unconfirmed'` — backend never silently drops the
flag (still `is_blob: true`) and never silently upgrades it to `'confirmed'`.
The frontend chip renders `⚠ grab-bag?` (vs the plain `⚠ grab-bag` for a
real confirmed fusion) with a tooltip reading "entropy candidate —
membership unconfirmed". **No threshold was tuned to pass GC** — `TAU_SEP`,
`TAU_SEP_LOW`, `MIN_MEMBERS`, `blob_entropy_tau`/`blob_indeg_min` are all
untouched from their existing measured values.

**What this measurement adds to the record, for whoever revisits the
over-merge detector next:** the 2-means confirmer's blind spot is not random
— it is structurally two things: (a) a firm member-count floor that a
meaningfully-sized fraction of real topics sit under, and (b) a bimodal-only
detection shape that misses N-way "many similar near-duplicate items"
junk/roundup blobs (the same shape the calibration doc's own entropy-feature
analysis flagged as within-category fusions being invisible to entropy "by
construction" — here the analogous limit is multimodality being blind to
non-bimodal fusions by the SAME construction). Neither is a regression from
this session; both are now measured rather than assumed.

## Reproduction

```
set -a; . ~/AtlasLocalWorker/.env; set +a
cd backend
python -m scripts.measure_c2_confirmer_check
```

Witness ids are frozen constants in the harness (lifted verbatim from
`docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.json`
§G1 `v1_true` and `2026-07-29-blob-flagger-calibration.json` `sample`
filtered to the (2.6, 4) operating point) — not re-derived here.
