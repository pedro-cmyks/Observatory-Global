# Atlas Papers — Master Plan

Date: 2026-05-27
Status: canon (active)
Scope: full methodological backbone for Atlas as a narrative intelligence
system. Each entry below is a stand-alone paper. The series together
constitutes the academic justification for every major design decision
in Atlas.

## Why a series, not a mega-paper

Atlas spans data ingestion, source quality, NLP, sentiment fusion,
topic classification, heat composition, thread aggregation, evidence
sampling, temporal model, visualization, and analyst workflow. A
single paper covering all of this would be 50+ pages, hard to peer
review, hard to cite, and slow to publish. A coordinated series:

- Ships incremental contributions on a tighter cadence.
- Lets each paper choose its best-fit venue.
- Lets a reader cite the exact methodological piece they need.
- Lets reviewers focus on one decision class.
- Keeps the schema (`atlas-topic-benchmark-v2` and successors) as the
  shared substrate across papers.

## Shared substrate across all papers

All papers in the series share:

- Production system reference: `atlas-api-pedro` on Fly + Supabase Postgres.
- Code repository: this repo (`v3-intel-layer` branch).
- Benchmark schema family: `atlas-topic-benchmark-v2` and evolutions.
- Reproducible audit + benchmark tooling under `backend/scripts/`.
- LLM-as-annotator and LLM-as-baseline (Sonnet 4.6) as common
  evaluation infrastructure.
- Statistical conventions: Wilson per-topic CI, stratified bootstrap
  overall CI, Cohen's kappa for inter-annotator agreement,
  Landis & Koch bands.
- Single-reviewer initial annotation honesty: labels are referred to
  as `pedro_initial` / `sonnet46_initial`; never "gold" without
  qualifier.

## Series index

### Paper 1 — Evidence-role topic classification + distillation methodology

**Status:** active; RQ1 measured at scale, manuscript still open. Outline doc:
`docs/research/atlas-paper/2026-05-27-methodology-paper-outline.md`.

**Core claim:** A single-layer topic classifier collapses semantic
roles; an evidence-role schema plus an LLM-distilled lexicon
refinement loop lifts precision toward LLM baselines while keeping
production inference at zero per-call cost.

**Evidence already collected:**
- Reviewed gold N=61 (batches 01+02).
- 3-vendor consensus-gold benchmark: 660 usable rows / 31 ties,
  Fleiss kappa `0.625`.
- Atlas v2 precision `41.6%` [37.8, 45.5].
- LLM zero-shot precision `78.6%` [75.3, 81.7].
- LLM few-shot precision `81.1%` [77.7, 84.0].
- Error anatomy: `off_topic` and `scope_mismatch` dominate; substring noise is
  only `0.6%` of incorrect rows.
- Scope gate lift measured: `41%` -> `70%` precision on scored rows.
- Evidence-role student v1 measured: `78.2%` primary_evidence precision,
  `71.4%` noise recall, no LLM at inference.
- Distillation candidates surfaced per topic (reasoning mining).

**Evidence still missing for submission:**
- Result-bearing draft skeleton with current tables and figures.
- Temporal generalization hold-out week.
- BERTopic / lex-only / theme-only ablation baselines.
- Anchoring effect measurement if the paper keeps the assistant-hint workflow as
  a central claim.
- Limitations language separating reviewed diagnostic labels, consensus gold,
  and local Ollama negative evidence.

**Target venues:** EMNLP industry, ACL Findings, NLP4PI workshop.

---

### Paper 2 — Cross-source source-quality scoring for narrative intelligence

**Status:** seed. No paper outline yet.

**Core claim:** A composite source-quality vector (`source_family`,
`geo_confidence`, `attribution_method`, `is_state_media`, source
diversity, aggregator down-weighting) is more predictive of analyst-
useful narrative evidence than any single signal alone.

**Evidence available:**
- 9 ingest sources (GDELT, RSS, NewsData, MediaStack, NewsAPI,
  Reddit, ReliefWeb, ACLED, AISStream, OpenSky).
- Per-source defaults documented in CLAUDE.md.
- Source blocklist (50+ domains).
- Atlas heat formula component `voice` already weights source
  diversity.

**Evidence to collect:**
- Cross-source coverage matrix (which sources cover which crises).
- Per-source false-positive rate on stratified sample.
- Aggregator-share metric per thread; correlation with analyst
  usefulness.
- State-media leakage rate by topic.

**Target venues:** ICWSM, JCDL, ACL Findings.

---

### Paper 3 — Atlas heat: composite heat detection for multi-source signals

**Status:** seed. Heat formula doc:
`docs/methodology/atlas-heat.md`. Mig 026 + `country_heat_v2`.

**Core claim:** A multi-component heat score (velocity + surprise +
diversity + voice + polyphony + geo_confidence + duplication) detects
narrative-grade heat with fewer volumetric false positives than raw
signal counts. Per-component ablation shows which signals contribute
the most to analyst-relevant ranking.

**Evidence available:**
- `country_heat_v2` matview with 7 components live.
- `heat_countries` API exposes the ranking.
- `heat_voluminous_countries` lens for volume comparison.

**Evidence to collect:**
- Per-component ablation: drop each component, measure ranking shift.
- Analyst preference study: heat-ranked vs volume-ranked panels.
- Time-correlation study: do heat spikes lead or lag external news?

**Target venues:** ICWSM, JCDL, KDD Applied Data Science track.

---

### Paper 4 — Thread aggregation and evidence sampling for real-time narrative tracking

**Status:** seed. Implementation in
`backend/app/services/thread_intelligence.py`. Spec:
`docs/specs/2026-05-24-living-narrative-threads.md`.

**Core claim:** Treating narrative threads as the first-class user
unit (instead of topic buckets) requires evidence-deduplication,
syndication detection, source diversity weighting, and a confidence
band. The resulting thread contract supports the seven Atlas questions
better than per-topic aggregation alone.

**Evidence available:**
- `THREAD_EVIDENCE_SQL` with `DISTINCT ON (LOWER(headline))` and
  `evidence_role` classification.
- `confidence_band()` classifier.
- Living thread contract `living-narrative-threads-v0`.
- Quality audit document
  (`docs/research/2026-05-24-thread-quality-audit.md`).

**Evidence to collect:**
- Thread-level benchmark (sample 30 threads; LLM annotator scores
  each against the 7 questions; compare to analyst judgement).
- Evidence-role accuracy per thread.
- Syndication detection precision.
- Confidence-band calibration.

**Target venues:** ICWSM main, EMNLP industry, CSCW.

---

### Paper 5 — Sentiment fusion and multilingual NLP calibration

**Status:** seed. Implementation in
`backend/app/services/sentiment_fusion.py`. Pre-agg coverage in
mig 025, 026, 033.

**Core claim:** Confidence-weighted fusion of GDELT V2Tone and an
XLM multilingual transformer is more faithful to human sentiment
judgement than either source alone. The calibration constant
`NLP_SENTIMENT_SCALE = 2.37` is empirically derived from per-source
stddev measurements and is the right baseline for downstream UI
thresholds.

**Evidence available:**
- 70.8% sign agreement between transformer and GDELT V2Tone.
- 29.2% disagreement, with lexicon weaker than transformer.
- Per-bucket `nlp_signal_count`, `avg_nlp_sentiment`,
  `nlp_sentiment_weight_sum`, `nlp_confidence_sum`.
- Three sentiment sources exposed: `gdelt`, `nlp`, `nlp_weighted`.

**Evidence to collect:**
- Human sentiment labels on a stratified sample (e.g., 100 headlines).
- Per-language accuracy breakdown.
- HTML entity decode impact ablation.
- `nlp_weighted` vs flat-AVG ablation on analyst-facing rankings.

**Target venues:** NAACL, EMNLP, *SEM (sentiment / semantics workshop).

---

### Paper 6 — Temporal model: hot vs cold storage, processed historical, time-bucketing

**Status:** seed. Specs:
`docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md`
plus ADR-0004 NLP stratified sampling and `data-operating-roadmap`.

**Core claim:** A two-tier temporal architecture (hot 24h on
Supabase + cold archive locally + compact processed historical on
Supabase) preserves long-window analytical surfaces under strict cost
budgets, while keeping 15-minute bucket SLAs on the hot path. Bucket
granularity choices are justified per use case.

**Evidence available:**
- Hot/cold cutover: 2,128,070 rows archived, 18 days, $0 lost.
- `historical_topic_country_daily`, `historical_source_daily`
  compact tables.
- Live coverage reports.

**Evidence to collect:**
- Query latency per bucket granularity.
- Cost per row across hot/cold tiers.
- Reproducibility of compact aggregates from cold archive.

**Target venues:** VLDB systems, CIDR, ICDE industry track, KDD ADS.

---

### Paper 7 — Visualization and analyst workflow for narrative intelligence

**Status:** seed. ADR-0005 Equal Earth pending. Workspace audit:
`docs/research/workspace-expert-audit.md`. UX iteration notes
under `docs/research/ux-video-evaluation/`.

**Core claim:** Specific visualization decisions (Equal Earth
projection, coverage badges, sentiment scaling, narrative-thread-first
panel layout, force-graph workspace) make Atlas measurably better at
the seven analyst questions than commodity dashboards.

**Evidence available:**
- Panel-by-panel audit
  (`docs/research/2026-05-24-app-panel-thread-audit.md`).
- Workspace expert audit.

**Evidence to collect:**
- Analyst task-completion study (10-15 analysts, structured tasks).
- Comparative dashboard (Atlas vs Google Trends + GDELT raw).
- Eye-tracking or click-stream where feasible.

**Target venues:** CHI, CSCW, IEEE VIS, InfoVis.

---

### Paper 8 — Open-set topic discovery and taxonomy evolution

**Status:** parking. Tied to BERTopic / dynamic topic modeling work
NOT yet started. This paper addresses Pedro's question about "new
buckets that could appear" — making the Atlas taxonomy adaptive
rather than manually curated.

**Core claim:** A semi-automated taxonomy evolution loop, combining
BERTopic clusters of unclassified signals with LLM-assisted naming
and human approval, expands the Atlas taxonomy without losing the
schema rigor of v2.

**Evidence to collect:** all of it.

**Target venues:** EMNLP, NAACL, ACL Findings, ICWSM.

---

## Recommended publication order

1. **Paper 1** (topic classification + distillation) — closes 4-8
   weeks from today with current data and migration 042.
2. **Paper 5** (sentiment fusion) — uses LLM-as-annotator extension
   to provide gold; can land 8-12 weeks after Paper 1.
3. **Paper 4** (thread aggregation) — depends on Papers 1 + 5 to
   anchor the thread-level metrics on validated underlying components.
4. **Paper 3** (atlas heat) — requires per-component analyst study;
   can be done in parallel with Paper 4.
5. **Paper 2** (source quality) — broader infrastructure piece; can
   start anytime once cross-source coverage matrix is automated.
6. **Paper 6** (temporal model) — most "systems" feeling paper;
   targets a different audience.
7. **Paper 7** (visualization) — needs real analyst recruitment.
8. **Paper 8** (open-set discovery) — most ambitious; could become
   a thesis-level project.

## Master criteria

For any paper in the series to ship:

- Reproducible benchmark with stratified sampling.
- Statistical CIs (Wilson per-bucket, stratified bootstrap overall).
- Inter-annotator agreement (Cohen's kappa).
- Single-reviewer disclosure.
- Anchoring-effect measurement when LLM hints are used.
- Public artifacts in repo: scripts, schemas, labels, reports.
- Methodology section that another team could replicate.

## Open questions for the series

- Do we publish the full LLM-annotator dataset (256 rows) as a
  citable resource? Yes — recommend release on Zenodo with DOI.
- Do we open the Atlas Review browser tool as a public-domain
  labeling instrument? Pedro flagged this as future product
  interest; potential Paper 8 demo / system paper.
- How do we credit Sonnet 4.6 in author / acknowledgement sections?
  Standard practice: "model assistance" disclosure in methodology
  section, no co-authorship.

## Next action

Update `2026-05-27-methodology-paper-outline.md` so that it is
explicitly labeled "Paper 1 of the Atlas methodology series" and
references this master plan as the framing document.
