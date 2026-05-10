"""
Atlas NLP Pipeline — Phase 1 + 2 + 3: Sentiment, Entity Extraction & Framing

Applies to ALL signals with valid headlines (GDELT + RSS + ReliefWeb).
No source filter — everything gets normalized to the same NLP annotations.

Two execution modes:
  CLI (Mac backfill):  python -m enrichment.nlp_pipeline [--limit N] [--dry-run]
  Ingest hook (Fly):   await run_nlp_enrichment(limit=500)  ← called from ingest_loop.py

Memory pattern on Fly (985MB machine):
  Load sentiment → run → del + gc → load NER → run → del + gc → load framing → run → del + gc
  Peak per phase: ~500MB. Never loads all models simultaneously.
"""
import argparse
import asyncio
import gc
import json
import logging
import os
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
FRAMING_MODEL   = "cross-encoder/nli-distilroberta-base"
BATCH_SIZE         = 20
FRAMING_BATCH_SIZE = 8
FRAMING_MIN_SCORE  = 0.35

FRAME_LABELS = [
    "conflict escalation",
    "diplomatic resolution",
    "humanitarian crisis",
    "economic impact",
    "political domestic",
    "information warfare",
]
LABEL_TO_DB = {
    "conflict escalation":   "conflict_escalation",
    "diplomatic resolution": "diplomatic_resolution",
    "humanitarian crisis":   "humanitarian_crisis",
    "economic impact":       "economic_impact",
    "political domestic":    "political_domestic",
    "information warfare":   "information_warfare",
}


# ── Filters ──────────────────────────────────────────────────────────────────
def _entity_valid(text: str) -> bool:
    t = text.strip()
    if len(t) < 3 or t.isdigit():
        return False
    non_ascii = sum(1 for c in t if ord(c) > 127)
    if (non_ascii / len(t)) >= 0.4:
        return False
    if len(t.split()) > 5:
        return False
    return True


# ── Inference helpers ─────────────────────────────────────────────────────────
def _map_sentiment(label_scores: list[dict]) -> tuple[float, float]:
    lookup = {d["label"].lower(): d["score"] for d in label_scores}
    pos = lookup.get("positive", 0.0)
    neg = lookup.get("negative", 0.0)
    return round((pos * 5.0) + (neg * -5.0), 3), max(lookup.values())


def _extract_entities(nlp, headline: str) -> list[dict]:
    seen: set[str] = set()
    entities = []
    for ent in nlp(headline).ents:
        if ent.label_ not in {"PERSON", "ORG", "NORP", "FAC", "GPE", "LOC"}:
            continue
        name = ent.text.strip()
        if not _entity_valid(name) or name.lower() in seen:
            continue
        seen.add(name.lower())
        entities.append({"name": name, "type": ent.label_})
    return entities


def _detect_framing(clf, headline: str) -> str | None:
    result = clf(headline, FRAME_LABELS, truncation=True)
    if result["scores"][0] < FRAMING_MIN_SCORE:
        return None
    return LABEL_TO_DB[result["labels"][0]]


# ── Phase runners (each loads, runs, unloads its model) ─────────────────────
async def _run_sentiment_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    rows = await conn.fetch(
        """
        SELECT id, headline FROM signals_v2
        WHERE nlp_processed_at IS NULL
          AND headline IS NOT NULL AND LENGTH(headline) > 10
        ORDER BY timestamp DESC LIMIT $1
        """,
        limit,
    )
    if not rows:
        return 0

    from transformers import pipeline as hf_pipeline
    clf = hf_pipeline(
        "sentiment-analysis", model=SENTIMENT_MODEL, tokenizer=SENTIMENT_MODEL,
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

    del clf; gc.collect()

    if not dry_run and records:
        await conn.executemany(
            "UPDATE signals_v2 SET nlp_sentiment=$1, nlp_confidence=$2, nlp_processed_at=$3 WHERE id=$4",
            records,
        )
    logger.info("Sentiment: %d signals", len(records))
    return len(records)


async def _run_ner_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    rows = await conn.fetch(
        """
        SELECT id, headline FROM signals_v2
        WHERE nlp_persons IS NULL
          AND headline IS NOT NULL AND LENGTH(headline) > 10
        ORDER BY timestamp DESC LIMIT $1
        """,
        limit,
    )
    if not rows:
        return 0

    import spacy
    try:
        nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler"])
    except OSError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler"])

    records = []
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        for row, doc in zip(batch, nlp.pipe([r["headline"] for r in batch], batch_size=BATCH_SIZE)):
            entities = _extract_entities(nlp, row["headline"])
            records.append((json.dumps(entities), row["id"]))

    del nlp; gc.collect()

    if not dry_run and records:
        await conn.executemany(
            "UPDATE signals_v2 SET nlp_persons=$1::jsonb WHERE id=$2",
            records,
        )
    logger.info("NER: %d signals", len(records))
    return len(records)


async def _run_framing_phase(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    rows = await conn.fetch(
        """
        SELECT id, headline FROM signals_v2
        WHERE nlp_framing IS NULL
          AND headline IS NOT NULL AND LENGTH(headline) > 10
        ORDER BY timestamp DESC LIMIT $1
        """,
        limit,
    )
    if not rows:
        return 0

    from transformers import pipeline as hf_pipeline
    clf = hf_pipeline("zero-shot-classification", model=FRAMING_MODEL, device=-1)

    records = []
    for i in range(0, len(rows), FRAMING_BATCH_SIZE):
        batch = rows[i:i + FRAMING_BATCH_SIZE]
        for row in batch:
            try:
                frame = _detect_framing(clf, row["headline"])
                records.append((frame, row["id"]))
            except Exception as e:
                logger.warning("Framing error id=%s: %s", row["id"], e)

    del clf; gc.collect()

    if not dry_run and records:
        await conn.executemany(
            "UPDATE signals_v2 SET nlp_framing=$1 WHERE id=$2",
            records,
        )
    classified = sum(1 for f, _ in records if f is not None)
    logger.info("Framing: %d signals (%d classified, %d ambiguous)", len(records), classified, len(records) - classified)
    return len(records)


# ── Public entry point for ingest_loop.py ────────────────────────────────────
async def run_nlp_enrichment(limit: int = 500) -> None:
    """
    Called from ingest_loop.py after each GDELT cycle.
    Processes up to `limit` signals per phase (sentiment, NER, framing).
    Models loaded and unloaded per phase to stay within 985MB Fly RAM.
    """
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.warning("NLP enrichment skipped: DATABASE_URL not set")
        return

    conn = await asyncpg.connect(db_url)
    try:
        await _run_sentiment_phase(conn, limit, dry_run=False)
        await _run_ner_phase(conn, limit, dry_run=False)
        await _run_framing_phase(conn, limit, dry_run=False)
    except Exception:
        logger.exception("NLP enrichment cycle failed")
    finally:
        await conn.close()


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
    parser.add_argument("--limit",   type=int, default=500, help="Signals per phase per run")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--phase",   choices=["all", "sentiment", "ner", "framing"], default="all")
    args = parser.parse_args()
    asyncio.run(_cli_run(args.limit, args.dry_run, args.phase))


if __name__ == "__main__":
    main()
