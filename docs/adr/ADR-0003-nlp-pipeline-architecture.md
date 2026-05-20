# ADR-0003: Atlas NLP Pipeline — Own Sentiment, Framing, and Entity Extraction

**Date:** 2026-05-09  
**Status:** Approved — 2026-05-09  
**Issue ref:** #92  
**Depends on:** ADR-0002 (Wave plan), Waves 0–2 stable

---

## Context

### The GDELT substrate problem

Atlas currently inherits all NLP annotations from GDELT:
- **Sentiment**: GDELT V2Tone — average of a word-list dictionary per article. Returns a single float. Cannot distinguish "Iran repelled US attack" from "US destroyed Iran vessel" — same words, opposite framing.
- **Entities**: GDELT V2Persons — heuristic NER that in live testing extracted "vasudhaiva kutumbakam" (Sanskrit philosophy phrase) as a Surinamese politician, and misattributed Zambian human rights cancellation to Marshall Islands.
- **Geography**: GDELT LocationV1 — heuristic that attributed Indonesia's Mount Dukono volcanic eruption to Singapore, and Polish/Catalan content to Marshall Islands.
- **Framing**: Not provided. GDELT has no framing detection.

These are not GDELT bugs. GDELT is a political-science event coding system optimized for volume and political event classification, not narrative intelligence. The longer Atlas treats GDELT annotations as ground truth for a *narrative* intelligence product, the more expensive the eventual correction.

### The positioning decision

There are two viable architectures:

**Option A — GDELT wrapper**: Atlas stays as an interface on top of GDELT. Fast to build, limited by GDELT's ceiling. Sentiment = V2Tone, entities = V2Persons. Differentiation is UI/UX, not data.

**Option B — Two-layer architecture**: GDELT as volume spine (scale, freshness) + Atlas NLP corpus (accuracy, framing, narrative intelligence). GDELT handles breadth; Atlas handles depth on a curated subset.

---

## Decision

**Atlas adopts the two-layer architecture (Option B).**

GDELT is not replaced — it is supplemented. The NLP pipeline runs on signals from curated RSS sources (Wave 1+) and selected GDELT signals, enriching them with higher-quality annotations stored alongside (not instead of) GDELT's.

---

## Architecture

```
Layer 1 (Volume Spine)          Layer 2 (Atlas NLP)
─────────────────────           ───────────────────
GDELT GKG (183K/day)            curated ~5K signals/day
GDELT Translation               from RSS + ReliefWeb
RSS curated (30 feeds)    →     processed by nlp_pipeline.py
ReliefWeb (OCHA)                sentiment (transformer)
                                framing (zero-shot)
                                entities (spaCy NER)
                                geo validation
```

Layer 2 writes to enriched columns in `signals_v2` or a parallel `signals_enriched` table (schema decision below). The API layer prefers Layer 2 annotations when available, falls back to GDELT for signals without NLP processing.

---

## NLP Components

### 1. Sentiment (replaces V2Tone for processed signals)

**Current**: GDELT V2Tone average (word-list, [-100, +100])  
**Target**: Per-sentence transformer sentiment, normalized to [-5, +5]  

**Model**: `cardiffnlp/twitter-roberta-base-sentiment-latest`  
- Fine-tuned on 198M tweets → generalist across news-like short text  
- 3-class output (positive/neutral/negative) → map to [-5, +5]  
- CPU inference: ~40–60ms per article on Fly.io  

**Alternative for economic signals**: `ProsusAI/finbert`  
- Finance-domain trained, better for tariff/trade/market coverage  

### 2. Framing Detection (new capability)

**Current**: Not provided by GDELT  
**Target**: Zero-shot frame classification per article  

**Frame labels (v1)**:
- `conflict_escalation` — military action, threats, strikes
- `diplomatic_resolution` — negotiations, ceasefire, talks
- `humanitarian_crisis` — civilian impact, displacement, aid
- `economic_impact` — markets, sanctions, trade effects
- `political_domestic` — internal politics, elections, governance
- `information_warfare` — propaganda, disinformation, narrative framing

**Model**: `facebook/bart-large-mnli` (zero-shot NLI)  
CPU inference: ~200ms per article. Run in batches of 10.

### 3. Entity Extraction (replaces GDELT V2Persons)

**Current**: GDELT V2Persons heuristic (produces "vasudhaiva kutumbakam" as a person)  
**Target**: spaCy NER with confidence scores  

**Model**: `en_core_web_trf` (English, transformer-based)  
For multilingual signals: `xx_ent_wiki_sm`  

Output fields:
```python
{
  "persons": [{"name": "Abbas Araghchi", "confidence": 0.94}],
  "orgs": [{"name": "IRGC", "confidence": 0.88}],
  "locations": [{"name": "Tehran", "confidence": 0.97}]
}
```

Filter: only emit entities with `confidence > 0.7`. This eliminates Sanskrit phrases, partial matches, and cross-article noise.

### 4. Geographic Attribution Validation

Cross-validate GDELT's `country_code` against spaCy location entities from the article text.

```python
def validate_geo(gdelt_country: str, spacy_locations: list) -> float:
    """Returns geo_confidence [0,1]. 1.0 = fully corroborated, 0.3 = conflicting."""
    if not spacy_locations:
        return 0.6  # no info to contradict GDELT
    top_country = resolve_country(spacy_locations[0])
    if top_country == gdelt_country:
        return 0.95
    if top_country in NEIGHBOR_MAP.get(gdelt_country, []):
        return 0.7
    return 0.3  # conflict: flag for review
```

The Singapore/Dukono case: spaCy finds "Indonesia" and "Maluku" in the article text → `geo_confidence = 0.3` for SG attribution → anomaly panel flags it as uncertain.

---

## Schema Decision: Enrich in-place vs separate table

**Option A — In-place enrichment** (preferred):  
Add nullable columns to `signals_v2`:
```sql
ALTER TABLE signals_v2
  ADD COLUMN nlp_sentiment      FLOAT,        -- NULL = not processed
  ADD COLUMN nlp_framing        VARCHAR(30),
  ADD COLUMN nlp_persons        JSONB,
  ADD COLUMN nlp_confidence     FLOAT,
  ADD COLUMN nlp_processed_at   TIMESTAMPTZ;
```
API logic: `COALESCE(nlp_sentiment, gdelt_tone_normalized)` — prefer NLP when available.

**Option B — Separate `signals_enriched` table**:  
JOIN required for every query. More complex. Rejected unless schema migration proves problematic.

**Decision: Option A.** Simpler queries, atomic signal record, COALESCE fallback is clean.

---

## Compute Budget

Fly.io machine: 1 shared CPU, 256MB–1GB RAM (current config).

| Component | Time/article | Batch size | Time/batch |
|-----------|-------------|------------|------------|
| Sentiment | 50ms | 20 | 1s |
| Framing | 200ms | 10 | 2s |
| NER | 80ms | 20 | 1.6s |
| Geo validation | 5ms | 20 | 0.1s |
| **Total** | ~335ms | **10** | **~3.4s** |

Run 100 articles per NLP cycle → ~34s. Acceptable as async background task after GDELT ingestion.

**Memory constraint**: `bart-large-mnli` is 1.6GB. This exceeds current Fly.io config.  
**Options**: (a) Upgrade Fly.io machine to 2GB RAM, (b) use `cross-encoder/nli-distilroberta-base` (250MB) as lighter alternative, (c) use Hugging Face Inference API (free tier, network latency).

**Recommendation**: Start with `cross-encoder/nli-distilroberta-base` for framing (lighter, still good). Upgrade if accuracy proves insufficient.

---

## Rollout Plan

### Phase 1 ✅ DONE (2026-05-09): Sentiment
- `nlp_sentiment` added. cardiffnlp model. 106 RSS signals enriched. COALESCE in API.

### Phase 2 ✅ DONE (2026-05-09): Entity extraction
- `nlp_persons` JSONB. spaCy en_core_web_sm. ASCII + word-count filter. API returns NLP persons.

### Phase 3 ✅ DONE (2026-05-09): Framing detection
- `nlp_framing` VARCHAR(30). cross-encoder/nli-distilroberta-base. 6 frames. 46 English signals classified.
- Arabic/non-English → NULL (English-only model, correct behavior).
- API returns `framing` field on every signal.

### Phase 3b — GDELT normalization (next session)
**Decision (2026-05-09):** Extend NLP to all signals, not just curated RSS subset.

**Two-track execution:**

**Track A — Historical backfill (Mac, one-time):**
- 2.14M GDELT signals with headlines, `nlp_framing IS NULL`
- Run `nlp_pipeline.py` on Mac, `ORDER BY timestamp DESC` (recent first)
- ~59h total CPU time, runs in background, no rush
- Writes directly to Supabase → visible in production immediately

**Track B — Ongoing automation (Fly, permanent):**
- Add NLP deps to Dockerfile: torch CPU-only, transformers, spaCy + en_core_web_sm
- Pre-bake models into image at build time (avoids runtime download)
- Add `run_nlp_enrichment()` call to `ingest_loop.py` after every GDELT cycle
- Processes latest 500 unprocessed signals per cycle (~90s on shared CPU)
- Independent of Mac, runs 24/7

**Fly RAM budget:**
- Current usage: ~205MB (API + ingestion watchdog)
- Available: ~654MB
- Models in-process during NLP run: ~500MB (sentiment + framing loaded one at a time)
- Pattern: load → run batch → unload → sleep. Peak ~500MB, stays under 985MB limit.

**Remove `CURATED_METHODS` filter:** pipeline processes all signals with `nlp_X IS NULL AND headline IS NOT NULL`.

### Phase 4: Geo validation
- Update `geo_confidence` using spaCy locations vs GDELT country_code
- Anomaly panel: badge when `geo_confidence < 0.7`
- Validates Singapore/Indonesia misattribution bug

---

## Consequences

### What this enables

- Framing comparison: "How does Russian state media vs Meduza frame the same ceasefire?"
- Entity trust: Person graphs without Sanskrit philosophers and Sanskrit proverbs
- Geographic confidence: Anomaly alerts distinguishable between real country spikes and misattribution noise
- Sentiment accuracy: Article-level nuance instead of word-list averages

### What this requires

- Model downloads on first deploy (one-time, ~300MB for lighter stack)
- Fly.io machine upgrade likely needed for framing model (2GB RAM, ~$4/mo increase)
- Migration for `nlp_*` columns in `signals_v2`
- 2–4 weeks of implementation

### What this does NOT do

- Does not process historical backlog instantly (Track A covers this over time, recent-first priority)
- Does not eliminate GDELT (remains the volume spine)
- Does not provide real-time framing (async, ~30-min lag after ingestion)

---

## Alternatives rejected

**Use OpenAI API for NLP**: Cost at scale (183K signals × $0.002 = $366/day). Rejected.  
**Use Hugging Face Inference API**: Free tier limited to 30K tokens/min. Viable for prototyping Phase 1.  
**Stick with GDELT V2Tone**: Rejected. V2Tone is the core limitation. Framing detection is impossible without own NLP.  
**Process all 183K signals**: Compute cost prohibitive. Curated subset (RSS + ReliefWeb) gets NLP treatment; GDELT gets it selectively.

---

## Approval required

Pedro must approve this ADR before any implementation begins. Key questions to confirm:

1. **Positioning**: Confirmed — Atlas is NOT a GDELT wrapper. Two-layer architecture accepted.
2. **Compute budget**: Accept Fly.io machine upgrade (~$4/mo) for framing model?
3. **Timeline**: Wave 4 starts after Waves 0–2 are stable (estimated: 3–5 weeks from now)
4. **State media**: Confirmed — state media sources (IRNA, RIA, Xinhua) included with `is_state_media = True` label
