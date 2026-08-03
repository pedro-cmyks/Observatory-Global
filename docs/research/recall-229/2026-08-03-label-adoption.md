# Label adoption at labeling-time — the 9th pre-registered gate

**Generated:** 2026-08-03 · read-only, no prod write
**Harness:** `backend/scripts/measure_label_adoption.py` (extends the 7th+8th harnesses, both
untouched; rules imported)
**Artifacts:** `2026-08-03-label-adoption.json` (all transcripts: 18,023 adoption decisions,
60 precision judgments, 12 landing judgments) · pre-registration frozen before any build:
`docs/superpowers/specs/2026-08-03-label-adoption-preregistration.md`
**Runtime:** adopt pass ~105 min (18,023 DeepSeek temp-0 decisions, concurrency 6,
0 API errors, disk-cached/resumable) + measure 570s + judge ~4 min; `taskpolicy -b`
throughout, zero memory-pressure pauses.

**Mechanism under test:** when the labeller labels a snapshot cluster and a nearby ELIGIBLE
topic exists (cos ≥ TAU_ADOPT = MATCH_THRESHOLD 0.88, frozen pre-run), the SAME labeling call
decides ADOPT (inherit the topic's label verbatim) vs NEW. Blob-confirmed / court-failed /
junk topics — and umbrellas, a pre-run extension motivated by the 8th §6's blob-corruption
evidence — are NEVER offered. Adopted same-story pairs become string-identical, so
consolidation and landing stop failing on re-phrasing. Production cost: zero extra calls
(§7). Simulation cost: one-time.

---

## VERDICT: **KILL** — three gates fired; the mechanism worked exactly where designed, and imported the pool's disease everywhere else

| gate | bar (frozen) | measured | verdict |
|---|---|---|---|
| **G-ADOPCION** (primary-1) | false-adoption ≤ 5% on ≥60 judged | **32/60 = 53.3%** | **FAIL → KILL** |
| **G-BLOB-ADOPCION** | 0 adoptions from excluded topics | **0** (verified from ledger vs fresh query) | **PASS** |
| **G-FALSE-BLOCK** | < 20% on known-same-story pairs (cos ≥ 0.99) | **16.4%** — first pass in the program (27.5 → 21.4 → **16.4**) | **PASS** |
| **G-FOUNDING** | B-p8-adopted foundings ≤ 15% of decidable picks | **32.8%** (4,009/12,231; was 41.7%) | **FAIL → KILL** |
| **G-LANDING** (primary-2) | ≥ ⌈⅔·6⌉ = 4 AND strictly > production | **B-p8-adopted 4/6 · production-on-adopted-feed 3/6** | **PASS** |
| **G-K2** (adopted field) | ≥ 14/15 nights ≤ 2% | **11/15** (07-01 2.19% · 07-06 2.02% · 07-09 2.20% · 07-19 2.97%) | **FAIL → KILL** |
| **G-784** (adopted field) | 0 | **0** | **PASS** |
| **G-FALSE** (adopted field) | 0/1200 per night | **0/1200 every night** | **PASS** |
| **G-COSTO** | production prompt published, zero extra calls | §7 | **PASS** |

## 1 · The adoption pass

18,023 cluster-with-candidate tasks over the 15 frozen nights (of 18,023 labelled clusters —
essentially every cluster has an eligible neighbor ≥ 0.88 in today's pool). **ADOPT
9,033 = 50.1%.** Eligibility filter live and consequential: **2,894 of 7,805 pool topics
excluded** (1,650 label-court-failed±, 1,331 junk±, 114 umbrellas, 28 blob-confirmed — the
ledger's exact overlap breakdown is in the JSON). Evidence caveat, stated per decision in the
ledger: only 12,403/145,805 sample headlines survive retention, so **16,361/18,023 decisions
ran on the cluster's historical label** as its content summary (production would always have
the headlines — it IS the labeling call; the simulated adopter is working evidence-poorer
than the real one would).

## 2 · Fidelity — reproduced before any gate was read

Run-5 graph rows exact 15/15 (original labels) · loader equivalence 17,827/0 · single-night
downstream 0.9296 (within 2pp of 93.81%) · **B-p8-original reproduces the 8th gate EXACTLY:
5,205 blocked, drift 0.00%** — three harness generations now agree byte-for-byte on the
shared arm.

## 3 · G-ADOPCION — the primary kill, decomposed

60 adoptions sampled (seed 42), judged quote-gated (3 of the 32 counted-false are
conservative ungrounded-after-retry counts), every judgment read by hand. The decomposition
is the finding:

| class | sampled | judged FALSE | what the false ones are |
|---|---|---|---|
| **identical-label** (orig == adopted; the string never changed) | 31 | **12 (39%)** | pure POOL ROT surfaced: the judge condemns the *topic*, not the adoption — 'Seattle Food Festival Shooting' adopting from a same-labeled topic whose receipts mix Gaza strikes; 'Vegetable Recipes' from a topic holding Sophia-Loren anecdotes; 'Ukraine Refuses Bodies in Kostiantynivka' from a topic holding Ceuta migration |
| **changed-label** (a real string unification) | 29 | **20 (69%)** | genuine gluing: granularity ('Doritos Chilli Heatwave Recall' ← 'Product Recalls in Canada'; 'World Cup Round-of-16' ← 'Final Preview'; 'Suspected H5 in NSW' ← Australia-wide H5N1) and outright cross-event ('Chile Severe Storm' ← **'Wildfires in France and Spain'**; 'Armenia Political and Economic Unrest' ← **'US-Iran Military Escalation'**; 'Hungary Closing Door on Russia' ← 'Estonia Russia Border Queues') |

Even the most lenient human re-read (discounting identical-label rot-condemnations and the
judge's strictest granularity calls, e.g. 'US Strikes on Iran' ← 'US Strikes Iran Seventh
Night') leaves ~15–18 clearly-false of 60 — the 5% bar is missed by 5–10× under every
reading. **The adopter says "same story" far too easily on label-level evidence, and at
cos ≥ 0.88 the candidate is frequently a different disaster in a different hemisphere.** The
black-hole-seed the bar exists to prevent is exactly what 69% of changed-label adoptions
would plant.

The identical-label figure deserves its own sentence: **39% of no-op adoptions were
condemned because the nearest healthy-looking topic's receipts do not match its own label.**
That is a new, cheap pool-health instrument (adoption-condemnation rate), measured on
eligibility-filtered topics — i.e. AFTER excluding everything the court/blob/junk machinery
already flags.

## 4 · G-K2 on the adopted field — the spreading cost

Adoption concentrates label mass (one topic's wording stamped on many clusters), so
`labels_compatible` passes more pairs and components grow: edges rise on every night
(63→77 · 40→59 · 53→93 · 266→402 on 07-28), and on the small early nights the largest
component crosses 2%: **11/15 vs the ≥14 bar** (07-01 2.19%, 07-06 2.02%, 07-09 2.20%,
07-19 19:04 2.97% — the last already failed pre-adoption at 3.15%; adoption *improved* it
and still fails). G-784 stays 0 and false-pairs stay 0/1200 — the growth is same-story-ish
consolidation plus label-spread, not war fusion — but the pre-registered K2 bar is the bar,
on the metric's own units. Fired, honoured.

## 5 · The founding/false-block ladder, now five predicates long

| configuration | foundings / decidable | false-block @ cos≥0.99 |
|---|---|---|
| labels_compatible (7th/8th b_p7) | 50.5% | 27.5% |
| P-NUEVO (8th b_p8) | 41.7% | 21.4% |
| P-NUEVO + gray-band court (8th, inviable) | 34.5% | 17.4% |
| **P-NUEVO + adopted labels (9th)** | **32.8%** | **16.4% ✓ first pass** |
| bar | 15% | 20% |

The mechanism did what it was designed to do — where the landing pick IS the adoption
source, the pair is string-identical and joins. The residual 32.8% is the program's oldest
enemy at a new layer: **argmax dispersion**. A cluster adopts topic X's label, but its
landing pick is topic Y (the blocked examples: 'Brazil Retaliates Against US Tariffs' -x->
'Brazil Responds to Trump Tariffs' at cos 1.0 — the cluster adopted from a THIRD wording of
the same story), plus the untouched cross-language/transliteration class ('Genoa Bridge
Collapse Verdict' -x-> 'Condena Puente Génova').

## 6 · Landing (context: the principle is now 4-for-4)

| family | production on adopted feed | B-p8-adopted |
|---|---|---|
| GQ-12 caspian | Iran Warns Ukraine **✓** (receipts carry the exact Caspian headline) | Iran Ukraine Caspian Attack ✓ |
| berlin pride | Berlin Pride Van Attack ✓ | Berlin Pride Van Attack ✓ |
| us-strikes-on-iran | Iran Military Posturing ✗ | US Military Strikes on Iran ✗ — receipts span sanctions + threats (breadth) |
| paris-knife-attack | Paris Knife Attack ✓ | Paris Knife Attack ✓ |
| kyiv missile strikes | Deadly Crash in Mykolaiv ✗ (the known black-hole) | Russian Attacks on Ukraine ✗ — a multi-date aggregation (breadth) |
| wildfires FR/ES | Severe Storms in France ✗ | **Wildfires in France and Spain ✓ — a true JOIN into the pre-existing correct identity** (the first run with ZERO self-founded landings; no pool-checks needed) |

**G-LANDING PASS: 4/6 vs 3/6** — the narrowest margin yet, and two instructive regressions
vs the 8th: on both ✗ families the adopted feed's supers carried labels inherited from
BROADER identities, and landed on breadth ('Russian Attacks on Ukraine' instead of the
specific Kyiv-region strike). **Adoption transmits breadth as efficiently as it transmits
correctness.** Also notable: production itself improved to 3/6 on the adopted feed (caspian
found a correct home) — better consolidation helps even the arm with no label gate.

## 7 · G-COSTO — the production prompt (zero extra calls, by construction)

Published in full in the JSON (`production_prompt` + `production_candidate_block`); it is
`emergent_poc.LABEL_PROMPT` — the call `snapshot_emergent_topics.py` already makes once per
cluster — with one injected block when a candidate exists:

```
A nearby existing topic already tracks a story (cosine similarity {cos}):
  "{candidate_label}"
If these headlines are THE SAME STORY that topic describes, set "adopted": true
and return that label VERBATIM as "label" — do not coin a new wording for a
story that already has a name. Only if this is a different story (or the
existing label misdescribes these headlines), set "adopted": false and coin a
new label.
```

The candidate lookup is a local centroid dot product against the already-loaded pool. Call
count with adoption == call count without. G-COSTO passes — and is moot under the KILL.

## 8 · Honest caveats

- **The simulated adopter is evidence-poorer than production would be** (16,361/18,023
  decisions on historical-label evidence; retention ate the headlines). A production adopter
  reading real headlines would plausibly beat 53.3% — but the identical-label rot class
  (39%) and the breadth-transmission mode are evidence-independent, and the bar is 5%.
- **DeepSeek judging DeepSeek** (adopter and judge share a model family; correlated blind
  spots) — mitigated by the quote-gate, the conservative ungrounded rule, and a full human
  read; the artifact carries every transcript.
- **Adoption applied to snapshot-side labels only**; a deployed system would have adopted
  historically too, compounding both the good (stability) and the bad (rot inheritance) in
  ways one generation cannot show.
- **Pool = as-of-now** (terrain constant across gates 7–9; all stated caveats carry).
- **What surprised:** (1) G-FALSE-BLOCK passed for the first time — the mechanism's designed
  effect is real; (2) 39% of *identical-label* adoptions were condemned — the eligibility
  filter (court+blob+junk+umbrella, 2,894 topics) is NOT sufficient to certify an identity
  as safe to inherit from; (3) production landing improved on the adopted feed without any
  label gate — consolidation quality, not join gating, moved arm A.

## 9 · What the KILL leaves — the label arc is closed

Gates 7–9 have now measured every label-side lever on one instrument: join-time string
similarity, join-time token containment, join-time receipts entailment (inviable), and
labeling-time adoption. The ladder moved founding 50.5 → 32.8 and false-block 27.5 → 16.4,
and **no rung reaches the frozen bars, because every rung inherits the same substrate: a
pool in which ~39% of even eligibility-filtered near-neighbor identities carry receipts
that do not match their own labels.** Adoption is the clearest statement of the circularity:
it needs healthy identities to inherit from, and healthy identities are what all of this is
trying to produce.

The honest next lead is therefore not another label mechanism. It is: (1) let the pool-health
machinery that started operating 08-01 (TF-3b court cycle, blob-veto, junk demotion) run its
arc, using the **adoption-condemnation rate** (§3) and the 7th–9th instruments as the
pre-registerable pool-health metrics; (2) when the condemnation rate on eligibility-filtered
neighbors drops materially, re-run THIS gate's exact harness — the mechanism's clean effect
(G-FALSE-BLOCK ✓, landing 4-for-4, breadth transmission excepted) is on record and the
instrument is idle, waiting for a substrate that deserves it. G-FOUNDING stays at 15%,
three KILLs strong.
