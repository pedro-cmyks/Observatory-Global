# Narrative Intelligence Field Review

Date: 2026-05-25  
Status: research input for Atlas framework  
Related: #203, #207  

## Why This Matters

Atlas is converging on a real research/product category:

> computational narrative intelligence over live media streams.

The market and academic literature already contain adjacent models:

- event-centric narrative graphs;
- narrative maps;
- dynamic topic models;
- topic detection and tracking;
- media framing analysis;
- media attention/influence platforms;
- interactive narrative analytics.

None maps perfectly to Atlas. The useful move is to borrow the strongest
parts, then define Atlas's own harness around answerability.

## Adjacent Models

### 1. Event-Centric Narrative Graphs

Relevant work:

- "Narrative Graph: Telling Evolving Stories Based on Event-centric Temporal
  Knowledge Graph" ([PubMed](https://pubmed.ncbi.nlm.nih.gov/37128597/))
- Event knowledge graph research
  ([review](https://www.mdpi.com/2076-3417/13/22/12338))
- Event extraction and event-relation extraction surveys
  ([ScienceDirect survey](https://www.sciencedirect.com/science/article/pii/S266665102100005X),
  [event-based news narrative extraction](https://arxiv.org/abs/2302.08351))

Core idea:

Represent news as events connected by time, entities, locations, and relations.
Then compress the graph into salient sequences or storylines.

Atlas fit:

- Strong fit for `what happened`, `who/where`, and timeline ordering.
- Useful for child threads: a child thread is often a compact event sequence.
- Useful for evidence roles: a row can be primary event evidence, context, or
  related background.

Atlas gap if copied directly:

- Event graphs usually emphasize event structure more than media attention,
  source mix, narrative framing, and user-facing exploratory UI.

Atlas adaptation:

```text
signal -> event candidate -> event cluster -> child thread -> parent thread
```

### 2. Narrative Maps

Relevant work:

- "Narrative Maps: An Algorithmic Approach to Represent and Extract
  Information Narratives" ([arXiv](https://arxiv.org/abs/2009.04508))
- "Evaluating the Ability of Computationally Extracted Narrative Maps to
  Encode Media Framing" ([arXiv](https://arxiv.org/abs/2405.02677))

Core idea:

Represent a narrative as a graph/map of landmarks and routes. The goal is not
only to cluster documents, but to show structure: how story elements connect
and how a person can move through the narrative.

Atlas fit:

- Very strong fit for the user-facing idea of Narrative Threads.
- Supports the product metaphor of moving from broad thread to subthreads to
  evidence.
- Aligns with Workspace: a user should be able to traverse a narrative route.

Atlas gap if copied directly:

- Narrative maps are often research artifacts, not live operational dashboards
  over 200k daily signals.

Atlas adaptation:

```text
parent thread = map region
child thread = route/landmark
entity thread = recurring landmark
evidence = cited map point
```

### 3. Dynamic Topic Modeling

Relevant work:

- Blei and Lafferty dynamic topic models
  ([PDF](https://www.cs.columbia.edu/~blei/papers/BleiLafferty2006a.pdf))
- BERTopic topics-over-time
  ([docs](https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html))
- BERTopic paper ([arXiv](https://arxiv.org/abs/2203.05794))

Core idea:

Topics are not fixed bags of words. They evolve through time. A topic's
representation at one time window can differ from its representation later.

Atlas fit:

- Good fit for detecting drift in thread language.
- Useful for `what changed in the last 10h`.
- Useful for watching parent concepts split into child threads.

Atlas gap if copied directly:

- Topic models can be coherent statistically but analytically weak.
- They often lack explicit entities, source roles, and evidence quality.

Atlas adaptation:

Use dynamic topic modeling as one feature for:

- emergence;
- split/merge candidates;
- label drift;
- lexical drift.

Do not use it as the full Atlas model.

### 4. Topic Detection And Tracking

Relevant work:

- Topic Detection and Tracking (TDT)
  ([NIST overview](https://www.nist.gov/itl/iad/mig/topic-detection-and-tracking-tdt))
- Temporal information retrieval
- Event-based news narrative extraction surveys
  ([arXiv](https://arxiv.org/abs/2302.08351))

Core idea:

Detect new stories in news streams, track known stories over time, and cluster
related reports.

Atlas fit:

- Direct fit for live ingestion.
- Useful for parent/child lifecycle:
  - emerging;
  - active;
  - splitting;
  - fading;
  - archived.

Atlas gap if copied directly:

- Classic TDT is mostly about story detection/tracking, not meaning,
  answerability, frame, or source integrity.

Atlas adaptation:

Use TDT-like logic as operational lifecycle management, not as the full
narrative intelligence layer.

### 5. Media Framing Analysis

Relevant work:

- computational media framing surveys
  ([ACL 2024 survey](https://aclanthology.org/2024.acl-long.822/));
- Media Frames Corpus;
- event-centric framing work
  ([WNU 2024 paper](https://aclanthology.org/2024.wnu-1.15.pdf));
- mixed-method computational frame analysis.

Core idea:

Different sources can cover the same event through different interpretive
frames. Framing is not only "what happened"; it is "what this event is made to
mean."

Atlas fit:

- Strong fit for `which sources are driving it` and `what related thread does
  it connect to`.
- Important for source lanes and eventual narrative contrast.
- Helps separate event similarity from narrative similarity.

Atlas gap if copied directly:

- Frame detection is hard and often domain-specific.
- LLM/frame classifiers can overstate confidence without labeled validation.

Atlas adaptation:

Treat framing as a later enrichment layer:

```text
event/thread similarity first
source and frame contrast second
```

### 6. Media Cloud / Attention Mapping

Relevant work:

- Media Cloud
  ([MIT overview](https://www.media.mit.edu/projects/media-cloud/overview/),
  [Berkman Klein](https://cyber.harvard.edu/research/mediacloud))
- Media Cloud ICWSM paper
  ([AAAI ICWSM](https://ojs.aaai.org/index.php/ICWSM/article/view/18127))

Core idea:

Measure media attention: what sources cover which stories, how language differs
across sources, and how stories spread.

Atlas fit:

- Very strong fit for source mix, source concentration, spread, and attention.
- Useful for source lanes and public-attention layers.

Atlas gap if copied directly:

- Media Cloud is more a media research platform than a live geopolitical
  narrative intelligence product.

Atlas adaptation:

Use attention mapping as a first-class component:

- volume;
- source diversity;
- source concentration;
- source family/lane;
- geographic spread;
- syndication.

### 7. StoryAtlas / Narrative Visualization

Relevant work:

- StoryAtlas from Cultural Heritage Informatics Initiative
  ([project page](https://chi.anp.casl.cal.msu.edu/2024/05/02/explore-storyatlas/))
- Visualizing narrative patterns in online news media
  ([Multimedia Tools and Applications](https://link.springer.com/article/10.1007/s11042-019-08186-9))

Core idea:

Narrative analysis should be visual and exploratory, not only tabular. Maps,
time, geography, and language patterns help people find a way into large text
corpora.

Atlas fit:

- Strong fit for Atlas as both model and visualizer.
- Reinforces that the visualization is not decorative; it is part of the
  analysis model.

Atlas gap if copied directly:

- StoryAtlas is closer to academic/journalistic discourse analysis than live
  operational signal intelligence.

Atlas adaptation:

Atlas should make the visual grammar part of the model:

- globe = where narratives manifest;
- threads = how narratives organize;
- stream = evidence;
- focus = analytical lens;
- workspace = reasoning route.

### 8. Interactive Narrative Analytics

Relevant work:

- "Interactive Narrative Analytics: Bridging Computational Narrative Extraction
  and Human Sensemaking" ([arXiv](https://arxiv.org/abs/2601.11459))

Core idea:

Narrative extraction should be paired with interactive visual analytics so a
human can inspect, validate, and make sense of the extracted structure.

Atlas fit:

- Very strong. This is close to the product direction.
- Atlas should not only compute clusters; it should let users inspect why a
  thread exists.

Atlas adaptation:

Atlas is not only a classifier. It is a model plus an inspection surface:

```text
model extracts structure
visualizer exposes structure
user validates structure through evidence
```

## Synthesis

The field suggests five durable ideas:

1. **Narratives are graph-like.** They connect events, entities, locations,
   sources, frames, and time.
2. **Narratives evolve.** Topic language, source attention, and geography shift
   over time.
3. **Narratives are not flat topics.** Parent/child/entity/evidence levels
   matter.
4. **Attention is part of the story.** Volume, source spread, and syndication
   are not just metadata.
5. **Visualization is part of analysis.** A narrative system must expose
   structure and evidence, not only labels.

## Atlas Positioning

Atlas should be defined as:

> a live narrative intelligence model and visualizer that turns global media
> signals into answerable, evidence-backed Narrative Threads.

That means Atlas is not:

- a news reader;
- a fixed taxonomy dashboard;
- a GDELT theme browser;
- a pure topic model;
- a generic clustering UI.

Atlas is:

- a thread model;
- a quality model;
- a source/geo/evidence model;
- a visual reasoning interface.

## References

- Narrative Graph: https://pubmed.ncbi.nlm.nih.gov/37128597/
- Narrative Maps: https://arxiv.org/abs/2009.04508
- Narrative maps and framing: https://arxiv.org/abs/2405.02677
- Narrative extraction survey: https://link.springer.com/article/10.1007/s10462-022-10338-7
- Event-based news narrative extraction survey: https://arxiv.org/abs/2302.08351
- Event Knowledge Graph review: https://www.mdpi.com/2076-3417/13/22/12338
- Event extraction survey: https://www.sciencedirect.com/science/article/pii/S266665102100005X
- Dynamic topic modeling in BERTopic: https://maartengr.github.io/BERTopic/getting_started/topicsovertime/topicsovertime.html
- Dynamic Topic Models: https://www.cs.columbia.edu/~blei/papers/BleiLafferty2006a.pdf
- BERTopic paper: https://arxiv.org/abs/2203.05794
- Media Cloud: https://cyber.harvard.edu/research/mediacloud
- Media Cloud platform paper: https://ojs.aaai.org/index.php/ICWSM/article/view/18127
- StoryAtlas: https://chi.anp.casl.cal.msu.edu/2024/05/02/explore-storyatlas/
- Visualizing narrative patterns in news: https://link.springer.com/article/10.1007/s11042-019-08186-9
- Media framing survey: https://aclanthology.org/2024.acl-long.822/
- Media framing through event-centric narratives: https://aclanthology.org/2024.wnu-1.15.pdf
- GDELT: https://gns.gdeltproject.org/
- GDELT GKG codebook: https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook.pdf
