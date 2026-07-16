"""
Atlas NLP Pipeline — Phase 1 + 2 + 3: Sentiment, Entity Extraction & Framing.

Applies to ALL signals with valid headlines (GDELT + RSS + ReliefWeb + API + Social).
No source filter — everything gets normalized to the same NLP annotations.

Multilingual mode (issue #162) routes by NLP_MULTILINGUAL_MODE env:
  - off:    English-only models, write to production nlp_* columns. (default)
  - shadow: multilingual models, write to nlp_*_xlm shadow columns.
  - on:     multilingual models, write to production nlp_* columns.

Memory pattern on Fly (985MB machine):
  Load sentiment -> run -> del + gc -> load NER -> run -> del + gc -> load framing -> ...
  Peak per phase: ~500MB. Never loads multiple models at once.
"""
import argparse
import asyncio
import gc
import json
import logging
import os
import time
from collections.abc import Sequence
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Mode + models ────────────────────────────────────────────────────────────
NLP_MULTILINGUAL_MODE = os.getenv("NLP_MULTILINGUAL_MODE", "off").lower()  # off | shadow | on

SENTIMENT_MODEL_EN = "cardiffnlp/twitter-roberta-base-sentiment-latest"
SENTIMENT_MODEL_XLM = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
FRAMING_MODEL_EN = "cross-encoder/nli-distilroberta-base"
FRAMING_MODEL_XLM = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
SPACY_MODEL_EN = "en_core_web_sm"
SPACY_MODEL_XX = "xx_ent_wiki_sm"
# Non-English NER backend (2026-07-01 real-fix eval): xx_ent_wiki_sm is worse-than-useless
# for non-Latin (fa: nothing; ar: Russia->PERSON). A proper xlm-roberta token-classification
# model extracts non-Latin entities with correct types (measured: Russia->LOC, Yazd via
# cross-lingual transfer). Flag-gated + reversible; default xlm when multilingual is enabled.
NER_MODEL_XLM = os.getenv("NLP_NER_MODEL_XLM", "Davlan/xlm-roberta-base-ner-hrl")
NLP_MULTILINGUAL_NER = os.getenv("NLP_MULTILINGUAL_NER", "xlm").lower()  # xlm | spacy
# Davlan HRL labels (PER/ORG/LOC/DATE/MISC) -> the kept entity schema; DATE/MISC dropped.
_HF_NER_LABEL_MAP = {"PER": "PERSON", "PERSON": "PERSON", "ORG": "ORG", "LOC": "LOC"}
# Davlan is strong for its trained langs + non-Latin transfer (zh/fa/ar/ko/de/pt 70–100%
# precision, measured) but has NO Russian (ru precision 0/3). A second model — wikineural —
# covers ru (measured 87.5% precision, 100% extract) but not the non-Latin set. So route
# Cyrillic langs to wikineural, everything-else-non-English to Davlan. Loaded lazily (only
# when a Cyrillic row is present) to keep the mindful M1 worker's memory bounded.
NER_MODEL_CYRILLIC = os.getenv("NLP_NER_MODEL_CYRILLIC", "Babelscape/wikineural-multilingual-ner")
NLP_CYRILLIC_LANGS = {  # wikineural covers ru; uk/be/bg via the same family (untested → guarded)
    x.strip() for x in os.getenv("NLP_CYRILLIC_LANGS", "ru").split(",") if x.strip()
}
# Langs neither model handles → skip to the English model (clean-empty → gazetteer carries it).
NLP_XLM_NER_SKIP_LANGS = {
    x.strip() for x in os.getenv("NLP_XLM_NER_SKIP_LANGS", "").split(",") if x.strip()
}

MODEL_VERSION_TAG = {
    "off": "en-v1",
    "shadow": "xlm-shadow-v1",
    "on": "xlm-v1",
}.get(NLP_MULTILINGUAL_MODE, "unknown")

BATCH_SIZE = 20
NER_BATCH_SIZE = max(1, int(os.getenv("NLP_NER_BATCH_SIZE", "8")))
# Independent work budget for the now-batched NER phase. Zero preserves the
# caller's base limit (Fly/default); the measured M1 runner sets 1200 without
# multiplying the slower sentiment/framing phases too.
NER_LIMIT = max(0, int(os.getenv("NLP_NER_LIMIT", "0")))
FRAMING_BATCH_SIZE = 8
FRAMING_MIN_SCORE = 0.35
# Multilingual MiniLM framing is a smaller NLI model than mDeBERTa, chosen so
# the worker can complete cycles on Fly shared CPU/2GB instead of stalling.
# Allow operators to skip the framing phase entirely (worker still does
# sentiment + NER + checkpoint) when NLP_SKIP_FRAMING=true. Useful while we
# evaluate replacing mDeBERTa with a lighter multilingual NLI model.
SKIP_FRAMING = os.getenv("NLP_SKIP_FRAMING", "false").lower() == "true"
# Independent batch limit for framing so we can cap it lower than sentiment/NER.
FRAMING_LIMIT_CAP = int(os.getenv("NLP_FRAMING_LIMIT", "0"))

FRAME_LABELS = [
    "conflict escalation",
    "diplomatic resolution",
    "humanitarian crisis",
    "economic impact",
    "political domestic",
    "information warfare",
]
LABEL_TO_DB = {
    "conflict escalation": "conflict_escalation",
    "diplomatic resolution": "diplomatic_resolution",
    "humanitarian crisis": "humanitarian_crisis",
    "economic impact": "economic_impact",
    "political domestic": "political_domestic",
    "information warfare": "information_warfare",
}

# Languages with non-Latin scripts where the existing ASCII filter would over-reject.
NON_LATIN_LANGS = {"ar", "fa", "he", "hi", "bn", "th", "ja", "ko", "zh", "am", "ti", "ka", "hy", "ur", "pa", "ta", "te"}


def _multilingual_enabled() -> bool:
    return NLP_MULTILINGUAL_MODE in ("shadow", "on")


def _shadow_writes() -> bool:
    return NLP_MULTILINGUAL_MODE == "shadow"


def _select_sentiment_model(source_lang: str | None) -> str:
    if not _multilingual_enabled():
        return SENTIMENT_MODEL_EN
    # Multilingual mode: always use XLM for consistency across languages.
    return SENTIMENT_MODEL_XLM


def _select_framing_model(source_lang: str | None) -> str:
    if not _multilingual_enabled():
        return FRAMING_MODEL_EN
    return FRAMING_MODEL_XLM


def _select_spacy_model(source_lang: str | None) -> str:
    if not _multilingual_enabled():
        return SPACY_MODEL_EN
    if (source_lang or "").lower() == "en":
        return SPACY_MODEL_EN
    return SPACY_MODEL_XX


def _ner_phase_limit(base_limit: int) -> int:
    return NER_LIMIT if NER_LIMIT > 0 else base_limit


# ── Filters ──────────────────────────────────────────────────────────────────
def _entity_valid(text: str, source_lang: str | None = None) -> bool:
    """Conservative entity quality filter.

    Multilingual mode relaxes the non-ASCII ratio because non-Latin scripts are
    valid entity tokens. We still reject digits, tiny strings, and overlong spans.
    """
    t = text.strip()
    if len(t) < 2 or t.isdigit():
        return False
    if len(t.split()) > 5:
        return False
    lang = (source_lang or "").lower()
    if lang in NON_LATIN_LANGS:
        return True
    non_ascii = sum(1 for c in t if ord(c) > 127)
    threshold = 0.6 if _multilingual_enabled() else 0.4
    return (non_ascii / max(len(t), 1)) < threshold


# Place-typed entity labels projected into nlp_places. spaCy en emits GPE/LOC;
# the HF xlm path maps everything location-shaped to LOC (_HF_NER_LABEL_MAP).
_PLACE_TYPES = {"GPE", "LOC"}
_PLACES_CAP = 10


def places_from_entities(entities) -> list[str]:
    """Project place-typed entities into the nlp_places payload.

    Pure hygiene mirror of the persons lane: lowercase + strip, drop 1-2 char
    tokens, case-insensitive dedupe preserving extraction order, cap at
    _PLACES_CAP per signal. Consumed by subject_geography.resolve_place_to_country
    (method "ner_place"), which is case-insensitive — lowercase is safe.
    """
    if not entities:
        return []
    seen: set[str] = set()
    places: list[str] = []
    for ent in entities:
        if ent.get("type") not in _PLACE_TYPES:
            continue
        name = str(ent.get("name") or "").strip().lower()
        if len(name) < 3 or name in seen:
            continue
        seen.add(name)
        places.append(name)
        if len(places) >= _PLACES_CAP:
            break
    return places


# ── Inference helpers ─────────────────────────────────────────────────────────
def _map_sentiment(label_scores: list[dict]) -> tuple[float, float]:
    """Map sentiment label/score list to (signed score [-5, 5], confidence [0, 1]).

    Both the English RoBERTa model and the multilingual XLM-R model expose the
    same `positive` / `neutral` / `negative` label set, so this mapping is shared.
    """
    lookup = {d["label"].lower(): d["score"] for d in label_scores}
    pos = lookup.get("positive", 0.0)
    neg = lookup.get("negative", 0.0)
    return round((pos * 5.0) + (neg * -5.0), 3), max(lookup.values()) if lookup else 0.0


def _extract_entities(nlp, headline: str, source_lang: str | None) -> list[dict]:
    seen: set[str] = set()
    entities = []
    for ent in nlp(headline).ents:
        if ent.label_ not in {"PERSON", "ORG", "NORP", "FAC", "GPE", "LOC", "EVENT"}:
            continue
        name = ent.text.strip()
        if not _entity_valid(name, source_lang) or name.lower() in seen:
            continue
        seen.add(name.lower())
        entities.append({"name": name, "type": ent.label_})
    return entities


def _entities_from_hf_spans(spans, source_lang: str | None) -> list[dict]:
    """Normalize one token-classification result into Atlas entity rows."""
    seen: set[str] = set()
    entities: list[dict] = []
    for sp in spans:
        etype = _HF_NER_LABEL_MAP.get(str(sp.get("entity_group", "")).upper())
        if not etype:
            continue
        name = str(sp.get("word", "")).replace("▁", " ").replace("##", "").strip()
        if not _entity_valid(name, source_lang) or name.lower() in seen:
            continue
        seen.add(name.lower())
        entities.append({"name": name, "type": etype})
    return entities


def _extract_entities_hf(ner, headline: str, source_lang: str | None) -> list[dict]:
    """Non-English NER for one headline, retained as the safe fallback path."""
    try:
        spans = ner(headline)
    except Exception:  # a single bad headline must not abort the batch
        return []
    return _entities_from_hf_spans(spans, source_lang)


def _extract_entities_hf_batch(
    ner,
    rows: Sequence[tuple[str, str | None]],
) -> list[list[dict]]:
    """Batch token classification while preserving per-headline degradation.

    The previous M1 path invoked the transformer once per headline. Hugging Face
    pipelines support list input, which amortizes tokenizer/model dispatch. If a
    backend rejects batching, fall back row by row so throughput work never
    becomes an availability regression.
    """
    if not rows:
        return []
    headlines = [headline for headline, _ in rows]
    try:
        batch_spans = ner(headlines, batch_size=NER_BATCH_SIZE)
    except Exception:
        logger.exception("NER batch failed; degrading to per-headline inference")
        return [
            _extract_entities_hf(ner, headline, source_lang)
            for headline, source_lang in rows
        ]
    if len(batch_spans) != len(rows):
        logger.warning(
            "NER batch result length mismatch (%d != %d); degrading to per-headline inference",
            len(batch_spans), len(rows),
        )
        return [
            _extract_entities_hf(ner, headline, source_lang)
            for headline, source_lang in rows
        ]
    return [
        _entities_from_hf_spans(spans, source_lang)
        for spans, (_, source_lang) in zip(batch_spans, rows)
    ]


def _detect_framing(clf, headline: str) -> str | None:
    result = clf(headline, FRAME_LABELS, truncation=True)
    if result["scores"][0] < FRAMING_MIN_SCORE:
        return None
    return LABEL_TO_DB[result["labels"][0]]


# ── Priority selection ───────────────────────────────────────────────────────
# Hybrid drain order (Option D, ADR-0004):
#   1) hot_lane — newest 24h first so today's incoming sources do not wait
#      behind the historical backlog.
#   2) sample_lane — stratified audit queue for country/source/topic coverage.
#   3) backlog_lane — bounded older control sample from the 15-day window.
#
# The unprocessed filter targets the column set we are actually writing this run.

HOT_LANE_SHARE = 0.65
SAMPLE_LANE_SHARE = 0.25
BACKLOG_LANE_SHARE = 0.10
STRATIFIED_REFRESH_POOL_LIMIT = 75_000

# Parallel-worker sharding (#184 throughput). Run N workers, each with a distinct
# SHARD_INDEX 0..N-1; the selector restricts each to its own disjoint partition
# of signal ids (id % N = K). Disjoint shards mean N workers never double-process
# the same row — no row locks, no held transactions (the NER batch is slow, so a
# FOR UPDATE SKIP LOCKED queue would hold a transaction open for minutes × N).
# id is a bigint serial, so the modulo distributes the backlog ~evenly.
SHARD_COUNT = max(1, int(os.getenv("NLP_WORKER_SHARD_COUNT", "1")))
SHARD_INDEX = int(os.getenv("NLP_WORKER_SHARD_INDEX", "0")) % SHARD_COUNT


def _validate_target_column(target_column: str) -> str:
    allowed = {
        "nlp_processed_at",
        "nlp_processed_at_xlm",
        "nlp_persons",
        "nlp_persons_xlm",
        "nlp_framing",
        "nlp_framing_xlm",
    }
    if target_column not in allowed:
        raise ValueError(f"Unsupported NLP target column: {target_column}")
    return target_column


def _priority_select_sql(target_column: str) -> str:
    """Return a mixed-priority selector for NLP batches.

    Performance note: each lane starts from a small created_at-indexed pool.
    We then sort only that pool by the priority expression (non-EN, API/social,
    high geo_confidence boosted). This avoids full-table sorts over 2M+ rows.
    """
    target_column = _validate_target_column(target_column)
    # Disjoint id-partition per worker (no-op when running a single worker).
    shard = f"AND (id % {SHARD_COUNT}) = {SHARD_INDEX}" if SHARD_COUNT > 1 else ""
    shard_s = f"AND (s.id % {SHARD_COUNT}) = {SHARD_INDEX}" if SHARD_COUNT > 1 else ""
    return f"""
        WITH budgets AS (
            SELECT
                GREATEST(1, CEIL($1 * {HOT_LANE_SHARE:.2f})::INT) AS hot_limit,
                GREATEST(1, CEIL($1 * {SAMPLE_LANE_SHARE:.2f})::INT) AS sample_limit,
                GREATEST(1, CEIL($1 * {BACKLOG_LANE_SHARE:.2f})::INT) AS backlog_floor
        ),
        hot_pool AS (
            SELECT id, headline, source_lang, source_family,
                   country_code, geo_confidence, timestamp, created_at
            FROM signals_v2
            WHERE {target_column} IS NULL
              AND headline IS NOT NULL AND LENGTH(headline) > 10
              AND created_at > NOW() - INTERVAL '24 hours'
              {shard}
            ORDER BY created_at DESC
            LIMIT 5000
        ),
        hot_lane AS (
            SELECT id, headline, source_lang, source_family,
                   country_code, geo_confidence, timestamp
            FROM hot_pool
            ORDER BY (
                EXTRACT(EPOCH FROM (NOW() - timestamp)) / 86400.0
                + CASE WHEN source_lang IS NOT NULL AND source_lang <> 'en' THEN -2 ELSE 0 END
                + CASE WHEN source_family IN ('api', 'social') THEN -1 ELSE 0 END
                + CASE WHEN geo_confidence IS NOT NULL AND geo_confidence > 0.8 THEN -0.5 ELSE 0 END
            ) ASC
            LIMIT (SELECT hot_limit FROM budgets)
        ),
        sample_lane AS (
            SELECT s.id, s.headline, s.source_lang, s.source_family,
                   s.country_code, s.geo_confidence, s.timestamp
            FROM nlp_sample_queue q
            JOIN signals_v2 s ON s.id = q.id
            WHERE s.{target_column} IS NULL
              AND s.headline IS NOT NULL AND LENGTH(s.headline) > 10
              AND s.id NOT IN (SELECT id FROM hot_lane)
              {shard_s}
            ORDER BY q.enqueued_at ASC
            LIMIT (SELECT sample_limit FROM budgets)
        ),
        backlog_pool AS (
            SELECT id, headline, source_lang, source_family,
                   country_code, geo_confidence, timestamp, created_at
            FROM signals_v2
            WHERE {target_column} IS NULL
              AND headline IS NOT NULL AND LENGTH(headline) > 10
              AND created_at <= NOW() - INTERVAL '24 hours'
              AND created_at > NOW() - INTERVAL '15 days'
              {shard}
            ORDER BY created_at DESC
            LIMIT 5000
        ),
        backlog_lane AS (
            SELECT id, headline, source_lang, source_family,
                   country_code, geo_confidence, timestamp
            FROM backlog_pool bp
            WHERE bp.id NOT IN (SELECT id FROM hot_lane)
              AND bp.id NOT IN (SELECT id FROM sample_lane)
            ORDER BY (
                EXTRACT(EPOCH FROM (NOW() - timestamp)) / 86400.0
                + CASE WHEN source_lang IS NOT NULL AND source_lang <> 'en' THEN -2 ELSE 0 END
                + CASE WHEN source_family IN ('api', 'social') THEN -1 ELSE 0 END
                + CASE WHEN geo_confidence IS NOT NULL AND geo_confidence > 0.8 THEN -0.5 ELSE 0 END
            ) ASC
            LIMIT GREATEST($1 - (SELECT COUNT(*) FROM hot_lane) - (SELECT COUNT(*) FROM sample_lane), 0)
        )
        SELECT * FROM hot_lane
        UNION ALL
        SELECT * FROM sample_lane
        UNION ALL
        SELECT * FROM backlog_lane
        LIMIT $1
    """


# Stratified sample refresh — populate nlp_sample_queue (issue #164, ADR-0004).
# Coarse buckets (country, theme_top, day) with K=3 per bucket keeps the queue
# under ~300K rows in the 15-day window.

def _stratified_refresh_sql(target_column: str) -> str:
    target_column = _validate_target_column(target_column)
    return f"""
    WITH recent_pool AS (
        SELECT
            id,
            country_code,
            source_family,
            signal_class,
            source_lang,
            themes,
            timestamp,
            geo_confidence
        FROM signals_v2
        WHERE created_at > NOW() - INTERVAL '15 days'
          AND {target_column} IS NULL
          AND headline IS NOT NULL
          AND LENGTH(headline) > 10
        ORDER BY created_at DESC
        LIMIT {STRATIFIED_REFRESH_POOL_LIMIT}
    ),
    stratified AS (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY
                    country_code,
                    COALESCE(source_family, 'unknown'),
                    COALESCE(signal_class, 'unknown'),
                    COALESCE(source_lang, 'unknown'),
                    LOWER(COALESCE(themes[1], '__none__')),
                    date_trunc('day', timestamp)
                ORDER BY timestamp DESC, geo_confidence DESC NULLS LAST
            ) AS rn
        FROM recent_pool
    )
    INSERT INTO nlp_sample_queue (id)
    SELECT id FROM stratified WHERE rn <= 3
    ON CONFLICT (id) DO NOTHING
    """

SAMPLE_CLEANUP_LIMIT = int(os.getenv("NLP_SAMPLE_CLEANUP_LIMIT", "500"))
SAMPLE_CLEANUP_TIMEOUT_SECONDS = float(os.getenv("NLP_SAMPLE_CLEANUP_TIMEOUT_SECONDS", "10"))

def _cleanup_drained_sample_queue_sql(target_column: str) -> str:
    target_column = _validate_target_column(target_column)
    return f"""
    WITH candidates AS (
        SELECT id
        FROM nlp_sample_queue q
        ORDER BY q.enqueued_at ASC
        LIMIT $1
    ),
    drained AS (
        SELECT c.id
        FROM candidates c
        JOIN signals_v2 s ON s.id = c.id
        WHERE s.{target_column} IS NOT NULL
    )
    DELETE FROM nlp_sample_queue q
    USING drained d
    WHERE q.id = d.id
    """


CLEANUP_DRAINED_SAMPLE_QUEUE_SQL = _cleanup_drained_sample_queue_sql("nlp_processed_at")


async def refresh_stratified_sample(conn, target_column: str = "nlp_processed_at") -> int:
    """Insert the latest stratified sample into nlp_sample_queue.

    Worker calls this every N cycles to keep coverage current. Returns the
    number of rows newly enqueued (best effort — Postgres does not expose the
    exact count after ON CONFLICT DO NOTHING without a RETURNING clause).
    """
    tag = await conn.execute(_stratified_refresh_sql(target_column))
    # tag looks like 'INSERT 0 12345'
    try:
        return int(tag.split()[-1])
    except (ValueError, IndexError):
        return 0


async def cleanup_drained_sample_queue(conn, target_column: str = "nlp_processed_at") -> int:
    """Remove ids from nlp_sample_queue once they have a transformer score."""
    tag = await conn.execute(
        _cleanup_drained_sample_queue_sql(target_column),
        SAMPLE_CLEANUP_LIMIT,
        timeout=SAMPLE_CLEANUP_TIMEOUT_SECONDS,
    )
    try:
        return int(tag.split()[-1])
    except (ValueError, IndexError):
        return 0


# ── Column targets ───────────────────────────────────────────────────────────
def _columns() -> dict[str, str]:
    """Return the column names the current mode reads/writes."""
    if _shadow_writes():
        return {
            "sentiment_target": "nlp_sentiment_xlm",
            "confidence_target": "nlp_confidence_xlm",
            "framing_target": "nlp_framing_xlm",
            "persons_target": "nlp_persons_xlm",
            "places_target": "nlp_places_xlm",
            "processed_at_target": "nlp_processed_at_xlm",
        }
    return {
        "sentiment_target": "nlp_sentiment",
        "confidence_target": "nlp_confidence",
        "framing_target": "nlp_framing",
        "persons_target": "nlp_persons",
        "places_target": "nlp_places",
        "processed_at_target": "nlp_processed_at",
    }


def processed_target_column() -> str:
    """Column that marks a row as processed in the current NLP mode."""
    return _columns()["processed_at_target"]


# ── Phase runners (each loads, runs, unloads its model) ─────────────────────
async def _run_sentiment_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    cols = _columns()
    rows = await conn.fetch(_priority_select_sql(cols["processed_at_target"]), limit)
    if not rows:
        return 0

    from transformers import pipeline as hf_pipeline
    model = SENTIMENT_MODEL_XLM if _multilingual_enabled() else SENTIMENT_MODEL_EN
    clf = hf_pipeline(
        "sentiment-analysis", model=model, tokenizer=model,
        top_k=None, truncation=True, max_length=512, device=-1,
    )
    now = datetime.now(timezone.utc)
    records = []
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        try:
            results = clf([r["headline"] for r in batch], batch_size=BATCH_SIZE)
            for row, res in zip(batch, results):
                score, conf = _map_sentiment(res)
                records.append((score, conf, now, row["id"]))
        except Exception as e:
            logger.warning("Sentiment batch error: %s", e)

    del clf
    gc.collect()

    if not dry_run and records:
        update_sql = (
            f"UPDATE signals_v2 "
            f"SET {cols['sentiment_target']}=$1, "
            f"    {cols['confidence_target']}=$2, "
            f"    {cols['processed_at_target']}=$3, "
            f"    nlp_model_version=$5, "
            f"    nlp_method=$6 "
            f"WHERE id=$4"
        )
        method = None if _shadow_writes() else "transformer"
        await conn.executemany(
            update_sql,
            [
                (score, conf, ts, sid, MODEL_VERSION_TAG, method)
                for (score, conf, ts, sid) in records
            ],
        )
    logger.info("Sentiment[%s]: %d signals (model=%s)", MODEL_VERSION_TAG, len(records), model)
    return len(records)


async def _run_ner_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    started_at = time.monotonic()
    cols = _columns()
    rows = await conn.fetch(_priority_select_sql(cols["persons_target"]), limit)
    if not rows:
        return 0

    import spacy

    def _load(name: str):
        try:
            return spacy.load(name, disable=["parser", "lemmatizer", "attribute_ruler"])
        except OSError:
            import subprocess
            import sys
            subprocess.run([sys.executable, "-m", "spacy", "download", name], check=True)
            return spacy.load(name, disable=["parser", "lemmatizer", "attribute_ruler"])

    nlp_en = _load(SPACY_MODEL_EN)
    # Non-English NER backend: xlm (Davlan HF token-classification, default — extracts
    # non-Latin with correct types) or spacy (xx_ent_wiki_sm, the legacy Latin-only path).
    nlp_xx = None
    hf_ner = None
    hf_cyr = None
    if _multilingual_enabled():
        if NLP_MULTILINGUAL_NER == "xlm":
            try:
                from transformers import pipeline as hf_pipeline
                hf_ner = hf_pipeline(
                    "token-classification", model=NER_MODEL_XLM,
                    aggregation_strategy="simple", device=-1,
                )
                # Cyrillic secondary (wikineural) — loaded ONLY if this batch has such a row.
                if any((r["source_lang"] or "").lower() in NLP_CYRILLIC_LANGS for r in rows):
                    try:
                        hf_cyr = hf_pipeline(
                            "token-classification", model=NER_MODEL_CYRILLIC,
                            aggregation_strategy="simple", device=-1,
                        )
                    except Exception:
                        logger.exception("cyrillic NER load failed — ru falls back to en")
            except Exception:
                logger.exception("xlm NER load failed — falling back to spaCy xx")
                nlp_xx = _load(SPACY_MODEL_XX)
        else:
            nlp_xx = _load(SPACY_MODEL_XX)

    records = []
    hf_rows = []
    cyrillic_rows = []
    for row in rows:
        lang = (row["source_lang"] or "").lower()
        non_en = bool(lang and lang != "en")
        if lang in NLP_CYRILLIC_LANGS and hf_cyr is not None:
            cyrillic_rows.append(row)
            continue
        elif non_en and hf_ner is not None and lang not in NLP_XLM_NER_SKIP_LANGS:
            hf_rows.append(row)
            continue
        else:
            nlp = nlp_xx if (non_en and nlp_xx is not None) else nlp_en
            entities = _extract_entities(nlp, row["headline"], lang or None)
        records.append(
            (json.dumps(entities), json.dumps(places_from_entities(entities)), row["id"])
        )

    for model, model_rows in ((hf_ner, hf_rows), (hf_cyr, cyrillic_rows)):
        if model is None or not model_rows:
            continue
        extracted = _extract_entities_hf_batch(
            model,
            [
                (row["headline"], (row["source_lang"] or "").lower() or None)
                for row in model_rows
            ],
        )
        records.extend(
            (json.dumps(entities), json.dumps(places_from_entities(entities)), row["id"])
            for row, entities in zip(model_rows, extracted)
        )

    del nlp_en
    if nlp_xx is not None:
        del nlp_xx
    if hf_ner is not None:
        del hf_ner
    if hf_cyr is not None:
        del hf_cyr
    gc.collect()

    if not dry_run and records:
        await conn.executemany(
            f"UPDATE signals_v2 "
            f"SET {cols['persons_target']}=$1::jsonb, {cols['places_target']}=$2::jsonb "
            f"WHERE id=$3",
            records,
        )
    logger.info(
        "NER[%s]: %d signals (spacy=%d, primary_hf=%d, cyrillic_hf=%d, duration=%.2fs)",
        MODEL_VERSION_TAG,
        len(records),
        len(records) - len(hf_rows) - len(cyrillic_rows),
        len(hf_rows),
        len(cyrillic_rows),
        time.monotonic() - started_at,
    )
    return len(records)


async def _run_framing_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    if SKIP_FRAMING:
        logger.info("Framing[%s]: skipped (NLP_SKIP_FRAMING=true)", MODEL_VERSION_TAG)
        return 0
    cols = _columns()
    effective_limit = min(limit, FRAMING_LIMIT_CAP) if FRAMING_LIMIT_CAP > 0 else limit
    rows = await conn.fetch(_priority_select_sql(cols["framing_target"]), effective_limit)
    if not rows:
        return 0

    from transformers import pipeline as hf_pipeline
    model = FRAMING_MODEL_XLM if _multilingual_enabled() else FRAMING_MODEL_EN
    clf = hf_pipeline("zero-shot-classification", model=model, device=-1)

    records = []
    for i in range(0, len(rows), FRAMING_BATCH_SIZE):
        batch = rows[i:i + FRAMING_BATCH_SIZE]
        for row in batch:
            try:
                frame = _detect_framing(clf, row["headline"])
                records.append((frame, row["id"]))
            except Exception as e:
                logger.warning("Framing error id=%s: %s", row["id"], e)

    del clf
    gc.collect()

    if not dry_run and records:
        await conn.executemany(
            f"UPDATE signals_v2 SET {cols['framing_target']}=$1 WHERE id=$2",
            records,
        )
    classified = sum(1 for f, _ in records if f is not None)
    logger.info(
        "Framing[%s]: %d signals (%d classified, %d ambiguous, model=%s)",
        MODEL_VERSION_TAG, len(records), classified, len(records) - classified, model,
    )
    return len(records)


# ── Public entry point for ingest_loop.py or worker ─────────────────────────
async def run_nlp_enrichment(
    limit: int = 500,
    phases: tuple[str, ...] = ("sentiment", "ner", "framing"),
) -> dict[str, int]:
    """Run the heavy NLP pass. `phases` selects which of the three heavy
    (load-run-unload) model passes execute. #184 P1.3: on the M1 the fast-lane
    already keeps nlp_sentiment ~100%, so an NER-only heavy pass (phases=("ner",))
    drops 2 of 3 model loads per cycle — the throughput lever for actor coverage.
    Default is all three so the Fly path is unchanged."""
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.warning("NLP enrichment skipped: DATABASE_URL not set")
        return {"sentiment": 0, "ner": 0, "framing": 0}

    counts = {"sentiment": 0, "ner": 0, "framing": 0}
    conn = await asyncpg.connect(db_url)
    try:
        if "sentiment" in phases:
            counts["sentiment"] = await _run_sentiment_phase(conn, limit, dry_run=False)
        if "ner" in phases:
            counts["ner"] = await _run_ner_phase(
                conn, _ner_phase_limit(limit), dry_run=False,
            )
        if "framing" in phases:
            counts["framing"] = await _run_framing_phase(conn, limit, dry_run=False)
    except Exception:
        logger.exception("NLP enrichment cycle failed")
    finally:
        await conn.close()
    return counts


# ── CLI for Mac backfill ──────────────────────────────────────────────────────
async def _cli_run(limit: int, dry_run: bool, phase: str) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        if phase in ("all", "sentiment"):
            await _run_sentiment_phase(conn, limit, dry_run)
        if phase in ("all", "ner"):
            await _run_ner_phase(conn, limit, dry_run)
        if phase in ("all", "framing"):
            await _run_framing_phase(conn, limit, dry_run)
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Atlas NLP pipeline — backfill tool")
    parser.add_argument("--limit", type=int, default=500, help="Signals per phase per run")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase", choices=["all", "sentiment", "ner", "framing"], default="all")
    args = parser.parse_args()
    asyncio.run(_cli_run(args.limit, args.dry_run, args.phase))


if __name__ == "__main__":
    main()
