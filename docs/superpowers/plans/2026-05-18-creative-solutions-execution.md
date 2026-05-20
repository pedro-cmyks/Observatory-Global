# Atlas — Creative Solutions Execution Plan

**Date:** 2026-05-18
**Author:** Pedro + Claude (Opus 4.7) brainstorm session
**Status:** In progress — Phase 1 + Phase 2 starting now
**Depends on:** `2026-05-18-multisource-intelligence-hardening.md`, `ADR-0003-nlp-pipeline-architecture.md`
**Related issues:** #154, #155, #157, #149, #150 (existing), plus new issues created in this plan

---

## Why this plan exists

The master plan `2026-05-18-multisource-intelligence-hardening.md` is correct in direction but Phase 2 ("NLP multilingual and backlog gate") describes a benchmark/decision step, not an execution path. The team also lacks concrete plans for:

1. The actual model swap once the benchmark confirms the obvious (English-first model under-serves multilingual signal).
2. A processing architecture that can drain a ~1.8M-row backlog without strangling the API + ingestion process.
3. A scoring model that does not let raw US/English volume dominate Atlas heat.
4. A correction feedback loop so quality improves with analyst use.

This document fills those gaps. Each phase below maps to a concrete issue and a definition of done.

---

## Decision summary

- **Multilingual NLP**: replace English-only sentiment + NER + framing with multilingual equivalents, gated by `source_lang` and `NLP_MULTILINGUAL_MODE` env var so we can rollback fast.
- **Backlog drain**: separate process group on Fly (`nlp_worker`) reading a priority queue from PostgreSQL, with a `nlp_progress` checkpoint table and lag telemetry on `/health`.
- **Stratified sampling**: not all 1.8M rows get transformer-grade scoring. We process a canonical sample stratified by `(country, theme, day, source_family, signal_class)` and tag the rest with lexicon-grade sentiment.
- **Atlas composite score**: replaces raw-volume ranking with a transparent multi-factor heat that exposes diversity, surprise, local voice, polyphony, and geo confidence.
- **Active learning loop**: analyst corrections feed a `nlp_corrections` table that calibrates confidence thresholds and trains a monthly adapter.

---

## Phase 1 — Multilingual NLP swap

**Owner:** Claude (Opus) + data-geointel-analyst review
**Issue:** new, `data(nlp): swap to multilingual sentiment, NER, and framing models`
**Depends on:** none, but #157 benchmark should run in parallel for receipts

### Model choices

| Phase | Old (English-only) | New (multilingual) | Size | Notes |
|-------|-------------------|--------------------|------|-------|
| Sentiment | `cardiffnlp/twitter-roberta-base-sentiment-latest` | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | ~280MB | 8 languages native, drop-in `pipeline("sentiment-analysis", ...)` |
| NER | `spacy en_core_web_sm` | `spacy xx_ent_wiki_sm` (default) + `en_core_web_sm` (English route) | ~12MB each | `xx` is multilingual Wikipedia-trained, conservative |
| Framing | `cross-encoder/nli-distilroberta-base` | `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | ~280MB | Multilingual NLI, 100 langs, similar speed |

Total peak memory per phase still ≤ 500MB. We never load all three simultaneously, so 1GB Fly machine remains within budget.

### Routing logic

- `source_lang = 'en'` → English models when available, multilingual as fallback.
- `source_lang != 'en'` → multilingual models only.
- `source_lang IS NULL` → multilingual default; mark `nlp_confidence` with `-0.1` adjustment.

### Filter changes

Current `_entity_valid()` rejects strings where ≥40% of chars are non-ASCII. This kills Arabic, Hindi, Bengali, Thai, Amharic entirely. Replace with:

```python
def _entity_valid(text: str, source_lang: str | None = None) -> bool:
    t = text.strip()
    if len(t) < 2 or t.isdigit():
        return False
    if len(t.split()) > 5:
        return False
    # Non-ASCII is fine when the source language uses non-Latin script
    if source_lang in NON_LATIN_LANGS:
        return True
    non_ascii = sum(1 for c in t if ord(c) > 127)
    return (non_ascii / max(len(t), 1)) < 0.6  # was 0.4
```

`NON_LATIN_LANGS = {'ar', 'fa', 'he', 'hi', 'bn', 'th', 'ja', 'ko', 'zh', 'am', 'ti', 'ka', 'hy'}`

### Rollback contract

`NLP_MULTILINGUAL_MODE` env var: `off | shadow | on`.

- `off`: existing English-only path. Default until Dockerfile rebuilt.
- `shadow`: multilingual models load, scores written to shadow columns (`nlp_sentiment_xlm`, `nlp_framing_xlm`), production columns stay on English models. Used for benchmark.
- `on`: multilingual models write to `nlp_sentiment` directly. Production mode.

### Definition of done

- [ ] `nlp_pipeline.py` accepts `NLP_MULTILINGUAL_MODE` and routes correctly.
- [ ] Dockerfile pre-bakes multilingual models (replaces English-only ones in image, or adds them if shadow mode survives 7 days).
- [ ] Migration adds `nlp_sentiment_xlm`, `nlp_framing_xlm`, `nlp_persons_xlm` columns (shadow mode).
- [ ] Unit test proves non-ASCII headlines (Arabic, Hindi, Thai) survive `_entity_valid`.
- [ ] Unit test proves selection query prioritizes non-English unprocessed rows.
- [ ] Fly deploy in shadow mode confirmed via `/health` lag metric.

### Risks

- mDeBERTa-v3 framing accuracy may drop on borderline frames vs the distilroberta English baseline. Mitigation: keep English route on English signals for at least 14 days while we collect comparative metrics.
- Memory: if 3 models pre-baked, image size grows from ~1.4GB to ~2.0GB. Acceptable but slows deploy.

---

## Phase 2 — Separate NLP worker process

**Owner:** backend-flow-engineer
**Issue:** new, `infra(nlp): split NLP enrichment into separate Fly process group with priority queue and lag telemetry`
**Depends on:** Phase 1 not strictly required; can ship in parallel

### Why

Current pipeline runs inside the ingestion loop (`ingest_loop.py` → `asyncio.create_task(_nlp_background(limit=100))`). Three problems:

1. `limit=100` per 15-min cycle ≈ 9600 rows/day. Projected volume is 100K rows/day. Backlog grows silently.
2. Raising the limit blocks ingestion when NLP cycles run long (model warmup + zero-shot framing on 500 rows = ~30s+).
3. Memory pressure peaks coincide with ingestion HTTP fetches → risk of OOM kills.

A separate process group lets us scale NLP independently and (eventually) move it to a larger machine.

### Architecture

```
[Fly app: atlas-api-pedro]
├── process group `app` (1 machine, 1GB)
│   └── API + ingestion watchdog + ingestion loop (no NLP)
├── process group `nlp_worker` (1 machine, 2GB, auto_stop)
│   └── nlp_worker.py — drains priority queue, writes results, exits
└── Postgres (Supabase)
    ├── signals_v2 (existing)
    └── nlp_progress (new, checkpoint table)
```

### Priority queue (PostgreSQL-native, no Redis stream)

We do not need Redis for this. PostgreSQL plus a priority-ranked query is enough at our volume.

```sql
SELECT id, headline, source_lang, source_family, country_code, timestamp
FROM signals_v2
WHERE nlp_processed_at IS NULL
  AND headline IS NOT NULL
  AND LENGTH(headline) > 10
ORDER BY
  -- Priority components, smallest = highest priority
  (
    -- Recency (newer = higher priority, smaller value)
    EXTRACT(EPOCH FROM (NOW() - timestamp)) / 86400.0  -- days old
    -- Language under-representation boost: non-English gets -2 days
    + CASE WHEN source_lang IS NOT NULL AND source_lang != 'en' THEN -2 ELSE 0 END
    -- Source family novelty boost: API/social gets -1 day
    + CASE WHEN source_family IN ('api', 'social') THEN -1 ELSE 0 END
    -- Country signal scarcity boost: country with <50 rows/day baseline gets -1 day
    + CASE WHEN country_code IN (SELECT country_code FROM low_volume_countries) THEN -1 ELSE 0 END
    -- Geo confidence: high confidence rows get -0.5 days
    + CASE WHEN geo_confidence > 0.8 THEN -0.5 ELSE 0 END
  )
LIMIT $1;
```

`low_volume_countries` is a materialised view refreshed daily. Quick first version: hard-code list of countries with under 200 signals per rolling 7d.

### Checkpoint table

```sql
CREATE TABLE nlp_progress (
  worker_id TEXT PRIMARY KEY,
  last_signal_id BIGINT,
  rows_processed_total BIGINT DEFAULT 0,
  lag_minutes INT,
  oldest_unprocessed_at TIMESTAMPTZ,
  unprocessed_24h INT,
  unprocessed_total BIGINT,
  current_phase TEXT,                -- 'sentiment' | 'ner' | 'framing'
  last_run_at TIMESTAMPTZ DEFAULT NOW(),
  last_run_duration_seconds REAL
);
```

`/health` endpoint reads `nlp_progress` and includes:

```json
{
  "nlp": {
    "unprocessed_24h": 4321,
    "unprocessed_total": 1812345,
    "oldest_unprocessed_at": "2026-04-22T11:14:03Z",
    "lag_minutes": 18,
    "last_run_at": "2026-05-18T09:14:50Z",
    "last_run_duration_seconds": 41.2
  }
}
```

### Definition of done

- [ ] Migration `014_nlp_progress.sql` adds checkpoint table and indexes (`signal_class` index optional here if not in migration 013).
- [ ] New file `backend/enrichment/nlp_worker.py` with priority query, batch loop, checkpoint update.
- [ ] `fly.toml` defines `[processes]` section with `app` and `nlp_worker`.
- [ ] `[[vm]]` blocks per process; `nlp_worker` allowed to `auto_stop_machines = true`.
- [ ] `/health` extended with `nlp` block reading from `nlp_progress`.
- [ ] Smoke test: run worker locally with `LIMIT=200`, confirm checkpoint and lag updated.

### Risks

- Worker on `auto_stop` may oscillate. First version: keep `min_machines_running = 1` for the worker too, optimise later.
- Two machines = roughly double cost. Acceptable trade for not blocking API.

---

## Phase 3 — Stratified sampling decision (ADR)

**Owner:** Claude + data-signal-architect
**Issue:** new, `nlp(strategy): decide between full backfill and stratified sample for the ~1.8M backlog`
**Depends on:** Phase 2 lag telemetry to inform decision

### Question

Do we transformer-process all 1.8M backlog rows, or a stratified canonical sample of ~80K?

### Argument for stratified

- 1.8M rows at 200/hr (current Fly capacity) = 375 days of continuous compute.
- The story Atlas wants to tell is comparative: cluster centroids, source-mix per country-day, frame distribution per theme. Adding more transformer-scored rows past a saturation point does not change the cluster picture, it only refines the within-cluster variance.
- Stratified sampling preserves coverage across `(country, theme, day, source_family)` buckets while cutting compute 95%.

### Argument for full

- Recency: an old row with a transformer score is still useful for time-series sentiment trajectories.
- Auditability: explaining "we did not score this" is uncomfortable when the row is part of a public surface.

### Recommendation (subject to ADR review)

Hybrid:
1. Full transformer-score everything from now forward (Phase 2 worker drains in near real time).
2. Backfill only stratified sample of `> 30 days old` rows.
3. Everything else gets lexicon-grade sentiment (multilingual VADER-style) and a `nlp_method = 'lexicon'` flag.

### Definition of done

- [ ] `docs/adr/ADR-0004-nlp-stratified-sampling.md` written and approved by Pedro.
- [ ] Stratified sample SELECT query proven against production data.
- [ ] Lexicon scorer module exists at `backend/enrichment/lexicon_sentiment.py` with at least 4 languages (en, es, fr, ar).
- [ ] `nlp_method` column added in migration 015.

---

## Phase 4 — Atlas composite score

**Owner:** narrative-geopolitics-analyst + backend-flow-engineer
**Issue:** new, `data(scoring): implement Atlas composite heat replacing raw-volume ranking`
**Depends on:** Phase 1 multilingual NLP (for polyphony), `signal_class` migration (#155), Voice Mix endpoint (#160)
**Replaces:** raw `volume DESC` ranking in heat surfaces

### Components

```
atlas_heat(country, hours) =
    0.25 * z_velocity                      # current volume vs country baseline
  + 0.20 * surprise_kl                     # KL divergence theme dist vs global
  + 0.15 * source_diversity                # Shannon entropy of source_family
  + 0.15 * local_voice_ratio               # local outlets / total outlets
  + 0.10 * polyphony                       # entropy of nlp_framing labels
  + 0.10 * geo_confidence_mean             # mean geo_confidence
  - 0.05 * duplication_index               # MinHash dupe density
```

Each component normalised to `[0, 1]`. UI shows the composite plus the breakdown so it is never a black box.

### Why this matters

Today, US with 10,000 routine signals beats Burkina Faso with 200 unusual ones. After this, Burkina Faso surfaces when:
- its `z_velocity` is high (200 = 4σ above its baseline of ~30/day);
- its `surprise_kl` is high (the country is suddenly covering an off-baseline theme);
- its `local_voice_ratio` is low (story is told from outside);

…even though absolute volume is tiny.

### Definition of done

- [ ] SQL CTE for each component (recomputed daily by aggregator job).
- [ ] `country_heat_v2` materialized view holds breakdown columns.
- [ ] `/api/v2/heat/countries?hours=N` returns composite + breakdown.
- [ ] Frontend heat list shows composite as the rank, with hover tooltip exposing components.
- [ ] Documented formula in `docs/methodology/atlas-heat.md` with worked example.

---

## Phase 5 — Active learning loop

**Owner:** Claude + analyst (manual review UI)
**Issue:** new, `data(nlp): analyst correction loop to calibrate confidence thresholds`
**Depends on:** Phase 1 multilingual NLP, basic analyst auth in frontend (out of scope here)

### Goal

Signals with `nlp_confidence < 0.5` are flagged in the UI. Analyst can override sentiment / framing / entity tagging. Corrections feed a calibration set used to:

1. Auto-tune the `FRAMING_MIN_SCORE` threshold per language.
2. Generate a monthly fine-tune dataset for a small adapter on top of XLM-R sentiment.

### Tables

```sql
CREATE TABLE nlp_corrections (
  id BIGSERIAL PRIMARY KEY,
  signal_id BIGINT NOT NULL REFERENCES signals_v2(id),
  analyst_id TEXT NOT NULL,
  original_sentiment FLOAT,
  corrected_sentiment FLOAT,
  original_framing VARCHAR(30),
  corrected_framing VARCHAR(30),
  original_persons JSONB,
  corrected_persons JSONB,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nlp_corrections_signal ON nlp_corrections(signal_id);
```

### Definition of done

- Out of scope for this iteration. Phase 5 is documented for tracking only.

---

## Execution order (immediate week)

1. **Today** — Phase 1 implementation: model swap + Dockerfile + selection priority. Ship behind `NLP_MULTILINGUAL_MODE=shadow`.
2. **Today** — Phase 2 scaffold: migration 014 (`nlp_progress`), `nlp_worker.py` skeleton, `/health` extension.
3. **Tomorrow** — `fly.toml` process group split, smoke test worker locally, deploy to staging machine.
4. **Day 3** — Promote `NLP_MULTILINGUAL_MODE` from `shadow` to `on` after 24h shadow comparison.
5. **Day 4–5** — ADR-0004 (stratified sampling), Atlas composite score formula draft.

Phases 3, 4, 5 are tracked as separate issues, executed in subsequent iterations.

---

## GitHub issue map

| Phase | Issue | Status |
|-------|-------|--------|
| 1 | `data(nlp): swap to multilingual sentiment, NER, framing models` | new |
| 2 | `infra(nlp): split NLP enrichment into separate Fly process with priority queue` | new |
| 3 | `nlp(strategy): stratified sampling vs full backfill decision` | new |
| 4 | `data(scoring): Atlas composite heat replacing raw-volume ranking` | new |
| 5 | `data(nlp): analyst correction loop` | new |

Existing related issues to keep coordinated:
- #157 — multilingual NLP benchmark (informs Phase 1 receipts)
- #155 — `signal_class` migration (required by Phase 4)
- #149 — volumetric US dominance normalization (Phase 4 closes this)
- #154 — production source-quality audit (Phase 4 reuses its baseline queries)
- #150 — non-anglophone source expansion (Phase 1 unlocks usable scoring for these)
