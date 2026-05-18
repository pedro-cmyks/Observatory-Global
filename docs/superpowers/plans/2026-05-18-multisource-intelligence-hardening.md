# Multi-source Intelligence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the new NewsData, MediaStack, NewsAPI, and Reddit ingestion useful in Atlas without corrupting sentiment, scoring, country attribution, or user-facing interpretation.

**Architecture:** Treat new sources as differentiated signal layers, not just more rows in `signals_v2`. First audit real production rows, then add source semantics with `signal_class`, then improve provider budgets and NLP quality before exposing source voice through API/UI. Clustering is deliberately later because it depends on language quality, dedupe, class semantics, and geographic confidence.

**Tech Stack:** FastAPI, asyncpg, Supabase PostgreSQL raw migrations, Python ingestion services, Hugging Face/spaCy NLP, React/Vite frontend.

---

## Validation Summary

The previous agent's direction is mostly correct, but several claims need refinement against the code:

- **NewsAPI quota math:** current code runs 8 queries every 2 hours (`gdelt_cycle % 8 == 4`), which is 96 requests/day. There is no 36-request reserve today. A reserve requires changing cadence or query budget.
- **NewsData geography:** current code already passes country filters per language batch, but each batch still mixes many countries and sets a flat `geo_confidence=0.7`. Country-primary buckets remain a valid improvement.
- **Reddit separation:** Reddit already uses `source_family="social"` and `attribution_method="reddit_public"`. `signal_class="social_commentary"` is still useful, but not the only existing separator.
- **NLP is the blocker:** `backend/enrichment/nlp_pipeline.py` uses `cardiffnlp/twitter-roberta-base-sentiment-latest`, `spacy en_core_web_sm`, and `cross-encoder/nli-distilroberta-base`. This is effectively English-first. `_entity_valid()` also rejects many non-ASCII entity strings, which will harm Arabic, Amharic, Thai, Hindi, Bengali, etc.
- **NLP capacity is undersized:** `ingest_loop.py` calls `_nlp_background(limit=100)` every 15 minutes, maxing out around 9,600 rows/day per phase if every cycle completes. New total volume is projected near 100K rows/day, so backlog can grow silently.
- **New API/social sources enter with `themes=[]`:** without theme classification or clustering, many product surfaces based on themes will underuse the new data.
- **`signal_class` should not wait for NLP:** provenance already tells us enough to distinguish reporting, humanitarian, state media, wire/API, and social commentary. This is required before Voice Mix and source-weighted scoring.
- **Atlas should not "cut" volume:** the product goal is not to suppress high-volume countries or sources. The goal is to show proportionality: baseline deviation, voice mix, local/international balance, source diversity, and confidence. Large countries can still be loud; Atlas should reveal when loudness is structural volume versus unusual narrative movement.

## GDELT Surface Area

Current code uses these GDELT paths:

- `backend/app/services/ingest_v2.py` uses GDELT GKG English via `lastupdate.txt`.
- `backend/app/services/ingest_v2.py` also uses GDELT Translingual GKG via `lastupdate-translation.txt`.
- `backend/app/services/ingest_events.py` uses GDELT Events `export.CSV.zip`.

Potential GDELT additions:

- **GDELT Event Mentions (`mentions.CSV.zip`)**: use for event propagation and repetition analysis. This should be audited before ingestion because it may be high-volume and should probably land in an event-mentions table, not `signals_v2`.
- **GDELT DOC 2.0 API**: use as query-time enrichment, not as another firehose. Best use cases: "find more evidence for this investigation", dossier/Reading Mode enrichment, multilingual article search around a selected country/theme, and contrast checks when Atlas detects a low-volume but high-deviation narrative.

Do not add either as raw volume until Phase 0 tells us where the current pipeline is losing signal.

## Statistical/Product Stance

Atlas should show the information environment without pretending all signals are equivalent.

Recommended measurements:

- **Raw volume:** still visible, but never alone.
- **Baseline deviation:** compare a country's current signal volume/theme activity against its own historical baseline.
- **Share of voice:** percentage by country, source family, source language, and signal class.
- **Voice Mix:** local-language, international press, state media, humanitarian, social commentary, public attention.
- **Source diversity:** number of distinct outlets and source families.
- **Geo confidence:** distinguish strong country attribution from weak inference.
- **Narrative lift:** detect countries/themes that are small in absolute volume but unusually active for their own baseline.

Avoid:

- suppressing large countries by fiat;
- hiding inconvenient volume;
- editorial labels that say a narrative is "important" without evidence;
- allowing raw US/English volume to dominate every score.

## File Map

Likely files:

- Modify: `backend/enrichment/nlp_pipeline.py` — multilingual model audit/swap, source-aware prioritization, lag metrics.
- Modify: `backend/app/services/ingest_loop.py` — NLP batch limits/cadence/backlog logging.
- Create: `backend/migrations/013_signal_class.sql` — `signal_class` and supporting indexes.
- Modify: `backend/app/services/ingest_newsdata.py` — country-primary request buckets and better `geo_confidence`.
- Modify: `backend/app/services/ingest_newsapi.py` — quota budget, evergreen/dynamic/query-reserve split.
- Modify: `backend/app/services/ingest_reddit.py` — write `signal_class="social_commentary"` after migration.
- Modify: `backend/app/services/ingest_mediastack.py` — write `signal_class="reporting"` after migration.
- Modify: `backend/app/services/ingest_v2.py`, `ingest_rss.py`, `ingest_reliefweb.py` — write `signal_class` defaults.
- Create: `backend/app/routers/voice_mix.py` or add to existing country router — endpoint for country/topic voice mix.
- Modify: `backend/app/main_v2.py` or router registration module — register voice mix router if needed.
- Modify: `frontend-v2/src/components/CountryBrief.tsx` — render Voice Mix.
- Modify: `frontend-v2/src/components/SourceIntegrityPanel.tsx` or related scoring panel — use weighted source semantics.
- Add tests under `backend/tests/` for NLP selection, provider budgets, signal class insertions, and voice mix endpoint.

## Phase 0 — Production Reality Check

Purpose: avoid optimizing against assumptions.

- [ ] Inspect Fly logs for the new ingestion sources.
  - Run: `fly logs -a atlas-api-pedro --since 6h | rg "NewsData|MediaStack|NewsAPI|Reddit|NLP"`
  - Expected: each source logs fetched/inserted counts; NLP logs start/complete or skip.
- [ ] Query source volume by family and attribution.
  - SQL:
    ```sql
    SELECT source_family, attribution_method, source_lang, COUNT(*) AS n
    FROM signals_v2
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY 1,2,3
    ORDER BY n DESC;
    ```
- [ ] Query NLP backlog by source.
  - SQL:
    ```sql
    SELECT source_family, attribution_method, source_lang,
           COUNT(*) FILTER (WHERE nlp_processed_at IS NULL) AS unprocessed,
           COUNT(*) AS total
    FROM signals_v2
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY 1,2,3
    ORDER BY unprocessed DESC;
    ```
- [ ] Decide if NLP should process all GDELT rows or prioritize non-GDELT rows first.
  - Recommended: prioritize non-GDELT rows because GDELT already has native tone while API/RSS/social rows have `sentiment=0.0`.
- [ ] Measure dominance and baseline deviation.
  - SQL sketch:
    ```sql
    WITH current AS (
      SELECT country_code, COUNT(*) AS n
      FROM signals_v2
      WHERE timestamp > NOW() - INTERVAL '24 hours'
      GROUP BY 1
    ),
    baseline AS (
      SELECT country_code, AVG(daily_n) AS avg_daily_n, STDDEV_POP(daily_n) AS sd_daily_n
      FROM (
        SELECT country_code, date_trunc('day', timestamp) AS day, COUNT(*) AS daily_n
        FROM signals_v2
        WHERE timestamp BETWEEN NOW() - INTERVAL '15 days' AND NOW() - INTERVAL '1 day'
        GROUP BY 1,2
      ) d
      GROUP BY 1
    )
    SELECT c.country_code, c.n, b.avg_daily_n, b.sd_daily_n,
           CASE WHEN b.sd_daily_n > 0 THEN (c.n - b.avg_daily_n) / b.sd_daily_n ELSE NULL END AS z_score
    FROM current c
    LEFT JOIN baseline b USING (country_code)
    ORDER BY z_score DESC NULLS LAST
    LIMIT 30;
    ```
  - Expected: identify countries that are unusually active relative to themselves, not only countries with the largest media volume.
- [ ] Audit unused GDELT surfaces before implementation.
  - Confirm latest `mentions.CSV.zip` availability and columns.
  - Estimate rows per 15-min cycle and storage impact.
  - Test one DOC 2.0 query for a selected Atlas theme/country and record result quality.

## Phase 1 — Signal Semantics

Goal: prevent social commentary and duplicate syndication from contaminating scoring, even before NLP is fully multilingual.

- [ ] Create migration `013_signal_class.sql`.
  - Recommended classes:
    - `reporting`
    - `wire`
    - `state_media`
    - `humanitarian`
    - `social_commentary`
    - `public_attention`
    - `unknown`
  - DDL:
    ```sql
    ALTER TABLE signals_v2
      ADD COLUMN IF NOT EXISTS signal_class VARCHAR(30) DEFAULT 'reporting';

    CREATE INDEX IF NOT EXISTS idx_signals_signal_class_time
      ON signals_v2 (signal_class, timestamp DESC);

    CREATE INDEX IF NOT EXISTS idx_signals_class_country_time
      ON signals_v2 (signal_class, country_code, timestamp DESC);
    ```
- [ ] Backfill classes:
  - `source_family='social'` or `attribution_method='reddit_public'` -> `social_commentary`.
  - `source_family='ngo'` or `attribution_method='reliefweb_ocha'` -> `humanitarian`.
  - `is_state_media=true` -> `state_media`.
  - `source_family='wire'` -> `wire`.
  - `source_family in ('gdelt','rss','api','independent')` -> `reporting` unless a stricter rule applies.
- [ ] Update all ingestion services to write `signal_class`.
- [ ] Expose provenance fields in `/api/v2/signals` if missing:
  - `source_family`
  - `source_lang`
  - `attribution_method`
  - `geo_confidence`
  - `signal_class`
- [ ] Exit criteria:
  - 100% of new rows have non-null `signal_class`.
  - Reddit is never counted as independent news corroboration.
  - Backend tests prove class assignment for GDELT/RSS/ReliefWeb/API/Reddit.

## Phase 2 — NLP Multilingual and Backlog Gate

Goal: make enrichment trustworthy before building UI on top of it.

- [ ] Add tests proving current pipeline prioritizes rows by source and language.
  - Test file: `backend/tests/test_nlp_pipeline_selection.py`
  - Required cases:
    - non-GDELT rows with `sentiment=0.0` are selected before recent GDELT rows;
    - social/API rows can be selected by language;
    - rows with non-ASCII headlines are not rejected wholesale.
- [ ] Build an offline benchmark before changing production models.
  - Use 20-30 headlines per language: `en`, `es`, `pt`, `fr`, `ar`, `hi`, `bn`, `sw`.
  - Measure sentiment plausibility, NER quality, framing quality, runtime, and memory.
- [ ] Replace or route sentiment model for multilingual text only after benchmark results.
  - Candidate: `cardiffnlp/twitter-xlm-roberta-base-sentiment` or another compact multilingual sentiment model that fits Fly memory.
  - Keep memory rule: one model loaded per phase; do not load all models simultaneously.
- [ ] Replace English-only NER for non-English text or degrade explicitly.
  - Minimum viable path: use `source_lang` to run `en_core_web_sm` only for English and mark other NER as skipped/low-confidence until a multilingual NER model is selected.
  - Better path: add a multilingual NER model after measuring Fly memory.
- [ ] Add NLP lag metric.
  - Endpoint option: extend `/health` with `nlp_unprocessed_24h`, `nlp_oldest_unprocessed_at`, `nlp_backlog_by_source`.
  - Exit criterion: the dashboard/health response makes backlog visible before user-facing features depend on it.

## Phase 3 — Provider Refactors

Goal: spend quotas where Atlas gets distinctive intelligence.

### NewsAPI

- [ ] Replace the current fixed 8-query loop with a quota budget object.
  - Current state: 8 queries x 12 runs/day = 96 req/day.
  - Recommended first budget:
    - 6 evergreen crisis queries every 3 hours = 48 req/day.
    - 2 dynamic GDELT spike queries every 3 hours = 16 req/day.
    - 36 req/day reserve for analyst-triggered "Investigate now".
- [ ] Store last request counts locally or in DB/cache so the loop cannot exceed daily quota.
- [ ] Dynamic queries should come from top spike countries/themes, not from global volume alone.

### NewsData

- [ ] Replace broad language batches with country-primary buckets.
  - Example: `CO,VE,EC,PE` + `language=es`; `BF,ML,NE,SN` + `language=fr`.
- [ ] Set `geo_confidence` based on whether the API returned country metadata:
  - API country present and bucket-specific: `0.85`.
  - inferred by text: `0.55-0.65`.
  - unknown: `0.2` and do not over-rank.

### Reddit

- [ ] Keep Reddit visible as social/commentary, not source corroboration.
- [ ] Add score/comment metadata only if useful and permitted by the API response.
- [ ] Do not count Reddit as independent news source in source integrity.

## Phase 4 — Voice Mix API and UI

Goal: make the new sources visible in the product.

- [ ] Add endpoint: `GET /api/v2/countries/{iso}/voice-mix?hours=24`.
  - Response:
    ```json
    {
      "country_code": "CO",
      "hours": 24,
      "total": 1234,
      "segments": [
        {"key": "local_language", "label": "Local-language", "count": 420, "share": 0.34},
        {"key": "international", "label": "International press", "count": 700, "share": 0.57},
        {"key": "social", "label": "Social commentary", "count": 114, "share": 0.09}
      ]
    }
    ```
- [ ] Add Voice Mix component to `CountryBrief`.
  - Show it as evidence of source diversity, not as a decorative chart.
  - Tooltip copy should explain that social commentary is early signal, not verified reporting.
- [ ] Add tests for endpoint and a frontend smoke test if feasible.

## Phase 5 — Source-weighted Scoring (#149)

Goal: score clusters, not raw rows.

- [ ] Define scoring inputs:
  - source family;
  - source language/locality;
  - geo confidence;
  - signal class;
  - cluster size;
  - source diversity within cluster.
- [ ] Social commentary should contribute to early-signal score, not corroboration score.
- [ ] GDELT high-volume duplicates should not dominate country risk just because of syndication.

## Phase 6 — Conservative Clustering

Goal: group duplicate coverage without creating false narrative authority.

- [ ] Add clustering only after:
  - `signal_class` is present;
  - NewsAPI and NewsData attribution rules are stable;
  - NLP multilingual behavior is benchmarked or explicitly degraded by language;
  - basic dedupe metrics are known.
- [ ] First version:
  - headline fingerprint + normalized URL/domain;
  - 24-48h time window;
  - separate or exclude `social_commentary`;
  - store `cluster_confidence`;
  - expose `representative_signal_id`.
- [ ] Exit criteria:
  - manual review of 50 clusters;
  - fewer than 15% mix distinct events;
  - low-confidence clusters degrade back to raw signal lists.

## Recommended Execution Order

1. Phase 0: production reality check.
2. Phase 1: `signal_class` migration, backfill, ingestion writes, API exposure.
3. Phase 3: provider refactors, starting with NewsAPI quota guard; run Phase 2 NLP benchmark in parallel.
4. Phase 4: Voice Mix endpoint/UI, because this creates visible product value with lower risk than clustering.
5. Phase 5: source-weighted scoring after source semantics exist.
6. Phase 6: conservative clustering only after semantics, provider attribution, and NLP quality are measured.

Do not start with UI-only work. Voice Mix can proceed before clustering, but not before `signal_class` and real production row audit.

## GitHub Issue Map

- **#154** — Phase 0 production source-quality audit, dominance analysis, and NLP backlog.
- **#155** — Migration 013 `signal_class`, backfill, ingestion writes, and API exposure.
- **#157** — Multilingual NLP benchmark and backlog capacity.
- **#156** — NewsAPI quota budget and dynamic crisis queries.
- **#158** — NewsData country-primary buckets and attribution confidence.
- **#160** — Voice Mix endpoint and CountryBrief component.
- **#159** — GDELT Event Mentions research for narrative propagation.
- **#161** — GDELT DOC 2.0 query-time evidence enrichment.
- **#149** — Source-weighted scoring normalization; depends on #154 and #155.
- **#150** — Non-anglophone source expansion; should follow #154 and align with #158.
