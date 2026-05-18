# ADR-0004: NLP Stratified Sampling — Hybrid Coverage + Backlog Prune

**Date:** 2026-05-18
**Status:** Approved by Pedro — 2026-05-18 (15-day cutoff + prune)
**Issue ref:** #164
**Depends on:** ADR-0003 (NLP pipeline architecture), migrations 014–016 (shadow columns, nlp_progress, nlp_method)

---

## Context

As of 2026-05-18 the production database holds roughly 2.1M rows in `signals_v2`, with about 1.8M never touched by the NLP pipeline (sentiment, NER, framing). The current Fly machine, running both API/ingestion and NLP enrichment in the same process, processes roughly 200 rows per hour when active.

Doing the arithmetic on the existing setup:

- 1,800,000 rows ÷ 200 rows/hour ≈ 9,000 hours of continuous compute.
- That is 375 days of 24/7 single-machine throughput.
- Adding the separate `nlp_worker` Fly process (issue #163) and a 2GB machine can push throughput to roughly 1,000 rows/hour. The backlog still takes 75 days at that rate.
- Backlog drainage time matters because the dataset is appending ~100K rows per day. Without higher throughput than ingest, the backlog never closes.

Two questions need to be answered before we burn compute:

1. **Coverage value.** Is it more important to have every row transformer-scored, or to have *every comparison Atlas surfaces* statistically supported?
2. **Cost/effort.** Even if we want full coverage, is the marginal value of going from 80K stratified rows to 1.8M rows worth the multi-week compute spend?

This ADR proposes the answer.

---

## Decision

**Atlas adopts a hybrid coverage model with aggressive prune:**

1. **Forward stream (real-time)** — every new row gets transformer-grade NLP via the worker (issue #163). The worker drains continuously and stays within ~30 min of ingestion lag.

2. **Recent backfill (≤15 days)** — transformer-grade NLP on a *stratified* sample of `(country_code, theme_top, date_bucket, source_family, signal_class)` buckets. Target ~30–40K rows that preserve coverage across every comparison Atlas exposes today.

3. **Optional lexicon fill (≤15 days only)** — for rows within the 15-day window that did not enter the stratified sample but still have a usable headline, the multilingual lexicon scorer (`enrichment/lexicon_sentiment.py`) writes `nlp_sentiment` with `nlp_method = 'lexicon'`. This is opt-in via env flag `LEXICON_BACKFILL=on` and runs after the stratified worker drains.

4. **Prune (>15 days unprocessed)** — rows older than 15 days that never received transformer-grade NLP and are not in the stratified sample are **deleted**. Reasoning: Atlas keeps only signals it can interpret. Storage stays bounded, query performance improves, and confidence-floor filtering on the API stops being half-empty.

5. **Never-processed rows** within the 15-day window retain `nlp_method = NULL` and `nlp_processed_at = NULL`. They drop out automatically when they age past 15 days unless the worker picks them up.

The 15-day cutoff replaces the original 30-day proposal. Rationale below.

### Why 15 days, not 30

- The product surfaces Atlas exposes today (heat, narrative threads, briefings, source integrity) are dominated by the last 7–14 days of activity. A 15-day window covers every visible surface plus a generous buffer for cross-week trend comparisons.
- The 30-day window doubles compute and storage cost without changing any visible comparison.
- 15 days × ~100K rows/day projected = ~1.5M rows in the window. With stratification (K=20 per bucket), the worker only scores ~30–40K of those — a 4-day drain at current capacity, a 1-day drain after the Phase 2 worker split.

### Why prune the >15-day tail

- Today the backlog is ~1.8M unprocessed signals. After prune, it is zero. The forward stream then keeps the floor at zero indefinitely because every new signal is scored within 30 min.
- Pruning frees database storage. Approximate savings: 1.8M rows × ~1.5KB/row ≈ 2.7GB Postgres footprint.
- Pruning eliminates the "half-scored history" problem where some old rows have transformer scores and some have none.
- Atlas is a *current* narrative intelligence product. Historical drift is valuable only when the historical rows can carry the same NLP labels as the present ones. Without uniform labels, comparisons across time are misleading.

---

## Why stratified over full

### Argument for stratified

- **Comparative power, not row coverage, drives Atlas insight.** The product compares countries, themes, source families, and time windows. Every Atlas comparison eventually rolls up to a bucket. As long as every bucket has enough sampled rows for a stable estimator, adding more rows to the same bucket does not change the comparison — it only tightens the within-bucket variance, which Atlas does not surface today.

- **Bucket math.** Roughly 200 countries × 50 thematic clusters × 30 days × 5 source families × 4 signal classes = 6 million logical buckets. The realised matrix is sparse (most cells empty), and in practice Atlas presents 30–50 buckets at a time. Sampling 20 rows per realised bucket yields ~80K rows, which is enough for stable means and proportions.

- **Compute proportional to insight.** 80K rows take 4 days of worker time vs 75 days for the full backlog. Pedro can run the worker for 4 days, ship the coverage, then re-evaluate. The decision is reversible.

- **Less storage churn.** Full backfill writes to every row. Stratified writes to ~5% of rows. Vacuum and index maintenance cost drops accordingly.

### Argument against stratified (and why we accept the risk)

- **Explainability.** "Why is this row not scored?" is an awkward question. Mitigation: every UI surface that consumes NLP labels filters on `nlp_method IS NOT NULL` and falls back to GDELT V2Tone or NULL when needed. The unscored rows are still queryable; they just do not influence narrative-aware aggregates.

- **Late-discovery use cases.** If we later add a feature that needs every row scored (e.g. exact frame counts per country-day), we re-run the worker against the remaining backlog. Stratified sampling does not lock us out of full coverage; it just defers it.

- **Historical sentiment trajectories.** Lexicon-grade sentiment is noisier per-row. Mitigation: when displaying trajectories, label the lexicon-scored portion clearly and use a rolling 7-day average to smooth noise.

---

## Stratification scheme

### Bucket key

```
bucket_key = (country_code, theme_top, date_trunc('day', timestamp), source_family, signal_class)
```

`theme_top` is the first entry of the `themes` array, lowercased and normalised. NULL themes go to a `__none__` bucket.

### Sampling target

Per bucket, sample up to `K=20` rows by recency, breaking ties on `geo_confidence` (higher first).

```sql
WITH stratified AS (
  SELECT
    id,
    country_code,
    LOWER(COALESCE(themes[1], '__none__')) AS theme_top,
    date_trunc('day', timestamp) AS day_bucket,
    source_family,
    signal_class,
    timestamp,
    geo_confidence,
    ROW_NUMBER() OVER (
      PARTITION BY
        country_code,
        LOWER(COALESCE(themes[1], '__none__')),
        date_trunc('day', timestamp),
        source_family,
        signal_class
      ORDER BY timestamp DESC, geo_confidence DESC NULLS LAST
    ) AS rn
  FROM signals_v2
  WHERE created_at > NOW() - INTERVAL '15 days'
    AND nlp_processed_at IS NULL
    AND headline IS NOT NULL
    AND LENGTH(headline) > 10
)
SELECT id FROM stratified WHERE rn <= 20;
```

Run target: every 30 minutes, materialise the latest stratified ID set into the working table `nlp_sample_queue(id BIGINT PRIMARY KEY)` shipped in migration 016. The worker drains `nlp_sample_queue` strictly before falling back to the global priority queue. This guarantees stratified coverage even when worker capacity is constrained.

### Prune step (>15-day unprocessed)

One-time operation, then optionally re-run weekly to catch any drift. Implemented as `backend/scripts/prune_unprocessed_backlog.py`.

```sql
DELETE FROM signals_v2
WHERE nlp_processed_at IS NULL
  AND nlp_method IS NULL
  AND created_at < NOW() - INTERVAL '15 days';
```

Script runs in batches of 50K rows to avoid long-running transactions on the live table. `--dry-run` mode reports counts only. `--max-rows` cap protects against accidental over-prune.

### Optional lexicon fill (≤15-day window)

Rows within 15 days that are not in the stratified sample and have `nlp_processed_at IS NULL` go through `backend/enrichment/lexicon_sentiment.py` when `LEXICON_BACKFILL=on`. The scorer writes `nlp_sentiment` + `nlp_confidence` (capped at 0.5) with `nlp_method = 'lexicon'`. No framing, no entities — lexicon only handles sentiment.

Default is `off`. The prune step above is enough to keep storage bounded; lexicon fill is for cases where API surfaces require non-NULL sentiment on every visible row.

---

## Lexicon scorer

### Languages supported in v1

- English (AFINN-111 + extension)
- Spanish (custom seed lexicon)
- French (custom seed lexicon)
- Arabic (compact seed lexicon)
- Portuguese (custom seed lexicon)

### Algorithm

1. Detect language from `source_lang` first. If absent, run lightweight script-based heuristic (Arabic script → ar, Latin extended → es/fr/pt fallback, etc).
2. Tokenize on whitespace, lowercase Latin scripts.
3. Sum signed token weights from the lexicon, normalise to `[-5, +5]`.
4. Confidence = `min(0.5, abs(score) / 5 * 0.5)` — capped so lexicon rows never look as confident as transformer rows.
5. Skip rows with fewer than 3 tokens.

### Why not VADER directly

VADER is English-only and tuned for social media. The lexicon module borrows VADER's signed-token approach but uses per-language seed lexicons. This is intentionally simple — the goal is reasonable historical signal, not best-in-class quality. Better historical accuracy can be earned later by running the worker against the tail.

---

## Schema changes

```sql
-- Migration 016: nlp_method tag for hybrid coverage.
ALTER TABLE signals_v2
  ADD COLUMN IF NOT EXISTS nlp_method VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_signals_v2_nlp_method
  ON signals_v2 (nlp_method, timestamp DESC)
  WHERE nlp_method IS NOT NULL;
```

Worker writes `nlp_method = 'transformer'` after transformer processing.
Lexicon scorer writes `nlp_method = 'lexicon'`.
Rows with `nlp_method IS NULL` are unscored.

Downstream API queries that depend on label confidence add `WHERE nlp_method = 'transformer'` when they need precision; otherwise they accept `nlp_method IN ('transformer', 'lexicon')`.

---

## Execution plan

1. **Day 1 (done).** Migrations 014, 015, 016 applied to Supabase. `lexicon_sentiment.py` shipped with en/es/fr/pt/ar seed lexicons. Unit tests pass.
2. **Day 2.** Run `prune_unprocessed_backlog.py --dry-run` to verify expected delete count (~1.8M). Pedro reviews. Then run live in batches of 50K.
3. **Day 3.** Worker drains `nlp_sample_queue` (populated every 30 min by the stratified scheduler). Coverage metric on `/health` shows `nlp_coverage_transformer_pct`.
4. **Day 4–5.** Optional: flip `LEXICON_BACKFILL=on` if any UI surface needs non-NULL sentiment on every row.
5. **Week 2 onward.** Re-run prune weekly as a maintenance task to catch any signals that aged past 15d without being picked up by the worker.

---

## Alternatives rejected

**Full transformer backfill.** Discussed above. Compute spend disproportionate to comparative value.

**No backfill at all.** Loses the ability to compare current narratives against pre-NLP history. Atlas already shows historical trajectories; ignoring them is a UX regression.

**OpenAI/Anthropic API for backfill.** 1.8M rows × ~$0.001 per row ≈ $1,800. Cost is bounded but billing is not the only constraint — adding a third-party dependency for historical processing creates audit and reproducibility questions we do not want to take on right now.

**MinHash dedupe before NLP.** Worth pursuing separately. Does not change the stratification decision because Atlas wants signal from duplicate clusters (the syndication itself is the signal), not just one representative row.

---

## Consequences

### What this enables

- Backlog closed in days, not months.
- Forward stream stays current with transformer-grade NLP.
- Historical surfaces have non-NULL sentiment for the long tail (lexicon-grade, clearly labeled).
- The `nlp_method` column lets every downstream query choose its own confidence floor.

### What this requires

- Migration 016 applied to Supabase.
- New module `backend/enrichment/lexicon_sentiment.py` shipped and tested.
- Worker update to drain `nlp_sample_queue` first.
- A small backfill CLI script that walks the >30-day tail, scores via lexicon, writes results.

### What this does NOT do

- Does not replace the transformer pipeline. Stratified sampling defers the volume problem; it does not solve it.
- Does not improve framing or NER on the historical tail (lexicon is sentiment-only).
- Does not change current production scoring surfaces. Surfaces that already depend on transformer NLP keep working; surfaces that need higher recall opt into lexicon-tagged rows via `nlp_method IN (...)`.

---

## Approval log

- **2026-05-18 — Pedro.** Approved stratified sample with 15-day cutoff and aggressive prune of >15-day unprocessed rows. Lexicon scorer kept but defaults off; runs only when a UI surface needs non-NULL sentiment everywhere. `nlp_method` enum accepted as `transformer | lexicon | NULL`. Backfill window set to 15 days based on which Atlas surfaces actually consume historical data.
