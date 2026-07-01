# Paper Staleness Ledger (PR3.0)

Date opened: 2026-07-01 · Owner: engine track · Status: **ACTIVE** (PR3.1 + PR3.3
doc pass done 2026-07-01 — 6 resolved, 1 partial, 4 experiment rows open; see the
"PR3 reconciliation pass" note at the bottom)
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
| **PR3-02** | P1 skeleton §Benchmark; labeling-guide; methodology-outline validation-map | benchmark = **30 atlas_topics × 4 buckets**, "256 rows / 30 topics" | R3.2 collapses atlas_topics from a served population to an attribute; served pop = **348 stories** (R3.7) | **PR3.2:** re-scope P1 benchmark as measuring the crisis-ANCHOR precision; add open-set category coverage/coherence for emergent extensions | **PARTIAL 2026-07-01** — the reject-GATE≠TYPING note + open-set framing added to P1 (§"Reject GATE ≠ category TYPING", canonical-regime open-set language); the FULL re-scope (a formal benchmark section measuring crisis-anchor precision + an open-set coverage/coherence metric for the emergent extensions) is a PR3.2 authoring task, not just a footnote — REMAINS OPEN |
| **PR3-03** | P6 master-plan L448-451; P8 skeleton baseline L26/L115 | topic set **FROZEN**, "last updated 06-29 17:00, 54/68 active >3d stale, lifecycle not retiring" (present tense) | FIXED — former revived mindful/off-peak (P8 Intervention-1); R1 wrote 731 clusters; 392→348 served | **PR3.3:** rewrite frozen claims to past-tense before/after; note R3.7 (B1 retirement) as the lifecycle fix | **RESOLVED 2026-07-01** — master-plan P6 dynamism bullet + P8 SHARPENED bullet + P8 skeleton baseline section all past-tensed to before→after (68→392→348, R3.7 retirement cited as the lifecycle fix); P8 baseline header banner-marked SUPERSEDED |
| **PR3-04** | R3 spec v1 §2 vs CLAUDE.md top | "candidate-v2 NOT wired" ‖ "v2 reject gate LIVE" read as a contradiction | BOTH true: the reject GATE (binary demote) is live; category TYPING is unbuilt — different ops | fixed in R3 v3 §2/§3.1 (reject≠typing); no paper edit, but note in P1 taxonomy section | **RESOLVED 2026-07-01** — spec already resolved; the P1 taxonomy-section note now added (§"Reject GATE ≠ category TYPING", clarifying `apply_v2_reject.py` binary demoter vs R3.1 `compute_category_typing.py`) |
| **PR3-05** | master-plan L96-104; unified-engine; gdelt-decoupling; R3 §4.1 | `gdelt_hint_ablation.py` is the reproducibility GATE on the 41.6% | BUILT + RUN 2026-07-01 | **PR3.4 / §4.1 build-dep:** build `gdelt_hint_ablation.py` before any theme-hint change; it is a required P1 result (recall-delta on theme-drop) | **RESOLVED 2026-07-01** — `backend/scripts/gdelt_hint_ablation.py` + report `docs/research/embedding-ablation/2026-07-01-gdelt-hint-ablation.md`. RESULT: theme-hint-dependent assignments (lex_count=0) are 20.2% correct ≪ 40.9% baseline = net NOISE; ablated (lexicon-standalone) precision 40.9%→**48.3%** (+7.4pp); recall cost 35 corrects (13%), 86–100% semantically recoverable at a moderate cut (threshold-cliff, [0.73,0.80] band). VERDICT: REMOVE-OK on the §3.2 noise branch. Theme-hint change is now unblocked. |
| **PR3-06** | master-plan cross-ref index (L716, "Updated 2026-06-26") | index has no row for unified-engine F0-F3, the A/B, candidate-v2/κ, R0-R3, R3 | the index (the map) lags the engine by ~5 weeks; P1/P8 skeletons were updated past it | **PR3.3:** append F0-F4 / R0-R3 / candidate-v2 / R3 rows; make index-lag a standing ledger trigger | **RESOLVED 2026-07-01** — index re-dated 2026-07-01 with 9 new rows (R3 unification, R3.1 typing, crisis-relevance lens, R1 scoped, R2 umbrella, R3.7 retirement, F3 A/B, F0–F2, canonical regime); index-lag noted as a standing ledger trigger |
| **PR3-07** | master-plan pub-order L674; P1 close-criteria L179-186 | "Paper 1 closes 4-8 weeks from [2026-05-27] with current data + mig-042" | 5 weeks elapsed; mig-042 lexicon + 30-topic benchmark superseded by the unified engine + candidate-v2; the A/B + κ are now P1's two biggest sections | **PR3.1/PR3.2:** absorb A/B + κ-0.739 + R3.1 precision-lift into the close-criteria | **RESOLVED 2026-07-01** — master-plan pub-order Paper-1 line rewritten: the 4–8-week/mig-042 estimate marked superseded; close-criteria now name the A/B, κ base, canonical regime, and R3.1 lift, with the unbuilt experiments (PR3-05/09/10) as the remaining gates |
| **PR3-08** | master-plan P8 L594 vs P8 skeleton | coverage "**0.2%**" ‖ "**5.6%** embedded / **2.5%** total" | different denominators (served/ingested vs embedded/embedded), presented without them → looks inconsistent | **PR3.3:** cite the denominator each time; defer to the P8-skeleton precise figures | **RESOLVED 2026-07-01** — master-plan P8 "0.2%" line now carries an inline denominator gloss (served÷ingested vs 5.6%-of-embedded/2.5%-of-ingested), both flagged as superseded "before" numbers pointing to the scoped-pass lift |
| **PR3-09** | P1 + P8 validation-plan §Baseline-families | ≥1 EXTERNAL baseline (BERTopic / flat-embedding / TDT / event-graph) REQUIRED for submission | BUILT + RUN 2026-07-01 | **PR3.4:** build ≥1 external baseline; the internal A/B alone does not meet the stated bar | **RESOLVED 2026-07-01** — `backend/scripts/external_baseline_comparison.py` + report `docs/research/embedding-ablation/2026-07-01-external-baseline.md`. Panel (KMeans + Agglomerative flat-embedding + HDBSCAN-global = BERTopic core) over the same e5 corpus. RESULT: HDBSCAN-global (the standard density method) CLIFFS at every mcs — mega-blob (43.6%@mcs10) or collapse (4.6% cover@mcs25, 0 topics@mcs75) = the measured justification for Atlas's scoped design. Flat KMeans/Agglo reach coherence PARITY (0.88/0.87 vs Atlas 0.849) but in-sample + no identity/lifecycle/noise-rejection. Honest takeaway: Atlas's edge is scoping (dissolves the cliff) + lifecycle, NOT raw one-shot coherence. BERTopic-proper (UMAP+cTFIDF) is the py3.12 follow-up (numba-blocked on py3.14). |
| **PR3-10** | P1 methodology-outline §8; master-plan Master-criteria | temporal hold-out week; `role_noise_rate` calibration; anchoring-effect (30 blind vs hinted); Wilson/bootstrap CIs; **crisis-only in-category κ split** — all "not started" | R3.1/R3.2 measure on 168h windows with no temporal hold-out, no CIs, no anchoring control on the LLM-in-loop typing; the crisis-only precision (the real successor to 41.6%) is UNMEASURED | **PR3.4:** schedule each as a ledger row with an owner; gate R3.1's precision claim on them | **PARTIAL 2026-07-01 (3 of ~5 done)** — (1) Wilson + bootstrap(5000) CIs on the PR3-05 ablation (`2026-07-01-ablation-cis.json`): baseline 40.9% [37.2,44.7], ablated 48.3% [43.8,52.7], Δ +7.4pp [5.2,9.6] (excludes 0), theme-dependent 20.2% [14.9,26.8] (non-overlapping). (2) inter-annotator κ (`2026-07-01-gold-kappa.json`): Fleiss binary 0.734 / 4-cat 0.623 = substantial → the gold is reliable. (3) **crisis-only precision = the successor to 41.6% (`2026-07-01-crisis-only-precision-and-kappa.md`): 53.8% (170/316)** vs 40.9% baseline; out-of-scope force-fits are 49.2% of usable at 27.1% → they pin the headline number, not the crisis classifier. REMAINS: temporal hold-out week, anchoring-effect control (blind vs hinted), `role_noise_rate` calibration. |
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
- **PARTIAL (1):** PR3-02 — the reject-GATE≠TYPING clarification + open-set framing
  landed in P1, but the full benchmark-universe re-scope (a formal crisis-anchor
  precision section + an open-set coverage/coherence metric for emergent categories)
  is a PR3.2 *authoring* task and REMAINS the open doc-track item.
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
