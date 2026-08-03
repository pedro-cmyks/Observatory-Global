# Paper A — Answerability-First Narrative Intelligence: an evidence-role benchmark and validation methodology

**Status:** skeleton (not a full manuscript) · **Date:** 2026-07-16
**Series role:** backbone. This paper *earns the right to measure*; Papers B and C
cite its benchmark and its LLM-panel-gold disclosure.
**Reframe authority:** `docs/research/atlas-paper/2026-07-16-papers-reorganization-justification-framing.md`
(the papers are a **justification layer** — "everything Atlas shows is valid because
it is backed by measured math, inference, and experiment; nothing is assumed, not
even the non-decisions" — **not** a superiority pitch).

> **Standing disclosure, repeated in every methods and limitations section.**
> Precision, throughout this paper, means **agreement with a 3-LLM consensus panel**
> (majority vote of `claude-sonnet-4-6`, `gpt-4.1`, `deepseek-chat`). The count of
> rows adjudicated by a **human** is **n_rows_with_human_gold = 0**. Every "precision"
> number is panel-relative. The LLM baselines are a **calibration reference on a
> shared answer key**, never an opponent Atlas is racing.

---

## Title / target venue

**Title:** *Answerability-First Narrative Intelligence: an evidence-role benchmark
and an LLM-panel validation methodology for zero-cost topic classification.*

**Target venue:** a measurement/eval track — e.g. NLP+CSS / *ICWSM* (computational
social science, media monitoring) or a *EMNLP/NAACL* resource-and-evaluation track.
The contribution is a **reproducible benchmark + a validation methodology with an
honest gold-provenance story**, not a leaderboard result.

---

## Abstract (≈150 words)

Narrative-intelligence systems must tell an analyst not merely *what topic* a news
signal touches but *what evidentiary role* it plays — is it primary evidence, context,
a reaction, or noise. We argue this "answerability-first" framing is a design
*decision that must be justified*, and we build the measurement apparatus to justify
it. On a stratified 3-vendor LLM-consensus benchmark (N=660 usable; Fleiss κ=0.625),
a zero-inference-cost static classifier reaches 41.6% panel-agreement precision
[37.8, 45.5], calibrated against an LLM reference at 78.6% zero-shot on the same key.
We then decompose *why*: errors are semantic (off-topic and scope-mismatch dominate;
substring noise is 0.6%), GDELT theme-hints are a measured net-noise source
(theme-only precision 20.2% vs 40.9%; removal +7.4pp, CI [5.2, 9.6]), and a
100%-crisis taxonomy with no reject class force-fits non-crisis content. A
multi-model / multi-persona ensemble raises inter-annotator agreement 76%→96% by
adding an OUT_OF_SCOPE class. We report every honest limit, including that our own
de-biasing (anchoring) control is within noise. Gold is LLM-panel consensus;
human-adjudicated rows: zero.

---

## 1. Thesis (in justification form)

Atlas ships an **evidence-role classifier over a curated crisis taxonomy, distilled
into a $0-inference lexicon, with a reject class and a scope gate**. Each of those is
a *choice that could have been arbitrary*. The competitive-superiority question
("does Atlas beat X?") is the wrong question and the one that trips the
LLM-as-gold circularity. The question this paper answers is:

> **Is each classification-design decision non-arbitrary — backed by a measurement
> of the naive alternative — and is the measurement apparatus itself honest about its
> gold?**

The contribution is therefore two-part and defensive:

1. **A benchmark + validation methodology** that can *tell* whether a design decision
   is justified: stratified sampling, an independent 3-LLM consensus panel with a
   reported Fleiss κ, Wilson + stratified-bootstrap intervals, and a written
   gold-provenance disclosure (LLM-panel, zero human rows).
2. **Five justified decisions** measured on that apparatus (§3): the evidence-role
   schema, the LLM-distilled lexicon, the removal of GDELT theme-hints, the
   OUT_OF_SCOPE reject class, and the scope gate — each with the naive alternative
   measured and ruled out, and each with its honest limit stated (including one case,
   the anchoring control, where our own de-biasing turned out to be within noise).

We take the LLM baseline strictly as a **calibration reference**: a static,
zero-cost classifier sitting ~37pp below an expensive model *on the same answer key*
is a legitimate calibration statement about how far a cheap method is from a semantic
reader — not a claim that either "wins."

---

## 2. Related work (honest positioning, no strawman)

- **GDELT / GDELT-GKG themes & EventRegistry.** GDELT-GKG's theme taxonomy is a
  keyword-driven, high-recall event/theme layer; EventRegistry and Media Cloud
  provide large-scale multilingual news aggregation and clustering. We *use* GDELT
  themes as an input and treat them as a hypothesis to test, not a ground truth:
  §3.3 measures that theme-hints are net noise on our key. We do not claim GDELT is
  "wrong"; we claim its theme overlap is a *low-precision candidate generator* for
  crisis assignment, and we measure it.
- **BERTopic + c-TF-IDF and neural topic modeling.** BERTopic (UMAP → HDBSCAN →
  class-based TF-IDF) is the closest external method to Atlas's discovery layer. We
  position our clustering findings against it honestly: a **BERTopic-proper external
  baseline (UMAP + c-TF-IDF) has not been run** (toolchain block, §7); what we *do*
  report is an HDBSCAN-over-e5 sweep that isolates a recall/purity cliff. We do not
  claim to beat BERTopic — we flag it as the missing external comparator that would
  isolate the schema's own contribution.
- **LLM-as-annotator / LLM-as-judge evaluation.** A growing literature uses LLMs as
  annotators and judges; the known hazards are label drift, single-model bias, and
  circularity when the judge and the system share priors. Our methodology *is* an
  instance of this paradigm and inherits its central caveat; we mitigate with a
  **multi-family panel + reported κ + a fixed, declared gold set**, and we foreground
  the caveat rather than bury it (§6). One of our findings is itself a
  methodological warning: an LLM judge scored against *production* labels is
  confounded by label drift (§3.4).
- **Embedding anisotropy — Mu & Viswanath / Arora et al. "all-but-the-top."** The
  observation that contextual/​static embeddings occupy a narrow anisotropic cone,
  curable by mean-removal + top-principal-direction projection, is directly relevant:
  §3.6 reports that e5 signal embeddings have near-perfect pairwise separability
  (AUC 0.985) masked by scale compression, and that all-but-top-k=1 whitening opens
  the same/different gap 4.4×. We credit this line of work and report a **nuanced
  negative** (whitening cures pair geometry but does not by itself dissolve the
  cluster-level recall ceiling).
- **HDBSCAN.** Density-based clustering with a variable-density model; we use it as
  the discovery substrate and report its parameter-cliff behavior on short-text news
  embeddings as a measured constraint, not a defect.

---

## 3. Design decisions (each in the 5-part template)

### 3.1 Decision: an evidence-**role** schema, not a single topic label

- **Decision.** Every signal→topic assignment carries a *semantic role*
  (primary_evidence / context / reaction / analysis / entity_reference / noise), not
  only a topic label.
- **Stakes.** The tempting, standard design is one flat label per document. It is
  cheaper, matches most topic-modeling output, and "looks done."
- **Backing.** On the N=660 consensus benchmark, incorrect rows are **dominated by
  `off_topic` and `scope_mismatch`**; pure **substring noise is only 0.6%** of
  incorrect rows (RQ2 error-composition artifact,
  `.../reports/llm-baseline/2026-06-02-rq1-error-composition.json`). The errors a
  flat label makes are *semantic role* errors — a reaction or an entity mention
  charged as evidence — which a single layer cannot express or repair.
- **Alternatives ruled out.** The flat single-label classifier *is* Atlas v2 as
  measured (41.6%); its failure anatomy shows the residual is not regex-fixable
  keyword noise (0.6%) but role/scope confusion — so "edit more keywords" is
  measured to be a dead lever.
- **Honest limit.** The evidence-role *schema value* (RQ3) is only **partially**
  measured: the role student (v1) shows semantic errors binary-correctness hides, but
  a role-level precision/recall on a held-out human set does not exist
  (n_rows_with_human_gold = 0).

### 3.2 Decision: an LLM-**distilled** lexicon at $0 inference

- **Decision.** The production classifier is a static multilingual lexicon +
  taxonomy, *distilled* from LLM labels, run at zero per-signal inference cost.
- **Stakes.** The obvious alternative is to call an LLM per signal (78.6–81.1% on our
  key). At Atlas's ingest volume that is a recurring cost and a latency/availability
  dependency.
- **Backing (calibration, not victory).** The LLM reference sits at **78.6% zero-shot
  [75.3, 81.7]** and **81.1% few-shot [77.7, 84.0]**; the static classifier sits at
  **41.6% [37.8, 45.5]** *on the same gold key* — a calibration gap of ~37pp that
  quantifies exactly how much a cheap static method concedes to a semantic reader.
  The distillation makes the lexicon reproducible from a versioned label set at
  $0 inference.
- **Alternatives ruled out.** Per-signal LLM inference is ruled out on cost/latency
  grounds, not accuracy — we *state* that the reference is more accurate on the key
  and treat the 37pp as the price of $0 inference, a design trade the analyst can see.
- **Honest limit.** The distilled artifact is English-majority (batch-03) and has
  **no temporal hold-out** (§6); "distillation preserves the reference's decisions"
  is unmeasured beyond the training window.

### 3.3 Decision: **remove** the GDELT theme-hints (the cleanest experiment)

- **Decision.** Demote GDELT-GKG theme-overlap from a hard candidate-generator to (at
  most) a weak confidence feature.
- **Stakes.** Theme-hints are the intuitive backbone of a GDELT-based classifier;
  four internal docs treated "hints carry precision" as a 🔒 assumption that must not
  be removed.
- **Backing.** `backend/scripts/gdelt_hint_ablation.py` (read-only, repeatable) on the
  batch-03 consensus gold: **theme-hint-dependent assignments are 20.2% correct
  [14.9, 26.8]** versus a **40.9% baseline**; removing the hints (lexicon-standalone)
  **rises to 48.3%**, a delta of **+7.4pp with bootstrap CI [5.2, 9.6] excluding 0**,
  at a recall cost of ≤13%. The theme-dependent interval [14.9, 26.8] and the baseline
  [37.2, 44.7] do **not overlap** — the theme-only path is significantly worse than
  the engine average, i.e. a *net noise source* (the "KILL"-GKG-theme-fires-on-idiom
  hypothesis, measured).
- **Alternatives ruled out.** "Keep the hints, they must help" is the naive belief;
  it is measured false. The 13% true-loss is 86–100% recoverable by the semantic path
  at a moderate cosine threshold (threshold-sensitive; report the curve, not a point).
- **Honest limit.** One benchmark, English-majority; the *ablated* engine assumes the
  lexicon becomes a standalone candidate-generator (an implementation follow-up); no
  temporal hold-out on the ablation itself. **This is the paper's cleanest,
  fully-backed experiment.**

### 3.4 Decision: an OUT_OF_SCOPE **reject class** as the taxonomy fix

- **Decision.** Add a rigorous OUT_OF_SCOPE reject class + per-category
  include/exclude rules to the crisis taxonomy (candidate-v2), rather than expand into
  an all-news taxonomy or add categories.
- **Stakes.** A 100%-crisis taxonomy with no reject option *forces* every non-crisis
  signal into the nearest crisis bucket; the tempting fix is "add more/better crisis
  categories," which the evidence shows is not the problem.
- **Backing.** A **multi-model × multi-persona ensemble** (DeepSeek `deepseek-chat`,
  GPT-4o, GPT-5.5/Codex, Claude-orchestrator; personas: wire-taxonomist,
  ontology-purist, geopolitics-analyst) diagnosed force-fit and measured the fix:
  - *Phase A (diagnosis):* on 50 gate-kept evidence headlines, **30% ensemble-unanimous
    (46% DeepSeek) are OUT_OF_SCOPE** — force-fit into a crisis bucket (a shopping
    article → "Heat health risk"; a book review → "Armed conflict").
  - *Phase C (fix, agreement):* the same headlines under v1 vs v2 prompts →
    inter-annotator agreement **76% → 96% (+20pp)** driven by both annotators agreeing
    on the reject label.
  - *Reliability:* a growing gold base (732 signals across a broad pass; 75%
    3-model-unanimous) with **artifact-reported Fleiss κ in the "substantial" band**
    (`kappa.py`; the artifact reports κ≈0.74–0.80 across label-space/in-category cuts,
    with the value climbing as the base grew — see §6 note on the pending
    final-numbers pass and the κ inconsistency across doc versions).
- **Alternatives ruled out.** "Rename/add categories" is ruled out: both proposing
  personas **kept the ~30 categories** and located the fix in the reject class +
  boundaries. The category *names barely move*; the value is refusing the non-crisis
  half.
- **Honest limit.** The random 72h sample is non-crisis-heavy, so the +20pp is driven
  mainly by agreement on the reject label for the non-crisis majority — the core fix,
  but it under-stresses *crisis-vs-crisis* separability. Gold is LLM-ensemble, not
  human (n_rows_with_human_gold = 0). The three contested categories
  (housing-cost-pressure, humanitarian-access-conflict, mining-royalty-risk) need
  their own targeted κ pulls.

### 3.5 Decision: a scope **gate** (abstain) rather than lowering thresholds for coverage

- **Decision.** Keep a per-topic scope gate that *abstains* on low-confidence rows
  rather than assign everything.
- **Stakes.** The intuitive move for "more coverage" is to lower thresholds; abstaining
  trades recall for precision and looks like "showing less."
- **Backing.** The M1 scope gate lifts precision from **41% to 70.3% at 37.3%
  coverage** on scored rows — i.e. serving the cleanest ~37% at ~70% precision.
- **Alternatives ruled out.** "Assign everything" is the 41% full-taxonomy operating
  point; the gate is the measured way to buy precision at a stated recall price the
  analyst can see (a precision-at-coverage point on a curve, never conflated with the
  full-taxonomy headline).
- **Honest limit — winner's-curse.** The gate's 70.3%@37.3% is **not yet verified on a
  held-out split**: only the downstream *student* model has shown cross-validation, not
  the gate thresholds themselves, which were tuned per-topic to ≥0.90 target precision.
  Until a held-out confirmation exists, treat 70.3% as an in-sample, possibly optimistic
  operating point. (Deployment note: a live A/B reject arm, `gate_model=v2-gate-e5-lr-1`,
  demoted **43.3% (567/1310)** of gate-kept rows as force-fit over 168h — reversible and
  audit-tagged — consistent with the gold-measured force-fit share; this is an
  operational cross-check, not a held-out precision proof.)

### 3.6 Decision (a *non*-decision, still backed): whitening is a geometry cure + stabilizer, **not** the recall lever

- **Decision.** Apply all-but-top-k whitening *selectively* where it measurably helps
  (pair-similarity consumers), and **do not** claim it as the clustering-recall fix.
- **Stakes.** An early result (a single 0.477-recall sample) tempted the claim
  "whitening crosses the recall/purity cliff." Publishing that would have been a
  measure-once error.
- **Backing (measure-twice).** `cluster_whiten_sweep.py` (3 samples, 2026-07-07):
  signal-pair separability is real and reproducible — same/different cosine
  **0.916 / 0.788**, **AUC 0.985**, gap opening **4.4×** after all-but-top-k=1. But the
  initial recall was **high-variance and non-reproducing (0.477 / 0.062 / 0.109 across
  three samples)**, and the best joint HDBSCAN point is `e5_whiten_k1` **recall 0.109 /
  purity 1.0** vs `e5_raw` **recall 0.756 / purity 0.146** — *each at its own
  best-joint config* (`e5_whiten_k1` at `eom mcs=5 ms=1`; `e5_raw` at
  `eom mcs=8 ms=3`); at a **matched** config (`eom mcs=8 ms=1`) raw e5 recall
  collapses to ~0.09 (see Paper C, Table 3). The cliff *persists*; whitening
  picks the purity end.
- **Alternatives ruled out.** "Whitening is the recall lever" is ruled out *by our own
  re-measurement*. The recall/coverage lever is **scoped partitioning** (§ Paper C /
  R1), not whitening.
- **Honest limit.** This is included as an exemplar of the paper's method (measure
  twice; walk back a tempting positive). The clustering-recall consequence is owned by
  Paper C; Paper A owns only the substrate/geometry claim.

---

## 4. Methods

### 4.1 Data & sampling
- **Population:** `signals_v2` news signals; the classifier under test is Atlas v2
  (`theme-hint-lex-v2`), multilingual lexicon + curated GDELT theme-hints, writing
  `signal_topic_assignments` with confidence/gate metadata.
- **Benchmark (canonical regime):** batch-03 — **691 stratified rows** from a 7-day
  window, **660 usable** (31 ties dropped); Atlas-scored subset n=635 (264 correct).
  Stratified across 30 crisis topics × 4 buckets.
- **Taxonomy-ensemble sampling:** two strata, deduped by headline — (1) stratified
  gate-kept evidence (every category represented) and (2) representative full-stream
  random (336h, gate-agnostic) so the OUT_OF_SCOPE decision is measurable on the
  ~91%-out-of-scope real distribution.
- **No temporal hold-out anywhere** (§6): batch-03 rows carry no timestamps and the
  underlying signals were purged under retention, so all generalization language is
  hedged to in-window.

### 4.2 Labels & gold provenance (the disclosure, in full)
- **Consensus benchmark gold** = majority vote of a 3-vendor panel:
  `claude-sonnet-4-6`, `gpt-4.1`, `deepseek-chat`. **Fleiss κ = 0.625** (the artifact
  additionally reports a binary correct-vs-not κ = 0.734 on a 684-row 3-annotator
  subset — "substantial," Landis–Koch).
- **Taxonomy-ensemble gold** = majority vote of scriptable annotators (DeepSeek,
  GPT-4o, Codex/GPT-5.5) with Claude-orchestrator adjudication of 3-way disagreements;
  each record carries `n_votes`/`agree_n` provenance and an e5-embedding flag.
- **n_rows_with_human_gold = 0.** Every precision number is agreement with an LLM
  panel; the LLM zero/few-shot baselines are a **calibration reference on the shared
  key**, not opponents.

### 4.3 Metrics & statistical conventions
- **Precision** = panel-agreement (correct / labeled).
- **Intervals:** Wilson score interval for every proportion; **stratified bootstrap**
  (10,000 resamples, seed 20260527) for the headline and for ablation deltas. A delta
  is called significant only when its bootstrap CI excludes 0 (e.g. theme-hint removal
  +7.4pp [5.2, 9.6]).
- **Reliability:** Fleiss' κ for ≥3 annotators; Cohen's κ / pairwise agreement for
  2-annotator cuts; report the κ *and* the label-space size (a 32-way + reject task).
- **Significance tests:** two-proportion z where two independent samples are compared
  (e.g. the anchoring control, §5).

---

## 5. Results (real numbers)

### R1 — Headline benchmark (calibration reference on a shared key)
| Method | Precision | Wilson 95% | Bootstrap 95% | n (labeled) | Gold |
|---|---:|---|---|---:|---|
| Atlas v2 (static, $0 inference) | **41.6%** | [37.8, 45.5] | [38.4, 44.7] | 635 | 3-LLM panel (κ=0.625) |
| LLM zero-shot *(calibration ref)* | 78.6% | [75.3, 81.7] | [75.8, 81.3] | 627 | same key |
| LLM few-shot *(calibration ref)* | 81.1% | [77.7, 84.0] | [78.2, 83.9] | 597 | same key |

*Reading:* a zero-cost static classifier sits ~37pp below the semantic reference on
the same key. This is a calibration statement, not a contest.

### R2 — Error composition (why the residual is not regex-fixable)
| Failure bucket | Share of incorrect rows |
|---|---|
| off_topic | largest |
| scope_mismatch | second |
| substring noise | **0.6%** |

### R3 — Theme-hint ablation (fully backed)
| Engine | Correct / usable | Precision | Wilson 95% |
|---|---:|---:|---|
| baseline (theme-hints on) | 270 / 660 | 40.9% | [37.2, 44.7] |
| theme-hint-dependent path only | 35 / 173 | **20.2%** | [14.9, 26.8] |
| ablated (lexicon-standalone) | 235 / 487 | **48.3%** | [43.8, 52.7] |
| **Δ ablated − baseline** | — | **+7.4pp** | bootstrap [5.2, 9.6] (excludes 0) |

> **Denominator footnote (same classifier, two numbers — not a conflict):** the
> headline **41.6%** is over the n=635 *gate-scored* subset; the ablation
> **40.9%** is over the full n=660 benchmark denominator (270/660). Same static
> classifier, different scoring population — chain neither as if the other.

### R4 — Taxonomy reject class (ensemble)
| Measurement | v1 | v2 (reject class) |
|---|---:|---:|
| inter-annotator agreement (Phase C, 72h sample) | 76% | **96%** |
| Phase A force-fit (OUT_OF_SCOPE, ensemble-unanimous / DeepSeek) | 30% / 46% | — |
| gold base reliability (Fleiss κ, artifact-reported, "substantial" band) | — | κ≈0.74–0.80 (final-numbers pass pending) |

### R5 — Scope gate (winner's-curse caveat attached)
| Operating point | Precision | Coverage |
|---|---:|---:|
| assign-everything (full taxonomy) | 41% | 100% |
| M1 scope gate | **70.3%** | 37.3% |
*Not yet held-out-validated on the gate thresholds themselves — treat as in-sample.*

### R6 — Anchoring control (honesty about our own de-biasing)
| Framing | Crisis-only precision | n | IN-rate |
|---|---:|---:|---:|
| hinted (assigned category shown) | 53.8% | 316 | 47.9% |
| blind (unanchored) | 48.2% | 390 | 59.1% |

*The 5.6pp "anchoring effect" is **within noise**: two-proportion z = 1.48, p ≈ 0.14
(not significant).* Consequently we **do not** present a clean "48–54% de-biased
successor to 41.6%": that band is a point-pair across two samples (not a CI), on a
**changed denominator** (crisis-only, force-fits excluded) versus the 41.6% headline
(all usable assignments). The two numbers are **bridged, not interchangeable**, and
the crisis-only control has **not** been retro-applied to the full N=660 *headline*
(an open, light recompute — §7).

### R7 — Substrate geometry (measure-twice exemplar)
| Space | same p50 | diff p50 | gap | AUC |
|---|---:|---:|---:|---:|
| e5 raw (signal-pair) | 0.916 | 0.788 | +0.13 | **0.985** |
| all-but-top k=1 (signal-pair) | — | — | +0.57 (4.4×) | ≈0.985 |

*Whitening cures pair geometry and stabilizes density clustering; it does **not** by
itself cross the cluster-level recall/purity cliff (recall non-reproducing 0.477 /
0.062 / 0.109 across 3 samples). The recall lever is scoped partitioning — Paper C.*

---

## 6. Limitations

1. **LLM-panel gold, not human gold (stated first, everywhere).** Every precision
   number is agreement with a 3-LLM consensus panel; **n_rows_with_human_gold = 0**.
   The multi-family panel + reported κ (0.625 benchmark; "substantial" band for the
   ensemble base) mitigate single-model bias but do **not** remove shared LLM priors.
   The LLM zero/few-shot numbers are a calibration reference on the same key, not
   independent ground truth. A human-adjudicated subset is required future work.
   *A methodological corollary, itself a finding:* an LLM judge scored against
   *production* labels is confounded by label drift — so all judging in this paper is
   against a **fixed, declared** gold set, never the production labels.
2. **No temporal hold-out — anywhere.** Batch-03 rows carry no timestamps and the
   source signals were purged under retention. Every generalization claim is hedged to
   **in-window**; "the classifier generalizes to a future week" is untested and needs
   a fresh labeled window.
3. **Per-topic statistical power.** Several categories have n < 15 (e.g.
   forced-displacement n=6, press-freedom n=7, transport-corridor n=6); their per-topic
   Wilson intervals are wide and must not be read as stable per-category precision.
4. **κ inconsistency across doc versions.** The taxonomy-ensemble κ is reported at
   different growing-base snapshots (≈0.74 → ≈0.78 full label space; ≈0.80
   in-category; ≈0.71–0.73 reject); the manuscript must pin **one** final-numbers pass
   and cite that JSON, not the running notes.
5. **Scope-gate winner's-curse.** 70.3%@37.3% is in-sample on gate thresholds tuned to
   the same data; only the student model has shown CV.
6. **English-majority benchmark.** batch-03 is English-heavy; non-English gate recall
   is named as the deeper, unmeasured lever.
7. **Coverage denominators are inconsistent across the corpus of internal docs**
   (0.2% / 2.5% / 5.6% / **25.8% funnel** / **26.72% scoped** / ~38% / 39.7% —
   funnel-coverage and scoped-recall are distinct claim-types, both canonical per
   the reconciliation doc `2026-07-16-coverage-metric-canonicalization.md`); this
   paper reports **only** the classification-precision metrics above and defers all
   coverage claims to Paper C, which must pick one defined denominator per claim.

---

## 7. What must exist before submission

- **[+EXP, light] Retro-apply the anchoring/blind control to the full N=660 headline.**
  Turn the crisis-only point-pair into a CI on the *headline* denominator so the
  "successor to 41.6%" is a real interval, not a cross-denominator point-pair.
- **[+EXP, blocked] BERTopic-proper external baseline (UMAP + c-TF-IDF).** Currently
  unrun (numba / Python 3.14 toolchain block). This is the missing external comparator
  that would isolate the schema's own contribution; state it as open, do not proxy it
  with the HDBSCAN-over-e5 sweep.
- **[+EXP] Held-out validation of the scope-gate thresholds** (not only the student) to
  remove the winner's-curse caveat on 70.3%@37.3%.
- **[data] A human-adjudicated gold subset** (even a few hundred rows) to convert at
  least one headline from panel-relative to human-anchored, and to bound the
  LLM-panel bias.
- **[data] A fresh, timestamped labeled window** for the first temporal hold-out
  (batch-03's signals are purged), lifting the in-window hedge on at least the
  theme-hint ablation and the reject-class agreement.
- **[housekeeping] Pin one final-numbers κ pass** for the ensemble base; restore/cite
  the exact JSON artifacts (`gold-kappa.json`, `anchoring-control.json`,
  `ablation-cis.json`); stop any "doc track CLOSED" language while the successor
  precision is still range-valued, in-window, and panel-relative.

---

### Provenance of every load-bearing number (for the fact-check pass)
- 41.6% / 78.6% / 81.1%, N=660, seed 20260527, 10000 resamples, κ 0.625 —
  `.../reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.json`.
- theme-hint ablation (20.2% / 40.9% / 48.3% / +7.4pp [5.2,9.6]) —
  `docs/research/embedding-ablation/2026-07-01-gdelt-hint-ablation.md`.
- anchoring control (48.2% n=390 / 53.8% n=316; z=1.48 p≈0.14) —
  `docs/research/embedding-ablation/2026-07-01-crisis-only-precision-and-kappa.md` +
  `2026-07-01-anchoring-control.json`.
- scope gate 41%→70.3%@37.3% — Paper-1 skeleton R3 / M1 gate artifact (held-out CV
  pending).
- taxonomy ensemble (76%→96%, force-fit 30/46%, gold base 732, κ "substantial") —
  `docs/research/taxonomy-revision/2026-06-29-taxonomy-revision-methodology.md`.
- substrate geometry (AUC 0.985, 0.916/0.788, 4.4×; whitening recall 0.477/0.062/0.109)
  — Paper-1 skeleton §"e5 anisotropic compression" + `cluster_whiten_sweep.py` (2026-07-07).
- error composition (substring 0.6%) — `.../reports/llm-baseline/2026-06-02-rq1-error-composition.json`.
