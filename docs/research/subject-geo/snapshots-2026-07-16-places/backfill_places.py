"""Bounded nlp_places backfill for the signals the serving inference READS (#238 D).

Scope: EXACTLY the distinct receipt signal ids served by the live front page
(threads_fresh.json, byte-identical to the 2026-07-16 baseline window) that
have nlp_places IS NULL. Idempotent: the UPDATE carries `AND nlp_places IS
NULL`; rows already annotated are never touched. Never writes nlp_persons.

Routing mirrors the production fleet (enrichment/nlp_pipeline, multilingual
mode 'on'): en -> spaCy en_core_web_sm; Cyrillic langs (ru) -> wikineural;
other non-en -> Davlan xlm-roberta-ner-hrl. Places projected with the SAME
places_from_entities hygiene (imported). One deliberate deviation, noted in
the artifact: headlines are HTML-entity-decoded before NER (stored GDELT
headlines carry &#x...; entities; the pipeline feeds them raw today).

Run: taskpolicy -b mlvenv python backfill_places.py
"""
from __future__ import annotations

import asyncio
import gc
import html
import json
import os
import sys
import time

os.environ.setdefault("NLP_MULTILINGUAL_MODE", "on")

sys.path.insert(0, "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend")
from enrichment.nlp_pipeline import (  # noqa: E402
    NER_MODEL_CYRILLIC,
    NER_MODEL_XLM,
    NLP_CYRILLIC_LANGS,
    _extract_entities,
    _extract_entities_hf_batch,
    places_from_entities,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def env(key: str) -> str | None:
    for line in open("/Users/pedro/AtlasLocalWorker/.env"):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def decode(value) -> str:
    text = str(value or "")
    for _ in range(3):
        d = html.unescape(text)
        if d == text:
            break
        text = d
    return text


async def fetch_targets():
    import asyncpg
    ids = sorted({
        int(e["id"])
        for t in json.load(open(os.path.join(HERE, "threads_fresh.json")))["threads"]
        if t.get("evidence_samples")
        for e in t["evidence_samples"]
    })
    conn = await asyncpg.connect(env("DATABASE_URL"), statement_cache_size=0)
    rows = await conn.fetch(
        "SELECT id, headline, source_lang FROM signals_v2 "
        "WHERE id = ANY($1::bigint[]) AND nlp_places IS NULL",
        ids,
    )
    await conn.close()
    return [dict(r) for r in rows]


async def write_places(records: list[tuple[str, int]]):
    import asyncpg
    conn = await asyncpg.connect(env("DATABASE_URL"), statement_cache_size=0)
    written = 0
    B = 100
    for i in range(0, len(records), B):
        batch = records[i:i + B]
        await conn.executemany(
            "UPDATE signals_v2 SET nlp_places=$1::jsonb "
            "WHERE id=$2 AND nlp_places IS NULL",
            batch,
        )
        written += len(batch)
        print(f"  wrote {written}/{len(records)}")
    await conn.close()


def main():
    t0 = time.time()
    rows = asyncio.run(fetch_targets())
    print(f"targets lacking nlp_places: {len(rows)}")
    by_lang: dict[str, int] = {}
    for r in rows:
        by_lang[(r["source_lang"] or "").lower() or "(null)"] = by_lang.get((r["source_lang"] or "").lower() or "(null)", 0) + 1
    print("by lang:", dict(sorted(by_lang.items(), key=lambda x: -x[1])))

    en_rows, cyr_rows, xlm_rows = [], [], []
    for r in rows:
        lang = (r["source_lang"] or "").lower()
        if lang and lang != "en":
            (cyr_rows if lang in NLP_CYRILLIC_LANGS else xlm_rows).append(r)
        else:
            en_rows.append(r)

    ledger = []  # per-signal extraction record for the artifact
    records: list[tuple[str, int]] = []

    # Phase 1: spaCy en
    import spacy
    nlp_en = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler"])
    for r in en_rows:
        head = decode(r["headline"])
        ents = _extract_entities(nlp_en, head, (r["source_lang"] or "").lower() or None)
        places = places_from_entities(ents)
        records.append((json.dumps(places), r["id"]))
        ledger.append({"id": r["id"], "lang": r["source_lang"], "model": "spacy-en", "places": places})
    del nlp_en
    gc.collect()
    print(f"spaCy en done: {len(en_rows)} rows, {time.time()-t0:.0f}s")

    # Phase 2 + 3: HF models, one at a time (pipeline memory pattern)
    from transformers import pipeline as hf_pipeline
    for model_name, model_rows, tag in (
        (NER_MODEL_XLM, xlm_rows, "davlan-xlm"),
        (NER_MODEL_CYRILLIC, cyr_rows, "wikineural"),
    ):
        if not model_rows:
            continue
        model = hf_pipeline("token-classification", model=model_name,
                            aggregation_strategy="simple", device=-1)
        extracted = _extract_entities_hf_batch(
            model,
            [(decode(r["headline"]), (r["source_lang"] or "").lower() or None) for r in model_rows],
        )
        for r, ents in zip(model_rows, extracted):
            places = places_from_entities(ents)
            records.append((json.dumps(places), r["id"]))
            ledger.append({"id": r["id"], "lang": r["source_lang"], "model": tag, "places": places})
        del model
        gc.collect()
        print(f"{tag} done: {len(model_rows)} rows, {time.time()-t0:.0f}s")

    nonempty = sum(1 for l in ledger if l["places"])
    print(f"extraction: {nonempty}/{len(ledger)} signals got >=1 place")
    json.dump(ledger, open(os.path.join(HERE, "backfill_ledger.json"), "w"),
              ensure_ascii=False, indent=1)

    asyncio.run(write_places(records))
    print(f"DONE in {time.time()-t0:.0f}s — {len(records)} rows updated (guarded nlp_places IS NULL)")


if __name__ == "__main__":
    main()
