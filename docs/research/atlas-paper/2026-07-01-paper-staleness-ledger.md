# Paper Staleness Ledger (PR3.0)

Date opened: 2026-07-01 · Owner: engine track · Status: **ACTIVE** (PR3 doc
track CLOSED 2026-07-01 — 10 resolved, 1 partial; **PR4 reconciliation pass
executed 2026-08-03** — 13/13 resolved: 10 doc rows + PR4-11/12/13 decided by
Pedro same day (keep B unified · keep A's framing · P7 multi-rater = a 5-agent
evaluator court + adjudicator, design frozen in the systems report §7); see the
"2026-08-03 reconciliation pass (PR4)" section at the bottom)
Companion: `docs/specs/2026-07-01-atlas-engine-r3-unification.md` §8 (the PR3
paper-coherence track). Purpose (Pedro, 2026-07-01): the papers drifted from the
engine reality; instead of patching ad-hoc, **track each stale claim as a
closeable row.** Every future engine change that invalidates a paper number
APPENDS a row here. This turns "the papers are disorganized" into a list with a
route.

Seeded from the 2026-07-01 4-agent deep read (paper agent = bucket I4/M5). Cite
each finding by its `F-D-*` id in the R3 §11 ledger.

## How to use
- **On any engine change** that changes a served number (precision, topic count,
  coverage, lifecycle, taxonomy), add a row BEFORE the paper is next touched.
- A row closes when the paper text is edited (or the experiment run) to match
  reality, with the commit noted.
- The **master-plan cross-ref index** is the canonical map; when it lags (it did,
  to 2026-06-26), that is itself a ledger row (PR3-06).

## Ledger

| id | paper · loc | claim as written | current engine reality (2026-07-01) | fix | status |
|---|---|---|---|---|---|
| **PR3-01** | P1 skeleton R1 + master-plan; **precision-to-90** §obj; **session-summary**; **spend-ledger** | FOUR un-reconciled Atlas precision numbers: **41.6%** (N660/3-vendor) · **50.79%** (N189/6-model) · **59.02%** (N61) · learned-gate **90%@64%**; and LLM **78.6%** vs **95.08%** | different N + annotator panels + gold sets; the 78.6 vs 95.08 gap is the label-drift confound P1 itself warns of | **PR3.1:** declare ONE canonical regime (recommend 3-vendor N660 headline), footnote the rest; reconcile the LLM split by naming the gold set each used | **RESOLVED 2026-07-01** — P1 skeleton §"Canonical benchmark regime (PR3.1)" declares 3-vendor N660 (41.6%/78.6%) as headline; 50.79/59.02/scope-gate footnoted as panel/N/coverage variants; 78.6-vs-95.08 resolved as different gold sets |
| **PR3-02** | P1 skeleton §Benchmark; labeling-guide; methodology-outline validation-map | benchmark = **30 atlas_topics × 4 buckets**, "256 rows / 30 topics" | R3.2 collapses atlas_topics from a served population to an attribute; served pop = **348 stories** (R3.7) | **PR3.2:** re-scope P1 benchmark as measuring the crisis-ANCHOR precision; add open-set category coverage/coherence for emergent extensions | **RESOLVED 2026-07-01** — P1 skeleton gained the formal §"Benchmark universe re-scope (PR3.2): crisis-anchor precision + open-set coverage" (placed after the canonical-regime section): Part A = crisis-anchor precision on the crisis-only held-out split (48–54% de-biased, κ 0.734 gold, CIs, anchoring control mandatory, 90% target); Part B = emergent extensions delegated to P8's coverage/coherence/dynamism; the 41.6→48–54 bridge stated as a QUESTION change (force-fits excluded from the crisis denominator via the reject class), not one measurement; gaps named (temporal hold-out DATA-LIMITED, role_noise_rate open). The stale "UNMEASURED" clause in §"Reject GATE ≠ category TYPING" updated to cite the landed PR3-10 numbers |
| **PR3-03** | P6 master-plan L448-451; P8 skeleton baseline L26/L115 | topic set **FROZEN**, "last updated 06-29 17:00, 54/68 active >3d stale, lifecycle not retiring" (present tense) | FIXED — former revived mindful/off-peak (P8 Intervention-1); R1 wrote 731 clusters; 392→348 served | **PR3.3:** rewrite frozen claims to past-tense before/after; note R3.7 (B1 retirement) as the lifecycle fix | **RESOLVED 2026-07-01** — master-plan P6 dynamism bullet + P8 SHARPENED bullet + P8 skeleton baseline section all past-tensed to before→after (68→392→348, R3.7 retirement cited as the lifecycle fix); P8 baseline header banner-marked SUPERSEDED |
| **PR3-04** | R3 spec v1 §2 vs CLAUDE.md top | "candidate-v2 NOT wired" ‖ "v2 reject gate LIVE" read as a contradiction | BOTH true: the reject GATE (binary demote) is live; category TYPING is unbuilt — different ops | fixed in R3 v3 §2/§3.1 (reject≠typing); no paper edit, but note in P1 taxonomy section | **RESOLVED 2026-07-01** — spec already resolved; the P1 taxonomy-section note now added (§"Reject GATE ≠ category TYPING", clarifying `apply_v2_reject.py` binary demoter vs R3.1 `compute_category_typing.py`) |
| **PR3-05** | master-plan L96-104; unified-engine; gdelt-decoupling; R3 §4.1 | `gdelt_hint_ablation.py` is the reproducibility GATE on the 41.6% | BUILT + RUN 2026-07-01 | **PR3.4 / §4.1 build-dep:** build `gdelt_hint_ablation.py` before any theme-hint change; it is a required P1 result (recall-delta on theme-drop) | **RESOLVED 2026-07-01** — `backend/scripts/gdelt_hint_ablation.py` + report `docs/research/embedding-ablation/2026-07-01-gdelt-hint-ablation.md`. RESULT: theme-hint-dependent assignments (lex_count=0) are 20.2% correct ≪ 40.9% baseline = net NOISE; ablated (lexicon-standalone) precision 40.9%→**48.3%** (+7.4pp); recall cost 35 corrects (13%), 86–100% semantically recoverable at a moderate cut (threshold-cliff, [0.73,0.80] band). VERDICT: REMOVE-OK on the §3.2 noise branch. Theme-hint change is now unblocked. |
| **PR3-06** | master-plan cross-ref index (L716, "Updated 2026-06-26") | index has no row for unified-engine F0-F3, the A/B, candidate-v2/κ, R0-R3, R3 | the index (the map) lags the engine by ~5 weeks; P1/P8 skeletons were updated past it | **PR3.3:** append F0-F4 / R0-R3 / candidate-v2 / R3 rows; make index-lag a standing ledger trigger | **RESOLVED 2026-07-01** — index re-dated 2026-07-01 with 9 new rows (R3 unification, R3.1 typing, crisis-relevance lens, R1 scoped, R2 umbrella, R3.7 retirement, F3 A/B, F0–F2, canonical regime); index-lag noted as a standing ledger trigger |
| **PR3-07** | master-plan pub-order L674; P1 close-criteria L179-186 | "Paper 1 closes 4-8 weeks from [2026-05-27] with current data + mig-042" | 5 weeks elapsed; mig-042 lexicon + 30-topic benchmark superseded by the unified engine + candidate-v2; the A/B + κ are now P1's two biggest sections | **PR3.1/PR3.2:** absorb A/B + κ-0.739 + R3.1 precision-lift into the close-criteria | **RESOLVED 2026-07-01** — master-plan pub-order Paper-1 line rewritten: the 4–8-week/mig-042 estimate marked superseded; close-criteria now name the A/B, κ base, canonical regime, and R3.1 lift, with the unbuilt experiments (PR3-05/09/10) as the remaining gates |
| **PR3-08** | master-plan P8 L594 vs P8 skeleton | coverage "**0.2%**" ‖ "**5.6%** embedded / **2.5%** total" | different denominators (served/ingested vs embedded/embedded), presented without them → looks inconsistent | **PR3.3:** cite the denominator each time; defer to the P8-skeleton precise figures | **RESOLVED 2026-07-01** — master-plan P8 "0.2%" line now carries an inline denominator gloss (served÷ingested vs 5.6%-of-embedded/2.5%-of-ingested), both flagged as superseded "before" numbers pointing to the scoped-pass lift |
| **PR3-09** | P1 + P8 validation-plan §Baseline-families | ≥1 EXTERNAL baseline (BERTopic / flat-embedding / TDT / event-graph) REQUIRED for submission | BUILT + RUN 2026-07-01 | **PR3.4:** build ≥1 external baseline; the internal A/B alone does not meet the stated bar | **RESOLVED 2026-07-01** — `backend/scripts/external_baseline_comparison.py` + report `docs/research/embedding-ablation/2026-07-01-external-baseline.md`. Panel (KMeans + Agglomerative flat-embedding + HDBSCAN-global = BERTopic core) over the same e5 corpus. RESULT: HDBSCAN-global (the standard density method) CLIFFS at every mcs — mega-blob (43.6%@mcs10) or collapse (4.6% cover@mcs25, 0 topics@mcs75) = the measured justification for Atlas's scoped design. Flat KMeans/Agglo reach coherence PARITY (0.88/0.87 vs Atlas 0.849) but in-sample + no identity/lifecycle/noise-rejection. Honest takeaway: Atlas's edge is scoping (dissolves the cliff) + lifecycle, NOT raw one-shot coherence. BERTopic-proper (UMAP+cTFIDF) is the py3.12 follow-up (numba-blocked on py3.14). |
| **PR3-10** | P1 methodology-outline §8; master-plan Master-criteria | temporal hold-out week; `role_noise_rate` calibration; anchoring-effect (30 blind vs hinted); Wilson/bootstrap CIs; **crisis-only in-category κ split** — all "not started" | R3.1/R3.2 measure on 168h windows with no temporal hold-out, no CIs, no anchoring control on the LLM-in-loop typing; the crisis-only precision (the real successor to 41.6%) is UNMEASURED | **PR3.4:** schedule each as a ledger row with an owner; gate R3.1's precision claim on them | **PARTIAL 2026-07-01 (3 of ~5 done)** — (1) Wilson + bootstrap(5000) CIs on the PR3-05 ablation (`2026-07-01-ablation-cis.json`): baseline 40.9% [37.2,44.7], ablated 48.3% [43.8,52.7], Δ +7.4pp [5.2,9.6] (excludes 0), theme-dependent 20.2% [14.9,26.8] (non-overlapping). (2) inter-annotator κ (`2026-07-01-gold-kappa.json`): Fleiss binary 0.734 / 4-cat 0.623 = substantial → the gold is reliable. (3) **crisis-only precision = the successor to 41.6% (`2026-07-01-crisis-only-precision-and-kappa.md`): 53.8% (170/316)** vs 40.9% baseline; out-of-scope force-fits are 49.2% of usable at 27.1% → they pin the headline number, not the crisis classifier. (4) anchoring control (`2026-07-01-anchoring-control.json`): blind (unanchored) crisis-only 48.2% (IN-rate 59.1%) vs hinted 53.8% (47.9%) — the hint was ~5.6pp optimistic; de-biased successor to 41.6% = **48–54% (48% floor)**. DATA-LIMITED: temporal hold-out (batch-03 has no timestamp + signals purged → needs a fresh labeled window). REMAINS: `role_noise_rate` calibration. **4 of 5 done.** |
| **PR3-11** | P3 seed "Evidence to collect" | per-component heat ablation + Kendall-tau composite-vs-volume | BUILT + RUN 2026-07-01 | **PR3.4:** the movement/attention roles are the substrate — run the P3 ablation | **RESOLVED 2026-07-01** — `external_baseline`-style pull of `/heat/countries` (N=200) + `docs/research/embedding-ablation/2026-07-01-heat-ablation.{md,json}`. Kendall-τ(composite vs volume) = **−0.198** (mildly NEGATIVE); top-8-by-composite vs top-8-by-volume overlap **0/8** (GT/CR/CI/HN… vs GB/CN/IN/RU…). Mechanism: `surprise_kl` +0.401 composite / −0.558 volume + `source_diversity` +0.486 drive the divergence; `local_voice_ratio` +0.413 is the one volume-leaning term. "volume≠importance" is measured, not asserted. |

## Notes
- PR3.1 + PR3.2 **gate R3.2's headline paper claim** (the "successor to 41.6%" is
  undefined until the regime is canonical + the universe re-scoped).
- Everything here is doc + offline-experiment work — **no serving risk**, runs in
  PARALLEL with the R3 build.
- The anchored-emergent category decision (R3 §3.1, E-R3-h) changes what "taxonomy
  precision" even measures: fixed-taxonomy precision for the crisis anchors,
  open-set coverage/coherence for the emergent extensions. PR3.2 must carry this.

## PR3 reconciliation pass — 2026-07-01 (doc-only; orchestrator commits)
The PR3.1 + PR3.3 doc reconciliation ran this date. Result:
- **RESOLVED (6):** PR3-01, PR3-04, PR3-06, PR3-07, PR3-08, PR3-03 (see each row's
  status cell for the exact edit + location).
- **PR3-02 RESOLVED 2026-07-01 (was the last open doc-track item).** The full
  benchmark-universe re-scope authored into the P1 skeleton as §"Benchmark universe
  re-scope (PR3.2)": Part A crisis-anchor precision (48–54% de-biased successor to
  41.6%, κ 0.734, CIs, anchoring control mandatory) + Part B open-set
  coverage/coherence/dynamism delegated to P8 + the explicit 41.6→48–54 bridge
  (question change, not one measurement) + honest gaps. **The PR3 doc track is now
  CLOSED**; remaining ledger work is experimental only (PR3-10's temporal hold-out,
  DATA-LIMITED, + `role_noise_rate` calibration).
- **PR3-05 RESOLVED 2026-07-01** (`gdelt_hint_ablation.py` built + run): theme-hints
  are a NET NOISE source on the canonical benchmark (theme-only 20.2% ≪ 40.9%
  baseline; ablated 48.3%). Removal unblocked. See the row above + the report.
- **PR3-09 RESOLVED 2026-07-01** (`external_baseline_comparison.py` built + run): the
  external baseline P1+P8 require. HDBSCAN-global (BERTopic core) cliffs at every mcs
  (mega-blob/collapse) = justification for scoped design; flat KMeans/Agglo reach
  coherence parity in-sample but no identity/lifecycle. See the row above + report.
- **OPEN — the EXPERIMENT backlog (build, not doc edits): PR3-10, PR3-11.**
  These are the ongoing paper-track work: the crisis-only in-category κ split + temporal
  hold-out + Wilson/bootstrap CIs + anchoring control (PR3-10, gates R3.1's precision
  claim); per-component heat ablation + Kendall-tau (PR3-11). None can be closed by
  editing prose. (PR3-09 BERTopic-proper UMAP+cTFIDF is a py3.12 follow-up, non-blocking.)
- **Files touched this pass:** `2026-06-03-paper-1-result-skeleton.md` (canonical
  regime + reject-vs-typing note), `2026-05-27-atlas-papers-master-plan.md` (P6/P8
  dynamism past-tensed, P8 0.2% denominator gloss, cross-ref index +9 rows +
  re-dated, pub-order Paper-1 close-criteria), `2026-06-30-paper-8-result-skeleton.md`
  (baseline banner-marked SUPERSEDED + dynamism subheads past-tensed), and this
  ledger.

## 2026-08-03 reconciliation pass (PR4) — the July/August results integrated into the reorg set

Trigger (Pedro, 2026-08-03): the papers fell ~3 weeks behind the measurement
arc (recall-229), the clock arc, the serving-enforcement arc, the primary
metric, the FIPS heal and the script-blind family. Method: every paper of the
2026-07-16 reorg set read in full, each result integrated **narratively in
place** (never as an addendum), every number cited to its artifact path.
Papers edited: A (`f5f09002`), B (`1131f784`), C (`a1ffeeb5`), systems report
(`35cc0384`), canonicalization + reorg framing (`07460cb3`), master plan (see
its own commit).

| id | paper · loc | claim as written (pre-pass) | current reality (2026-08-03) | fix applied | status |
|---|---|---|---|---|---|
| **PR4-01** | Paper B (whole) | four refutations of ranking proxies = the paper's content | ten refutations: the identity arc added five pre-registered kills (whitening-at-identity STOP; evidence-overlap NO-GO by percolation, 48×; LLM judge dead-at-volume 2.4–1117×; `used_t` NO-GO ×1000 + **argmax dispersion named**, 43/54 top-12; consolidation NO-GO — coverage ≠ correctness, 4/6 wrong identity) + the ungated-revival composition KILL (37.5%→ gated 70.5%) + the silent-risk placebo kill | Part II authored (§4), method section §5 (pre-registration, false-side-same-pass, density≠precision, blind detectors, measure-twice), results table 10 rows, methods/limitations updated | **RESOLVED** `1131f784` — artifacts `recall-229/2026-07-{28,29,30,31}-*`, `2026-08-03-tf3b-gate-c-census.md`, `silent-risk/2026-07-22-*` |
| **PR4-02** | Paper A §3.6 / Paper C Table 3 | whitening = "geometry cure + stabilizer, not the recall lever" (two boundaries) | third + fourth boundary measured: whitened identity gates STOP (anchor gap −0.5471) because the removed top PC carries **cross-lingual alignment** in multilingual-e5; encoder swap NO-GO (e5-large ≡ e5-base; task-dependence total — the gate-bake-off loser bge-m3 is strongest on identity stats) | A §2 anisotropy bullet + §3.6 extended ("not the recall lever, not a gate, not fixable by a better encoder"); C cross-refs Paper B §4 | **RESOLVED** `f5f09002` / `a1ffeeb5` — `recall-229/2026-07-28-whitened-identity-taus.md`, `2026-07-31-embedding-bakeoff-v2.md` |
| **PR4-03** | Paper A (title concept) | "answerability-first" had no end-to-end answerability measurement anywhere in the series | the primary metric exists and is a day series: anti-circular gold set (20+6 controls, sha-pinned), answer rate **14→7→21→29%**, honesty floor 0.17→0.23→0.09→0.40, **persistence first-class** (instability witness GQ-02; churn total → first 3/3 hold under the M=2+TF-3b ensemble), two-arm UI/API decomposition (14.3% answered vs 71.4% informed), label-blackout confounder refuted, semantic-into-search refuted | A §3.7 + R8 authored; methods + limitations (n=14, single judge, K3 unrun, day-4 attribution confounded) | **RESOLVED** `f5f09002` — `gold/2026-07-{27,28}-gold-query-eval.md`, `2026-07-28-rerun-comparison.md`, `2026-07-31-gold-eval-day3-m2.md`, `2026-08-03-gold-eval-day4.md`, `2026-07-30-ui-eval-v2-run.md`, `2026-07-27-semantic-search-feasibility.md` |
| **PR4-04** | Paper A §2 (LLM-as-judge) | judge hazards named (drift confound) but no production-judge calibration existed | the label court is calibrated like an annotator: GB1→GB5 blind checks 3/10→7/10 (bar ≥8/10 never met, flag never flipped), blind-spot audit (PASS-stamp 0/30; `partial` over-strict 13/15; **enforcement gap** 66% court-failed still serving), certificate precision at census scale 70.5% (n=244, inter-judge 98.4%, +33pp vs ungated, 0/72 decay) | A §3.8 + R9 authored; related-work extended | **RESOLVED** `f5f09002` — `label-court/2026-07-29-gb*-blind-check.md`, `2026-07-29-court-blindspot-audit.md`, `recall-229/2026-08-03-tf3b-gate-c-census.md` |
| **PR4-05** | Paper C (every per-country number) | country axis implicitly trusted | FIPS→ISO map wrong since inception (5 mis-translations + ~89 missing codes; Lebanon served as Lesotho — 316 signals, found by the UI eval's control arm); hot remap ledgered, **22,472-row historical heal** (idempotent), corrections-v1 wired into 3 archive writers; old "LS/OS/MG geocode noise" note re-attributed to this bug; OS identified as GDELT "Oceans" pseudo-code | C Decision 3 authored; Table 4 row; limitation 9 (pre-heal provenance); canonicalization provenance note | **RESOLVED** `a1ffeeb5` + `07460cb3` — `country-code-remap/2026-07-28-country-code-remap.md` + ledgers |
| **PR4-06** | Paper C (diversity claims) | corpus diversity measured at the feed level only | the **script-blind heuristic family** structurally excluded CJK/non-Latin at capture (≥4-word title validation: CN 53.3%/TW 45.5%/JP 38.5% NULL headlines, ~33k/week; fixed, post-deploy JP 0.0%/CN 1.5%), clustering (flat 20-char floor: CN 15.0% vs US 0.95%; script-aware, env-gated) and dedup (`_norm_headline`, fixed `924174b2`) | C Decision 4 authored; B §3.2 postscript cross-ref | **RESOLVED** `a1ffeeb5` — `recall-229/2026-07-30-gdelt-null-headline-diagnosis.md`, `2026-07-30-cjk-length-floor-measurement.md` |
| **PR4-07** | canonicalization doc | three claim-types (funnel / scoped / served-count) | fourth claim-type: **serving-level country coverage** (30/168 census; lifecycle-bound, not a data floor; recovery gated on revival composition 37.5%→70.5%, bar 90%); assigned→formed→served each carry their own number | Group D + citation-card rows | **RESOLVED** `07460cb3` — `recall-229/2026-07-29-threading-floor-diagnosis.md`, `2026-07-30-tickv2-tf1-tf2-verdict.md`, `2026-08-03-tf3b-gate-c-census.md` |
| **PR4-08** | report P7 | "no analyst study exists" (comparative claim removed, thesis untested) | the honest-by-construction thesis is **tested**: full-20 rendered-pixels eval (answered 14.3% / informed 71.4% / honesty 0.83 / NAV-LOSS 20/20 / UI-WORSE ×0) — survives with one amendment (mis-measured country renders worse) + one exception (markets panel paints its own refusal); 23-defect ledger = honesty is per-surface; Story Lens **dark-shipped by its own pre-registered gate** (NAV-LOSS held 6/6; anchor-fusion inversion — "the finder was never the failure") | P7.6 + P7.7 authored; limitation 6 re-scoped (gap narrowed, not closed); graduation gate updated | **RESOLVED** `35cc0384` — `gold/2026-07-30-ui-eval-v2-run.md`, `2026-07-29-story-lens-navloss-check.md`, `recall-229/2026-07-29-sibling-finder-v2-measurement.md` |
| **PR4-09** | report P6 | temporal section had zero measured systems results | two: tick semantics bound global serving coverage (2–4 ticks/night; 1,007 topics aged 4 in one snapshot; TF-1 PASS / TF-2 KILL); fetch-boundary enforcement under a frozen 5-condition gate (M=2 live, entailed +17.8pp, **C2 denominator-artifact lesson → C2b pre-registered**) | P6.3 + P6.4 authored; results rows 17–20 | **RESOLVED** `35cc0384` — `label-court/2026-07-29-a0b-fetch-gate-measurement.md`, `2026-07-30-fetchmult-flip-postverify.md`, `2026-07-29-court-enforcement-simulation.md` |
| **PR4-10** | master-plan cross-ref index | last refreshed 2026-07-06/16; lags the engine by ~4 weeks (the PR3-06 standing trigger) | index re-dated with the 2026-07-17→08-03 evolution block + new rows | see master-plan commit | **RESOLVED** (same pass) |
| **PR4-11** | Paper B (structure) | — | the identity arc is large enough (5 kills + named disease + instrument suite) to be a standalone paper ("Argmax dispersion: pre-registered refutations at the news-identity layer") | integrated into B Part II; splitting was an editorial call | **RESOLVED 2026-08-03 (Pedro)** — keep unified in B per the integration recommendation |
| **PR4-12** | Paper A (center of gravity) | title/venue framed on the classification benchmark | the task-level metric + persistence + two-arm decomposition may now be the stronger headline; re-titling/re-centering would reorder §3 | integrated as §3.7/§3.8 without re-centering | **RESOLVED 2026-08-03 (Pedro)** — keep A's current framing per the integration recommendation |
| **PR4-13** | report P7 (graduation) | gate = 10–15-user task-time study | only available human evaluator is the author → multi-rater requirement met with an **agent-evaluator court** (Pedro's decision, evaluator count delegated) | gate re-written in the report §7: **5 evaluator agents (wedge personas) + 1 ledgered adjudicator**, rubric v2 verbatim, same-corpus-window discipline, Fleiss κ, per-evaluator control-arm validity, 5-query human-anchor subset (author double-scores), paired commodity-baseline arm licensing only a caveated agent-rated comparative claim; standing disclosure "raters are LLM agents, n_human_raters = 1 (anchor)" | **RESOLVED 2026-08-03 (Pedro + design frozen this pass)** — study itself still to run |

Standing rules unchanged: on any engine change that invalidates a paper number,
append a row BEFORE the paper is next touched; index-lag is itself a ledger
trigger. Still open from PR3: `role_noise_rate` calibration; temporal hold-out
remains DATA-LIMITED for batch-03 (the gold day series now provides task-level
temporal structure, but it is not a classification hold-out).
