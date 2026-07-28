# Gold eval re-run (post label restore) vs baseline — the confounder hypothesis is REFUTED

**Runs:** 2026-07-27 (labels 100% NULL all eval week) vs 2026-07-28 (labels 0% NULL,
precondition verified before firing). Same instrument, same gold set, same judge chain.

## Headline

| | 07-27 | 07-28 |
|---|---|---|
| Answer rate (roadmap metric) | **14%** (2/14) | **7%** (1/14) |
| Controls | 6/6 pass | 6/6 pass |

**Restoring labels did NOT raise the answer rate.** The "14% is a floor because merging was
disabled" hypothesis is refuted for the answer rate: with a fully-labeled snapshot the
number moved DOWN one query. At n=14 each query is ±7pp, so 14%→7% is within noise — the
honest statement is **the steady-state answer rate is 7–14%**, and the label blackout was
not the dominant confounder.

## What actually moved (per-query)

| Query | 27→28 | What happened |
|---|---|---|
| GQ-02 Berlin Pride | **2→0** | Yesterday: a thread with 26 on-topic receipts. Today: the served thread is a *Klopp coaching appointment*. The corpus control proves the story is STILL in the corpus (88 `berlin` rows, 17 on-topic, 16 sources). **The correct thread existed and vanished overnight.** |
| GQ-09 Nicaragua | 1→0 | Served thread drifted to Iran conflict |
| GQ-10 / GQ-11 | 0→1 | Honest floors improved (fresh labels let adjacency get flagged) |
| GQ-12 Caspian | 0→1 | Adjacent bucket now honestly flagged |
| GQ-13 / GQ-19 | 1→0 | Off-topic threads served / judge variance |

## The new finding: INSTABILITY is a failure mode of its own

GQ-02 is the loudest single data point either run has produced: **an answer that existed on
day N was gone on day N+1**, with the story still in the corpus. That is the identity
layer's nightly churn (re-founding + shredding) surfacing directly in the primary metric.
The engine does not only fail to FORM the right threads — it fails to KEEP them.

This sharpens the case for the entity-overlap identity work
(`docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md`): its success
metrics should add **day-over-day answer persistence** — a gold query answered on day N
must stay answered on day N+1 while the story remains in-corpus.

## Instrument notes (logged, not fixed — thresholds do not move post-hoc)
- K1 as pre-registered (`mean(controls) >= 1.0 => VOID`) contradicts §2, where a level-1
  honest floor is a control PASS: a run where all six controls behave *correctly* would be
  voided. Computed as written; flagged for rubric v2.
- The corpus-control probes under-count when the remaining query tokens are generic verbs.

## Baseline going forward
The band **7–14% (n=14)** is the pre-fix baseline for the entity-overlap work, with GQ-02's
disappearance as the named instability witness. Post-fix measurement must run on ≥2
consecutive days to capture persistence, not just a single-day rate.
