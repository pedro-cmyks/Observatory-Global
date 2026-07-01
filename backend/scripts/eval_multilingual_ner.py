"""Offline eval: multilingual NER swap (Davlan xlm-roberta) vs the current path (xx_ent_wiki_sm).

Step 2 of the multilingual real-fix (docs/research/multilingual-nlp/2026-07-01-real-fix-evaluation.md).
Measures, on real non-English headlines, whether the new xlm-roberta NER extracts entities the
current spaCy `xx_ent_wiki_sm` path misses, AND at what precision (DeepSeek-judged — the project's
label-free judging method, since there is no non-English NER gold).

Reports per language: extraction rate (xx vs xlm) + xlm entity precision (real entity + right
type, judged). Read-only. Usage (from backend/, mlvenv):  python -m scripts.eval_multilingual_ner
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

_LANGS = ["fa", "ar", "zh", "ru", "ko", "de", "pt"]
_PER_LANG = 8


async def _sample(n_per: int):
    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (source_lang, headline) source_lang, headline
            FROM signals_v2
            WHERE source_lang = ANY($1::text[]) AND headline IS NOT NULL AND length(headline) >= 25
              AND timestamp > NOW() - INTERVAL '168 hours'
            ORDER BY source_lang, headline, timestamp DESC
            """,
            _LANGS,
        )
    finally:
        await conn.close()
    by: dict = {}
    for r in rows:
        by.setdefault(r["source_lang"], [])
        if len(by[r["source_lang"]]) < n_per:
            by[r["source_lang"]].append(r["headline"])
    return by


async def _judge(headline: str, lang: str, ents: list[dict], key: str) -> list[bool]:
    """DeepSeek: is each (name,type) a REAL entity of that type for this headline?"""
    if not ents:
        return []
    import httpx
    listing = "\n".join(f"{i}. {e['name']} [{e['type']}]" for i, e in enumerate(ents))
    prompt = (
        f"Headline (lang={lang}): {headline}\n\n"
        f"Extracted entities (PERSON/ORG/LOC):\n{listing}\n\n"
        "For EACH numbered entity, is it a REAL named entity of that type actually present in the "
        "headline (not a common noun, not a wrong type)? Reply ONLY a JSON array of booleans in "
        "order, e.g. [true,false,true]."
    )
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post("https://api.deepseek.com/chat/completions",
                             headers={"Authorization": f"Bearer {key}"}, json=body)
            txt = r.json()["choices"][0]["message"]["content"]
        s = txt[txt.index("["): txt.rindex("]") + 1]
        out = json.loads(s)
        return [bool(x) for x in out][: len(ents)]
    except Exception as e:  # noqa: BLE001
        print(f"  judge failed: {e}", file=sys.stderr)
        return [False] * len(ents)


async def main() -> int:
    from enrichment.nlp_pipeline import _extract_entities, _extract_entities_hf
    import spacy
    from transformers import pipeline as hf_pipeline

    key = os.environ["DEEPSEEK_API_KEY"]
    print("loading models…", file=sys.stderr)
    nlp_xx = spacy.load("xx_ent_wiki_sm", disable=["parser", "lemmatizer", "attribute_ruler"])
    hf_ner = hf_pipeline("token-classification", model="Davlan/xlm-roberta-base-ner-hrl",
                         aggregation_strategy="simple", device=-1)

    by = await _sample(_PER_LANG)
    per_lang: dict = {}
    all_prec = []
    for lang, heads in by.items():
        xx_hits = xlm_hits = 0
        judged_ok = judged_tot = 0
        for h in heads:
            xx = _extract_entities(nlp_xx, h, lang)
            xlm = _extract_entities_hf(hf_ner, h, lang)
            xx_hits += 1 if xx else 0
            xlm_hits += 1 if xlm else 0
            if xlm:
                verd = await _judge(h, lang, xlm, key)
                judged_ok += sum(verd)
                judged_tot += len(verd)
        prec = round(100 * judged_ok / judged_tot, 1) if judged_tot else None
        if prec is not None:
            all_prec.append((judged_ok, judged_tot))
        per_lang[lang] = {
            "n": len(heads),
            "xx_extract_rate_pct": round(100 * xx_hits / len(heads), 1),
            "xlm_extract_rate_pct": round(100 * xlm_hits / len(heads), 1),
            "xlm_entities_judged": judged_tot,
            "xlm_precision_pct": prec,
        }
        print(f"  {lang}: xx {per_lang[lang]['xx_extract_rate_pct']}% vs xlm "
              f"{per_lang[lang]['xlm_extract_rate_pct']}% extract; xlm precision {prec}% "
              f"({judged_ok}/{judged_tot})", file=sys.stderr)

    ok = sum(a for a, _ in all_prec); tot = sum(b for _, b in all_prec)
    report = {
        "per_lang": per_lang,
        "overall_xlm_precision_pct": round(100 * ok / tot, 1) if tot else None,
        "overall_xlm_entities": tot,
    }
    print("\n" + json.dumps(report, indent=2))
    out = "../docs/research/multilingual-nlp/2026-07-01-ner-swap-eval.json"
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(report, open(out, "w"), indent=2)
        print(f"wrote {out}", file=sys.stderr)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
