# Subject-Geography Inference — remeasure WITH NER places (#238 D), 2026-07-16

Third measurement in the 2026-07-16 series, same harness/definitions as the
baseline (`2026-07-16-inference-quality.md`) and the post-fix remeasure
(`2026-07-16-post-fix-remeasure.md`). This one measures the committed code
(person-proxy demotion + lexicon recall + **dominance cap**, `0a981e54`, plus
the place→country resolver + GeoNames gazetteer, `7f1a3750`/`21a7bf46`) with
the NER `places` hook **actually fed** — the first activation of the C-clean
block that was a no-op in both prior measurements.

**Window integrity:** the live front page (`/threads?hours=24&limit=40`,
pulled at run time) still serves the SAME 31 threads as
`snapshots-2026-07-16-places/threads_fresh.json`, receipts byte-identical on
spot-checked threads (dt-320/714/21, 24/24 receipts each) — so this is the
same controlled window as the baseline and post-fix measurements: same 31
threads, same 686 receipts, same baseline DeepSeek judgments.

**Places provenance (the heavy half, done before this measure):**
`backfill_places.py` annotated exactly the 686 distinct receipt signal ids
the front page serves — all 686 lacked `nlp_places` (routing: davlan-xlm 416 /
spacy-en 252 / wikineural 18; ledger = `backfill_ledger.json`). **270/686
receipts (39%) carry ≥1 extracted place.** This measure reads the places back
from the DB (source of truth), not the ledger.

## Headline before/after

| Metric | Baseline (pre-fix) | Post-fix as shipped | Post-fix + cap (sim → now committed) | **+ NER places (this measure)** |
|---|---|---|---|---|
| Precision of `verified` (judge same-or-superset) | 12/16 = 75.0% | 10/15 = 66.7% | 13/15 = 86.7% | **19/22 = 86.4%** |
| Recall strict (verified AND agreeing / judge-named) | 12/31 = 38.7% | 10/31 = 32.3% | 13/31 = 41.9% | **19/31 = 61.3%** |
| Recall lenient (verified at all / judge-named) | 16/31 = 51.6% | 15/31 = 48.4% | 15/31 = 48.4% | **22/31 = 71.0%** |
| Status verified / partial / unavailable | 16 / 8 / 7 | 15 / 11 / 5 | 15 / 11 / 5 | **22 / 9 / 0** |

All columns are scored against the SAME baseline judgments
(`snapshots-2026-07-16-postfix/baseline-judgments.json`) — judge-controlled.
Sanity: the no-places leg of this run (committed code, `places` absent)
reproduces the cap simulation **exactly** (13/15 = 86.7% / 13/31 = 41.9%,
`scored_noplaces_baseline_judge.json`) — the shipped dominance cap behaves as
the post-fix artifact predicted.

**Places buy +19.4pp strict recall over the capped code (+22.6pp over the
original baseline) at essentially unchanged precision (−0.3pp, one
impact-location case below).** Every thread now produces at least a
candidate: `unavailable` went 5 → 0.

## Fate of the 9 structural-miss threads (domestic stories that never name their country)

The baseline's dominant miss class (9/15 = 60% of misses, "unfixable by
lexicon"). With places:

| Thread | Baseline → with places | Detail |
|---|---|---|
| dt-21 IT cronaca (Riminese, never "Italia") | partial → **verified [IT], agree** | 10 receipts w/ places (Rimini-area toponyms → IT via gazetteer) |
| dt-2521 US domestic | unavailable → **verified [US], agree** | 21 receipts w/ places |
| dt-66 US domestic | unavailable → **verified [US], agree** | 13 receipts w/ places |
| dt-2458 US domestic | partial → **verified [US], agree** | 5 receipts w/ places |
| dt-1112 US domestic | unavailable → **verified [US], agree** | 10 receipts w/ places |
| dt-553 BR crime (g1.globo city-level) | unavailable → partial | BR 10 receipts via ner_place — but **1 outlet** (g1.globo); the ≥2-outlet bar correctly refuses single-outlet corroboration |
| dt-565 BR jobs (g1.globo) | unavailable → partial | Same: BR 7 receipts / 1 outlet |
| dt-2455 US Senate appointment | partial (unchanged) | Receipts yielded no resolvable US places (only a spurious RU 1/1 headline hit) |
| dt-245 AL protests | partial (unchanged) | Davlan on Albanian headlines extracted nothing resolvable; only a spurious AF 1/1 candidate |

**5/9 structural misses now verify, all judge-agreeing.** The 2 BR threads
are a corroboration honesty story, not a places failure — the places fired,
the single-outlet bar held (same class as dt-96 Côte d'Ivoire, below). The 2
genuinely unchanged threads are NER extraction misses, not resolver misses.

## Person-proxy regressions recovered

The post-fix demotion cost 4 judge-agreeing verifications (US/IT domestic
stories that say "Trump"/"Meloni", not "US"/"Italy"). Places recover half:

- dt-2369 Keystone Pipeline: partial → **verified [US], agree** (4 receipts w/ places).
- dt-2493 Daylight Saving bill: partial → **verified [US], agree** (2 receipts w/ places — exactly clears the bar).
- dt-372 "Trump Attacks Meloni": still partial — IT evidence remains 100%
  person-proxy (12 receipts, 0 non-proxy; no places extracted).
- dt-2536 US Mint coin: still partial — US 13/13 all "Trump"-proxy, 0 places.

This was the post-fix artifact's predicted refinement (ii): "NER places —
Keystone/DST/Mint receipts are full of US places". True for 2 of 3.

## New false verifies from places?

**Zero from gazetteer ambiguity.** Every ambiguous/spurious place resolution
observed lands as a 1-receipt/1-outlet candidate that the corroboration bar
holds: dt-287 IS(Iceland) 1/1, dt-245 AF 1/1, dt-1334's FX-roundup
country-mentions (GT/HN/MX/NI all 1/1 — the roundup **stays correctly
suppressed** with places, as at baseline and post-fix).

**One new precision loss, and it is an impact-location judgment, not a
resolver error:** dt-287 "Southern Europe Wildfires" (the Canada-smoke
thread) verified [CA] → [CA, **US**]; judge says CA. The US evidence is real
ner_place (9 receipts/9 outlets: Ohio/New York/Toronto-adjacent US cities in
"smoke chokes/air quality advisory" headlines) — the smoke's US impact is
arguably a co-subject, but under the strict same-or-superset rule it scores
as a disagreement. This is the sole delta between 86.7% (no places) and
86.4% (with places).

The other two disagreements are pre-existing and unchanged by places:
dt-438 [RU, UA] vs judge UA (actor-vs-location weighting, still the open
dt-438-class fix) and dt-90 [IR, FR] vs judge [IR, US] (Greek mixed cluster;
FR is genuinely frequent in those receipts).

## Secondary: fresh judge pass

A fresh DeepSeek pass (temp 0, same prompt) over the identical receipts was
also run (31 calls, `judgments.json`): against it, the with-places numbers
read 15/22 = 68.2% precision / 15/30 = 50.0% strict recall. The spread vs
the baseline-judgment scoring (86.4% vs 68.2% on identical predictions) is
the same judge variance the post-fix artifact documented (fresh passes
narrow 2-country answers: dt-644 [AR,GB]→[AR], dt-606 [ES,FR]→[], dt-387
[UA,RU]→ same but dt-457 [UA,RU]→[UA]…). The judge-controlled column is the
comparison of record; the fresh pass is a variance caveat that applies
equally to every measurement in this series.

## Caveats

- Same single front-page window as the whole series (31 threads, World Cup
  week); one run, no variance estimate on the thread sample.
- The backfill decoded HTML entities before NER (stored GDELT headlines
  carry `&#x...;`); the production fleet feeds headlines raw today — serving
  parity needs the same decode (or accepts a slightly lower place yield).
  Deviation documented in `backfill_places.py`.
- Places here are headline-NER only (that is what the fleet extracts);
  body-text NER would presumably lift dt-372/dt-2536-class threads.
- `rows_with_ge1_place` = 270/686 (39%) — coverage of the places lane on
  this window's receipts, after full backfill. On un-backfilled traffic the
  lane's reach is whatever the fleet has annotated (#184 throughput).

## Verdict on wider consumption

**The places lane works and should be plumbed into serving.** The serving
hook (`infer_receipt_subject_geography` C-clean block) already consumes
`places` when present — what is missing is the serving layer passing
`nlp_places` through with each receipt, plus fleet coverage (#184) so fresh
signals carry places without a manual backfill. Measured effect: strict
recall 41.9% → 61.3% with precision flat at ~86%, `unavailable` eliminated,
5/9 of the class the baseline called "unfixable by lexicon" fixed, 2/4
person-proxy regressions recovered, zero gazetteer false verifies.

For consumption beyond `why_now` (chips, ranking, C7 voice-asymmetry):
**closer, not yet unconditional.** At 86% precision with honest reason codes
this is now defensible for display surfaces (chips labeled as verified
subject geography). The two remaining systematic error classes both sit on
crisis threads — actor-vs-location (dt-438: aggressor verified alongside
attacked) and impact-location co-subjects (dt-287: smoke destination
verified alongside source) — so C7/ranking consumption should still wait for
actor-vs-location weighting (the un-built baseline fix #2), which this
window suggests is now the single highest-leverage remaining fix.

## Reproduction

- Harness: `snapshots-2026-07-16-places/run_places_remeasure.py`
  (synchronous; verifies window match, fetches `nlp_places` from DB, runs
  inference ±places, judges once per thread, replays baseline judgments).
  Run: `cd backend && .venv/bin/python .../run_places_remeasure.py`.
- Cost this run: 31 deepseek-chat calls ≈ $0.01 (< $0.05 budget).
- Snapshots (versioned, next to the ledger in
  `snapshots-2026-07-16-places/`): `threads_fresh.json` (window) ·
  `backfill_ledger.json` + `backfill_places.py` (heavy half) ·
  `judgments.json` (fresh judge) · `local_inference.json` (±places results
  per thread) · `scored.json` (**measurement of record**: with-places vs
  baseline judgments) · `scored_noplaces_baseline_judge.json` (cap-sim
  reproduction) · `scored_fresh_judge.json` (secondary) ·
  `metrics_summary.json`.
- Definitions identical to the series: agree = verified set ⊆ judge set
  (non-empty); precision over verified threads; recall over judge-named.
- Code under measure: committed `subject_geography.py` at `21a7bf46`
  (clean working tree).
