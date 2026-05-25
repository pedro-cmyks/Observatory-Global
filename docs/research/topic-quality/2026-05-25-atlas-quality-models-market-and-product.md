# Atlas Quality Models: Market Review And Product Fit

Date: 2026-05-25  
Status: draft canon for quality-model design  
Related: #203, #207  

Reference sources:

- IBM, "What Are Data Quality Dimensions?"
- IBM, "Result Evaluation for RAG"
- Ragas documentation, "Metrics"
- Lucidworks documentation, "Evaluation Metrics"
- Wikipedia, "Evaluation measures (information retrieval)"
- IBM documentation, "Data quality dimensions"

## Purpose

Atlas should not measure quality only by asking whether a topic assignment is
right or wrong. Quality should start from the questions Atlas promises to
answer:

1. Why is this moving now?
2. What changed in the last 10h?
3. Where is it concentrated?
4. Which subthreads are forming?
5. Which sources are driving it?
6. What evidence supports it?
7. What related thread does it connect to?

The right quality model asks:

> Can Atlas answer each of these questions with enough evidence, at the right
> semantic level, and with clear uncertainty?

## Existing Models In The Market

### 1. Data Quality Dimensions

Common enterprise data-quality frameworks use dimensions such as:

- accuracy;
- completeness;
- consistency;
- timeliness;
- validity;
- uniqueness;
- integrity.

These dimensions are useful for Atlas's raw and aggregate data health:

| Market dimension | Atlas interpretation |
|---|---|
| Accuracy | Is the extracted country/entity/source/sentiment/topic value correct? |
| Completeness | Does the thread have enough coverage across expected fields? |
| Consistency | Do panel counts, focus counts, and evidence rows agree? |
| Timeliness | Is the thread current enough for the selected window? |
| Validity | Are fields shaped correctly, ranges normalized, and codes valid? |
| Uniqueness | Are syndicated or duplicate headlines controlled? |
| Integrity | Do aggregates reconcile with represented signals and archive coverage? |

Limit: these dimensions validate data hygiene, not narrative usefulness. A row
can be valid, timely, and unique while still being the wrong evidence for a
thread.

### 2. Information Retrieval Metrics

Search and retrieval systems usually evaluate:

- precision;
- recall;
- F1;
- precision@k;
- recall@k;
- MAP;
- MRR;
- nDCG@k.

These are directly useful for Atlas surfaces that rank threads or evidence.

| Metric | Atlas use |
|---|---|
| Precision | Of shown threads/evidence, how many are actually relevant? |
| Recall | Of relevant narratives in the sample, how many did Atlas surface? |
| F1 | Balance precision and recall when both matter. |
| Precision@k | Are the top cards/evidence rows clean? |
| nDCG@k | Are the most useful/relevant threads ranked highest? |
| MRR | How quickly does the first relevant result appear? |

Limit: these metrics require labeled relevance judgments and do not by
themselves explain why a row failed.

### 3. Classification Metrics

Machine-learning classifiers use:

- accuracy;
- precision/recall/F1 per class;
- macro/micro averages;
- confusion matrices;
- ROC-AUC / PR-AUC;
- calibration curves.

These are useful for `signal_topic_assignments` and any future encoder.

Atlas-specific use:

- per-anchor precision: is this anchor reliable?
- confusion matrix: which anchors are being confused?
- calibration: does confidence 0.80 actually mean roughly 80% correctness?
- macro average: are small topics being ignored by aggregate success?

Limit: normal classification assumes the label set is flat. Atlas's main
problem is not only classification; it is semantic level. Domain, parent
thread, child thread, entity thread, and evidence role cannot be collapsed into
one class label.

### 4. Clustering And Topic Modeling Metrics

Unsupervised clustering/topic systems use:

- silhouette score;
- Davies-Bouldin / Calinski-Harabasz;
- adjusted Rand index;
- adjusted mutual information;
- topic coherence;
- human intrusion tests.

These are relevant once Atlas starts forming living child threads instead of
only grouping by `atlas_topics`.

Atlas-specific use:

- cluster coherence: do signals in a child thread talk about one thing?
- cluster separation: are two child threads truly distinct?
- split/merge validation: did a proposed split improve coherence?
- stability: does the same story remain recognizable across runs?

Limit: generic embedding clusters can look mathematically coherent while being
analytically useless. Human-labeled question-answerability must remain the
final gate.

### 5. RAG / Answer Quality Metrics

RAG evaluation frameworks measure:

- context precision;
- context recall;
- answer relevance;
- faithfulness / groundedness;
- factual correctness;
- answer completeness.

These map strongly to Atlas because Atlas is effectively answering questions
from retrieved evidence.

| RAG metric | Atlas equivalent |
|---|---|
| Context precision | Are the evidence rows shown under a thread actually useful? |
| Context recall | Did Atlas include the key evidence needed to explain the thread? |
| Faithfulness / groundedness | Is the summary/why_now supported by evidence? |
| Answer relevance | Does the thread answer the selected Atlas question? |
| Correctness | Is the explanation factually consistent with the signals? |
| Completeness | Does the answer cover geography, movement, sources, and evidence? |

Limit: LLM-as-judge can help scale review, but it should not be the only judge
for production quality. Atlas needs deterministic metrics plus labeled samples.

### 6. News / Media-Intelligence Reliability Models

Media intelligence usually looks at:

- source diversity;
- source concentration;
- syndication/duplication;
- recency;
- provenance;
- geographic spread;
- state/media/source-class weighting;
- corroboration across independent sources.

Atlas already has parts of this through `source_count`, `top_sources`,
`evidence_role`, source mix, and source integrity panels.

Limit: source diversity does not guarantee narrative correctness. Many sources
can repeat the same wrong or irrelevant frame.

## What Atlas Already Has

### Thread Confidence Band

File: `backend/app/services/thread_intelligence.py`

Current inputs:

- evidence count;
- source count;
- geography count;
- average assignment confidence.

Current bands:

- `high`;
- `medium`;
- `thin`;
- `degraded`.

What it answers:

- Is this thread strong enough to show?
- Is there enough evidence/source/geo support?

What it misses:

- semantic role;
- parent vs child distinction;
- evidence primary vs contextual;
- whether the thread answers a specific Atlas question.

### Thread Quality Report

File: `backend/scripts/thread_quality_report.py`

Current inputs:

- `lex_pct`;
- source flags;
- geo flags;
- entity flags;
- high-volume low-lex guardrail.

Grades:

- `pass`;
- `review`;
- `fail`.

What it answers:

- Is the visible thread obviously fragile?
- Are there source/geography/entity warnings?

What it misses:

- whether the thread is at the right semantic level;
- whether evidence supports `why_now`;
- whether subthreads are coherent.

### Topic Quality Audit

File: `backend/scripts/topic_quality_audit.py`

Current inputs:

- assignment volume;
- average confidence;
- lex_pct;
- theme_only_pct;
- source count;
- country count;
- unresolved geography;
- sample headlines;
- top terms.

Outputs:

- `promising`;
- `monitor`;
- `review`;
- `thin`;
- risk flags.

What it answers:

- Which internal anchors are theme-heavy, thin, or noisy?
- Where should manual review start?

What it misses:

- whether the topic should be a domain, parent thread, child thread, or entity
  thread;
- whether a broad term is valid at a higher level.

### Path B Benchmark

Files:

- `backend/scripts/topic_benchmark_harness.py`
- `docs/research/topic-quality/2026-05-25-path-b-priority-label-results.md`

Current inputs:

- labeled JSONL;
- `gold_decision`;
- `gold_topic_slug`;
- `gold_error_type`.

Outputs:

- overall precision;
- per-topic precision;
- typed failure distribution.

What it answers:

- Did current assignments clear the 85/90 precision gate?
- What kind of failure occurred?

What it misses:

- explicit `gold_scope`;
- primary/parent thread labels;
- entity references;
- whether each Atlas question was answerable.

### Sentiment Fusion Quality

File: `backend/app/services/sentiment_fusion.py`

Current inputs:

- GDELT tone;
- NLP sentiment;
- NLP coverage;
- confidence-weighted NLP sums.

What it answers:

- Which sentiment source should be used for a bucket?
- Is NLP coverage sufficient to trust Atlas sentiment over GDELT fallback?

What it misses:

- statistical validation of sentiment accuracy against human labels;
- per-language calibration;
- thread-level sentiment coherence.

### Historical Coverage Report

File: `backend/scripts/historical_coverage_report.py`

Current inputs:

- historical aggregate rows;
- represented signals;
- topic coverage;
- sentiment coverage;
- entity coverage;
- countries/topics represented.

What it answers:

- Does compact historical storage represent enough of the archive?
- Are long-window surfaces backed by processed history?

What it misses:

- whether historical topics are semantically coherent;
- whether older evidence answers the same questions as hot evidence.

## Atlas-Specific Quality Model

The recommended model is **Answerability Quality**:

> A thread is high quality if Atlas can answer the intended question with
> relevant evidence, correct semantic scope, enough coverage, and clear
> uncertainty.

### Quality Components

| Component | Question answered | Existing basis | Gap |
|---|---|---|---|
| Assignment precision | Is the signal attached to the right internal anchor? | Path B benchmark | Needs more labels. |
| Scope precision | Is this domain, parent, child, entity, evidence, context, or noise? | Root-cause audit | Needs `gold_scope`. |
| Evidence precision | Are evidence rows primary support or contextual mentions? | `evidence_role` only syndication today | Needs role labels. |
| Thread coherence | Do signals describe one live narrative? | Not yet measured directly | Needs cluster/subthread eval. |
| Question answerability | Can the thread answer the Atlas question it is shown for? | Product canon | Needs question-specific score. |
| Source integrity | Are sources diverse, non-duplicative, and useful? | thread quality/source flags | Needs source class lanes. |
| Geo coherence | Does geography concentration make sense? | country counts/flags | Needs country-level validation samples. |
| Movement integrity | Is acceleration real or caused by duplicates/syndication? | changed_10h + evidence_role | Needs dedup-adjusted velocity. |
| Sentiment reliability | Is Atlas sentiment supported and calibrated? | weighted fusion + coverage | Needs human sentiment eval. |
| Coverage sufficiency | Is the data complete enough for the window? | historical coverage + nlp coverage | Needs per-question thresholds. |

## Question-Based Validation

Each Atlas question should have its own validation test.

### 1. Why is this moving now?

Validation:

- `why_now` must cite a measurable driver: volume delta, source shift,
  geography shift, entity spike, sentiment swing, or public-attention spike.
- Evidence must include at least one primary row from the changed window.

Metrics:

- movement explanation precision;
- dedup-adjusted velocity integrity;
- source/geography/entity driver attribution.

### 2. What changed in the last 10h?

Validation:

- current 10h and prior 10h windows must be comparable;
- acceleration should not be dominated by syndicated duplicates;
- the changed entities/geographies/sources should be exposed.

Metrics:

- delta correctness;
- duplicate-adjusted delta;
- top-driver precision.

### 3. Where is it concentrated?

Validation:

- country/region concentration must match signal geography;
- unresolved or misleading country codes must be flagged;
- global vs local thread scope must be clear.

Metrics:

- geo precision;
- unresolved geo rate;
- concentration entropy.

### 4. Which subthreads are forming?

Validation:

- child threads must be more coherent than the parent cluster;
- child threads should have distinct evidence, geography, entities, or source
  mix;
- split should improve answerability.

Metrics:

- child coherence;
- parent-child evidence overlap;
- split gain;
- cluster stability.

### 5. Which sources are driving it?

Validation:

- top sources should not be only aggregators;
- syndicated copies should be collapsed or labeled;
- source lanes should distinguish wire/reporting/social/public attention.

Metrics:

- source diversity;
- top-source concentration;
- aggregator dominance;
- independent-source count.

### 6. What evidence supports it?

Validation:

- evidence rows must be primary support for the thread, not only contextual
  mentions;
- repeated evidence should be labeled as repeated/syndicated;
- evidence should cover the reason the thread is shown.

Metrics:

- evidence precision;
- primary/context ratio;
- supporting evidence coverage;
- contradiction/weakness flags.

### 7. What related thread does it connect to?

Validation:

- related threads should share meaningful co-occurrence, entity, geography,
  or causal context;
- relationships should distinguish parent/child, sibling, entity-linked, and
  geography-linked.

Metrics:

- related-link precision;
- relation-type accuracy;
- graph coherence.

## Recommended Score Shape

Do not start with one opaque score. Use a small dashboard of component scores:

```text
Atlas Quality
  Answerability: 0-100
  Evidence:      0-100
  Scope:         0-100
  Source:        0-100
  Movement:      0-100
  Coverage:      0-100
```

Then expose one simple band to users:

- high;
- medium;
- thin;
- degraded.

Internally, keep the components visible for debugging.

## Immediate Implementation Direction

1. Extend the benchmark schema with:
   - `gold_scope`;
   - `gold_primary_thread`;
   - `gold_parent_thread`;
   - `gold_entity_refs`;
   - `gold_answers_questions`.
2. Extend the scorer to report:
   - assignment precision;
   - scope precision;
   - evidence precision;
   - question answerability by Atlas question.
3. Add an `atlas_quality_model.md` spec that defines the band thresholds.
4. Only after that, decide whether to:
   - repair a mechanical matcher;
   - add parent/child thread hierarchy;
   - train an encoder;
   - adjust UI ranking.

## Decision

Atlas should evaluate quality by answerability, not by topic assignment alone.

The market gives useful pieces:

- data quality dimensions for data health;
- IR metrics for ranking;
- classification metrics for anchors;
- clustering metrics for child threads;
- RAG metrics for grounded answers;
- media-intelligence metrics for sources/provenance.

Atlas's product needs a combined model centered on the seven Atlas questions.

## References

- https://www.ibm.com/think/topics/data-quality-dimensions
- https://www.ibm.com/docs/en/ws-and-kc?topic=quality-data-dimensions
- https://www.ibm.com/think/architectures/rag-cookbook/result-evaluation
- https://docs.ragas.io/en/latest/concepts/metrics/
- https://doc.lucidworks.com/docs/managed-fusion/06-metrics-and-analytics/evaluation-metrics
- https://en.wikipedia.org/wiki/Evaluation_measures_%28information_retrieval%29
