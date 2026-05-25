# Atlas Narrative Intelligence Model: State Of The Art And Validation Plan

Date: 2026-05-25  
Status: research roadmap, not a submitted paper  
Related implementation docs:
`docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`,
`docs/research/topic-quality/2026-05-25-narrative-intelligence-field-review.md`,
`backend/scripts/topic_benchmark_harness.py`  
Related issues: #203, #204, #207  

## Purpose

This document starts the research track for a future paper about the Atlas
Narrative Intelligence Model.

It is not the paper. It is the plan for making a paper defensible:

1. define the research problem;
2. position Atlas against the state of the art;
3. make the hypothesis falsifiable;
4. define baselines and ablations;
5. specify data, labels, metrics, and experiments;
6. list what evidence must exist before writing a publishable manuscript.

## Working Title

**Atlas Narrative Intelligence Model: An Answerability-First Framework for Live
Media Narrative Extraction, Validation, and Visualization**

Shorter candidate:

**Atlas: Answerability-First Narrative Intelligence Over Live Global Media
Signals**

## Research Thesis

Atlas should be evaluated as a narrative intelligence model, not merely as a
topic classifier or news dashboard.

Working hypothesis:

> An answerability-first narrative intelligence framework can produce more
> analytically useful representations of live media narratives than topic-only
> classification or flat clustering, by modeling temporal movement, semantic
> scope, evidence roles, source dynamics, and visual inspectability.

This is a hypothesis, not a claim already proven.

## Problem Formulation

Live media streams create several linked problems:

- **Volume:** hundreds of thousands of signals can arrive per day.
- **Flat-topic ambiguity:** the same term can be a parent theme, a child event,
  an entity reference, background context, or noise.
- **Temporal drift:** the language and geography of a story change over time.
- **Evidence ambiguity:** not every matching signal is direct evidence.
- **Source dynamics:** coverage volume can reflect attention, syndication,
  source concentration, or genuine event escalation.
- **User inspection:** an analyst needs to see why a thread exists, not only
  the label attached to it.

The research question is:

> Can live media narratives be modeled as temporal, semantic, evidential, and
> visual structures whose quality is measured by their ability to answer
> analytical questions?

## State Of The Art Map

### 1. Computational Narrative Extraction

The broad narrative extraction literature frames the field as a pipeline of
tasks over text and emphasizes the need for narrative elements, annotation
schemes, extraction methods, multilingual handling, formal representations, and
standard evaluation datasets/metrics
([Santana et al., 2023](https://link.springer.com/article/10.1007/s10462-022-10338-7)).

Relevance to Atlas:

- Supports the need for explicit annotation beyond `correct`/`incorrect`.
- Supports Atlas's v2 benchmark fields: `gold_scope`, `gold_evidence_role`,
  parent/child thread candidates, and supported analytical questions.
- Warns against treating clustering alone as narrative understanding.

Atlas gap to validate:

- Atlas must show that its label schema is not arbitrary. It should demonstrate
  that semantic scope and evidence role improve evaluation and downstream
  thread quality.

### 2. Event-Based News Narrative Extraction

Event-based news narrative extraction organizes prior work by representation
models, extraction criteria, and evaluation approaches
([Norambuena, Mitra, and North, 2023](https://arxiv.org/abs/2302.08351)).

Relevance to Atlas:

- News narratives can be represented around events and relations.
- This supports Atlas child threads as event-centered structures.
- It also supports testing whether a row is `primary_event`, `followup`,
  `background`, or `reaction`.

Atlas gap to validate:

- Atlas should not stop at event extraction. It also needs source dynamics,
  geography, movement drivers, and visual inspection.

### 3. Narrative Maps

Narrative Maps propose a theory-driven computational representation of
narratives using landmarks and routes, extracting graph structure through an
optimization approach that balances coherence and coverage
([Keith and Mitra, 2020](https://arxiv.org/abs/2009.04508)). Later work
evaluates whether computationally extracted narrative maps can encode media
framing ([Keith et al., 2024](https://arxiv.org/abs/2405.02677)).

Relevance to Atlas:

- Strong theoretical support for treating narratives as structured routes, not
  only topic labels.
- Directly aligns with Atlas parent thread -> child thread -> evidence route.
- Supports the idea that visualization can be part of the analytic method.

Atlas gap to validate:

- Atlas operates on live, noisy, multilingual, high-volume media streams. It
  must prove that the map/thread concept survives operational data conditions.

### 4. Topic Detection And Tracking

The NIST Topic Detection and Tracking program focused on searching, organizing,
and structuring multilingual news materials, with tasks such as topic tracking,
link detection, topic detection, first-story detection, and story segmentation
([Fiscus and Doddington, 2002](https://www.nist.gov/publications/topic-detection-and-tracking-evaluation-overview)).

Relevance to Atlas:

- Provides a serious baseline family for detecting and tracking stories in news
  streams.
- Supports lifecycle concepts: emerging, active, splitting, fading, archived.

Atlas gap to validate:

- TDT-style tracking does not by itself answer why a narrative is moving, what
  evidence supports it, or how sources are shaping it.

### 5. Dynamic Topic Modeling

Dynamic Topic Models analyze how topics evolve across sequential document
collections using probabilistic time-series models
([Blei and Lafferty, 2006](https://www.cs.columbia.edu/~blei/papers/BleiLafferty2006a.pdf)).
More recent topic-modeling systems such as BERTopic use transformer embeddings,
clustering, and class-based TF-IDF to produce coherent topic representations
([Grootendorst, 2022](https://arxiv.org/abs/2203.05794)).

Relevance to Atlas:

- Useful baseline for temporal drift and language evolution.
- Useful feature family for label drift, lexical drift, split/merge candidates,
  and emergence detection.

Atlas gap to validate:

- Topic coherence is not the same as analytical usefulness.
- Topic models often lack explicit evidence roles, source dynamics, and
  answerability.

### 6. Media Framing

Computational media framing research argues that frames are not just topical
content; they involve interpretive schemas and communicative aspects that shape
how facts are understood
([Otmakhova, Khanehzar, and Frermann, 2024](https://aclanthology.org/2024.acl-long.822/)).

Relevance to Atlas:

- Supports separating event similarity from narrative similarity.
- Supports source/frame contrast as a later Atlas relation type.
- Helps explain why two sources covering the same event may still represent
  different narrative structures.

Atlas gap to validate:

- Atlas should not overclaim framing until labeled frame data exists. For the
  first paper, framing can be positioned as related work and future enrichment,
  while source-lane and evidence-role measures are evaluated first.

### 7. Media Attention Platforms

Media Cloud is an open-source media research platform for studying online news
ecosystems, collecting and organizing media data and supporting attention over
time, source collections, and media ecosystem analysis
([Roberts et al., 2021](https://ojs.aaai.org/index.php/ICWSM/article/view/18127);
[Media Cloud search](https://search.mediacloud.org/)).
The MIT overview describes Media Cloud as tracking stories across many sources
and languages, supporting attention/coverage peaks, network analysis, and
clustered language use
([MIT Media Lab overview](https://www.media.mit.edu/projects/media-cloud/overview/)).

Relevance to Atlas:

- Strong baseline for attention and coverage analysis.
- Supports Atlas source dynamics: volume, source diversity, concentration,
  geography, and syndication.

Atlas gap to validate:

- Attention is a necessary component, but Atlas claims a thread-quality layer
  based on answerability and evidence roles.

### 8. GDELT / Theme-Based Global Monitoring

GDELT's Global Knowledge Graph extracts entities, locations, themes, counts,
dates, and other fields from global news content
([GDELT GKG codebook](https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.pdf)).
GDELT also exposes tone timelines as a way to inspect emotional tone over time
([GDELT Tone Timeline](https://analysis.gdeltproject.org/module-gkg-tonetimeline.html)).

Relevance to Atlas:

- GDELT is a practical upstream signal provider and an obvious baseline.
- GDELT themes are useful hints, but the Atlas audits show they are not enough
  to validate a user-facing narrative thread.

Atlas gap to validate:

- Atlas must show improvement over theme-only classification in precision,
  semantic scope, evidence quality, and answerability.

## Proposed Atlas Contribution

Atlas should claim a specific, testable contribution:

1. **Representation:** a live narrative thread object that separates domain
   anchors, parent threads, child threads, entity threads, evidence, context,
   and noise.
2. **Validation:** an answerability-first harness that scores whether a thread
   can answer analytical questions with evidence.
3. **Operationalization:** a pipeline that works over high-volume global media
   signals rather than curated case studies only.
4. **Visualization:** a product interface where the visualization is part of
   inspection and validation, not decoration.

This should be framed as a framework and empirical system paper, not as a claim
that Atlas has solved narrative understanding.

## Research Questions

RQ1. Does semantic/evidence-role labeling improve evaluation quality compared
with binary topic relevance?

RQ2. Do parent/child/entity thread structures reduce false positives and false
negatives compared with fixed topic labels?

RQ3. Does answerability predict analytical usefulness better than raw volume,
confidence, or topic precision alone?

RQ4. Do source dynamics, geography, and temporal movement improve thread
quality beyond text-only clustering?

RQ5. Can a visual thread interface help users inspect and validate narrative
structure more effectively than a flat list of topics or articles?

## Hypotheses

H1. A semantic/evidence-role benchmark will identify failure modes that binary
topic labels hide.

H2. Parent/child/entity thread modeling will preserve useful broad concepts
while reducing false direct-evidence assignments.

H3. Threads with higher answerability scores will be rated as more analytically
useful by human reviewers than threads selected by raw volume alone.

H4. Adding temporal, geo, source, and evidence-role features will improve
thread quality over text-only embedding clusters.

H5. Visual inspectability will improve reviewer confidence and error discovery
compared with non-visual tabular outputs.

## Baseline Families

| Baseline | What it tests | Candidate implementation |
|---|---|---|
| GDELT theme-only | Whether upstream themes are enough. | `signals_v2.themes` / GKG theme hints. |
| Atlas topic assignment | Current internal anchor quality. | `signal_topic_assignments` v2/v3. |
| Flat embedding clustering | Whether semantic clustering alone works. | Sentence embeddings + HDBSCAN/BERTopic-style labels. |
| Dynamic topic model | Whether temporal topic drift explains threads. | DTM or BERTopic topics-over-time report. |
| TDT-style tracking | Whether story detection/tracking is enough. | first-story/link detection approximation over signals. |
| Event-centric graph | Whether event/entity/time graph explains child threads. | event/entity/location/time extraction report. |
| Media attention | Whether attention curves/source spread explain quality. | volume/source/geography concentration baseline. |
| Atlas full model | Proposed framework. | semantic scope + evidence role + movement + source + geo + answerability. |

Internal Atlas v1/v2 comparisons are useful for engineering progress, but the
paper must compare against at least some external baseline families above.

## Ablation Plan

The Atlas full model should be tested by removing components:

| Ablation | Removed component | Expected failure if Atlas thesis is true |
|---|---|---|
| No semantic scope | parent/child/entity/evidence separation | broad concepts become noisy direct assignments. |
| No evidence role | primary/background/reaction/source distinction | thread evidence quality drops. |
| No temporal movement | movement drivers and timeline features | cannot answer why moving now / what changed. |
| No geography | country/region concentration | cannot answer where concentrated. |
| No source dynamics | diversity/concentration/source lane | cannot distinguish event movement from syndication. |
| No visual inspection | only tabular/text output | human reviewers find fewer errors or trust less. |

## Dataset Plan

### Data Source

Use Atlas's live and archived signal store:

- hot `signals_v2` data;
- `signal_topic_assignments`;
- source metadata;
- country/geography fields;
- NLP sentiment/entity fields when available;
- processed historical aggregates for longer windows.

### Sampling Strategy

Build a stratified benchmark, not a convenience sample:

- time windows: 10h, 24h, 7d if processed coverage is available;
- assignment method: lex-supported, theme-only, high-confidence, low-confidence;
- topic/domain: conflict, health, migration, labor, mining, food, transport,
  environment;
- geography: high-volume countries and lower-volume regions;
- language/source: English and non-English where available;
- volume level: high-volume, medium, thin/emerging;
- source concentration: diverse vs single-source-heavy.

### Label Schema

Use `atlas-topic-benchmark-v2`:

- `gold_decision`;
- `gold_error_type`;
- `gold_scope`;
- `gold_evidence_role`;
- `gold_parent_thread`;
- `gold_child_thread`;
- `gold_supported_questions`;
- notes.

Future multi-annotator runs should add:

- `annotator_id`;
- `annotation_round`;
- `disagreement_reason`;
- adjudicated final label.

## Metrics

### Assignment Metrics

- topic precision;
- topic recall where feasible;
- false-positive rate by source/language/topic;
- precision by confidence bucket.

### Semantic Metrics

- scope accuracy;
- evidence-role accuracy;
- parent-child consistency;
- entity-thread participation accuracy;
- context-vs-evidence separation.

### Answerability Metrics

For each thread, score the seven Atlas questions:

| Question | Metric |
|---|---|
| Why moving now? | movement driver present and evidence-backed. |
| What changed? | temporal delta or before/after explanation present. |
| Where concentrated? | geo distribution coherent and inspectable. |
| Which subthreads? | child clusters distinct and evidence-backed. |
| Which sources? | source mix and concentration available. |
| What evidence? | representative evidence roles present. |
| Related thread? | typed relation exists and is defensible. |

Thread Answerability Score:

```text
answerability_score =
  weighted_mean(
    movement_answer,
    temporal_answer,
    geo_answer,
    subthread_answer,
    source_answer,
    evidence_answer,
    relation_answer
  )
```

Weights should start equal. Weight tuning should not happen until enough labels
exist to avoid overfitting.

### User/Analyst Metrics

For later paper phases:

- usefulness rating;
- error discovery rate;
- time to understand thread;
- confidence calibration;
- preference against baseline presentation.

## Experimental Sequence

### Phase 1: Label Validity

Goal: prove that the v2 label schema is usable and reveals meaningful failure
modes.

Work:

- generate a larger stratified sample;
- label semantic scope and evidence role;
- compute label distributions;
- measure how often topic failures are actually parent/entity/context cases.

Exit criteria:

- label instructions are stable;
- at least one pilot sample has low ambiguity;
- the benchmark exposes actionable model errors.

### Phase 2: Baseline Comparison

Goal: compare Atlas against topic-only and flat clustering baselines.

Work:

- run GDELT theme-only baseline;
- run current Atlas assignment baseline;
- run a flat embedding/BERTopic-style clustering baseline;
- score all outputs using the same v2 labels where possible.

Exit criteria:

- Atlas full model clears topic-only and flat-clustering baselines on
  answerability and evidence quality;
- failures are documented, not hidden.

### Phase 3: Thread Graph Report

Goal: generate a read-only Narrative Thread Graph report before adding
persistent graph tables.

Work:

- propose parent/child/entity thread candidates;
- compute relation candidates;
- attach movement drivers and evidence roles;
- score thread answerability;
- produce a reproducible report artifact.

Exit criteria:

- report explains top threads better than the current flat thread list;
- at least one visible Atlas surface can consume the report without changing
  the product contract.

### Phase 4: Analyst Evaluation

Goal: evaluate whether the Atlas representation is more useful to humans.

Work:

- compare Atlas thread graph vs topic list vs flat cluster list;
- ask reviewers to answer the seven Atlas questions;
- measure accuracy, time, confidence, and error discovery.

Exit criteria:

- Atlas improves usefulness or error discovery without hiding uncertainty.

## Paper Structure Draft

1. **Introduction**
   - problem of live media narrative overload;
   - why topic dashboards are insufficient;
   - Atlas's answerability-first proposal.

2. **Related Work**
   - narrative extraction;
   - event-based news narratives;
   - narrative maps;
   - topic detection/tracking;
   - dynamic topic modeling;
   - media framing;
   - media attention platforms;
   - visual analytics.

3. **Framework**
   - signals;
   - parent/child/entity threads;
   - evidence roles;
   - movement drivers;
   - source/geography;
   - quality envelope;
   - visual inspection.

4. **Evaluation Design**
   - data;
   - label schema;
   - baselines;
   - ablations;
   - metrics.

5. **Experiments**
   - benchmark quality;
   - baseline comparisons;
   - thread graph report;
   - analyst evaluation.

6. **Results**
   - reserved for measured experiment outputs.

7. **Discussion**
   - what answerability captures;
   - what it misses;
   - multilingual and source-bias limitations;
   - operational constraints.

8. **Conclusion**
   - Atlas as a validated framework if evidence supports it.

## Evidence Required Before Writing The Paper

Do not write a final paper until these artifacts exist:

- larger v2 labeled sample;
- label guide with examples;
- score report with scope/evidence/question distributions;
- at least one baseline comparison;
- at least one ablation report;
- read-only Narrative Thread Graph report;
- evidence that answerability correlates with reviewer usefulness or error
  discovery;
- limitations section grounded in observed failures.

## Immediate Next Work

1. Create a v2 label guide with examples.
2. Generate a larger stratified sample using `topic_benchmark_harness.py`.
3. Supplement labels with semantic scope, evidence role, parent/child thread,
   and supported questions.
4. Build a read-only report that aggregates v2 labels into answerability
   metrics.
5. Only then decide which baseline to implement first.

## Initial Bibliography

- Blei, D. M., and Lafferty, J. D. 2006. Dynamic Topic Models.
  https://www.cs.columbia.edu/~blei/papers/BleiLafferty2006a.pdf
- Fiscus, J. G., and Doddington, G. R. 2002. Topic Detection and Tracking
  Evaluation Overview.
  https://www.nist.gov/publications/topic-detection-and-tracking-evaluation-overview
- GDELT Project. Global Knowledge Graph Codebook V2.
  https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.pdf
- GDELT Project. GKG Tone Timeline Visualizer.
  https://analysis.gdeltproject.org/module-gkg-tonetimeline.html
- Grootendorst, M. 2022. BERTopic: Neural topic modeling with a class-based
  TF-IDF procedure. https://arxiv.org/abs/2203.05794
- Keith, B., and Mitra, T. 2020. Narrative Maps: An Algorithmic Approach to
  Represent and Extract Information Narratives. https://arxiv.org/abs/2009.04508
- Keith, B., et al. 2024. Evaluating the Ability of Computationally Extracted
  Narrative Maps to Encode Media Framing. https://arxiv.org/abs/2405.02677
- Norambuena, B. K., Mitra, T., and North, C. 2023. A Survey on Event-based
  News Narrative Extraction. https://arxiv.org/abs/2302.08351
- Otmakhova, Y., Khanehzar, S., and Frermann, L. 2024. Media Framing: A
  typology and Survey of Computational Approaches Across Disciplines.
  https://aclanthology.org/2024.acl-long.822/
- Roberts, H., et al. 2021. Media Cloud: Massive Open Source Collection of
  Global News on the Open Web.
  https://ojs.aaai.org/index.php/ICWSM/article/view/18127
- Santana, E., et al. 2023. A survey on narrative extraction from textual data.
  https://link.springer.com/article/10.1007/s10462-022-10338-7
