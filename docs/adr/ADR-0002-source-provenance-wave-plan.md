# ADR-0002: Source Robustness Wave Plan

**Date:** 2026-05-09  
**Status:** Accepted  
**Issue refs:** #84 (migration 008), #85 (blocklist), #86 (GDELT translation), #87 (sentiment fix), #88 (RSS), #89 (ReliefWeb), #90 (Wave 3), #91 (confidence badges), #92 (NLP ADR)

---

## Context

Live investigative session on 2026-05-08 probed Atlas across 20+ API endpoints and surfaced structural signal quality issues:

1. **Entertainment noise**: iHeart.com = #1 global source (4,695 signals/day). Carnival stories classified as "Manmade Disaster Implied."
2. **Humanitarian blind spots**: Gaza = 23 signals/day. "Gaza hospital humanitarian" search → ZERO signals.
3. **Chokepoint under-coverage**: Strait of Hormuz = 6 signals in 168h during active US-Iran naval engagements.
4. **Language bias**: ~68% of signals from/about the US. Arabic, Persian, Russian, Chinese primary sources absent.
5. **Geographic misattribution**: Mount Dukono (Indonesia) attributed to Singapore. Polish content attributed to Marshall Islands.
6. **Sentiment inconsistency**: Same country shows different sentiment values in different endpoints (Gaza: -5.33 briefing vs -0.48 country endpoint).
7. **Identity-less signals**: No way to distinguish Reuters wire from state media from entertainment blog.

GDELT was Atlas's first data source and is an excellent volume spine, but it is a pre-LLM political-science event coding system not designed for narrative framing intelligence.

---

## Decision

**Implement a phased wave plan to robustify signal quality and coverage, anchored by a source provenance schema before any new external source is added.**

### Pre-condition: Migration 008 — Source Provenance

Before activating any new source, add provenance fields to `signals_v2`:

```sql
ALTER TABLE signals_v2
  ADD COLUMN source_family      VARCHAR(20) DEFAULT 'unknown',
  ADD COLUMN source_country     CHAR(2),
  ADD COLUMN source_lang        CHAR(2)    DEFAULT 'en',
  ADD COLUMN geo_confidence     FLOAT      DEFAULT 1.0,
  ADD COLUMN attribution_method VARCHAR(30) DEFAULT 'gdelt_gkg',
  ADD COLUMN is_state_media     BOOLEAN    DEFAULT FALSE;
```

**Rationale**: Without identity fields, new sources inherit the same trust vacuum as iHeart. The schema must exist before any signal can be tagged with its origin.

---

### Wave 0 — Clean what exists (estimated: 3–4 days)

**0a. Domain blocklist** (`backend/app/config/source_blocklist.py`)  
Filter known entertainment/tabloid domains at ingestion time. iHeart alone accounts for ~4,700 signals/day of low-quality content. Expected: -25–35% noise reduction.

**0b. GDELT Translation Feed activation**  
`ingest_v2.py` already defines `GDELT_TRANS_UPDATE_URL` but never calls it. One additional `fetch_latest_gdelt_url()` call per cycle adds Arabic, Persian, Russian, Chinese, Spanish, Portuguese coverage. Same vendor, same schema, zero new dependencies. Biggest single free unlock available.

**0c. Sentiment methodology fix**  
Unify the sentiment calculation formula across `/api/v2/briefing` and `/api/v2/country/:code`. Add `sentiment_n` and `sentiment_basis` to API responses so analysts can assess confidence.

---

### Wave 1 — Curated RSS (estimated: 4–5 days)

`backend/connectors/rss.py` already exists with a production `RSSConnector` that is **not wired** into `ingest_loop.py`. Wire it with a curated feed list targeting specific gaps:

| Category | Feeds | Gap filled |
|----------|-------|-----------|
| Maritime/chokepoints | gCaptain, Splash247, Reuters Shipping | Hormuz, shipping |
| Middle East | Al Jazeera EN, Middle East Eye, Al-Monitor | Iran, Gaza |
| Russia independent | Meduza EN, RFE/RL | Non-state Russian view |
| Asia | SCMP, Dawn PK, The Hindu | Pakistan, India, China |
| Humanitarian | UN News RSS, MSF Newsroom | Gaza, Somalia, Yemen |
| Africa/LatAm | The Africa Report, AllAfrica | Underrepresented regions |

Each feed tagged with `source_family`, `source_country`, `source_lang`, `is_state_media`.

---

### Wave 2 — ReliefWeb (estimated: 2–3 days)

Free OCHA API covering Gaza, Somalia, Yemen, Myanmar, Sudan, DRC, Haiti, Afghanistan, Syria with:
- `geo_confidence = 0.99` (explicit geographic fields, not NLP-inferred)
- `source_family = 'ngo'`
- MSF, UNHCR, WFP, IRC situation reports

Run every 6 hours. No API key required.

---

### Wave 3 — Non-English RSS with state-media classification (estimated: 3–4 days)

15–25 non-English/non-Western feeds to capture how stories are framed from *inside* the countries generating them. Includes state media sources (IRNA, RIA, Xinhua) explicitly tagged `is_state_media = True`.

**Design principle**: Hiding state media makes Atlas less accurate, not more. An analyst studying Russian narrative needs to see RIA Novosti's framing alongside Meduza's. The `is_state_media` field lets the UI surface this honestly.

---

## Consequences

### What this changes

- Signal volume: estimated +40–80% (GDELT Translation + RSS + ReliefWeb)
- Signal quality: noise reduced ~25% (domain blocklist)
- Coverage: Gaza, Somalia, Hormuz, China-Iran diplomacy all significantly improved
- Analyst trust: `coverage_confidence` badges prevent misleading high-precision sentiment from small-N samples

### What this does NOT fix

- Social media signals (Telegram, VK, Weibo) — require commercial APIs or scraping, not in scope
- Deep framing analysis — addressed in ADR-0003 (NLP pipeline)
- GDELT's fundamental geographic attribution heuristics — partially mitigated by geo_confidence field and Wave 4 NLP validation

### Risks

- DB growth: +40–80% signal volume could strain Supabase free tier. Monitor `signals_v2` table size after each wave.
- RSS feed instability: 30 feeds = 30 potential failure modes. Each must fail silently (log, skip, continue).
- Duplicate prevention: `source_url` unique constraint handles deduplication across sources.

---

## Alternatives considered

**Add social media APIs (Twitter/X, Telegram)**: Rejected. Commercial API costs ($5K+/mo for X), legal complexity, scraping instability. Wrong shape for current Fly.io/pg stack.

**NewsAPI.org**: Rejected for now. $449/mo paid tier. Free tier (100 req/day) insufficient for production. Revisit if NLP layer (ADR-0003) demonstrates value of curated corpus.

**Common Crawl**: Rejected. Too large, wrong shape, requires big-data infrastructure.

**Replace GDELT entirely**: Rejected. GDELT provides scale (183K signals/day) and 15-min freshness that no free alternative matches. It remains the volume spine; Wave 4 adds quality on top.
