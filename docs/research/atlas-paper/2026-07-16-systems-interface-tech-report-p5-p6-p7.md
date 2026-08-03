# Atlas Systems & Interface: Justified Design Decisions (P5 sentiment/NLP · P6 temporal · P7 visualization)

**Type:** Technical report (skeleton) — NOT three standalone papers yet.
**Date:** 2026-07-16
**Status:** justification-layer draft, following the reorg framing
(`2026-07-16-papers-reorganization-justification-framing.md`, §1 template).
**Series role:** the "Systems & interface" report of §3 of the reorg. Each of
the three sections is a *justified-design* section that **graduates to a
standalone paper only when its ONE named missing study exists** (P5 → a
human-labeled per-language accuracy set; P6 → latency-per-bucket + cost-per-row;
P7 → a 10–15-user task-time study). Until then this is a report/appendix that
cites Paper A's benchmark and its gold disclosure.

> **Gold disclosure (repeated in every methods block below, non-negotiable):**
> every precision/agreement number in this report is **agreement with an
> LLM judge or with another automated source, not accuracy against human
> adjudication. n_rows_with_human_gold = 0.** The P5 NER precision figures are
> agreement with a *single* DeepSeek judge (weaker than Paper A's 3-LLM
> consensus panel); the P5 sentiment "agreement" figure is *inter-source*
> agreement between two automated labelers, not correctness. The LLM is a
> **calibration reference on a shared key, never an opponent.**

---

## 1. Thesis (in justification form)

We do not claim the Atlas sentiment fusion, temporal tiering, or visualization
surfaces are *better* than any competing system — no like-for-like baseline was
run for any of the three. We claim something narrower and defensible:

> Each of these systems/interface decisions is **non-arbitrary and honest**: it
> is either derived from a stated measurement, or — where we could not measure —
> it *discloses the gap instead of fabricating the capability*.

Three concrete forms of that thesis, one per section:

- **P5 (sentiment/NLP):** the confidence-weighted fusion and the `2.37` scale are
  design constants with a stated derivation; and the load-bearing contribution is
  an **honest negative** — rather than assume multilingual coverage, we *measured
  it broken* (non-Latin NER returns nothing; the xlm tokenizer broke in prod) and
  labeled the affected subjects `unverified`. We drop the earlier "more faithful
  to human sentiment" framing entirely: that number was inter-source agreement,
  not accuracy.
- **P6 (temporal):** the hot/cold boundary sits at `168h` because we *measured*
  the catch-up runner silently holding hot at 1–2 days and corrected it — the
  boundary is set by observed behavior, not a round number. This section stays an
  **architecture-justification appendix** because the two numbers a systems venue
  requires — latency-per-bucket and cost-per-row across tiers — are **unmeasured**.
- **P7 (visualization):** every decision is **honest-by-construction** — equal-area
  projection (no size lie), "positions approximate · relations exact" (the view
  teaches its own epistemics), `relationActive=false` keeps a surface global
  rather than fabricate a relation, orbit radius *is* the classifier's own cosine
  distance (falsifiable against the engine), and relations are rarity-weighted
  because naive overlap launders common actors. The claim is the **validity/
  honesty of the representation**, not measured analyst superiority — that
  comparative claim is dropped, pending a task-time study that does not exist.

---

## 2. Related work positioning (honest, no strawman)

- **GDELT 2.0 / GDELT-GKG themes, EventRegistry, Media Cloud** — the upstream
  event/theme feeds. GKG theme codes are a *lexical* signal we consume but
  measured to be net noise as a classifier hint (Paper A / P1 theme-hint
  ablation); here they are relevant because GDELT V2Tone is one of the two
  sentiment inputs P5 fuses. We do not position against these systems' coverage;
  we position on what we do with their tone/theme fields.
- **LLM-as-annotator evaluation** (recent NLP eval literature on using LLMs as
  cheap labelers, and its known circularity risks). We adopt it *and foreground
  its limit*: our per-language NER precision is DeepSeek-judged agreement, our
  sentiment number is inter-source agreement — both with zero human-adjudicated
  rows. This is the report's most important methodological engagement: we do not
  launder LLM agreement as accuracy.
- **Multilingual NER / token classification** (spaCy `xx_ent_wiki_sm`;
  transformer token classifiers — `Davlan/xlm-roberta-base-ner-hrl`,
  `Babelscape/wikineural-multilingual-ner`; cardiffnlp `twitter-xlm-roberta`
  sentiment). We engage these as the concrete models we measured: the free spaCy
  multilingual model is the naive option we *ruled out on non-Latin scripts*, and
  the two transformer models are the measured replacement — with their real
  failure modes (ru transfer 0/3 on Davlan; sports-headline mistypes at serving).
- **BERTopic + c-TF-IDF topic modeling; HDBSCAN; embedding anisotropy
  (Mu & Viswanath / "all-but-the-top", Arora et al.)** — primarily P8/Paper C
  territory, cross-referenced from P7 because the Universe/Orbital views *render*
  the embedding geometry those methods operate on. P7's honesty split (PCA top-2 =
  ~17% variance, labeled "approximate") is the visualization-side acknowledgment
  of exactly the anisotropy those papers characterize. **BERTopic-proper (UMAP +
  c-TF-IDF) as an external topic-modeling baseline remains UNRUN** (numba/py3.14
  toolchain block) — named here as the missing external comparison, not claimed.
- **Analyst/OSINT tooling** (Palantir, i2 Analyst's Notebook, Maltego,
  commodity BI dashboards). Engaged only as *design references* in the workspace
  audit (`workspace-expert-audit.md`), NOT as measured baselines. Any "better than
  commodity dashboards" language is removed until a task-time study exists.

---

## 3. Design decisions (5-part template each)

### P5.1 — Confidence-weighted fusion of GDELT V2Tone + XLM transformer sentiment

1. **Decision.** Served sentiment is a confidence-weighted fusion of GDELT V2Tone
   and an XLM multilingual transformer (`sentiment_fusion.py`), exposed as three
   named sources (`gdelt`, `nlp`, `nlp_weighted`) so a consumer can see the fused
   and unfused values.
2. **Stakes.** The tempting default is to pick one source (GDELT tone is free and
   always present) or a flat average. Either would be arbitrary if the two sources
   disagree in a structured way.
3. **Backing.** Measured **inter-source sign agreement = 70.8%** (disagreement
   29.2%), with the lexicon weaker than the transformer on the disagreement set
   (source: master-plan P5 / `sentiment_fusion.py`). This *justifies fusing rather
   than picking*: a ~29% structured disagreement means one source is not a drop-in
   for the other. **This is agreement, not accuracy — n_human_gold = 0.**
4. **Alternatives ruled out.** Single-source (discard the disagreement signal) and
   flat-average (ignores that the transformer is the stronger member on the
   disagreement set). The `nlp_weighted` vs flat-AVG ablation on analyst-facing
   rankings is **not yet run** (listed in §7).
5. **Honest limit.** The 70.8% is inter-source agreement; **we make no claim that
   the fused value is more faithful to a human judgment** — that framing is
   dropped. No human sentiment labels exist.

### P5.2 — The `NLP_SENTIMENT_SCALE = 2.37` constant

1. **Decision.** Transformer sentiment is rescaled by `2.37` before it drives UI
   thresholds.
2. **Stakes.** A scale constant that sets where "negative" bands begin is exactly
   the kind of magic number that reads as arbitrary if unstated.
3. **Backing.** Stated derivation: `2.37` is the ratio derived from **per-source
   standard-deviation measurements** aligning the transformer's spread to GDELT
   V2Tone's, so the two feed one threshold scale. *The underlying per-source stddev
   values are [PLACEHOLDER] — the derivation is stated in the master plan but the
   numeric stddevs are not in a cited artifact here.*
4. **Alternatives ruled out.** An unscaled transformer output (bands calibrated
   for V2Tone would misfire) or a hand-tuned round constant (e.g. 2.5) with no
   derivation.
5. **Honest limit.** Until the stddev artifact is attached, `2.37` is a
   *derivation-stated* constant, not a fully reproducible one. No threshold-band
   validation against human perception exists.

### P5.3 — Disclosing multilingual NER failure instead of assuming coverage (the honest-negative contribution)

1. **Decision.** Non-English subjects that the pipeline cannot verify with a
   working NER model are labeled **`unverified` via a gazetteer**, and the
   multilingual-NER limitation is stated as a finding rather than hidden.
2. **Stakes.** The tempting move for a "global" narrative system is to assert
   multilingual coverage. Diversity is the whole pitch (English is 96.9% of
   language-known signals at baseline; see Paper C), so there is pressure to claim
   the non-Latin pipeline works.
3. **Backing (measured failure, then measured partial fix).**
   - The free `xx_ent_wiki_sm` returns **nothing** on Persian/Arabic/CJK
     (measured extract-rate: fa 12.5%, zh 0%, ko 0%, ar 25%) — useless for exactly
     the diversity gap.
   - The xlm sentiment tokenizer **broke in prod** (missing `protobuf` →
     SentencePiece falls back to a broken TikToken extractor → `ValueError`);
     re-measured, the block dissolved with a pip install, but the *original prod
     state was broken*, which is the honest finding.
   - Replacement transformer NER (`Davlan/xlm-roberta-base-ner-hrl`, Cyrillic →
     `wikineural`) measured at **82.1% overall DeepSeek-judged precision**, with a
     real gap: **ru = 0% (0/3) on Davlan**, closed to **87.5% (14/16)** only by
     routing Cyrillic to a second model.
4. **Alternatives ruled out.** (a) Assuming coverage and serving gazetteer guesses
   as verified — measured to surface photo-credit tokens ("margo evardson
   unsplash") as people. (b) A single multilingual model for everything — measured
   sub-optimal (Davlan does non-Latin transfer, wikineural does Cyrillic; neither
   covers both), so the two-model route is the measured optimum. (c) `xx_ent_wiki_sm`
   for non-Latin — ruled out at ~0 extract-rate.
5. **Honest limit.** 82.1% is **single-LLM-judge agreement, n_human_gold = 0**; at
   serving, NER-wins-over-gazetteer means a NER mistype on entity-dense sports
   headlines (England→PERSON, LaLiga→PERSON) is *not* corrected; non-English
   verified subjects **accumulate slowly** (surface payoff is a drain, not a
   switch); and no per-language *accuracy* (vs human) breakdown exists.

### P6.1 — Hot/cold boundary at 168h, set by measured catch-up behavior

1. **Decision.** The hot (queryable) window is `168h`; older data lives in
   processed aggregates and a cold external archive that is not directly queryable.
2. **Stakes.** A retention boundary is trivially arbitrary if it is a round number
   picked for tidiness ("keep a week").
3. **Backing.** The boundary was corrected *because of an observed behavior*: the
   catch-up runner default was silently holding the hot window at **1–2 days**,
   starving long-window surfaces; fixing it to `168h` was the measured correction.
   Tiering operations are concrete: **2,128,070 rows archived over 18 days at $0
   lost**; 59 manifest dirs / 272 records / 3,947,759 rows verified on the external
   archive.
4. **Alternatives ruled out.** The silent 1–2-day default (measured to freeze
   long-window analytics) and an unbounded hot table (cost-prohibitive on the
   managed Postgres tier).
5. **Honest limit.** The boundary is justified by *behavior*, not by a latency/cost
   curve. See P6.2 — the systems numbers do not exist yet.

### P6.2 — Bucket granularity justified by query patterns (architecture appendix only)

1. **Decision.** Time is bucketed at mixed granularities (15-minute hot-path
   buckets; hourly/daily pre-aggregates for long windows).
2. **Stakes.** Granularity trades storage/latency against resolution; picking it by
   feel is arbitrary.
3. **Backing.** Justified by the query patterns each tier serves (real-time hot
   scans vs long-window trend reads over pre-agg matviews). This is a
   *pattern-fit* justification, not a benchmarked one.
4. **Alternatives ruled out.** A single uniform granularity — qualitatively wrong
   for one of the two access patterns (fine buckets over 168h, or coarse buckets on
   the real-time path).
5. **Honest limit — the blocking gap.** **Latency-per-bucket and cost-per-row
   across tiers are UNMEASURED.** Until both numbers exist, P6 is explicitly an
   architecture-justification appendix of the backbone paper, **not a standalone
   systems paper.** No claim of systems superiority is made.

### P7.1 — Equal-Earth projection (equal-area, no size lie)

1. **Decision.** The map uses an Equal-Earth (equal-area) projection.
2. **Stakes.** A Mercator-family default would inflate high-latitude countries —
   an area lie that directly distorts a coverage/heat map.
3. **Backing.** Equal-area is a *property of the projection*, verifiable by
   construction: relative country areas are preserved, so a heat encoding is not
   confounded by projection area. (ADR-0005 pending.)
4. **Alternatives ruled out.** Web-Mercator (area distortion) as the commodity
   default.
5. **Honest limit.** Equal-area trades shape/angle fidelity; and the projection
   choice is honesty-of-encoding, not an evaluated analyst outcome.

### P7.2 — "Positions approximate · relations exact" (the two-layer honesty split)

1. **Decision.** In the Universe/Orbital views, node **positions** come from a PCA
   projection and are labeled *approximate by design*; **relations** (edges) are
   computed in the full 768-dim space and labeled *exact*. The legend states both.
2. **Stakes.** A 2-D scatter of high-dim embeddings invites the reader to trust
   pixel distance as semantic distance — a classic dimensionality-reduction lie.
3. **Backing.** **PCA top-2 explains ~17% of variance (measured)** — so positions
   are explicitly weak; relations use top-3 cosine neighbors in full space. The
   threshold alternative for edges was *measured and rejected*: **e5 centroid NN
   similarities have p50 = 0.943**, so any fixed similarity threshold explodes the
   edge count. The visualization **teaches its own epistemics.**
4. **Alternatives ruled out.** (a) Presenting PCA position as trustworthy distance
   (17% variance refutes it). (b) A fixed cosine threshold for edges (p50 0.943
   makes it degenerate).
5. **Honest limit.** "Approximate" positions can still mislead a reader who ignores
   the label; the honesty is in the disclosure, not in a better projection.

### P7.3 — Orbit radius = the classifier's own cosine distance (falsifiable against the engine)

1. **Decision.** In the Orbital "story system," a body's orbit radius **is** the
   cosine distance between its member `signal_embeddings` and the topic centroid —
   the same distance the classifier uses.
2. **Stakes.** A layout could place bodies for aesthetic spacing, making the view a
   decorative proxy that can silently disagree with the engine.
3. **Backing.** Because radius is the engine's own measure, a body that *looks*
   misplaced is an **engine finding, not a layout artifact** — the view is
   falsifiable against the classifier. Motion is driven by a deterministic time
   scrubber (`lib/orbitalLayout.ts`, pure/vitest-frozen), so it is interaction, not
   animation.
4. **Alternatives ruled out.** The prior metadata-proxy force graph
   (`TemporalNarrativeGraph`), fed by country/person/source co-occurrence, which
   could disagree with the engine's own membership.
5. **Honest limit.** Falsifiability against the engine is not correctness against
   the world; and the "answer this task faster" acceptance metric (e.g. "who
   entered this story this week?") is **not yet measured** — see §7.

### P7.4 — `relationActive=false` keeps surfaces global rather than fabricate a relation

1. **Decision.** When a focused entity has no computable relation to a surface,
   `computeFocusRelation` returns `relationActive=false` and the surface stays
   global — it does not blank, and it does not invent a scoped relation.
2. **Stakes.** The tempting UX is to always "do something" on focus — fabricate a
   scoped view even when the relation is null.
3. **Backing.** Honest-by-construction: the null case is an explicit code path
   (`lib/focusRelation.ts`, `useFocusRelation`), not an accident. Same discipline
   as the L1 reserved-gap-box / no-silent-blank thesis.
4. **Alternatives ruled out.** Fabricating a scoped relation on null (misleading);
   blanking the surface (loses the global context).
5. **Honest limit.** This is an honesty property of the interaction model, not an
   evaluated task outcome.

### P7.5 — Rarity-weighted relations (naive overlap launders common actors)

1. **Decision.** Thread-sibling / focus relations count only **distinctive**
   shared entities (document-freq ≤ min(3, 25% of the list)) ORed with primary
   geography — not raw entity overlap.
2. **Stakes.** Naive shared-entity overlap is the obvious relation metric.
3. **Backing.** Measured failure of the naive metric: one entity (**"donald trump"
   in 14 of 30 concurrent threads**) linked every unrelated narrative (Pauline
   Hanson ↔ Venezuela Earthquake). Rarity-weighting removes the laundering while
   keeping genuine geography-independent siblings. This is the **same volume ≠
   importance principle as Paper 3's heat composite**, transferred from intensity
   to relation — a citable cross-method result within the series.
4. **Alternatives ruled out.** Naive entity-overlap (measured to launder common
   actors).
5. **Honest limit.** The distinctiveness cutoff (`min(3, 25%)`) is a chosen
   threshold, not a tuned one; relation-quality has no task-time validation.

---

## 4. Methods

- **Data.** Atlas `signals_v2` hot window (≤168h) + processed historical
  aggregates + cold external archive; sentiment/NER enrichment via
  `enrichment/nlp_pipeline.py` (M1 mindful daemon + Fly light lane); embeddings
  via the e5 service backing the Universe/Orbital projections.
- **Labels / gold.** **No human-adjudicated gold anywhere in this report.** P5 NER
  precision = agreement with a **single DeepSeek judge** (`eval_multilingual_ner.py`);
  P5 sentiment 70.8% = **inter-source agreement** between two automated labelers;
  Paper A's 3-LLM consensus panel (sonnet-4.6 + gpt-4.1 + deepseek, Fleiss κ 0.625)
  is the shared calibration key this report *cites* but does not re-run. The LLM is
  a **calibration reference, not an opponent.**
- **Metrics.** Proportions reported with **Wilson** score intervals; overall
  precision aggregates with **stratified bootstrap** (per-language strata) where an
  interval is quoted; inter-annotator/inter-source agreement with **Fleiss / Cohen
  κ** where ≥3 / 2 labelers respectively. **Where a script/JSON artifact does not
  exist, the number is marked [PLACEHOLDER] or [NEEDS-EXPERIMENT] and never
  reported as a measured CI.**
- **Stats conventions.** Two-proportion z for A/B deltas; bootstrap CIs at 10,000
  resamples with a fixed seed when an artifact exists. **No temporal hold-out
  exists in this report** — every generalization statement is hedged to "in-window,
  on this sample."

---

## 5. Results (real numbers only; status tagged)

| # | Section | Quantity | Value | Status | Source / caveat |
|---|---|---|---|---:|---|
| 1 | P5.1 | Inter-source sentiment sign agreement | 70.8% (disagree 29.2%) | backed (agreement, not accuracy) | master-plan P5 / `sentiment_fusion.py`; n_human_gold=0 |
| 2 | P5.2 | Sentiment scale constant | `2.37` | placeholder (derivation stated, stddev artifact missing) | master-plan P5 |
| 3 | P5.3 | xlm NER precision, overall | 82.1% | backed (DeepSeek-judged, n_human_gold=0) | `eval_multilingual_ner.py` |
| 4 | P5.3 | xlm NER precision, per-language | zh 100% (11/11), fa 91.7% (11/12), ko 100% (4/4), ar 70.6% (12/17), pt 84.6% (11/13), de 85.7% (6/7) | backed (small n; Wilson intervals wide) | same; ru handled separately |
| 5 | P5.3 | ru NER: Davlan → wikineural | 0% (0/3) → 87.5% (14/16) | backed | Cyrillic two-model route |
| 6 | P5.3 | `xx_ent_wiki_sm` non-Latin extract-rate | fa 12.5%, zh 0%, ko 0%, ar 25% | backed | the ruled-out naive model |
| 7 | P5.3 | NER throughput (batch-16) vs inflow | 16,216 rows/hr vs 4,848 rows/hr; backlog 86,307→85,455 | backed | `2026-07-13-ner-throughput-measurement.md` (projection confirmed on one autonomous cycle; no daily-avg hold-out) |
| 8 | P5.3 | Served coverage split | sentiment ~100% served; NER 3.9% (pre-M1-move Fly measure) | backed | master-plan P5 / #184 |
| 9 | P6.1 | Hot window boundary | 168h (was silently 1–2 days) | backed | catch-up-runner correction |
| 10 | P6.1 | Cold tiering | 2,128,070 rows / 18 days / $0 lost | backed | hot/cold cutover |
| 11 | P6.x | Served-vs-embedded *infrastructure* ratio (NOT funnel coverage) | 13,354 distinct / 239K embedded (5.6%) / 534K total (2.5%) | backed (distinct metric) | a served-vs-embedded infra ratio, *not* the funnel-coverage claim; canonical funnel coverage = **25.8% useful-served** per `2026-07-16-coverage-metric-canonicalization.md` (Group A marks 5.6%/2.5% superseded *as funnel coverage*). Do NOT chain. |
| 12 | P6.2 | Latency-per-bucket; cost-per-row | — | needs-experiment | the blocking systems gap |
| 13 | P7.2 | PCA top-2 explained variance | ~17% | backed | Universe View; labeled "approximate" |
| 14 | P7.2 | e5 centroid NN similarity p50 | 0.943 | backed | why a fixed edge threshold was rejected |
| 15 | P7.5 | Common-actor laundering | "donald trump" in 14/30 concurrent threads | backed | rarity-weighting justification |
| 16 | P7.3/all | Analyst task-time study | — | needs-experiment | gates the P7 "better than commodity" claim (currently dropped) |

---

## 6. Limitations (ordered by severity)

1. **LLM-panel / LLM-judge gold, zero human rows (FIRST).** Every precision and
   agreement figure here is agreement with an automated labeler. P5 sentiment is
   *inter-source* agreement (not accuracy). P5 NER is *single-DeepSeek-judge*
   agreement — weaker than Paper A's 3-LLM consensus. **n_rows_with_human_gold = 0
   everywhere.** No number in this report may be read as accuracy against human
   judgment.
2. **No temporal hold-out anywhere.** The NER throughput "matches inflow" result is
   one confirmed autonomous cycle plus a projection, not a multi-day average; the
   sentiment agreement and NER precision are in-window samples. All generalization
   is hedged.
3. **Per-language / per-topic statistical power is thin.** Several P5 per-language
   cells are single-digit n (ko 4/4, de 6/7, ru 3–16); Wilson intervals are wide
   and are the honest form — point rates overstate certainty.
4. **P5.2 `2.37` derivation artifact missing.** The stddev measurements that
   produce the constant are stated but not attached; the value is
   derivation-stated, not reproducible, until the artifact lands.
5. **P6 systems numbers absent.** Latency-per-bucket and cost-per-row are
   unmeasured; P6 cannot make a systems-superiority claim and stays an appendix.
6. **P7 has no analyst study.** The "measurably better than commodity dashboards"
   claim is **removed** (it was false, not merely unproven — no study exists). The
   honesty-of-encoding claims stand alone; the comparative claim is gated on §7.
7. **Serving-time NER-wins-over-gazetteer is uncorrected on sports/entity-dense
   headlines** — a known false-verify path (England→PERSON).
8. **Coverage denominators must not be chained.** This report quotes the single
   `5.6% of embedded / 2.5% of total` metric (#229) and no other; the 0.2% /
   25.8% / ~38% / 39.7% figures elsewhere use different denominators, and the
   "54× more narratives" cross-country figure double-counts duplicates R2 exists to
   collapse — excluded here.

---

## 7. What must exist before submission

**Graduation gate — each section becomes a paper only when its ONE study lands:**

- **P5 → NAACL/EMNLP/*SEM sentiment-NLP paper** needs:
  - a **human-labeled** per-language accuracy set (even ~100 stratified headlines)
    so precision stops being LLM-judge agreement;
  - the `2.37` stddev-derivation artifact (script + JSON);
  - the `nlp_weighted` vs flat-AVG ablation on analyst-facing rankings;
  - a daily-average throughput hold-out (not a single-cycle projection);
  - HTML-entity-decode impact ablation.
- **P6 → VLDB/CIDR/ICDE systems paper** needs:
  - **latency-per-bucket** across granularities;
  - **cost-per-row** across hot/cold tiers;
  - reproducibility of compact aggregates from the cold archive;
  - recency-scheduling coverage impact (served window vs full 168h under load).
- **P7 → CHI/VIS design paper** needs:
  - a **10–15-user task-time study** on the seven analyst questions (the only thing
    that would license any comparative claim; until then, drop all "better than"
    language);
  - the Orbital "who entered this week?" task-time vs the signal list (the acceptance
    metric the view was built to make measurable);
  - the **BERTopic-proper external baseline** (UMAP + c-TF-IDF) once the
    numba/py3.14 toolchain is unblocked — to isolate the schema/engine's own
    contribution behind the P7 visualizations.

**Housekeeping that costs credibility if left (from the reorg §4):** attach the
`2.37` derivation artifact; keep every coverage claim to one named denominator;
retain the LLM-panel-gold disclosure line in each methods block on every revision.
