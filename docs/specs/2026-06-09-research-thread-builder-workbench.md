# Research Thread Builder + Workbench Investigation Spec

**Date:** 2026-06-09  
**Status:** active design target  
**Branch:** `v3-intel-layer`  
**Related:** #213 Research Thread Builder, #207 Living Narrative Threads, #175 Search, #177 Signal Stream,
Workbench, `docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`

## Objective

Atlas search should let a user type a natural investigation question and receive
a compact research dossier that is as rich as a careful web investigation, but
grounded in Atlas evidence and compressed into one navigable workspace.

Target user job:

> "I want to investigate a developing topic, understand who is talking about it,
> what each actor/source is saying, what frames are competing, where the story is
> happening, what else it connects to, and how the story is evolving."

This is not a one-off Iran climate feature. The Iran case is the forcing
example for a general product capability:

- natural-language research intent;
- compound/multi-hop question expansion;
- evidence-backed Narrative Thread tree;
- "who says what" source/actor matrix;
- frame comparison;
- coverage-gap detection;
- list-vs-detail reconciliation;
- Workbench handoff for iterative investigation.

The expected result is that Atlas stops losing the majority of relevant
information because the user's words do not exactly match the current signal
fields or topic slugs.

## Forcing Case

Initial user intent:

> "Noticias relacionadas con el clima en Medio Oriente, específicamente en
> Irán. Quiero saber quién habla de eso, qué dice cada quien, cómo evoluciona la
> historia, qué países están hablando, fuentes, actores, dónde se desarrolla, y
> por qué se está desarrollando ahora."

Expanded compound intent:

> "Además, quiero conectar eso con ataques a bases o infraestructura
> estadounidense/satelital/comunicaciones en Medio Oriente, otros países
> afectados, y cómo esa dimensión se relaciona con clima, agua, energía,
> infraestructura y guerra."

The correct Atlas interpretation is not a single keyword query. It is a
research graph:

```text
Iran climate
├─ water scarcity / drought / reservoirs / dams / Tehran rationing
├─ heatwaves / extreme temperatures / dust / public health
├─ agriculture / self-sufficiency / groundwater / food prices
├─ protests / governance / mismanagement / sanctions
├─ conflict damage to water/electricity infrastructure / WASH / disease risk
├─ regional water-energy-security spillovers
└─ US/allied bases and satellite/communications infrastructure
   ├─ Iran/proxy attacks on bases in Kuwait, Bahrain, Qatar, UAE, Saudi, Iraq
   ├─ radars, radomes, satellite communications, air-defense equipment
   ├─ commercial satellite imagery and evidence restrictions
   ├─ alleged Chinese/Russian targeting-support routes
   └─ links to energy/water infrastructure threats in the Gulf
```

## Web Investigation Baseline

Manual web research on 2026-06-09 found a coherent storyline that Atlas should
eventually reconstruct from its own data plus explicit external enrichment:

1. **Climate/water core.** Iran is under severe long-running drought and water
   stress. UNICEF frames this as climate risk for children and public health:
   hotter temperatures, reduced rainfall, water scarcity, heat waves, dust
   storms, floods, urban heat, energy demand, displacement, and child
   vulnerability.
2. **Tehran and reservoir crisis.** Al Jazeera frames the story through dams,
   rationing, possible evacuation, low precipitation, heatwaves above 50C,
   agriculture consuming most water, poor management, sanctions, and local
   experts.
3. **Security and governance.** WRI frames the same crisis as water bankruptcy:
   climate plus unsustainable water use, groundwater depletion, agriculture,
   dams, subsidence, protests, food security, energy, health, and conflict.
4. **Humanitarian/WASH.** ACAPS frames conflict damage as compounding the chronic
   water crisis: damaged water infrastructure, electricity cuts affecting
   pumping, displaced people in water-stressed areas, waterborne disease risk,
   food inflation, and strained health systems.
5. **Political stability.** The Guardian frames water shortages as a backdrop to
   protest and regime pressure: day-zero risk, pressure cuts, demands for water
   and electricity, and climate breakdown plus mismanagement.
6. **Regional conflict infrastructure.** Recent reporting and OSINT analysis
   connect Iran conflict escalation to attacks on US/allied bases and
   communications/radar/satellite-linked infrastructure in Kuwait, Bahrain,
   Qatar, UAE, Saudi Arabia, Iraq, and Jordan; commercial satellite imagery
   becomes both evidence and contested infrastructure.

## Current Atlas Result

Production checks on 2026-06-09:

| Query / route | Result | Product meaning |
|---|---|---|
| `/api/v2/search/thread?q=Iran climate water drought&hours=168&country_code=IR` | `0` signals | Exact evidence query misses the research intent. |
| `Iran water shortage`, `Iran drought`, `Tehran water`, `Iran heatwave`, `Iran dams`, `Iran water crisis` | `0` signals | Natural query variants still miss. |
| `/api/v2/search/unified?q=Iran climate water drought&country=IR` | detects `IR`, suggests Climate/Water concepts but no signal matches | Search knows the idea at taxonomy level but cannot bridge it to evidence. |
| `/api/v2/threads?hours=168&country_code=IR` | returns threads such as `flood-landslide-disaster--ir`, `armed-conflict-escalation--ir`, `oil-gas-supply-risk--ir` | Atlas has relevant country activity, but it is not linked to the query intent. |
| `/api/v2/theme/flood-landslide-disaster?hours=168&country_code=IR` | `0` | List/detail contract mismatch. |
| `/api/v2/signals?hours=168&country_code=IR&sort=relevance` | signals returned, but mixed/noisy for the climate/water intent | Stream relevance is not intent-aware enough. |

Conclusion:

Atlas has relevant information, but search and Workbench do not yet assemble it
into an investigation. The missing product layer is a Research Thread Builder.

## Product Principle

Search is not just retrieval. For Atlas, search must be an investigation
constructor.

The user should be able to start with:

```text
clima en Irán y relación con ataques a infraestructura estadounidense/satelital
en Medio Oriente
```

Atlas should respond with:

- an interpreted research intent;
- editable subquestions;
- evidence tree;
- sources and actors;
- frame comparison;
- gaps;
- suggested next branches;
- Workbench graph/dossier.

The system must make uncertainty visible. It should not pretend it found
evidence when it only found taxonomy similarity or web context.

## Target User Experience

### 1. Natural Research Query

The user enters a broad or compound query in Search or Workbench:

```text
clima Irán Medio Oriente agua sequía y ataques a bases estadounidenses satélite
```

Atlas creates an interpreted query card:

```json
{
  "main_intent": "Iran climate-water crisis",
  "geo_scope": ["IR", "Middle East"],
  "time_scope": "recent + historical context",
  "subquestions": [
    "What is happening with drought, water shortages, heat, and reservoirs in Iran?",
    "Who is talking about it and how are they framing it?",
    "How does conflict damage water/electricity infrastructure?",
    "Which other Middle Eastern countries are connected by water, energy, bases, or shipping?",
    "What is the connection to US/allied bases, satellite imagery, communications, and targeting?"
  ],
  "expanded_terms": {
    "climate": ["drought", "heatwave", "water scarcity", "reservoirs", "dams", "WASH"],
    "conflict_infrastructure": ["US bases", "radar", "radome", "satellite communications", "air defense"],
    "regional": ["Kuwait", "Bahrain", "Qatar", "UAE", "Saudi Arabia", "Iraq", "Jordan"]
  }
}
```

The user can edit/remove subquestions before running the investigation.

### 2. Research Thread Tree

Atlas returns a tree, not a flat result list:

```text
Iran climate-water crisis
├─ Water scarcity and drought
│  ├─ Tehran reservoirs and rationing
│  ├─ dams / aquifers / groundwater depletion
│  └─ agriculture and self-sufficiency water demand
├─ Humanitarian consequences
│  ├─ WASH and disease risk
│  ├─ food prices and livelihoods
│  └─ displacement / children / health
├─ Governance and protest
│  ├─ mismanagement frame
│  ├─ sanctions/economic capacity frame
│  └─ protest/stability frame
├─ Conflict and infrastructure
│  ├─ damaged water/electricity infrastructure
│  ├─ energy and water security in Gulf states
│  └─ international-law/civilian-harm frame
└─ US bases and satellite/communications layer
   ├─ strikes on bases / radars / communications
   ├─ satellite imagery as evidence
   ├─ targeting-support claims
   └─ regional countries hosting affected infrastructure
```

Each node has:

- evidence count;
- countries;
- sources;
- frame labels;
- representative evidence;
- confidence/coverage band;
- gaps.

### 3. Who Says What Matrix

For every node, Atlas should show:

| Source / actor | Type | What they say | Frame | Evidence role | Confidence |
|---|---|---|---|---|---|
| UNICEF | UN/humanitarian | Climate change worsens water, health, children, displacement. | child-rights / climate adaptation | background/context | high |
| Al Jazeera | media | Dams, rationing, agriculture, sanctions, mismanagement. | water crisis / governance | primary reporting + analysis | medium/high |
| WRI | think tank | Water bankruptcy; conflict can amplify scarcity into security risk. | water-security | analysis | high |
| ACAPS | humanitarian analysis | Conflict damage compounds WASH and disease risks. | humanitarian/WASH | analysis | high |
| Iran officials | state | Conservation, rationing, local management, emergency supply. | governance/response | actor statement | medium |
| OSINT/satellite reporters | investigative media | Damage to bases/radars/comms visible in satellite imagery. | conflict infrastructure | evidence/verification | medium |

This is the core "quién dice qué" object.

### 4. Frame Comparison

Atlas should compare frames instead of collapsing them into one summary:

| Frame | Claim | Supporting sources | Tension |
|---|---|---|---|
| Climate stress | hotter/drier conditions worsen scarcity | UNICEF, WRI, Al Jazeera | long-term driver, not full explanation |
| Mismanagement | dams, wells, agriculture, leakage, poor planning | Al Jazeera, WRI, Guardian | can be politicized |
| Conflict/WASH | strikes/electricity damage worsen water and disease risk | ACAPS, UNICEF, Guardian/WRI | needs event-level evidence |
| Protest/stability | water shortages feed unrest and political pressure | Guardian, WRI, local reporting | causality can be overclaimed |
| Military infrastructure | US/allied bases and communications become targets | AP, WaPo/OSINT, regional media | public imagery may be incomplete/restricted |
| Regional spillover | energy, food, shipping, desalination, Gulf security | ACAPS, WRI | broad but important |

### 5. Coverage Gaps

Atlas must say what it cannot answer:

- "Atlas found climate/water taxonomy matches but no direct signal evidence for
  `Iran water shortage` in the selected 7-day window."
- "Atlas has Iran conflict and flood/disaster threads, but the theme-detail
  route returns zero for the country-scoped detail; list/detail reconciliation is
  required."
- "Atlas has no source lane for UN/NGO PDF analysis unless those sources are
  ingested or externally enriched."
- "Satellite imagery evidence may appear through media reports, not raw imagery;
  the system should label it as reported OSINT/media evidence."

Coverage gaps are not failures. They are part of the product if presented
honestly with next actions.

## Required Data/Model Capabilities

### A. Query Intent Parser

Input:

- raw query;
- optional selected country/person/source/theme;
- user-added subquestion;
- current Workbench context.

Output:

- `main_intent`;
- `geo_scope`;
- `time_scope`;
- `topic_axes`;
- `entity_axes`;
- `infrastructure_axes`;
- `subquestions`;
- `expanded_terms`;
- `must_include`;
- `nice_to_have`;
- `excluded_noise`.

Implementation v1 can be deterministic + small LLM-free rules:

- country/entity extraction from existing search;
- phrase expansion dictionaries for climate/water/conflict/infrastructure;
- concept map used internally only, not as visible taxonomy;
- query variants per subquestion;
- explicit compound operators:
  - `AND`: climate + Iran;
  - `RELATED`: climate thread related to bases/satellite;
  - `EXPAND`: include water/drought/heat/WASH;
  - `COMPARE`: frames/sources.

### B. Evidence Retrieval Plan

The builder must run several retrieval lanes:

| Lane | Purpose | Sources |
|---|---|---|
| direct lexical | exact headline/theme/person/source match | `signals_v2` |
| semantic expansion | query terms to sibling concepts | internal expansion dictionary, future embeddings |
| existing threads | country/time thread candidates | `/api/v2/threads` / `dynamic_topics` |
| theme/detail | static and dynamic detail packets | `/api/v2/theme/*`, `/api/v2/threads/*` |
| signal stream | recent notable evidence | `/api/v2/signals` with intent-aware filters |
| public attention | wiki/search attention | existing public attention endpoints |
| external context | web/manual enrich, only if enabled | explicit external source adapter |
| historical processed | broader background windows | processed historical tables |

The output must label each evidence item by `retrieval_lane`, so the UI can show
whether it is direct evidence, context, weak support, or external enrichment.

### C. Evidence Role Classifier

Every evidence item needs a role:

- `primary_event`;
- `direct_evidence`;
- `background_context`;
- `actor_statement`;
- `analysis`;
- `reaction`;
- `public_attention`;
- `osint_verification`;
- `weak_support`;
- `contradiction`;
- `noise`.

This should reuse the existing evidence-role validation direction. The research
thread builder should not treat all retrieved rows as equal.

### D. Frame Extractor

Frame extraction should start rule-based, then graduate to model-assisted only
after a benchmark exists.

Initial frame families:

- `climate_stress`;
- `water_security`;
- `mismanagement_governance`;
- `food_agriculture`;
- `energy_infrastructure`;
- `conflict_damage`;
- `humanitarian_wash`;
- `public_health`;
- `protest_stability`;
- `sanctions_economy`;
- `military_bases`;
- `satellite_osint`;
- `regional_spillover`.

Each evidence item can carry multiple frames with scores.

### E. Research Graph Builder

Objects:

- `research_thread`;
- `research_node`;
- `subquestion`;
- `evidence_item`;
- `actor`;
- `source`;
- `frame`;
- `place`;
- `relation`;
- `coverage_gap`.

Relation types:

- `supports`;
- `context_for`;
- `contradicts`;
- `same_actor_as`;
- `same_place_as`;
- `same_source_lane_as`;
- `frame_contrast_with`;
- `causal_claim`;
- `temporal_precedes`;
- `regional_spillover`;
- `infrastructure_dependency`;
- `reported_by_satellite_imagery`;

### F. List/Detail Reconciliation

Before presenting a node as answerable, the builder must reconcile:

1. Thread list count.
2. Detail endpoint count.
3. Signal sample count.
4. Country/time filters.
5. Retrieval lane count.

If these disagree, the node should show a gap:

```json
{
  "gap_type": "list_detail_mismatch",
  "thread_id": "flood-landslide-disaster--ir",
  "list_count": 133,
  "detail_count": 0,
  "recommended_action": "route country-scoped thread detail through thread packet or explain unavailable detail"
}
```

No user-facing surface should silently show `133` in one place and `0` in
another.

## Backend Contract Proposal

### `POST /api/v2/research/thread`

Request:

```json
{
  "query": "clima en Iran y ataques a bases estadounidenses satelitales en Medio Oriente",
  "hours": 168,
  "geo_scope": ["IR", "ME"],
  "mode": "build",
  "context": {
    "selected_country": "IR",
    "workspace_items": []
  }
}
```

Response:

```json
{
  "research_id": "research-thread-...",
  "query": "...",
  "interpreted_intent": {},
  "tree": [],
  "who_says_what": [],
  "frames": [],
  "coverage_gaps": [],
  "evidence": [],
  "next_questions": [],
  "quality_envelope": {
    "band": "thin|medium|high|degraded",
    "answerable_questions": ["where", "sources", "evidence"],
    "missing_questions": ["why_moving"]
  }
}
```

V1 can be stateless/read-only. Persistence is optional later.

### `POST /api/v2/research/thread/expand`

Adds a branch:

```json
{
  "research_id": "...",
  "branch_query": "relacion con ataques a bases estadounidenses y comunicaciones satelitales",
  "relation": "related_to"
}
```

V1 can simply rebuild the dossier with the new subquestion appended.

### `GET /api/v2/research/thread/{id}/export`

Future: export dossier to Markdown/JSON.

## Frontend / Workbench UX

### Search Entry

Current SearchBar should keep quick direct search, but add a clear action:

- `Build research thread`
- `Add to Workbench`

For broad queries, the primary action should become research-thread builder, not
theme detail.

### Workbench Mode

Workbench becomes the investigation editor:

- left: research tree;
- center: evidence/storyline;
- right: who-says-what + frames + gaps;
- bottom or side rail: next questions / add branch.

User can add:

- another query;
- another country;
- another actor/source;
- another relation.

Example:

1. User starts: `clima Iran Medio Oriente`.
2. Atlas builds water/climate tree.
3. User adds: `ataques a bases estadounidenses y satelite`.
4. Atlas adds a sibling branch connected through:
   - conflict infrastructure;
   - satellite imagery;
   - regional bases;
   - energy/water security;
   - Middle East spillover.

### Dossier View

The final view should read like a structured report:

1. Executive summary.
2. Timeline.
3. Narrative tree.
4. Who says what.
5. Frame comparison.
6. Evidence table.
7. Gaps/uncertainty.
8. Related questions.

## Phased Implementation

### Phase 0 — Spec + fixture from Iran case

Deliverables:

- this spec;
- a manually curated expected-output fixture for the Iran compound case;
- current Atlas failure snapshot.

No product code.

### Phase 1 — Read-only Research Builder API

Deliver:

- deterministic intent parser;
- expansion dictionary for climate/water/conflict/infrastructure;
- multi-lane retrieval;
- research tree JSON;
- who-says-what matrix from source/actor/entity extraction;
- coverage gaps including list/detail mismatch.

No persistence. No LLM dependency required.

Acceptance:

- Query `Iran climate water drought` no longer returns empty if related Atlas
  threads/evidence exist.
- Query can add the US bases/satellite branch.
- Output labels evidence as direct/context/weak/external.
- Output marks gaps instead of hiding them.

### Phase 2 — Workbench UI

Deliver:

- Workbench accepts a natural research query.
- Renders tree, evidence, frames, sources, actors, gaps.
- Allows `Add branch`.
- Exports Markdown dossier.

Acceptance:

- User can reproduce the Iran climate + satellite/bases compound investigation
  without leaving Atlas.

### Phase 3 — Evidence/Frame Quality

Deliver:

- benchmark labels for research-thread evidence roles;
- frame extraction validation;
- source/actor normalization;
- duplication/syndication detection;
- confidence bands.

Acceptance:

- At least 85% precision on direct evidence vs context/noise for a small
  reviewed sample.
- Frame labels useful enough for human review, not necessarily fully automatic
  truth.

### Phase 4 — Optional External Context Adapter

Deliver:

- explicit "web context" lane for sources Atlas does not ingest;
- citation list;
- source reliability labels;
- separation from Atlas-ingested evidence.

Acceptance:

- Atlas can say: "Atlas evidence is thin; external context from UNICEF/WRI/ACAPS
  fills background, but current Atlas hot window lacks direct evidence."

## Open Technical Problems

1. Query expansion must avoid over-recall. `climate` should not pull every
   environment article unless tied to Iran/water/heat/drought/infrastructure.
2. Cross-language evidence must work. Persian/Arabic/Hebrew/Russian/Spanish
   headlines need translation or multilingual matching.
3. Actor extraction is currently noisy. Who-says-what needs normalized actor
   identities, not raw repeated strings.
4. Source framing needs source-family and article-type awareness.
5. Historical processed tables may lack enough evidence detail for older
   windows; research builder may need small evidence samples or archive bridge.
6. Dynamic-topic list/detail paths must be reconciled before Workbench relies on
   counts.
7. Satellite/OSINT claims should be labeled carefully as reported analysis,
   imagery-derived evidence, or actor claim.

## Product Success Criteria

This feature is successful when:

- a broad natural query produces a useful research tree, not zero results;
- a user can add a related branch without restarting;
- Atlas shows who says what and how frames differ;
- Atlas clearly separates evidence, context, weak support, and gaps;
- list counts and detail panels do not contradict each other;
- the output can become a report/dossier in Workbench;
- the user can understand the story's evolution and related routes from one
  place.

## Immediate Next Step

Create a concrete fixture for the Iran case:

```text
Query A: climate/water in Iran and Middle East
Query B: relation to attacks on US bases/satellite/communications infrastructure
Time: recent + 7d Atlas hot window + historical context
Expected nodes: water scarcity, heat/drought, Tehran reservoirs, agriculture,
governance/protest, WASH/conflict damage, regional spillover, US bases/satellite
infrastructure.
```

Then implement Phase 1 as a read-only API and compare Atlas output to the
fixture before touching public UI.
