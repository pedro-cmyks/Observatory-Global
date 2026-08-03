# Paper B — Nothing is assumed: measured refutations of intuitive narrative-signal proxies

**Status:** skeleton (2026-07-16). Part of the Atlas justification series
(reorg: `2026-07-16-papers-reorganization-justification-framing.md`). This paper
is a *justification layer*, not a superiority pitch: each section shows that an
intuitive shortcut, taken as obvious by practitioners, is measurably misleading,
and that the shipped design is therefore non-arbitrary. The "alternatives ruled
out" ARE the result.

**Target venue.** A measurement / methods venue rather than a systems-superiority
one: ICWSM (dataset & methods track), the *Journal of Computational Social
Science*, or a workshop on computational journalism / news measurement (e.g.
Computation + Journalism). The contribution is a set of falsifications of common
news-ranking heuristics on a live global-media corpus, with reproducible scripts
— not a claim that Atlas outranks a named competitor.

---

## Abstract (target ~150 words; draft below is ~150)

News-intelligence systems routinely rank stories by proxies that feel obviously
correct: story volume, syndication breadth, and short-horizon acceleration; and
they enrich topic assignment with pre-computed theme codes. We report four
read-only measurements on a live multilingual media corpus (GDELT plus ~219 RSS
feeds), each testing one such proxy against the quantity it is assumed to track.
We find (1) composite "heat" and raw volume are rank-disjoint (Kendall-tau
-0.198, top-8 overlap 0/8); (2) syndication breadth cannot separate a hard-news
strike report (116 reprints/115 domains) from a recipe (92/92); (3) smoothed
velocity does not lead future volume (forward Spearman -0.477; it mean-reverts);
(4) GDELT theme-hint-dependent assignments are 20.2% correct versus a 40.9%
baseline, and removing them lifts precision to 48.3% (+7.4pp, bootstrap CI
[5.2,9.6]). Each negative result justifies a shipped design choice. Precision is
agreement with a 3-LLM consensus panel; zero rows are human-adjudicated.

---

## 1. Thesis, in justification form

The organizing claim of Atlas's paper series is that everything the system shows
an analyst is *valid because it is backed by measured math, inference, and
experiment — and nothing is assumed, not even the choices not to act.* This paper
is the literal embodiment of that thesis for four ranking / enrichment heuristics.

For each heuristic we run the template:

- **Decision** — the concrete thing Atlas ships (or deliberately declines to
  ship).
- **Stakes** — why the obvious alternative is tempting and why picking wrong is
  not free.
- **Backing** — the measurement that makes the choice non-arbitrary (N, CI,
  script).
- **Alternative ruled out** — the naive proxy we measured and rejected. Here the
  rejection *is* the finding.
- **Honest limit** — what is not yet backed (window-only, no temporal hold-out,
  LLM-panel gold, single snapshot).

None of these four results is a standalone paper. Individually each is "we
measured the obvious thing and it failed." Assembled, they are a citable
statement about news-signal measurement: the intuitive proxies practitioners
reach for do not track the quantity they are assumed to track, and measuring that
is the contribution. Good science includes measuring the obvious thing and
showing exactly why it fails.

A note carried into every methods and limitations section: **precision here means
agreement with a 3-LLM consensus panel (Claude Sonnet 4.6 + GPT-4.1 + DeepSeek);
n_rows_with_human_gold = 0.** The LLM figures are a **calibration reference on a
shared answer key**, never an opponent.

---

## 2. Related work positioning

Engage the real literature; no strawmen.

- **GDELT / GDELT-GKG themes and Event Registry.** GDELT-GKG attaches a large
  controlled vocabulary of themes to each article; systems built on it (and on
  Event Registry's concept tagging) commonly use theme/concept overlap as a
  cheap candidate-generator for topic assignment. We do not dispute that theme
  codes carry signal on average; we measure the precision of the *theme-only*
  assignment path specifically, where idiomatic firing (e.g. the `KILL` theme on
  "killing it") is plausible, and report it against a lexicon-standalone
  ablation. Position: complementary measurement, not a rejection of GDELT.

- **BERTopic + c-TF-IDF and neural topic modeling.** BERTopic (embeddings ->
  UMAP -> HDBSCAN -> c-TF-IDF) is the natural external baseline for the discovery
  and labeling work this paper's engine sits on. We flag honestly that a
  BERTopic-proper baseline is **not yet run** (toolchain block: numba on Python
  3.14) — so we make no comparative claim against it; it is named as the missing
  external anchor.

- **Media Cloud** and computational-journalism measurement traditions frame
  "attention" as counts of stories/outlets. Our heat and syndication results are
  in direct dialogue with that framing: we test whether count-based attention
  tracks a composite anomaly signal, and whether syndication breadth is
  separable from filler.

- **LLM-as-annotator / LLM-as-judge evaluation.** A growing body treats a strong
  LLM (or a panel) as a scalable annotator, with active debate on circularity and
  bias. We adopt a 3-vendor consensus panel *and foreground its circularity as a
  first-class limitation* (Section 6): the panel is a calibration key, not ground
  truth. Reported panel agreement (Fleiss kappa) is 0.625.

- **Embedding anisotropy** (Mu & Viswanath, "all-but-the-top", 2018; Gao et al.
  on representation degeneration) motivates the whitening our sister paper (Paper
  C) uses. We cite it here only where the movement/velocity discussion touches
  representation geometry; the whitening ablation lives in Paper C.

- **HDBSCAN** (Campello, Moulavi, Sander) is the density clustering under the
  discovery engine; its noise-vs-purity behavior is the backdrop for why volume
  and velocity are the tempting shortcuts we test.

---

## 3. Design decisions (the four refutations)

### 3.1 Heat is a composite, because volume is not a proxy for importance

- **Decision.** Country "heat" on the map is a 7-component composite
  (`z_velocity`, `surprise_kl`, `source_diversity`, `local_voice_ratio`,
  `polyphony`, `geo_confidence_mean`, `duplication_index`) — deliberately NOT
  story volume.
- **Stakes.** Volume rank is free, monotonic, and intuitive ("more stories =
  more important"). Shipping it produced the US-always-reddest artifact the
  composite was built to remove. If volume actually tracked the composite, the
  extra machinery would be unjustified.
- **Backing.** Over N=200 countries (24h, `/api/v2/heat/countries?limit=200`):
  **Kendall-tau(composite rank, volume rank) = -0.198** — not merely
  uncorrelated but mildly negative. Top-8-by-composite and top-8-by-volume
  overlap **0/8**. Per-component analysis identifies the mechanism:
  `surprise_kl` correlates +0.401 with the composite but **-0.558 with volume**
  (it rewards distributionally anomalous, disproportionately low-volume
  countries), and `source_diversity` (+0.486 with composite, +0.061 with volume)
  is the strongest volume-neutral driver.
- **Alternative ruled out.** Volume-rank heat. It shares none of its top-8 with
  the composite and is mildly anti-correlated; it is measurably not a proxy.
- **Honest limit.** One 24h snapshot; `polyphony` was constant (0.5) in-window so
  its correlation is undefined (harmless). Weights are v1, not learned — this
  measures the *served* blend's behavior, not an optimal one. No temporal
  hold-out (a multi-day tau would tighten it). The design only needs "not a
  volume proxy," which is shown; correctness-against-an-analyst is explicitly out
  of scope. Script currently a single live pull (`/heat/countries`), not a saved
  harness — wrap it if it stays load-bearing.

### 3.2 No syndication penalty, because reprint breadth cannot separate news from filler

- **Decision.** Thread ranking is `0.45·log-volume + 0.35·movement +
  0.20·coherence` and deliberately carries **no** `headline_diversity` /
  syndication penalty term.
- **Stakes.** It is tempting to demote heavily-syndicated items ("100 identical
  reprints = one wire story, not 100 stories"). A `headline_diversity =
  distinct_normalized_headlines / sample_signals` penalty is the obvious knob.
  The non-decision — choosing NOT to add the knob — must itself be backed, or it
  is an assumption.
- **Backing.** Syndication audit over 13/13 served threads (24h): "Iran attacks
  Bahrain"-class hard news scores diversity 1.0 (45 serving / 24 domains for
  Las Vegas Travel Guide; multiple hard-news threads at 1.0) and a genuinely
  syndicated wire story would score LOW on the same axis. The audit's own
  false-demote check makes the structural point: a high-reprint / high-domain
  hard-news dispatch is indistinguishable, on the diversity axis, from a
  high-reprint recipe. Illustrative pair carried in the reorg canon: "Iran
  attacks Bahrain" (116 reprints / 115 domains) vs a sausage-rolls recipe (92 /
  92) — structurally identical breadth. A diversity penalty would false-demote
  real news.
- **Alternative ruled out.** A `headline_diversity` ranking penalty. If it must
  exist at all, it must DAMP (input) rather than EXCLUDE (gate) — but the audit
  shows it does not cleanly separate the classes it is meant to, so it is not
  wired as a ranking term.
- **Honest limit.** 13-thread, 24h, single-snapshot audit over the served
  evidence sample; `headline_diversity` estimated on that sample, not the full
  member set. 0/13 threads flagged (diversity < 0.35) in-window means the
  pathology is rare here, not absent in general. The clean statement is "reprint
  breadth is not separable from value on this sample," not "syndication never
  matters."

### 3.3 changed_10h stays the ordering source, because velocity does not lead volume

- **Decision.** Front-page thread ordering uses contemporaneous `changed_10h`.
  The smoothed Kalman `topic_movement` (velocity/surprise/trend) is a
  **display-only** chip, never a ranking input.
- **Stakes.** Wiring a smoothed velocity into ranking is attractive: it *looks*
  like a leading indicator and would let the front page "predict" rising stories.
  If it does not lead, ranking on it would over-rank topics about to cool.
- **Backing.** Read-only replay backtest over the durable `emergent_clusters`
  snapshot series (99 snapshots / 33.2 days, ~8h cadence; per-topic sliding point,
  Kalman estimated from PAST snapshots only, target = future log-volume growth;
  n = 786-879 points across 36-52 topics). Forward Spearman:

  | horizon | velocity -> future | surprise -> future | changed_10h -> future |
  |---|---|---|---|
  | 1 (~8h)  | **-0.477** [-0.53, -0.42] | +0.005 (ns) | -0.390 |
  | 2 (~16h) | -0.347 [-0.41, -0.29] | -0.038 (ns) | +0.025 (ns) |
  | 3 (~24h) | -0.224 [-0.29, -0.15] | -0.089 | +0.038 (ns) |

  Velocity is significantly *negatively* correlated with future growth at every
  horizon (mean reversion: spikes exhaust themselves); surprise is ~0; velocity
  is significantly worse than naive `changed_10h` at forward prediction. A
  definitional-artifact check rules out construction as the sole cause:
  `changed_10h` is built from the same trailing window yet comes out ~0 at
  h2/h3, while velocity stays -0.35/-0.22, so velocity's anti-prediction is a
  real property.
- **Alternative ruled out.** Ranking on Kalman velocity/surprise. It is not a
  leading indicator on this corpus; wiring it would degrade ordering. This is a
  clean falsification that *prevented a bad ranking change* before it shipped.
- **Honest limit.** 33 days of ~8h snapshots is a modest window; re-run as the
  series lengthens. A cleaner target (future vs a fixed per-topic baseline, not
  the trailing window) would sharpen magnitude, but the sign / no-lead
  conclusion is robust. The result is corpus- and cadence-specific: attention
  series are mean-reverting *at this snapshot cadence*; a genuine leading
  indicator would need a different observable (cross-source attention ratio,
  early-forum velocity), not smoothing of volume.

### 3.4 GDELT theme-hints removed, because the theme-only path is net noise

- **Decision.** Demote GDELT theme-hints from a hard candidate-generator to (at
  most) a weak confidence feature; assignment leans on the LLM-distilled lexicon
  + semantic recovery.
- **Stakes.** Theme-hints are assumed to *add* precision (four internal docs
  named an ablation as the gate before removal was allowed). Removing a
  precision contributor to simplify the engine would be reckless; keeping a noise
  source would be worse. Only a measurement decides.
- **Backing.** Threshold-independent gold decomposition on the canonical N=660
  3-vendor consensus benchmark (`gdelt_hint_ablation.py`, batch-03 gold):

  | engine | correct / usable | precision | Wilson 95% |
  |---|---|---|---|
  | baseline (with theme-hints) | 270 / 660 | **40.9%** | [37.2, 44.7] |
  | ablated (lexicon-standalone) | 235 / 487 | **48.3%** | [43.8, 52.7] |
  | theme-hint-dependent path | 35 / 173 | **20.2%** | [14.9, 26.8] |

  > *The static classifier's 40.9% (n=660 ablation denominator) and the 41.6%
  > headline (n=635 gate-scored subset) in Paper A are the same classifier over
  > different scoring populations — not a discrepancy.*

  The theme-only path is 20.2% correct — roughly half the baseline — and its
  Wilson interval [14.9, 26.8] does not overlap the baseline [37.2, 44.7].
  Removal delta **+7.4pp, bootstrap 95% CI [5.2, 9.6] excludes 0**. Recall cost =
  35 correct assignments (13.0% of corrects); a Stage-2 semantic recovery curve
  recovers 86-100% of those 35 at a moderate cosine cut (0.72-0.75) and little at
  a strict cut (0.80+). This is the cleanest experiment in the paper.
- **Alternative ruled out.** Keeping theme-hint overlap as a hard
  candidate-generator. It is a net noise source on the canonical benchmark, not a
  precision contributor.
- **Honest limit.** One benchmark, English-majority (batch-03 N=660); a
  non-English theme-hint ablation is a separate, unrun row. The ablated engine
  assumes the lexicon becomes a standalone candidate-generator (an implementation
  follow-up the semantic path already approximates). Stage-2 recovery is
  threshold-sensitive — quote the curve, not a single number. No temporal
  hold-out on the ablation itself. And, as everywhere: precision = 3-LLM-panel
  agreement, zero human gold.

---

## 4. Methods

- **Data.** Live global-media corpus: GDELT plus ~219 RSS feeds across 126
  countries and 31 languages (English 96.9% of language-known at baseline). Heat:
  200-country 24h snapshot. Syndication: 13 served threads, 24h. Movement:
  `emergent_clusters` snapshot series, 99 snapshots / 33.2 days. Theme-hint
  ablation: N=660 consensus-gold benchmark (batch-03).
- **Labels / gold.** Precision = **agreement with a 3-LLM consensus panel**
  (Claude Sonnet 4.6, GPT-4.1, DeepSeek). **n_rows_with_human_gold = 0.** Panel
  inter-annotator agreement Fleiss kappa = 0.625. The panel is a calibration
  reference; the zero-shot / few-shot LLM figures (78.6% / 81.1% on the same key,
  static Atlas classifier 41.6%) are reported as calibration points, not as a
  contest.
- **Statistics conventions.**
  - Binomial precision intervals: **Wilson score** 95%.
  - Deltas and rank statistics: **stratified bootstrap** (seed 20260527, 10000
    resamples for the N=660 benchmark; 5000 for the ablation slice; fixed
    bootstrap seeds for the movement backtest). The benchmark recomputes to the
    decimal under this seed.
  - Rank association: **Kendall-tau** (heat vs volume) and **Spearman**
    (movement, paired bootstrap CI).
  - Panel agreement: **Fleiss kappa** (3 raters); pairwise **Cohen kappa** where
    a 2-way comparison is needed.
  - "ns" marks CIs that include 0.
- **Reproducibility.** Scripts: `gdelt_hint_ablation.py` (+ JSON),
  `backtest_movement_leading.py` (+ `2026-07-04-h{1,2,3}.json`), the syndication
  audit (spec §4), and the heat pull (`/api/v2/heat/countries`, currently a live
  snapshot — flagged for harness-wrapping).

---

## 5. Results (real-numbers summary)

| # | Intuitive proxy | Tracks its target? | Key statistic | N | Design consequence |
|---|---|---|---|---|---|
| 1 | volume == importance | **No** | Kendall-tau -0.198; top-8 overlap 0/8 | 200 countries, 24h | heat is a 7-component composite |
| 2 | syndication breadth == filler | **Not separable** | hard news 1.0 vs filler 1.0 diversity; 0/13 flagged | 13 threads, 24h | no `headline_diversity` penalty |
| 3 | velocity leads volume | **No (leads negatively)** | forward Spearman -0.477 [-0.53,-0.42] @h1 | 786-879 pts, 33.2d | `changed_10h` orders; Kalman display-only |
| 4 | theme-hints add precision | **No (net noise)** | 20.2% [14.9,26.8] vs 40.9%; removal +7.4pp [5.2,9.6] | 660 gold | theme-hints demoted/removed |

Calibration reference (shared key, same benchmark): static Atlas classifier
41.6% [37.8, 45.5]; LLM zero-shot 78.6% [75.3, 81.7]; few-shot 81.1% [77.7,
84.0]; panel Fleiss kappa 0.625; n_rows_with_human_gold = 0.

---

## 6. Limitations

1. **LLM-panel gold, not human gold (stated first, everywhere).** Precision is
   agreement with a 3-LLM consensus panel; **zero rows are human-adjudicated.**
   This is a known circularity in LLM-as-annotator evaluation: the classifier and
   the panel may share blind spots, and the panel's own agreement is moderate
   (Fleiss kappa 0.625). The refutations that do NOT depend on this gold — heat
   (rank correlation of two engine outputs) and movement (forward correlation of
   observed volume) — are the most robust; the theme-hint result inherits the
   gold caveat directly and the syndication result inherits it through thread
   labels.
2. **No temporal hold-out anywhere.** Every measurement is in-window
   (single-snapshot heat/syndication; 33-day movement replay; one benchmark
   vintage). No result is validated on a future, unseen time slice, so all
   generalization language is hedged: these are properties of the measured
   windows, not proven-stationary laws. The movement sign-of-effect is the one
   conclusion robust to window length; magnitudes are not.
3. **Per-topic / per-country power.** Heat and syndication are single 24h
   snapshots (polyphony undefined in-window; syndication pathology rare at 0/13).
   The theme-hint ablation is English-majority; non-English is unmeasured. The
   movement backtest pools 36-52 topics — powered for the pooled sign, thinner
   per lifecycle state.
4. **Missing external baseline.** No BERTopic-proper (UMAP + c-TF-IDF) run exists
   (numba / Python 3.14 toolchain block), so none of these refutations is
   positioned against a standard external topic model. This is the named open gap
   that would isolate the schema's own contribution.
5. **Coverage denominators are not chained.** Where coverage is mentioned, one
   defined metric is named per claim; the paper does not multiply
   inconsistently-defined coverage figures, and does not use the "54x more
   narratives" framing (it double-counts cross-country duplicates a separate
   umbrella layer exists to collapse).

---

## 7. What must exist before submission

- **Wrap the heat pull in a reproducible harness** (currently one live
  `/heat/countries` snapshot) and re-run tau across multiple days to report a
  multi-day interval instead of a single-snapshot point.
- **Persist the syndication audit as a saved artifact** with a fixed sample and
  its false-demote check, over more than 13 threads / more than one snapshot, so
  the "not separable" claim rests on a distribution, not one window.
- **Lengthen the movement backtest** as the snapshot series grows, and add the
  fixed-per-topic-baseline target variant to sharpen magnitudes (sign already
  robust).
- **Add a non-English theme-hint ablation row** (batch-03 is English-majority),
  the deeper lever named in the source doc.
- **Run the BERTopic-proper external baseline** once the numba/py3.14 toolchain
  unblocks, to anchor the results against a standard topic model.
- **Keep the LLM-panel-gold disclosure and the "calibration reference, not
  opponent" framing in every methods and results caption** — this is the framing
  that makes the series defensible.
- **Confirm every number against its live artifact at submission time**; mark any
  figure without a backing JSON/script as `[PLACEHOLDER]` until it has one.
