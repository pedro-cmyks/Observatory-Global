# Consolidation + shared-country, scored on IDENTITY-LANDING — the 7th pre-registered gate

**Generated:** 2026-08-03 · read-only (`SET default_transaction_read_only = on`), no prod write
**Harness:** `backend/scripts/measure_consolidation_landing.py` (extends run 5's
`measure_cluster_consolidation.py`, which is left byte-untouched; every rule imported, never
re-implemented)
**Artifacts:** `2026-08-03-consolidation-landing.json` (this file's every number, plus raw judge
transcripts) · pre-registration **frozen before any code was written**:
`docs/superpowers/specs/2026-08-03-consolidation-landing-preregistration.md`
**Runtime:** measure 481s + judge ~30s, `taskpolicy -b`, zero memory-pressure pauses (floor 15%,
never approached).

**The rule under test** (run 5 §11.1 promoted to primary, pre-registered this time):

```
cos(centroid_a, centroid_b) >= 0.90  AND  labels_compatible  AND  countries_share
```

**Two landing arms** per super-cluster against TODAY's pool (hydrated as-of
2026-08-03T16:30Z — the cleaned field: TF-3b + court + blob-veto + junk operating since 08-01):
**Arm A** = production join semantics (`process_snapshot_sim`, MATCH 0.88 + ANCHOR 0.93,
`used_t` intact). **Arm B** = the same production pick, additionally gated on
`labels_compatible(super_label, target_label)`; an incompatible pick FOUNDS a new identity
(target not consumed; no fall-through to the next-best target). Super-cluster label = the label
of its **largest member cluster** by n_signals (overriding `build_super_clusters`' modal choice;
212 overrides across the 6 labelled feed nights — stated per the pre-registration).

---

## VERDICT: **KILL** — one gate fired, and it is the anti-trivialization gate

| gate | bar (frozen) | measured | verdict |
|---|---|---|---|
| **G-K2** | largest component ≤ 2% on ≥ 14/15 inherited nights | **14/15** (only 07-19 19:04 at 3.15%) | **PASS** |
| **G-784** | ≥3-country + incompatible-label components = 0 across 15 nights | **0** | **PASS** |
| **G-LANDING** (primary) | arm B correct on ≥ ⌈⅔·6⌉ = 4 families AND strictly > arm A | **arm B 6/6 · arm A 2/6** | **PASS** |
| **G-COVERAGE** (secondary) | arm B family coverage ≥ RAW arm, every scorable family | **6/6 up** (e.g. 0.109→0.931, 0.174→1.000) | **PASS** |
| **G-FOUNDING** | arm B label-blocked foundings ≤ 15% of landing super-clusters | **50.5%** of decidable picks (6,300/12,469); 22.5% even counting blackout-degraded joins | **FAIL → KILL** |
| **G-FALSE** | 0/1200 false pairs admitted per night | **0/1200 every night** (label-only form also 0; structural note §3) | **PASS** |

**Any fail = KILL, and it is honoured with no threshold moved.** For the first time in seven
gates, the PRIMARY metric passed — identity landing went from 2/6 (run 5, and arm A today) to
**6/6 correct** under the found-biased arm. The kill is that arm B buys those landings by
founding **half the field**: 6,300 foundings in 12 nights, pool 7,942 → 14,114 topics (+78%).
Founding everything is hiding the problem — the pre-registration wrote that sentence before the
run, and the run confirmed it numerically. §5 shows the mechanism is a single, sharply
measurable defect: **`labels_compatible` (ASCII SequenceMatcher ≥ 0.80) rejects roughly half of
KNOWN-same-story label pairs**, because the labeller re-words the same story night to night and
because non-Latin labels normalize to the empty string and can never match — even against
themselves.

---

## 1 · Fidelity — the instrument reproduces run 5 (STOP rule armed, never fired)

| check | expected (run 5) | measured today | verdict |
|---|---|---|---|
| chunked loader ≡ `load_clusters` (07-28 onward window) | exact | **17,827 rows, 0 mismatches** | ✓ |
| fast-path label conjunct ≡ `labels_compatible` (07-28) | 0/20,000 | **0/20,000** | ✓ |
| sampled FALSE pairs satisfy imported construction | 0/1,200 | **0/1,200 every night** | ✓ |
| +country graph rows, all 15 frozen nights (edges/largest/share/784/false) | run 5 JSON | **exact, 15/15** | ✓ |
| label-only graph rows, all 15 frozen nights | run 5 JSON | **exact, 15/15** | ✓ |
| 07-28 unicode variant | 380 edges / 23 / 1.13% | **380 / 23 / 1.13%** | ✓ |
| 07-28 cos-only variant | 88,103 edges / 1997 / 98.28% | **88,103 / 1997 / 98.28%** | ✓ |
| §11.1 family components under +country (07-28) | 5/3/2/1/4/1 | **5/3/2/1/4/1** | ✓ |
| single-night downstream RAW vs prod (hydrate as-of 07-28) | 93.81% | **92.96%** (1889/2032; 94.12% excl-umbrella; 0 in-prod-not-in-sim) | ✓ within 2pp tolerance |

The single 0.85pp drift is terrain, not instrument: `dynamic_topics` rows are MUTABLE and
TICK-V2's 1,026-state revert, TF-3b revivals, the court and the blob-veto have all written to
them since run 5; the geometry is member-replayed from immutable `emergent_clusters` and
reproduces. Every gate below was read only after this table was green.

## 2 · Terrain — what is different from run 5, said plainly

1. **The pool is today's** (7,805 prod topics: 2,153 active / 3,985 candidate / 1,667 retired;
   hydration loaded 7,599 with members + 206 fallback + 114 umbrellas). Run 5 hydrated as-of
   07-17. Consequence: topics founded during the July window EXIST here, including correct
   identities the cleanup era created — the RAW arm attaches 29,084 of 29,221 clusters with
   only 137 foundings, i.e. nearly every replayed cluster re-encounters its own prod topic.
2. **The replay window is run 5's exact 12 nights** (07-17 → 07-28, incl. the 5 blackout
   nights), so family numbers are comparable; the last-night RAW agreement vs prod is 59.5% in
   this 12-night as-of-now configuration (accumulated re-attachment drift + `used_t`
   competition) — the arm-vs-arm comparisons all share that terrain, and the configuration
   whose absolute labels are trusted is the single-night fidelity check above (92.96%).
3. **Five extra fully-labelled nights exist post-07-28** (07-29, 07-30, 07-31 14:58, 08-01,
   08-03) — outside the frozen gate, reported in §3. (07-31 03:16 and 08-02 carry 1–2 NULL
   labels and are excluded by the 0%-NULL rule.)

## 3 · G-K2 / G-784 / G-FALSE per night (rule = +country primary)

| night | clusters | edges | largest | share | K2 | 784 | false full / label-only |
|---|---|---|---|---|---|---|---|
| 07-01 | 731 | 63 | 14 | 1.92% | ✓ | 0 | 0 / 0 |
| 07-03 | 186 | 2 | 2 | 1.07% | ✓ | 0 | 0 / 0 |
| 07-04 | 285 | 11 | 3 | 1.05% | ✓ | 0 | 0 / 0 |
| 07-05 | 224 | 5 | 2 | 0.89% | ✓ | 0 | 0 / 0 |
| 07-06 | 594 | 40 | 9 | 1.52% | ✓ | 0 | 0 / 0 |
| 07-09 | 728 | 53 | 11 | 1.51% | ✓ | 0 | 0 / 0 |
| 07-12 | 773 | 63 | 6 | 0.78% | ✓ | 0 | 0 / 0 |
| 07-13 | 788 | 59 | 9 | 1.14% | ✓ | 0 | 0 / 0 |
| 07-17 | 1966 | 212 | 9 | 0.46% | ✓ | 0 | 0 / 0 |
| 07-19 16:34 | 537 | 38 | 6 | 1.12% | ✓ | 0 | 0 / 0 |
| **07-19 19:04** | 539 | 99 | **17** | **3.15%** | **✗** | 0 | 0 / 0 |
| 07-20 | 3754 | 556 | 20 | 0.53% | ✓ | 0 | 0 / 0 |
| 07-21 | 2369 | 337 | 15 | 0.63% | ✓ | 0 | 0 / 0 |
| 07-22 | 2517 | 410 | 17 | 0.68% | ✓ | 0 | 0 / 0 |
| 07-28 | 2032 | 266 | 23 | 1.13% | ✓ | 0 | 0 / 0 |
| *extra* 07-29 | 863 | 68 | 5 | 0.58% | ✓ | 0 | 0 / 0 |
| *extra* 07-30 | 1258 | 102 | 6 | 0.48% | ✓ | 0 | 0 / 0 |
| *extra* 07-31 | 1153 | 219 | 14 | 1.21% | ✓ | 0 | 0 / 0 |
| *extra* 08-01 | 3323 | 626 | 29 | 0.87% | ✓ | 0 | 0 / 0 |
| *extra* 08-03 | 3170 | 817 | 31 | 0.98% | ✓ | 0 | 0 / 0 |

**G-K2 = 14/15, exactly at the bar** — the sole failure is the known 07-19 19:04 component: 17
correctly-merged `US Strikes on Iran` clusters on a 539-cluster night (run 5 §4 hand-read; the
share metric's size-sensitivity, not a fusion). **G-784 = 0/15.** **G-FALSE = 0/1,200 on every
night** — with the honest structural note, pre-written into the harness: the FALSE construction
requires `countries_disjoint`, so the +country rule can never admit one *by construction*; the
informative number is the label-only admission, which is **also 0/1,200 everywhere**, while
cosine alone admits 19–210 per night. The five extra nights (two of them 3.2–3.3k clusters, the
current field under fetch-mult M=2) all pass everything — reported, not gated.

## 4 · The landing table — the primary metric, with the evidence inline

Judge: DeepSeek temp-0, the court's GB3 quote-gate imported verbatim (`_reason_quotes_a_receipt`)
— a verdict counts only if its reason quotes a VERBATIM excerpt from the destination's receipts
(family's own clusters EXCLUDED from those receipts, so an event cannot vouch for itself).
**12/12 judgments grounded on the first attempt.** Coverage column = share of family signals on
the destination (G-COVERAGE: RAW → arm B rises on all six).

| family | arm | landed on | judge | verbatim evidence quoted by the judge (from destination receipts) |
|---|---|---|---|---|
| GQ-12 caspian (9 cl, 183 sig) | A | India Condemns Hormuz Attacks | **WRONG** | "Iran says it struck two oil tankers attempting to transit Strait of Hormuz" — different sea, different incident |
| | B | **Iran Ukraine Caspian Attack** (prod dt-3805) | **CORRECT** | "Iran accuses Ukraine of attacking Iranian vessel in Caspian Sea" |
| berlin pride (23 cl, 276 sig) | A | Berlin Pride Van Attack (dt-7358) | **CORRECT** | "Berlino, furgone contro la folla al Gay Pride: una donna morta e 16 feriti" |
| | B | Berlin Pride Van Attack (dt-7358) | **CORRECT** | "Attentato a Berlino, furgone contro la folla al Gay Pride…" |
| us-strikes-on-iran (9 cl, 111 sig) | A | US Launches New Attacks on Iran (dt-2552) | **WRONG** | "Irán asegura que seguirá atacando intereses de EE. UU. hasta su 'rendición total'" — a multi-week campaign blob (07-17→08-03), not the incident |
| | B | **US Strikes on Iran** (founded in-window by a blocked non-family super) | **CORRECT** | "US Strikes on Iran" / "US Military Strikes on Iran" |
| paris-knife-attack (9 cl, 149 sig) | A | Paris Knife Attack (dt-8497) | **CORRECT** | "Muž v Paříži pobodal tři ženy" |
| | B | Paris Knife Attack (dt-8497) | **CORRECT** | "Polícia v Paríži zadržala muža, ktorý nožom zaútočil na tri ženy" |
| russian-missile-strikes-on-kyiv (9 cl, 163 sig) | A | Russian Missile in Poland (dt-9727) | **WRONG** | receipts center on "Russian Missile in Poland" — a distinct incident |
| | B | **Russian Missile Strikes on Kyiv** (self-founded†) | **CORRECT** | "10 загиблих і десятки постраждалих: рятувальники показали наслідки ракетного удару РФ на Київщині" |
| wildfires-in-france-and-spain (8 cl, 178 sig) | A | Severe Storms in France (dt-5104) | **WRONG** | destination receipts are "French Embassy Bomb Threat" — the topic is itself a blob |
| | B | **Wildfires in France and Spain** (self-founded†) | **CORRECT** | «"Orage de feu" sur la France et l'Espagne, la chaleur en embuscade» |

**Arm A: 2/6 · Arm B: 6/6.** † = the destination was founded by the family's own blocked
super-cluster, so its correctness is quasi-tautological (the founded identity IS the event) —
that is the pre-registered semantics ("fundar es barato"), and the robustness read stands
without them: **excluding both self-founded rows, arm B is 4/6, still at the bar and still
strictly above arm A's 2.** The `us-strikes` arm-A WRONG is the judge's strictest reading (a
campaign-blob destination); scoring it CORRECT changes nothing (B 6 > A 3, B ≥ 4).

Two terrain notes the table carries quietly. First, **the cleaned pool already improved
production landing**: run 5's arm-A-equivalent sent Paris to "Monaco Explosion Targets
Ukrainian…"; today a true `Paris Knife Attack` topic (dt-8497) exists and production semantics
finds it. Second, **arm B's caspian landing is a pre-existing prod topic** (dt-3805, `Iran
Ukraine Caspian Attack`) — the correct identity was IN the pool all along; production's
best-cos pick preferred a Hormuz topic, and only the label gate redirected the event onto it
(by refusing the wrong join and letting the next night's fragments accrete correctly).

Coverage (G-COVERAGE, secondary — never reported alone): RAW → arm B = caspian 0.383→0.683 ·
berlin 0.109→0.931 · us-strikes 0.180→0.820 · paris 0.174→1.000 · kyiv 0.239→0.755 · wildfires
0.483→1.000. Topics-per-event: 9→5, 23→3, 9→2, 9→1, 9→4, 8→1.

## 5 · G-FOUNDING — the kill, and the mechanism behind it

Per-night landing decisions in arm B (decidable = the super-cluster carries a label, so the
gate can actually fire; the 5 blackout nights are undecidable by construction and degrade to
production joins, per the pre-registration's "no pueden portar la regla"):

| night | fed | joins (decidable) | label-blocked → founded | undecidable joins |
|---|---|---|---|---|
| 07-17 | 1835 | 809 | 1026 | 0 |
| 07-19 ×2 | 511 / 470 | 266 / 263 | 245 / 206 | 0 |
| 07-20 | 3413 | 1882 | 1531 | 0 |
| 07-21 | 2123 | 1197 | 925 | 0 |
| 07-22 | 2276 | 1080 | 1196 | 0 |
| 07-23 … 07-27 | 2190–3854 | 0 | **0** | 15,500 |
| 07-28 | 1843 | 672 | 1171 | 0 |
| **total** | | **6,169** | **6,300** | **15,500** |

**Blocked rate = 6,300 / 12,469 decidable picks = 50.5%** (bar ≤ 15%). Under the alternative
denominator reading — all landing picks including the blackout-degraded joins — it is 22.5%,
also a fail; no definition rescues it. Arm B's pool ends at 14,114 topics vs RAW's 7,942
(+78%); founded_total 6,309 vs RAW's 137.

**The mechanism is measurable and singular.** Because the pool is hydrated as-of-now, almost
every decidable pick is a cluster re-encountering the very topic it founded or joined in prod —
the RAW arm confirms it (29,084 attaches, 137 foundings). So the blocked set is, by
construction, overwhelmingly **KNOWN-same-story label pairs** — and `labels_compatible` fails
on about half of them. The stored top-of-order blocks (60/60 at cos ≥ 0.99) read like a
taxonomy of the defect:

```
'Галявиев Женился в Колонии'    -x->  'Галявиев Женился в Колонии'      cos=1.0000   ← IDENTICAL label, blocked
'Therapy Dog Calms Students'    -x->  'Millie the Therapy Dog'           cos=1.0000
'US Citizen Released by Iran'   -x->  'American Released from Iran'      cos=0.9998
'Shania Twain Missed Wedding'   -x->  'Shania Missed Taylor's Wedding'   cos=0.9997
'Hong Kong Bookshop Raids'      -x->  'Hong Kong Booksellers Arrested'   cos=0.9995
'Trump Naval Blockade Iran'     -x->  'Trump Restablece Bloqueo Naval a Irán'  cos=0.9999
```

Three failure classes, all in production's own `labels_compatible`: (1) **labeller re-wording**
— DeepSeek names the same story differently on different calls, and SequenceMatcher-0.80 over
the whole string does not absorb it ('US Citizen Released by Iran' vs 'American Released from
Iran' = same event, sub-0.80); (2) **cross-language labels** for the same story ('Trump Naval
Blockade Iran' vs 'Trump Restablece Bloqueo Naval a Irán'); (3) **the ASCII normalizer** —
`[^a-z0-9]+` reduces a Cyrillic label to the empty string, and empty never matches ANYTHING,
*including a byte-identical copy of itself* (the Галявиев row: same label, cos 1.0, blocked).
Run 5 §2 measured class 3 as 1.23% of labels; this run shows what it does at the landing layer.
43 further blocks hit empty-labelled targets.

This doubles as the number the program never had: **two independent labeller calls on the same
story agree (at SequenceMatcher 0.80) only ~half the time.** The same brittleness shows up in
the lexical `identity_ok` proxy: it scores arm B's caspian landing FALSE ('Iran Ukraine Caspian
Attack' vs modal 'Iran Accuses Ukraine of Caspian Attack' — sub-0.80!) while the quote-grounded
judge says CORRECT. The instrument that killed G-FOUNDING and the proxy that under-counts
correct landings are the same defect.

**Ship-relevance of the 50.5%:** the replay construction (re-encountering one's own prod topic)
makes the rate an upper-bound flavour of the nightly number — in real operation tonight's
cluster meets a topic founded from *earlier* nights, not literally itself. But the mechanism
transfers unchanged: the pool topic's label and tonight's super label always come from two
independent labeller calls, which is exactly the pair this run measured at ~50% failure. The
magnitude may move; the defect does not.

## 6 · Human spot-check of all 12 judgments

Read individually (the JSON carries every raw transcript): **12/12 agree in direction with my
own read.** Every quote was verified mechanically as a verbatim destination-receipt substring
(court normalizer). Annotations: `us-strikes/A` is the one borderline call (campaign-blob
destination judged WRONG under the strict same-incident rule — defensible, and verdict-invariant
either way); `kyiv/B` and `wildfires/B` are self-founded (§4 †); `paris` and `berlin` are judged
on non-English receipts (Czech/Slovak/Italian), which the judge handled correctly — a small
demonstration that receipts-based judging crosses languages exactly where label-string matching
(§5 class 2) cannot.

## 7 · Honest caveats

- **The 5 blackout nights carry no rule and no gate** — consolidation is a no-op (0 edges) and
  arm B degrades to production joins there (15,500 undecidable). They are reported as
  non-scorable per the pre-registration, never as success. 29 of Berlin Pride's window
  fragments still live on those nights (run 5 §6b): the window-scoped numbers keep measuring
  the blackout, not the rule.
- **Self-founded destinations** make 2 of arm B's 6 correct landings quasi-tautological; the
  bar holds without them (4/6 > 2/6), stated in §4.
- **Super-cluster label = largest member's label** — a run-design choice (task-specified,
  stated up front); 212 of 1,006 merged supers differ from the modal choice. Not measured
  against the modal alternative.
- **The 12-night as-of-now replay is arm-vs-arm terrain, not a prod reproduction** (59.5%
  last-night agreement; the trusted absolute configuration is the single-night check, 92.96%).
- **G-FALSE passes structurally** for the +country rule; the informative label-only form also
  passes (0/1200 every night) — both printed, neither alone.
- **The judge is one model (DeepSeek temp-0) with a quote-gate + human read of all 12** — n=6
  families, small by design; the pre-registration sized the bar (⌈⅔·scorables⌉) for it.
- **Family receipt survival:** 766/919 family sample signals still resolve in `signals_v2`;
  judgments used what survives (all 12 still grounded).
- **What surprised:** (1) the primary metric passed for the first time in the program — and the
  run still KILLs, on the exact anti-trivialization gate written to catch this shape; (2) the
  cleaned pool alone fixed 1–2 of run 5's wrong landings under untouched production semantics;
  (3) an IDENTICAL Cyrillic label blocked against itself — the sharpest possible witness that
  the label gate's normalizer, not label agreement as an idea, is the defect.

## 8 · What the KILL leaves (the honest lead — not a result)

The landing instrument works and the direction is now measured: **refusing label-incompatible
joins converts landings from 2/6 to 6/6 correct.** What fails is the *predicate*, not the
*principle* — `labels_compatible` is simultaneously too strict on same-story pairs (50% false
block: re-wording, cross-language) and structurally blind outside ASCII (self-block). The next
pre-registerable run should keep arm B's shape and replace the join predicate with one that
tolerates labeller variance — candidates to measure, each cheap to pre-register: a
Unicode-aware normalizer first (kills class 3 outright, run 5 already carries the variant); a
subject-token containment test instead of whole-string SequenceMatcher (classes 1–2); or a
court-style receipts entailment on the gray band only (volume must respect the 150-call/night
cap that killed refutation #3). G-FOUNDING stays at 15% for that run; the bar did its job here
and earns its keep unchanged.
