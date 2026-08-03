# Atlas Papers — Reorganization around the true purpose (justification, not superiority)

Date: 2026-07-16
Status: proposal (does NOT overwrite the master plan; a parallel session is editing it)
Author: review + reorg pass
**STATUS 2026-07-16 — the reorganization is DRAFTED (this doc = the map; the
drafts = the deliverable):**
- `2026-07-16-paper-A-answerability-first-benchmark.md` — backbone (evidence-role
  benchmark + methodology + taxonomy ensemble).
- `2026-07-16-paper-B-nothing-is-assumed.md` — the 4 measured refutations.
- `2026-07-16-paper-C-global-measured-claim.md` — voice ownership + open-set coverage.
- `2026-07-16-systems-interface-tech-report-p5-p6-p7.md` — P5/P6/P7 justified-design.
- `2026-07-16-coverage-metric-canonicalization.md` — denominator reconciliation.
All four papers: comparative language stripped, LLM baseline reframed as
calibration, LLM-panel-gold disclosure foregrounded, whitening walk-back +
anchoring-within-noise stated honestly (independently audited PASS). The old
master plan is NOT overwritten (a parallel session edits it); reconcile via the
old→new map in §3 when that session closes.

Anchors in existing canon:
- `2026-05-27-atlas-papers-master-plan.md` (the 8-paper index being reorganized)
- `2026-05-25-...state-of-art-and-validation-plan.md` ("make a paper **defensible**";
  working title **"An Answerability-First Framework"**)
- `2026-07-01-paper-staleness-ledger.md` (the honesty audit these reframes must respect)

---

## 0. The correction that reorganizes everything

The papers were never meant to argue *"Atlas is amazing / Atlas beats X."*
Their purpose (Pedro, 2026-07-16, and already implicit in the 2026-05-25
validation plan) is:

> **Everything Atlas shows the analyst is VALID because it is backed by
> measured math, inference, and experiment. Nothing is assumed — not even the
> things we chose NOT to do.**

The value proposition is **defensibility**, not victory. Under that lens, the
biggest weakness a competitive read finds — *"7 of 8 papers make a comparative
superiority claim that is never measured"* — is not a missing experiment. **It is
a framing bug.** Comparative language ("more predictive than", "supports the
seven questions better than per-topic", "measurably better than commodity
dashboards") leaked into the master-plan *Core claims* and mis-labels the work.
The actual contribution of most papers is:

> *We measured the intuitive shortcut everyone assumes, found it misleading,
> and therefore justified a non-obvious design.*

That reframe **rescues** most of the series, because the negatives and the
honest-limits — which a superiority read treats as "missing" — become the whole
point. A justification paper is *supposed* to say "here is what we ruled out."

---

## 1. The reframing template (apply to every paper)

Every paper section becomes a **justified design decision**, in this fixed shape:

1. **Decision** — the concrete thing Atlas ships / shows.
2. **Stakes** — why it could be arbitrary / why the obvious choice is tempting.
3. **Backing** — the math + inference + experiment that makes it non-arbitrary
   (with N, CI, script path).
4. **Alternatives ruled out** — the naive option we *measured* and rejected
   (this is where the "negatives" live, and they are strengths here).
5. **Honest limit** — what is NOT yet backed, stated plainly (in-window only, no
   temporal hold-out, LLM-panel gold, etc.).

Two rules that come free from this framing and fix the fatal flaws at once:

- **The LLM baseline is a CALIBRATION REFERENCE, not an opponent.** "A zero-cost
  static classifier sits ~37pp below an expensive model *on the same key*" is a
  legitimate calibration statement. "Atlas beats/approaches the LLM" is a race we
  never needed to enter, and it is the claim that trips the LLM-as-gold
  circularity. Say *calibration*, and disclose in every methods section: **"gold
  = agreement with a 3-LLM panel; n_rows_with_human_gold = 0."**
- **Drop every bare comparative adjective** ("better", "more predictive",
  "fewer false positives *than*") unless a like-for-like baseline was actually
  run. Replace with the justification form ("the obvious proxy is measurably
  wrong, therefore this design").

---

## 2. Per-paper reframe (comparative → justification)

For each: the leaked superiority claim, the reframed justification thesis, the
backing that ALREADY exists, and the one gap. `CHEAP` = language-only rewrite.
`+EXP` = needs one measurement to be fully honest.

### P1 — Evidence-role classification + distillation  `CHEAP + one EXP`
- **Leaked:** "lifts precision *toward LLM baselines*."
- **Reframed:** *The evidence-role schema is the justified classification design
  because (a) we measured that a single layer collapses semantic roles [error
  anatomy: off_topic + scope_mismatch dominate, substring noise only 0.6%];
  (b) the lexicon is LLM-distilled and reproducible at $0 inference; (c) we
  measured what the naive components actually contribute — **GDELT theme-hints
  are net noise: 20.2% [14.9,26.8] vs 40.9% baseline; removal → 48.3%, Δ+7.4pp
  CI [5.2,9.6] excludes 0** at ≤13% recall cost. The LLM zero/few-shot numbers
  (78.6% / 81.1%) are a **calibration reference on a shared key**, not a race.*
- **Backing (real):** `gdelt_hint_ablation.py` + JSON + consensus-gold 691 rows;
  N=660 3-vendor benchmark recomputes to the decimal (seed 20260527).
- **Gap (corrected 2026-07-16 after inline verification):** the whitening→HDBSCAN
  raw-vs-whitened recall/purity ablation is **already run** (`cluster_whiten_sweep.py`,
  3 samples, 2026-07-07) and the answer is a **nuanced negative** — whitening
  cures the signal-*pair* geometry (AUC 0.985; 4.4× separation) and *stabilizes*
  density clustering, but does **not** by itself cross the cluster-level
  recall/purity cliff (recall was high-variance 0.477/0.062/0.109 across samples).
  So the honest P1/P8 claim is "geometry cure + stabilizer," not "the recall
  lever" — the recall win is the scoped-partition lever (§P8). The **anchoring
  control also already ran** on crisis-only (`2026-07-01-anchoring-control.json`:
  blind 48.2% n=390 vs hinted 53.8% n=316 → the 5.6pp effect is **within noise**,
  two-proportion z=1.48, p≈0.14). Real remaining +EXP: extend the anchoring
  control to the full N=660 *headline* (light recompute), and BERTopic-proper.
  **This is the backbone paper — it earns the right to measure.**

### P2 — Cross-source source quality  `CHEAP` (fully rescued)
- **Leaked:** composite is "more predictive of analyst-useful evidence than any
  single signal."
- **Reframed:** *Why Atlas separates WHO-speaks from WHO-is-spoken-about and
  scores self-voice by **ownership, not language**: because volume maps launder
  perspective, and we made it a number — Iran self_voice **1.4%** (98.6%
  foreign), diversity_score **3.3 → 23.9**, voice_entropy **0.71** over 89
  countries. BBC Persian on Iran is soft-power, not Iranian voice; the ownership
  rule is justified because the language rule is measurably wrong.* The composite
  is an **honesty instrument that makes "global" a measured claim** — predictive
  usefulness is explicitly future work.
- **Backing (real):** `voice_mix_audit.py`, `/api/v2/voice-mix`, versioned
  baseline JSON. Reproducible.
- **Gap:** none for the reframed thesis. (Only the old, dropped, predictiveness
  claim needed data.)

### P3 — Composite heat  `CHEAP`
- **Leaked:** "fewer volumetric false positives *than* raw counts."
- **Reframed:** *Why heat is a 7-component composite and not volume rank: because
  we measured volume ≠ importance — **Kendall-τ(composite, volume) = −0.198**,
  top-8 overlap **0/8**. The composite is the justified choice precisely because
  the obvious one is measurably not a proxy for it. Per-component ablation shows
  each signal's contribution.* No claim of "accuracy" against an unmeasured
  ground truth — the design only requires "not a volume proxy," and that is what
  is shown.
- **Backing (real):** `country_heat_v2` matview, `/heat/countries` N=200 pull.
- **Gap:** the pull has no reproducible harness (one live snapshot) — wrap it in a
  script if it stays load-bearing. Correctness-vs-analyst is out of scope by
  design; don't claim it.

### P4 — Thread aggregation + evidence sampling  `CHEAP` (the cleanest nugget)
- **Leaked:** thread contract "supports the seven questions *better than*
  per-topic aggregation."
- **Reframed:** *Why the thread ranking is `0.45·log-vol + 0.35·movement +
  0.20·coherence` and — the sharp part — why it deliberately has **no**
  syndication/`headline_diversity` penalty: because we measured that reprint
  count and domain diversity **cannot** separate real news from filler. "Iran
  attacks Bahrain" (116 reprints / 115 domains) is structurally identical to a
  sausage-rolls recipe (92 / 92); a diversity penalty would false-demote real
  news. The design is justified by the alternative we ruled out. **Nothing
  assumed — even the non-decision is backed by a measurement.***
- **Backing (real):** `thread_ranking.py` (6 tests), syndication audit.
- **Gap:** none for the reframed thesis. (This is the runner-up publishable
  result — a clean refutation of an obvious metric.)

### P5 — Sentiment fusion + multilingual NLP  `CHEAP` (honesty-of-limits IS the content)
- **Leaked:** fusion is "more faithful to human sentiment *than* either source
  alone."
- **Reframed:** *Why sentiment is a confidence-weighted fusion, and why we
  **disclose where multilingual NER fails instead of assuming coverage**: the
  fusion + the 2.37 scale are design choices we state the derivation for; and
  rather than assume the multilingual pipeline works, we measured it broken
  (non-Latin NER returns nothing on Persian/Arabic/CJK; xlm tokenizer breaks in
  prod) and label those subjects `unverified` via the gazetteer.* The
  contribution is **not fabricating a capability we don't have** — the honest
  negative, not a faithfulness win.
- **Backing (real):** NER-throughput + real-fix-evaluation docs (measured the
  failure).
- **Gap:** the "faithfulness" number was inter-source agreement, not accuracy —
  so **drop the faithfulness framing entirely**; keep the honesty framing. No new
  experiment needed for the reframed (limits) thesis.

### P6 — Temporal model (hot/cold, buckets)  `CHEAP, but weakest — see §4`
- **Leaked:** two-tier architecture as a systems-superiority claim.
- **Reframed:** *Why the hot/cold boundary sits where it does: retention is set by
  **measured** catch-up behavior (the runner default silently held hot at 1–2
  days → fixed to 168h), not by a round number; bucket granularity chosen from
  the query patterns it serves.*
- **Gap (+EXP):** the two numbers a systems venue demands — **latency-per-bucket
  and cost-per-row across tiers** — are unmeasured. Until they exist this is a
  **justified-architecture appendix of the backbone paper, not a standalone
  paper.**

### P7 — Visualization + analyst workflow  `CHEAP reframe, but gated`
- **Leaked:** viz decisions make Atlas "*measurably better* at the seven analyst
  questions *than commodity dashboards*." (This one is currently **false**, not
  merely unproven — no analyst study exists.)
- **Reframed:** *Why each visualization decision is **honest-by-construction**:
  Equal-Earth = equal-area (no size lie); "positions approximate · relations
  exact" (PCA top-2 = 17%, labeled); `relationActive=false` → surfaces stay
  global rather than **fabricate** a relation; orbit radius = the classifier's
  own cosine distance, so the view is **falsifiable against the engine**;
  rarity-weighted relations because naive entity-overlap launders common actors
  (measured: "donald trump" in 14 of 30 concurrent threads).* The claim is the
  **validity/honesty of the representation**, which is exactly your thesis.
- **Gap:** the comparative "better than commodity" claim must be **dropped or
  gated** on a small analyst study (10–15 users, task-time). The honesty claims
  stand alone today; the superiority claim does not.

### P8 — Open-set discovery + taxonomy evolution  `CHEAP reframe + one EXP`
- **Leaked:** coverage/"54× more narratives" superiority + a "semi-automated
  taxonomy-evolution loop" that is partly **unbuilt**.
- **Reframed:** *Why discovery is scoped-per-country, and why we did **not**
  accept the recall ceiling as intrinsic to short-text news: we measured the
  global HDBSCAN purity/recall cliff, then measured that **scoped partitioning
  dissolves it (4.94% → 26.72% across 117 countries)** and that e5 anisotropy —
  not separability — was the cause (**signal-pair AUC 0.985**; all-but-top-k
  whitening opens the gap 4.4×/7×). The design is justified by measuring the
  alternative's failure mode.*
- **Gap:** report only what ran (the taxonomy-evolution **loop** is a robot
  artifact, status "parking" — don't title the paper after it); reconcile the
  coverage denominators into ONE defined metric; kill the "54×" cross-country
  double-count. The whitening→HDBSCAN ablation is **already run** (nuanced
  negative, §2 P1) — frame the recall win as the scoped-partition lever
  (4.94%→26.72%), with whitening as the geometry-cure/stabilizer, not the lever.

---

## 3. Recommended reorganization: 8 loose seeds → a 3-paper justified core (+ 1 systems report)

The reframe makes the real spine obvious. Consolidate so each paper is
independently defensible and stops double-counting the same ~4 results.

**Paper A — "Answerability-First Narrative Intelligence: an evidence-role
benchmark and validation methodology."**
Absorbs: P1 + the methodology outline + the **taxonomy-revision ensemble**
(multi-model/multi-persona annotation, Fleiss κ, OUT_OF_SCOPE reject class,
agreement 76%→96%) + the answerability-first frame. *This is the paper that earns
the right to measure; every other paper cites its benchmark and its
LLM-panel-gold disclosure.* **Load-bearing. Closest to submittable.**

**Paper B — "Nothing is assumed: measured refutations of intuitive
narrative-signal proxies."**
Absorbs: P3 (volume ≠ importance) + P4-syndication (reprint ≠ value) + the
movement backtest (velocity does **not** lead volume, Spearman −0.477) + the P1
theme-hint ablation (hints are net noise). *This is the literal embodiment of
your thesis — four intuitive shortcuts, each measured and ruled out. None
survives as a standalone paper; together they are a genuinely citable
contribution.*

**Paper C — "Making 'global' a measured claim: voice ownership and open-set
coverage."**
Absorbs: P2 (voice/ownership honesty instrument) + P8-reframed (scoped
partitioning + whitening cure). *Both are "we measured the thing everyone assumes
— diversity, an intrinsic recall ceiling — and it was false/curable."*

**Systems & interface tech report (promote to papers only when their one missing
study exists):** P5 (sentiment honesty-of-limits) + P6 (temporal architecture,
needs latency/cost benchmarks) + P7 (honest-by-construction viz, needs the
analyst study). Ship as a technical report / appendix now; P7 graduates to a
standalone CHI/VIS design paper the moment a 10–15-user task-time study runs.

Old → new map: P1→A · P2→C · P3→B · P4→B(+system contract in report) · P5→report
· P6→report · P7→report(→standalone later) · P8→C · taxonomy-ensemble→A ·
backtest→B.

---

## 4. Cost of each move

**Pure language (do now, in the other chat's edit pass):** every §2 reframe
marked `CHEAP` — strip comparative adjectives, restate as justification, relabel
the LLM baseline as calibration, add the one-line LLM-panel-gold disclosure to
each methods section. This alone removes the single biggest reviewer objection
and makes the series read as what it is.

**Experiment status (corrected 2026-07-16 — two of the three "needed" experiments
already ran; verify before re-running):**
- whitening → HDBSCAN ablation — **DONE** (nuanced negative: stabilizer, not the
  recall lever; §2 P1). No re-run needed; **incorporate the walk-back honestly**.
- anchoring control — **DONE on crisis-only** (5.6pp within noise, z=1.48). Only
  the extension to the full N=660 *headline* remains (light recompute, serves A).
- BERTopic-proper (UMAP+c-TF-IDF) external baseline — **genuinely unrun**, blocked
  on the numba/py3.14 toolchain. The one real open experiment; isolates the
  schema's own contribution.

**Gated (don't claim until the study exists):** P7 "better than commodity"
(needs analyst study); P6 systems-superiority (needs latency/cost).

**Housekeeping (corrected 2026-07-16 after inline check):**
- reconcile coverage denominators into one metric — see the reconciliation doc.
- delete/caveat the "54×" double-count — real, do it.
- `bootstrap-batch-02.json` — **confirmed genuinely broken** (all zeros; input
  path resolved to 0 rows) and **superseded by `bootstrap-combined-01-02.json`**.
  Regenerate or remove; do NOT cite it.
- `2026-05-29-scope-gate-v1.json` — **NOT missing** (false alarm from the review):
  it exists and is valid at
  `phase-1-validation/models/2026-05-29-scope-gate-v1.json` (OpenAI 1538-dim,
  real scaler). No action.
- stop "doc track CLOSED" language while successor precision is still
  range-valued, in-window, and panel-relative.

---

## 5. One-paragraph version (for the other chat)

The papers are a **justification layer**, not a superiority pitch — "what Atlas
shows is valid because it is backed by math + inference + experiment, and nothing
(not even the non-decisions) is assumed." Rewrite every *Core claim* from
comparative ("better than X") to justified-design ("the obvious proxy is
measurably wrong → therefore this design → here is what we ruled out → here is the
honest limit"), and relabel the LLM baselines as a **calibration reference on a
shared key** with a plain "gold = 3-LLM-panel agreement" disclosure. That single
reframe turns the series' apparent weakness (unmeasured comparative claims) into
its actual strength (measured refutations of intuition). Then consolidate the 8
seeds into **A** (evidence-role benchmark + methodology + taxonomy-ensemble),
**B** ("nothing is assumed": volume≠importance + syndication≠value +
velocity-doesn't-lead + theme-hints-are-noise), **C** ("global as a measured
claim": voice-ownership + scoped-discovery/whitening), and a **systems/interface
tech report** (P5/P6/P7) that graduates to papers when their one missing study
exists.
