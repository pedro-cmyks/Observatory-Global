# #184 — NER / entity data quality: diagnosis + plan (2026-07-14)

**Why this is the deep lever.** Three depth problems this session converged on
one root: the umbrella-by-actor (gap 2) can't reconnect the US-Iran war
fragments (the distinctive actors Araghchi/Khamenei/Hormuz aren't cleanly
extracted); the L1/L3 `who` dimension is `partial`; and the L2 sport
mis-typing leaks. All three need clean, corroborated actors — which the NER lane
does not currently supply at the served scale.

## Measured state (production, 2026-07-14)

| window | NER-processed (`nlp_processed_at`) | non-empty `nlp_persons` |
|---|---:|---:|
| 1 h | 7% | 7% |
| 24 h | **12%** | 24% |
| 168 h | 23% | 17% |

- **Throughput: NER 1,543/hr vs ingest 9,001/hr — a 7,458/hr deficit.** NER
  keeps up with ~17% of the inflow.
- The served 24-hour window would need ~6,560/hr just to stay level; NER runs at
  ~1.5k/hr, so it covers ~12% and never catches up.
- **Two different `persons` fields, and the consumers use the wrong one.**
  `signals_v2.persons` (GDELT-provided) is 100% populated but noisy — it is what
  produced the garbage in the gap-2 test (`cross ormuz`, ubiquitous
  `donald trump`, byline names). `signals_v2.nlp_persons` (the M1 NER lane) is
  the clean field but exists for only ~12-24% of the window.

## Root cause

- NER runs heavy transformers — `cardiffnlp/twitter-xlm-roberta` (sentiment) and
  `Davlan/xlm-roberta-base-ner-hrl` (NER) — load-run-unload each cycle to fit the
  shared 8 GB M1, which also runs the embed/clustering/daily crons.
- Priority is **not** the problem: `_priority_select_sql` already has a hot lane
  (recent 24 h, `created_at DESC`), so recent signals are NER'd first. The
  binding constraint is raw throughput — even a 100%-hot budget covers only ~17%
  of recent inflow at 1.5k/hr.
- NER reads the **headline only** (`_extract_entities(nlp, headline)`), so a
  story whose headline names a company/person but not the distinctive actor
  (the oblique-headline class) yields nothing usable even when it is processed.

## Consequence

At 12% served-window NER coverage, ~7 of 8 signals carry only GDELT persons.
Verified-subject corroboration (needs a typed person in ≥2 receipts from ≥2
outlets) rarely clears, so: umbrella-by-actor starves (gap 2), `who` stays
partial, and category typing can't lean on actors. Every other depth lever —
breadth, damp, selection, cited prose — already shipped; NER coverage is the
ceiling now.

## Plan (prioritized)

**P0 — use the clean field + concentrate it (cheap, immediate).**
1. Point the actor consumers at `nlp_persons` (typed, cleaner) with `persons`
   (GDELT) as a labeled fallback — umbrella `_ACTORS`, `verified_subjects_from_receipts`,
   the `who` lane. This alone raises precision where NER exists and would let the
   gap-2 mechanism (already built + tested) use clean actors on the covered 12%.
2. Raise `HOT_LANE_SHARE` so the served 24 h window approaches full coverage even
   while the total backlog stays behind — serve-window-first, backlog-later.

**P1 — 4× the throughput (the real fix).**
3. Split the NER path from sentiment: the actor lane needs NER, not tone. Running
   NER-only on the hot lane (sentiment on a slower cadence) recovers the biggest
   per-cycle cost.
4. Lighter/faster NER model (a GLiNER-class or distilled token-classifier) in
   place of the full `xlm-roberta-base-ner-hrl`, measured for the
   Araghchi/Khamenei/Hormuz-class recall.
5. If (3)+(4) don't reach ~6.5k/hr, a dedicated NER box off the shared 8 GB M1
   (the crons + embed already contend for it — measured this session at 400-min
   mutex holds).

**P2 — recall + quality.**
6. NER over the snippet/body, not just the headline — extracts the actor an
   oblique headline omits (this is what the whole `resolve_place_to_country` /
   NER-place slice was waiting on).
7. Entity-quality gate on the output (`_is_valid_person` exists) to drop the
   `cross ormuz`/byline class before it reaches consumers.

**Unlock.** Each point of served-window NER coverage feeds three shipped-but-
starved mechanisms at once — the gap-2 umbrella wiring, the `who` readiness, and
category typing. P0 is a code change landable now; P1 is the compute program that
actually moves the 12%.

## Correction after the P0.1 validation (measured, same day)

The validation was run and it **falsifies the umbrella-by-actor hypothesis**, and
narrows what #184 actually blocks:

- On the 25 **active served topics**, clean `nlp_persons` coverage is **92%**, not
  12% — active topics accumulate NER'd members over time. So the umbrella is **not**
  starved of actors.
- Re-running the gap-2 linkage against clean `nlp_persons` still produced a
  garbage megagroup at a loose centroid floor (Iran + Ukraine + Côte d'Ivoire
  merged) and **zero edges** at a tight floor. There is **no operating point** where
  the US-Iran war fragments group cleanly: they do **not** share distinctive
  actors (US-strikes and the Bahrain drone story carry different persons), so
  tightening kills every edge, and loosening chains unrelated topics.

**Conclusions.**
1. **Gap 2 is not an #184 problem.** Shared-person-actor is the wrong signal for
   reconnecting event fragments — the connector is the EVENT (the Hormuz
   chokepoint, temporal co-locality), not a shared byline. The committed
   `_shared_actor_edges` mechanism should be treated as a negative result, not a
   ready-to-wire fix. A workable gap-2 approach is event-level: an LLM same-event
   judge over candidate-adjacent fragments, or a place/chokepoint feature — a
   separate design.
2. **#184 stands, but scoped to `who` + typing, not the umbrella.** Those lanes
   need actors across ALL signals (not just accumulated active topics), where
   coverage really is ~12% and the 1.5k/hr-vs-9k/hr throughput deficit bites.

## Revised immediate next step

Drop the umbrella-by-actor. For #184's real beneficiaries (`who`, typing), the
lever is throughput (P1) — split NER from sentiment and measure a lighter NER
model toward ~6.5k/hr — plus P0.1 (consumers read `nlp_persons`, not GDELT
`persons`) and P2.6 (NER over the snippet/body) so the actor an oblique headline
omits is captured. Gap 2 returns as its own event-level design, not here.
