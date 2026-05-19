# Topic Intelligence and Source Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Atlas explain what is happening with deeper, human-readable narrative topics while making each source layer visible and methodologically separate.

**Architecture:** Keep GDELT themes as one input, not the final topic model. Add an Atlas-owned topic intelligence layer that combines lexicon rules, multilingual embeddings, and zero-shot/topic classification to produce specific `atlas_topics` and `topic_clusters` across GDELT, RSS, APIs, Reddit, Trends, and Wikipedia. Then expose source mix, voice mix, public-attention links, and topic explanations in the product.

**Tech Stack:** FastAPI, asyncpg, Supabase PostgreSQL migrations, Python NLP/enrichment workers, Hugging Face multilingual models, pgvector or stored embedding vectors if enabled later, React/Vite frontend, GitHub issues for delivery tracking.

---

## 0. Validation Against Existing Issues

Validated open issues on 2026-05-19 before proposing new work:

| Area | Existing issue | Status | Decision |
|---|---:|---|---|
| Production source audit | #154 | Open | Keep; this is still the Phase 0 gate. |
| Signal class / semantic provenance | #155 | Open | Keep; add topic-intelligence dependency notes. |
| NewsAPI budget and dynamic queries | #156 | Open | Keep; already covers provider refactor. |
| Multilingual NLP benchmark | #157 | Open | Keep; topic model evaluation should reuse its benchmark harness where possible. |
| NewsData country-primary buckets | #158 | Open | Keep; already covers geography refactor. |
| Voice Mix endpoint/UI | #160 | Open | Keep; expand from CountryBrief into narrative cards later. |
| Multilingual sentiment/NER/framing | #162 | Open | Mostly implemented operationally, but leave open until acceptance criteria/report are done. |
| NLP worker / priority queue | #163 | Open | Keep; topic classification should run in this worker family, not inline ingestion. |
| Stratified sampling / backlog strategy | #164 | Open | Keep; topic backfill should follow the same 15-day/prioritized strategy. |
| Atlas composite heat | #165 | Open | Keep; should consume `signal_class`, topic clusters, and source diversity. |
| Analyst correction loop | #166 | Open | Keep; extend later to topic corrections. |
| Narrative thread UX explanation | #146 | Open | Keep; update copy after new topic model exists. |
| Visual use-case manual | #140/#134 | Open | Keep; screenshots should show Source Mix, Voice Mix, and topic explanations once built. |
| Workspace signal dossier | #133 | Closed | Reopen or recreate only if export is not implemented in current product. |

Gaps found:

1. No open issue specifically covers **Atlas-owned topic intelligence** beyond GDELT themes.
2. No open issue specifically covers **public attention threads** as first-class narrative objects.
3. No open issue specifically covers **Source Mix in narrative cards/workspace**, though #160 covers CountryBrief Voice Mix.

## 1. Product Principle

Atlas should not only say `ECON_CRISIS`, `PROTEST`, or `ARMEDCONFLICT`. Those are database categories, not user-facing intelligence.

Atlas should produce richer topic descriptions such as:

- "fuel subsidy protests tied to transport strikes"
- "copper royalty dispute and mining investment risk"
- "gang control disrupting humanitarian corridors"
- "election legitimacy dispute after court intervention"
- "grid instability after heat wave and energy rationing"

GDELT themes remain useful as structured priors. They are not deep enough to be the user's final mental model.

## 2. Target Data Model

Add an Atlas-owned layer without breaking existing `themes` consumers:

```sql
CREATE TABLE atlas_topics (
  id BIGSERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  description TEXT,
  parent_domain TEXT NOT NULL,
  lexicon_terms TEXT[] DEFAULT '{}',
  gdelt_theme_hints TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE signal_topic_assignments (
  signal_id BIGINT NOT NULL REFERENCES signals_v2(id) ON DELETE CASCADE,
  topic_id BIGINT NOT NULL REFERENCES atlas_topics(id),
  method TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  evidence JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (signal_id, topic_id, method)
);

CREATE INDEX idx_signal_topic_assignments_topic ON signal_topic_assignments(topic_id);
CREATE INDEX idx_signal_topic_assignments_confidence ON signal_topic_assignments(confidence DESC);
```

Optional later table for dynamic clusters:

```sql
CREATE TABLE topic_clusters (
  id BIGSERIAL PRIMARY KEY,
  label TEXT NOT NULL,
  summary TEXT,
  country_codes TEXT[] DEFAULT '{}',
  topic_ids BIGINT[] DEFAULT '{}',
  source_mix JSONB DEFAULT '{}'::jsonb,
  attention_mix JSONB DEFAULT '{}'::jsonb,
  first_seen_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 3. Model Strategy: "RoBERTa for Topics"

The desired equivalent of RoBERTa sentiment is a multilingual topic classifier. The recommended implementation is hybrid:

1. **Lexicon pass** for high precision and explainability.
2. **Embedding retrieval** to find semantically similar topics even when wording differs.
3. **Zero-shot multilingual classifier** for final disambiguation when lexicon/embedding conflict.
4. **Cluster naming** to create human-readable narrative labels from representative headlines.

Candidate model families to benchmark:

| Role | Candidate | Reason |
|---|---|---|
| Multilingual embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Small, multilingual, common baseline. |
| Multilingual embeddings | `intfloat/multilingual-e5-small` | Strong retrieval behavior with compact size. |
| Zero-shot topic classification | `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` | Already operationally aligned with current lighter framing model family. |
| Higher quality fallback | `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | Better quality, but likely too slow/heavy on current Fly worker. |

Do not start with a huge model in production. Benchmark first, then promote.

## 4. Execution Sequence

### Task 1: Extend #154 Audit With Topic Readiness

**Files:**
- Modify: `docs/research/` audit report created by #154
- Query only: Supabase `signals_v2`, `trends_v2`, `wiki_pageviews_v2`

- [ ] Add topic-readiness checks to #154:

```sql
SELECT source_family, attribution_method,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE themes IS NULL OR cardinality(themes)=0) AS empty_themes,
       COUNT(*) FILTER (WHERE headline IS NULL OR length(trim(headline)) < 12) AS weak_headline,
       COUNT(*) FILTER (WHERE nlp_processed_at IS NOT NULL) AS nlp_processed
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY 1,2
ORDER BY total DESC;
```

- [ ] Add sample extraction for topic benchmark:

```sql
SELECT id, timestamp, country_code, source_family, source_lang, headline, themes
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '24 hours'
  AND headline IS NOT NULL
  AND length(trim(headline)) >= 25
ORDER BY random()
LIMIT 300;
```

- [ ] Report which sources are topic-ready:
  - GDELT: has themes, needs better labels/subtopics.
  - RSS/ReliefWeb: good text, weak themes.
  - NewsData/MediaStack/NewsAPI: good candidate text, weak themes.
  - Reddit: useful for social topic emergence, not factual corroboration.
  - Trends/Wikipedia: attention topics, not article evidence.

### Task 2: Create Topic Intelligence Migration

**Files:**
- Create: `backend/migrations/019_atlas_topics.sql`
- Test: `backend/tests/test_topic_intelligence_schema.py`

- [ ] Create migration with `atlas_topics` and `signal_topic_assignments`.
- [ ] Seed a small v1 taxonomy with 25-40 Atlas topics. Include domains:
  - conflict/security
  - political legitimacy
  - economic stress
  - resources/energy
  - climate/disaster
  - migration/humanitarian
  - technology/infrastructure
  - public health
  - social unrest/labor
  - information environment
- [ ] Add tests that verify expected columns and required indexes exist.

### Task 3: Build Topic Lexicon Pass

**Files:**
- Create: `backend/enrichment/topic_intelligence.py`
- Create: `backend/tests/test_topic_intelligence.py`

- [ ] Implement `TopicCandidate` dataclass:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TopicCandidate:
    slug: str
    label: str
    confidence: float
    method: str
    evidence: dict
```

- [ ] Implement `classify_with_lexicon(headline, themes, source_lang)`:
  - Match explicit lexicon terms.
  - Use GDELT themes only as hints.
  - Return zero or more candidates with confidence between `0.55` and `0.9`.
- [ ] Test that broad GDELT themes become more specific when headline supports it:
  - `ECON_CRISIS` + "fuel subsidy protests..." -> `fuel-subsidy-unrest`.
  - `ECON_TRADE` + "copper royalty dispute..." -> `mining-royalty-risk`.
  - `ARMEDCONFLICT` + "humanitarian corridor..." -> `humanitarian-access-conflict`.

### Task 4: Benchmark Embedding and Zero-Shot Topic Models

**Files:**
- Create: `backend/scripts/benchmark_topic_models.py`
- Create: `docs/research/topic-model-benchmark-2026-05-19.md`

- [ ] Benchmark at least two compact multilingual embedding models and one zero-shot classifier.
- [ ] Use the 300-row sample from Task 1.
- [ ] Measure:
  - runtime per row,
  - memory peak,
  - language coverage,
  - agreement with manual labels for a 50-row sample,
  - quality of generated topic labels.
- [ ] Recommended promotion gate:
  - median runtime under 300ms per row for embedding retrieval, or batch mode equivalent;
  - zero-shot used only for ambiguous candidates;
  - no production worker memory above current Fly limits.

### Task 5: Add Topic Assignment Worker Phase

**Files:**
- Modify: `backend/enrichment/nlp_pipeline.py`
- Modify: `backend/app/services/nlp_worker.py` if present, otherwise worker entrypoint used by Fly
- Modify: `backend/app/services/ingest_loop.py` only for refresh/metrics, not inline classification
- Test: `backend/tests/test_topic_worker_selection.py`

- [ ] Add env flags:

```bash
TOPIC_INTELLIGENCE_ENABLED=false
TOPIC_INTELLIGENCE_MODE=shadow
TOPIC_WORKER_LIMIT=50
```

- [ ] Selection priority:
  1. recent non-GDELT rows with empty `themes`;
  2. recent Reddit/social commentary;
  3. recent GDELT rows with broad themes requiring subtopic labels;
  4. older rows from the 15-day stratified backlog.
- [ ] In `shadow`, write to `signal_topic_assignments` without changing narrative ranking.
- [ ] In `on`, allow narrative endpoints to use assignments above a confidence threshold.

### Task 6: Expose Topics Through API

**Files:**
- Create: `backend/app/routers/topic_intelligence.py`
- Modify: `backend/app/main_v2.py`
- Test: `backend/tests/test_topic_intelligence_api.py`

- [ ] Add endpoint:

```http
GET /api/v2/topics/assignments?country=CO&hours=24&source_family=social
```

- [ ] Add endpoint:

```http
GET /api/v2/topics/clusters?hours=24&country=OPTIONAL
```

- [ ] Response must include:
  - topic label,
  - confidence,
  - method,
  - supporting signal count,
  - source mix,
  - attention mix if linked,
  - example headlines.

### Task 7: Narrative Threads Use Atlas Topics

**Files:**
- Modify: `backend/app/routers/narratives.py`
- Test: `backend/tests/test_narratives_topic_assignments.py`

- [ ] Keep existing GDELT theme path as fallback.
- [ ] Add topic assignment path when `TOPIC_INTELLIGENCE_MODE=on`.
- [ ] Narrative ranking inputs:
  - Atlas topic assignment count,
  - country spread,
  - velocity vs baseline,
  - source diversity,
  - signal class mix,
  - public-attention linkage.
- [ ] Do not let Reddit/social commentary create factual narratives alone. It can create `social-led` candidate threads that require visual distinction.

### Task 8: Public Attention Threads

**Files:**
- Create: `backend/app/routers/attention_threads.py`
- Modify: `backend/app/main_v2.py`
- Test: `backend/tests/test_attention_threads.py`

- [ ] Build first-class attention threads from:
  - Google Trends keywords,
  - Wikipedia article titles,
  - country/language context.
- [ ] Link attention threads to media topics through embeddings or normalized phrase matching.
- [ ] Label each relationship:
  - `media-led`
  - `public-led`
  - `social-led`
  - `uncoupled-attention`
  - `silent-risk`
- [ ] Frontend can still start with badges, but backend should return the relationship type.

### Task 9: Source Mix and Voice Mix UI

**Files:**
- Modify: `frontend-v2/src/lib/sourceFamily.ts`
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`
- Modify: `frontend-v2/src/components/CountryBrief.tsx`
- Modify: `frontend-v2/src/components/InvestigationWorkspace.tsx` if Workspace evidence cards need source classes
- Test: frontend build with `npm run build`

- [ ] Extend source-family mapping to include:
  - `gdelt`
  - `api`
  - `social`
  - `ngo`
  - `wire`
  - `state`
  - `independent`
- [ ] Narrative cards show compact source mix:
  - media reporting,
  - humanitarian,
  - social commentary,
  - public attention,
  - state/wire/API if present.
- [ ] CountryBrief reuses #160 Voice Mix endpoint.
- [ ] Tooltips must avoid native `title=` and use `data-tip`.

### Task 10: Analyst Corrections Include Topics

**Files:**
- Modify: migration/table from #166 or create a follow-up migration if #166 already shipped
- Modify: `backend/app/routers/nlp.py` or correction router
- Modify: relevant UI correction component

- [ ] Extend correction model to include:
  - original topic assignments,
  - corrected topic labels,
  - false-positive / false-negative markers,
  - analyst notes.
- [ ] Monthly export includes topic corrections as JSONL.
- [ ] Use correction rate by language/source to tune topic thresholds.

### Task 11: Documentation and Visual Manual

**Files:**
- Modify: `docs/methodology/atlas-data-operating-model-2026-05-19.md`
- Modify: `docs/methodology/atlas-heat.md`
- Modify: `frontend-v2/src/pages/Docs.tsx`
- Later create: `docs/use-cases/*.md`

- [ ] Update methodology once topic intelligence reaches shadow mode.
- [ ] Use #140 screenshots to show:
  - Source Mix,
  - Voice Mix,
  - topic explanations,
  - attention relationship (`media-led`, `public-led`, etc.),
  - Workspace dossier evidence.

## 5. Recommended New or Updated Issues

Do not duplicate the issues listed in section 0. Recommended GitHub action:

1. Create one new issue for **Topic Intelligence**.
2. Create one new issue for **Public Attention Threads**.
3. Add comments to #155, #160, #165, #166, #146, and #140 linking this plan and explaining how they should consume the new topic/source model.

Suggested issue titles:

- `feat(data): add Atlas topic intelligence beyond raw GDELT themes`
- `feat(narratives): create public attention threads and semantic links to media topics`

Optional only if #160 scope is kept country-only:

- `feat(ui): show source mix and topic evidence in narrative cards and workspace`

## 6. Execution Order

Recommended order:

1. Finish #154 audit with topic-readiness section.
2. Implement #155 `signal_class`.
3. Create Topic Intelligence migration and lexicon pass.
4. Benchmark compact multilingual topic models.
5. Run topic intelligence in `shadow`.
6. Expose topic assignments via API.
7. Add Source Mix and Voice Mix to UI.
8. Add attention threads and semantic linking.
9. Promote topic intelligence into narrative ranking.
10. Extend analyst corrections to topics.
11. Update docs/use-case manual with real screenshots.

## 7. Non-Goals

- Do not replace GDELT themes immediately.
- Do not use an expensive/heavy model in the ingest loop.
- Do not let Reddit count as factual corroboration.
- Do not hide raw volume; contextualize it.
- Do not make topic labels purely LLM-generated without confidence/evidence metadata.

