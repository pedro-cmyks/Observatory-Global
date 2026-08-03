# The landing join predicate — the 8th pre-registered gate

**Generated:** 2026-08-03 · read-only, no prod write
**Harness:** `backend/scripts/measure_landing_predicate.py` (extends the 7th gate's harness,
left byte-untouched; rules imported, never re-implemented)
**Artifacts:** `2026-08-03-landing-predicate.json` (every number + all judge/court transcripts) ·
pre-registration frozen before any build:
`docs/superpowers/specs/2026-08-03-landing-predicate-preregistration.md`
**Runtime:** measure 3,601s + judge ~90s, `taskpolicy -b`, zero memory-pressure pauses. (A first
attempt was killed externally mid-court-arm; nothing was written, the court cache persisted, and
the full re-run is the only measured run — the interrupted attempt's b_p7/b_p8 per-night numbers,
visible in its log, match the final run's exactly.)

**Inherited intact from the 7th:** consolidation rule (cos≥0.90 AND `labels_compatible` AND
`countries_share` — the graph gates double as fidelity anchors), arm-B shape, witness families,
quote-gated landing judge, 12-night replay against TODAY's pool (hydrated as-of
2026-08-03T13:07Z). **New here:** P-NUEVO at the landing join, four arms, G-PREDICADO, and the
self-founded rule (a founding counts only if no correct identity existed in the pool that night).

---

## VERDICT: **KILL** — two gates fired; the landing principle passed its third straight test

| gate | bar (frozen) | measured | verdict |
|---|---|---|---|
| **G-K2** | ≥14/15 inherited nights ≤2% | **14/15** (07-19 19:04, 3.15%) | **PASS** |
| **G-784** | 0 across the 15 nights | **0** | **PASS** |
| **G-LANDING** (primary) | b_p8 ≥ ⌈⅔·6⌉=4 correct AND strictly > arm A, self-founded rule active | **b_p8 4/6 · arm A 2/6** | **PASS** |
| **G-FOUNDING** | b_p8 foundings ≤ 15% of decidable picks | **41.7%** (5,205/12,469) | **FAIL → KILL** |
| **G-COVERAGE** | b_p8 ≥ RAW per scorable family | 6/6 up (identical to the 7th's coverages) | **PASS** |
| **G-FALSE** | 0/1200 per night | **0/1200 every night** (structural note stands; label-only also 0) | **PASS** |
| **G-PREDICADO** | calibration 10/10 pre-run AND false-block < 20% on known same-story pairs | calibration **10/10** · false-block **21.4%** | **FAIL → KILL** |

The predicate gate missed by **1.4pp** — and the miss is the finding. P-NUEVO repaired every
failure class the 7th diagnosed (calibration table below: 10/10, rescuing 5 of 6 pairs the old
predicate blocked AND blocking the three-war template the old predicate would have joined), yet
the false-block on known-same-story pairs only moved **27.5% → 21.4%**, and total foundings
**50.5% → 41.7%**. The residual is a class no label-level comparison can bridge — §5.

## 1 · G-PREDICADO part 1 — the calibration table (written FIRST, passed before the run)

| # | pair | category | expected | P-NUEVO | old `labels_compatible` |
|---|---|---|---|---|---|
| 1 | US Citizen Released by Iran ↔ American Released from Iran | anchor · re-wording (spec) | compat | **compat ✓** | incompat ✗ |
| 2 | Berlin Pride Van Attack ↔ Drone Attacks on Moscow | anchor · different event (spec) | incompat | **incompat ✓** | incompat |
| 3 | Shania Twain Missed Wedding ↔ Shania Missed Taylor's Wedding | re-wording (7th §5) | compat | **compat ✓** | incompat ✗ |
| 4 | Soviet Flag Sold at Auction ↔ Soviet Moon Flag Auction | re-wording (7th §5) | compat | **compat ✓** | incompat ✗ |
| 5 | Iran Accuses Ukraine of Caspian Attack ↔ Iran Ukraine Caspian Attack | containment | compat | **compat ✓** | compat |
| 6 | Trump Naval Blockade Iran ↔ Trump Restablece Bloqueo Naval a Irán | cross-language (7th §5) | compat | **compat ✓** | incompat ✗ |
| 7 | Галявиев Женился в Колонии ↔ (itself) | Cyrillic self-pair (7th §5) | compat | **compat ✓** | incompat ✗ |
| 8 | Russia-Ukraine Conflict Escalation ↔ US-Iran Conflict Escalation | NEG · three-war template (run 5 §7) | incompat | **incompat ✓** | **compat ✗** — the old predicate joins the war fusion |
| 9 | Russian Missile Strikes on Kyiv ↔ Russian Missile in Poland | NEG · 7th arm-A wrong landing | incompat | **incompat ✓** | incompat |
| 10 | Iran Attacks UAE Tankers ↔ Iran Ukraine Caspian Attack | NEG · run 5 §6a wrong landing | incompat | **incompat ✓** | incompat |

**10/10.** Frozen definition in the harness docstring: Unicode normalizer (NFKC + casefold +
NFKD, combining marks stripped — never `[^a-z0-9]`), subject tokens ≥3 alpha chars minus the
imported `_GENERIC_TOKENS` ∪ a frozen war-template set, one-trailing-'s' fold, then:
norm-equal → pass; no shared token → fail; one side fully contained → pass; ≥3 shared →
min-residual ≤1; =2 shared → max-residual ≤1. Two pre-run decisions documented in the harness
(allowed; gates untouched): **night-df plays no role** (df-forgiveness re-admits the war fusion
when big families inflate russia/ukraine/iran into the top decile — run 5 §11.1's trap bites in
both directions, so the generic set is static), and **strict containment is bounded-residual**
(the spec's own anchor pair carries one leftover token per side and cannot pass strict).

## 2 · Fidelity — reproduced, or the run stops

| check | expected | measured | ✓ |
|---|---|---|---|
| chunked loader ≡ `load_clusters` | exact | 17,827 rows, 0 mismatches | ✓ |
| +country graph rows, 15 frozen nights (edges/largest/share/784/false) | run 5 JSON | **exact 15/15** | ✓ |
| fastpath ≡ `labels_compatible` (07-28) | 0/20,000 | 0/20,000 | ✓ |
| FALSE construction | 0/1,200 | 0/1,200 every night | ✓ |
| single-night downstream RAW vs prod | 93.81% ± 2pp | **92.96%** (1889/2032) | ✓ |
| **b_p7 ≡ the 7th's arm B** (cross-harness: the generalized arm with `labels_compatible`) | 7th JSON | **exact** — 6,300 blocked, rate 0.5053, 14,114 topics, per-night identical | ✓ |
| calibration re-verified in-process before measuring | 10/10 | 10/10 | ✓ |

## 3 · The four-arm landing table (judge = DeepSeek temp-0 + court quote-gate; 24/24 grounded)

✓* = judged CORRECT but **does not count** under the new self-founded rule (a correct identity
already existed in the pool — §4). Counting rows: arm A **2/6** · b_p7 **4/6** · **b_p8 4/6** ·
b_court **3/6**. G-LANDING (b_p8 ≥4 and > arm A) **PASS** — the third consecutive run in which
refusing label-incompatible joins beats production landing.

| family | arm A (production) | b_p7 (old predicate) | **b_p8 (P-NUEVO)** | b_court |
|---|---|---|---|---|
| GQ-12 caspian | India Condemns Hormuz Attacks ✗ | Iran Ukraine Caspian Attack ✓ | **Iran Ukraine Caspian Attack ✓** (join) | Iran Ukraine Caspian Attack ✓ |
| berlin pride | Berlin Pride Van Attack ✓ | Berlin Pride Van Attack ✓ | **Berlin Pride Van Attack ✓** (join) | Berlin Pride Van Attack ✓ |
| us-strikes-on-iran | US Launches New Attacks on Iran ✗ (campaign blob) | US Strikes on Iran ✓ | **US Strikes on Iran ✓** (join) | US Launches New Attacks on Iran ✗ — a court-granted join INTO the blob |
| paris-knife-attack | Paris Knife Attack ✓ | Paris Knife Attack ✓ | **Paris Knife Attack ✓** (join) | Paris Knife Attack ✓ |
| kyiv missile strikes | Russian Missile in Poland ✗ | Russian Missile Strikes on Kyiv ✓* | **Russian Missile Strikes on Kyiv ✓*** (self-founded) | Russian Missile Strikes on Kyiv ✓* |
| wildfires FR/ES | Severe Storms in France ✗ | Wildfires in France and Spain ✓* | **Wildfires in France and Spain ✓*** (self-founded) | Wildfires in France and Spain ✓* |

Sample judge evidence (all 24 in the JSON, each with its verbatim quote): caspian/b_p8 quotes
"Iran accuses Ukraine of attacking Iranian vessel in Caspian Sea"; kyiv/b_p8 quotes the exact
Ukrainian receipt "10 загиблих і десятки постраждалих…"; wildfires/b_p8 quotes «"Orage de feu"
sur la France et l'Espagne». My human read agrees with all 24; the one borderline
(us-strikes/arm-A WRONG on the campaign-blob) is the same strict call as the 7th and is
verdict-invariant.

## 4 · The self-founded rule — Pedro's quasi-tautology, closed and measured

Both self-founded landings (kyiv, wildfires — identical in all three B arms) were pool-checked:
top-10 pool identities by centroid cos to the family's main super at hydration ∪ pool labels
P-NUEVO-compatible with the family's modal label, each with receipts, judged quote-gated.
**Both came back "a correct identity existed" (grounded)** → neither counts. The 7th's arm-B
6/6 therefore re-scores as **4/6 under this rule** (b_p7 column) — exactly the correction the
pre-registration ordered.

- **wildfires:** candidate 1 = umbrella dt-9721 `Wildfires in France and Spain`, `first_seen`
  **2026-06-14** (pre-exists the landing night — verified, since candidates were drawn from
  as-of-now hydration); three further pre-existing same-label topics (dt-3000 07-17, dt-6974 /
  dt-6744 07-25) corroborate. Founding duplicated a correct identity four times over.
- **kyiv:** the judge's cited candidate (dt-357, first_seen 07-01) is label-wise **'Deadly
  Crash in Mykolaiv'** — itself a mislabeled black hole that holds the event's receipts (the
  quote is real, the identity is wrong: the exact class this program fights). The YES verdict
  survives anyway on candidates the judge did not cite: dt-6703 **'Russian Strike Kyiv Region
  Death Toll'** and dt-6705 'Russian Strikes on Kyiv Region', founded **07-25** — correct,
  pre-existing identities for the event. Spot-check annotation recorded; conclusion unchanged.

The rule bites in the honest direction: arm B never falls through to a second-best target, so
when the production pick is wrong AND a correct identity exists elsewhere in the pool, arm B
founds a duplicate and correctly gets no credit. The steering problem — reaching the correct
existing identity that is not the argmax — remains open and is now measured as exactly these
two rows.

## 5 · G-FOUNDING and G-PREDICADO — the kill, and the three-predicate ladder

| arm | join predicate | foundings / decidable picks | false-block on known-same-story (cos ≥ 0.99) | pool end (RAW = 7,942) |
|---|---|---|---|---|
| b_p7 | `labels_compatible` (string ratio) | **50.5%** | **27.5%** (3,032/11,020) | 14,114 |
| **b_p8** | **P-NUEVO** (unicode + token containment) | **41.7%** | **21.4%** (2,146/10,041) | 13,021 |
| b_court | P-NUEVO + gray-band court | **34.5%** | **17.4%** (1,635/9,403) | 12,115 |

(The cos≥0.99 instrument refines the 7th's "~50%" claim: that number was ALL decidable blocks —
false and correct together; on the pure known-same-story subset the old predicate's false-block
is 27.5%. The 7th's mechanism claim stands; this is the cleaner measurement of it.)

Bars: 15% foundings, <20% false-block. b_p8 misses both — **41.7%** and **21.4%**. The
calibration classes are fully fixed, so the residual is a different animal. The stored top-cos
blocks name it — **facet divergence**: the labeller names *different aspects of one story*:

```
'Jens Spahn Leihmutterschaft'    -x->  'Jens Spahn Becomes Father'        cos=0.9995
'Hanson vs Great PMs'            -x->  'Vanstone Criticizes Hanson'       cos=1.0000
'Singers Fight Homelessness'     -x->  'Homelessness Choir Initiative'    cos=0.9999
'Hong Kong Bookshop Raids'       -x->  'Hong Kong Booksellers Arrested'   cos=0.9995
'Genoa Bridge Collapse Verdict'  -x->  'Condena Puente Génova'            cos=0.9987
```

Shared tokens after normalization: {jens, spahn} · {hanson} · {homelessness} · {hong, kong} ·
{} (Genoa ≠ Génova→genova — **transliteration**, beyond diacritic folding). The two sides
describe cause/consequence, actor/counter-actor, event/reaction. No comparison of label STRINGS
can certify these as one story without also certifying the war-template fusions; the
information simply is not in the labels. That is the wall, and it is now measured from three
angles.

## 6 · The court arm — better numbers, inviable, and corrupted by blobs

- **Volume:** gray band (P-NUEVO fails, cos ≥ 0.93) = **5,379 picks over 7 labelled nights =
  768/night, 5.1× the 150-call cap → INVIABLE-AT-VOLUME**, per the pre-registration, however
  well it measures. In-run: 1,500 fresh calls + 1,603 cache hits, **2,276 gray picks unresolved
  by budget** (resolve as found; truncation stated — its founding rate is a floor-biased 34.5%).
- **Grant rate:** 1,085 joins of ~3,100 court-resolved picks (~72% at the cached/called
  high-cos end) — an independent confirmation that the blocked mass at high cos is mostly
  same-story.
- **The failure mode the transcripts expose** (sample log in the JSON): the court joins
  fragments **into blobs**, because a blob's receipts contain everything — measured live:
  `'Ukraine Political Turmoil and Conflict'` court-joined into a topic labeled **'Health and
  Lifestyle Advice'** ("the fragment label exactly matches T9's label" — T9 being a member of
  the blob); `'Arjantin Dünya Kupası Tartışmaları'` into 'Beşiktaş Transfer News' by the same
  route; and the b_court landing table's one regression (us-strikes → the campaign blob) is a
  court-granted join. Receipts-entailment against black-hole targets inherits the black hole.
  The quote-gate did hold where it could: ungrounded 'same' verdicts were withheld (e.g. the
  Iran-Supreme-Leader pick, grounded=False → no join).

## 7 · Honest caveats

- **Blackout nights carry no gate**: 15,498 undecidable joins (arm B degrades to production
  semantics on NULL-label supers, per the pre-registration's blackout clause).
- **Pool-check candidates were drawn from as-of-now hydration**; "existed that night" was then
  verified via `first_seen` for the deciding candidates (§4). One judge citation pointed at a
  mislabeled black-hole (annotated); independent pre-existing correct identities carry the
  verdict.
- **The court arm is budget-truncated and cache-dependent**: deterministic across re-runs via
  the disk cache, but which gray picks got calls follows pick order; the unresolved 2,276
  resolve as found. Its numbers are floors, and its inviability verdict does not depend on them.
- **The cos≥0.99 known-same-story instrument** is by-construction (own-topic re-encounters);
  in nightly operation the same mechanism operates slightly below that cos — magnitudes may
  shift, the mechanism does not (7th §5's argument, unchanged).
- **Single judge model** (DeepSeek temp-0) + quote-gate + human read of all 24 landing and 6
  pool-check judgments; n=6 families by design.
- **What surprised:** (1) a predicate that fixes *every diagnosed failure class* recovers only
  a third of the false blocks — the majority class (facet divergence) was invisible until the
  calibrated classes were removed; (2) the court's 72% grant rate and its blob-corruption mode
  are the same fact seen from two sides: receipts know more than labels, including the wrong
  receipts; (3) the self-founded rule re-scored the 7th's headline result (6/6 → 4/6) without
  changing its verdict — the pre-registration discipline absorbed its own correction.

## 8 · What the KILL leaves

Three join predicates now sit on one instrument: **string ratio 27.5% / token containment
21.4% / receipts court 17.4%** false-block — converging on, and none clearing, the 20% bar,
while G-FOUNDING's 15% stays out of reach of all three (50.5 / 41.7 / 34.5). The landing
principle itself is 3-for-3 (4/6 vs 2/6 under the strictest scoring yet). The predicate ladder
is exhausted at the join layer: the residual false-block class (facet divergence +
transliteration) does not carry the needed information in the label pair, and the layer that
does carry it (receipts) is 5× over the call cap and unreliable against blob targets.

The honest next lead is therefore **upstream, not at the join**: the labeller's wording
variance is the root supply of false blocks (two temp-varying calls per story per night). A
label-STABILITY mechanism — at labeling time, show the labeller the candidate topic's existing
label and let it ADOPT rather than re-coin when it is the same story — would shrink the
divergence P-NUEVO cannot bridge, at zero additional nightly calls (it rides the existing
labeling call). That is a measurable, pre-registerable change with its own kill rules
(adoption must not glue different stories: the 784-class control and the FALSE construction
both transfer). G-FOUNDING stays at 15%; it has now killed two gates running and is doing
exactly the job it was frozen for.
