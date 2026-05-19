# Topic Intelligence + Signal Class Attack Plan — 2026-05-19

Successor to [2026-05-16-productization-roadmap.md](2026-05-16-productization-roadmap.md). Drives 3 parallel tracks against the open issue backlog (#145–#169).

## Why this plan now

Audit [docs/research/2026-05-19-topic-readiness-and-search-performance-audit.md](../research/2026-05-19-topic-readiness-and-search-performance-audit.md) closed #154 and identified 3 concurrent problems:

1. **Search broken in production** — `copper`, `gaza`, `conflicto colombia` timeout >20s. Backend doesn't accept `country` param. Production credibility issue.
2. **New ingest sources invisible** — NewsData, MediaStack, NewsAPI, Reddit all have `themes=[]` (96%+ outside GDELT). Diversity exists in DB but not in UI.
3. **No semantic provenance** — without `signal_class`, Reddit commentary and Reuters syndication count equally in scoring; #149 cluster scoring blocked; Voice Mix blocked.

Plan #11 ([2026-05-19-topic-intelligence-and-source-visibility.md](../superpowers/plans/2026-05-19-topic-intelligence-and-source-visibility.md)) sequenced these serially. This attack plan runs them as 3 parallel tracks because dependencies allow it.

---

## Track A — Search performance (P0, ~3 days)

**Issues closed**: [#169](https://github.com/pedro-cmyks/Observatory-Global/issues/169)
**Issues advanced**: [#69](https://github.com/pedro-cmyks/Observatory-Global/issues/69) (Spanish/multilingual search)

**Why P0**: production users hit timeouts today. Unrelated to topic intelligence; runs independently.

**Moves**:

1. Migration 022: `gin_trgm_ops` on `lower(headline)` and `lower(article_title)`
   ```sql
   CREATE INDEX CONCURRENTLY idx_signals_headline_trgm
     ON signals_v2 USING gin (lower(headline) gin_trgm_ops);
   ```
   Bonus: same index accelerates Track B lexicon pass.

2. `backend/app/routers/search.py` — accept `country` param, scope `country_code = $1` before taxonomy joins.

3. Replace `LIKE ANY('%term%')` against `array_to_string(themes,' ')` with GIN-friendly `themes && ARRAY['THEME1','THEME2']`.

4. Per-segment 8s timeout in `unified_search` — return partial with `degraded:true` flag.

5. `frontend-v2/src/components/SearchBar.tsx` — `AbortController` per keystroke.

**Exit gate**: `copper`/`gaza`/`conflicto colombia` <2s p95. Spanish compound queries route through `parseCompoundQuery` to scoped backend.

---

## Track B — Signal Class + Topic Intelligence (P1, ~7 days)

Serial within track. Each step unblocks the next.

**Issues closed**: [#155](https://github.com/pedro-cmyks/Observatory-Global/issues/155), [#157](https://github.com/pedro-cmyks/Observatory-Global/issues/157), [#162](https://github.com/pedro-cmyks/Observatory-Global/issues/162), [#167](https://github.com/pedro-cmyks/Observatory-Global/issues/167)
**Issues advanced**: [#149](https://github.com/pedro-cmyks/Observatory-Global/issues/149), [#163](https://github.com/pedro-cmyks/Observatory-Global/issues/163), [#164](https://github.com/pedro-cmyks/Observatory-Global/issues/164)
**Issues unblocked**: [#165](https://github.com/pedro-cmyks/Observatory-Global/issues/165) (composite heat), [#166](https://github.com/pedro-cmyks/Observatory-Global/issues/166) (analyst corrections)

### B.1 — Migration 021 `signal_class` ✅ DONE 2026-05-19

`signal_class VARCHAR(30) NOT NULL DEFAULT 'reporting'` + CHECK constraint + 2 indexes (`idx_signals_class_time`, `idx_signals_class_country_time`).

Backfill rules (provenance-only, NOT NLP):

| Rule (most specific first) | Mapping |
|---|---|
| `attribution_method='reddit_public'` OR `source_family='social'` | `social_commentary` |
| `attribution_method LIKE 'reliefweb%'` OR `source_family='ngo'` | `humanitarian` |
| `is_state_media=TRUE` OR `source_family='state'` | `state_media` |
| `source_family='wire'` | `wire` |
| else | `reporting` (default) |

Helper: [backend/app/services/_signal_class.py](../../backend/app/services/_signal_class.py) — `derive_signal_class()` mirrors migration CASE order. All 7 ingest services consume it.

**Verified distribution in production (2026-05-19)**:

| signal_class | count |
|---|---:|
| reporting | 2,288,194 |
| state_media | 2,641 |
| wire | 2,127 |
| social_commentary | 351 |
| humanitarian | 3 |

Humanitarian = 3 reveals broken ReliefWeb ingestion (separate followup; not blocking).

### B.2 — Bulk SQL lexicon classifier (creative shortcut)

Plan #11 specifies Python loop. Replaced by single SQL UPDATE leveraging GIN trigram index from Track A migration 022:

```sql
INSERT INTO signal_topic_assignments (signal_id, topic_id, method, confidence, model_version, evidence)
SELECT s.id, t.id, 'lexicon',
       0.75 + LEAST(0.15, 0.05 * cardinality(ARRAY(
         SELECT 1 FROM unnest(t.lexicon_terms) lex WHERE lower(s.headline) LIKE '%' || lex || '%'
       ))),
       'atlas-topic-v1',
       jsonb_build_object(
         'matched_terms', ARRAY(SELECT lex FROM unnest(t.lexicon_terms) lex WHERE lower(s.headline) LIKE '%' || lex || '%'),
         'theme_overlap', t.gdelt_theme_hints && s.themes
       )
FROM signals_v2 s
JOIN atlas_topics t ON (
     EXISTS (SELECT 1 FROM unnest(t.lexicon_terms) lex WHERE lower(s.headline) LIKE '%' || lex || '%')
  OR t.gdelt_theme_hints && s.themes
)
WHERE s.timestamp > NOW() - INTERVAL '24 hours'
  AND length(coalesce(s.headline,'')) >= 25
ON CONFLICT DO NOTHING;
```

Backfill 7 days first, then incremental cron via worker.

### B.3 — Worker phase for embedding + zero-shot

`backend/enrichment/topic_intelligence.py`:
- `classify_with_embedding()` — `paraphrase-multilingual-MiniLM-L12-v2`, kNN vs precomputed atlas_topic embeddings
- `classify_with_zeroshot()` — `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`, only when embedding confidence <0.7

Selection: non-GDELT first, recent first, headline length ≥25. Env flags:

```bash
TOPIC_INTELLIGENCE_ENABLED=true
TOPIC_INTELLIGENCE_MODE=shadow
TOPIC_WORKER_LIMIT=50
TOPIC_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
TOPIC_ZEROSHOT_MODEL=MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli
```

**Memory caveat**: load topic models in separate phase from sentiment/NER/framing — kill+load cycle, not co-resident. Measure before promoting `TOPIC_INTELLIGENCE_MODE=on`.

### B.4 — Benchmark + promotion gate

`backend/scripts/benchmark_topic_models.py`. Use stratified 300-row sample from audit §5 SQL. Manual annotation of 50 rows. Promotion gate:
- agreement >70% vs manual
- p50 runtime <300ms
- worker memory <3GB
- per-language coverage report

---

## Track C — Voice Mix UI + Public Attention Threads (P2, ~5 days, parallel from B.1)

**Issues closed**: [#160](https://github.com/pedro-cmyks/Observatory-Global/issues/160), [#168](https://github.com/pedro-cmyks/Observatory-Global/issues/168)
**Issues advanced**: [#145](https://github.com/pedro-cmyks/Observatory-Global/issues/145), [#146](https://github.com/pedro-cmyks/Observatory-Global/issues/146)

### C.1 — Voice Mix endpoint + CountryBrief component

`GET /api/v2/countries/{iso}/voice-mix?hours=24` aggregates `signal_class` + `source_lang` + `is_state_media`:

```json
{
  "country_code": "CO",
  "hours": 24,
  "total": 1234,
  "segments": [
    {"key": "local_language", "label": "Local-language", "count": 420, "share": 0.34},
    {"key": "international", "label": "International press", "count": 700, "share": 0.57},
    {"key": "humanitarian", "label": "Humanitarian", "count": 24, "share": 0.02},
    {"key": "state_media", "label": "State media", "count": 0, "share": 0.0},
    {"key": "social", "label": "Social commentary", "count": 90, "share": 0.07}
  ]
}
```

Stacked bar in `CountryBrief.tsx`. Tooltips via `data-tip` (not native `title=`).

### C.2 — Public Attention Threads (creative)

Use Wikipedia opening sentence + Trends keyword as zero-shot input — no article scraper needed. `wiki_pageviews_v2` already caches first paragraph.

`GET /api/v2/attention/threads?country=CO&hours=48`:

| Relationship | Definition |
|---|---|
| `media-led` | media_signals >50 AND attention >10 |
| `public-led` | attention >50 AND media_signals <10 |
| `social-led` | reddit_share > 0.5 |
| `silent-risk` | attention >0 AND media_signals = 0 (high-value detection) |
| `uncoupled-attention` | other |

`silent-risk` is Atlas's strongest differentiator — narratives users care about that media isn't covering.

---

## Decisions to commit before B.3

| Decision | Recommendation |
|---|---|
| pgvector vs JSON cache | pgvector. Standard. Native kNN. |
| Worker 4GB enough? | Measure during benchmark. Split workers if topic + NLP co-resident exceeds 3.5GB. |
| Topic backfill scope | 7 days shadow first. Expand only after promotion. |
| Trigram index | `CONCURRENTLY` (lock too long on 2.28M rows otherwise). |
| GDELT `xx` lang handling | cld3 detect in pipeline (~5ms/row). |
| Search degraded mode | per-segment 8s timeout, partial return with flag. |

---

## Risks (rigorous)

1. **Topic shadow → on changes ranking**. Mitigate: A/B flag-gated 1-week minimum, compare narrative thread CTR pre/post.
2. **Lexicon false positives** (e.g. "election" in non-electoral US news). Mitigate: require `themes && gdelt_theme_hints` for confidence >0.8.
3. **GDELT translated `xx`** breaks multilingual embeddings without lang detect. Mitigate: cld3 step before embed.
4. **Worker memory contention** with NLP + topic models loaded simultaneously. Mitigate: kill+load cycle by phase.
5. **GDELT volume bias migrates to atlas_topics** if no source diversity weighting. Blocker: topic ranking must consume `signal_class` + #149 before going on.
6. **Search degraded mode UX**: must label "results may be incomplete" if any segment times out.

---

## Issue map summary

**Closes 7**: #155, #157, #160, #162, #167, #168, #169
**Advances 7**: #69, #145, #146, #149, #150, #163, #164
**Unblocks 2**: #165, #166
**New 3** (this plan opens them): trigram index, bulk SQL lexicon, silent-risk detector
**Parking 14**: ACLED, mascot, polish, downstream research

Net: 45% backlog clearance + 4 previously-blocked features unblocked.

---

## Execution order today

1. ✅ Migration 021 `signal_class` (DONE)
2. ✅ 7 ingest services patched (DONE)
3. ✅ Tests 23/23 passing (DONE)
4. ✅ Migration applied + backfilled in Supabase (DONE)
5. Open 3 new GitHub issues
6. Comment on #154/#155/#167/#169 linking work
7. Commit + push branch
8. Next: Track A migration 022 trigram index + `country` param in search
9. Next: Track B.2 bulk SQL lexicon classifier
