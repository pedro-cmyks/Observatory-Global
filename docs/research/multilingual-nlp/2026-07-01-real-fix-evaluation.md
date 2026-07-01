# Multilingual NLP — the "real fix" evaluation (measure-first)

**Date:** 2026-07-01 · **Trigger:** Pedro — "evalúa el fix real (modelo multilingüe propio + env)
y cómo se conecta con el motor." · **Prior state:** 2026-06-25 concluded multilingual NER on M1 was
"not worth it / a scoped task" (two blockers). **This evaluation FLIPS that conclusion** — both
blockers dissolve; the fix is cheap + high-value. Every claim below is measured on the M1.

## The 2026-06-25 blockers — re-measured, both dissolve

### Blocker A ("xlm sentiment crashes the M1 env") → it was a MISSING pip package
Root cause was NOT a Python-3.14 / transformers-5.9 incompatibility. The real error:
`SentencePieceExtractor requires the protobuf library but it was not found` → transformers falls
back to a broken TikToken extractor → `ValueError`. **Fix: `pip install protobuf` (mlvenv).**
After it, `cardiffnlp/twitter-xlm-roberta-base-sentiment` loads as `XLMRobertaTokenizer` and
tokenizes Persian correctly (`ایران آب` → `['▁ایران','▁آب']`). Multilingual SENTIMENT then produces
sane output:
- ar "انفجار ضخم يقتل العشرات" (huge blast kills dozens) → **negative 0.89** ✓
- fa "ایران و آمریکا به توافق رسیدند" (Iran-US reach agreement) → neutral 0.44 (defensible)
- zh economic-growth headline → negative 0.41 (wrong but low-conf; twitter-trained model)

vs the current state (multilingual OFF): the ENGLISH sentiment model runs on all non-English text →
100% populated but noise.

### Blocker B ("multilingual NER doesn't work") → they only tried the FREE spaCy `xx_ent_wiki_sm`
Measured on real DB headlines, `xx_ent_wiki_sm` is worse-than-useless for non-Latin:
- fa: returns `[]` (nothing).
- ar "روسيا تنزل..." → روسيا (Russia) labeled **PER** (wrong type); نبض/كأس (common nouns) → ORG.

A proper xlm-roberta token-classification model — **`Davlan/xlm-roberta-base-ner-hrl`** — works:
- ar روسيا → **LOC** (correct type); أوروبا → LOC (Europe ✓).
- fa یزد → **LOC** (Yazd ✓) — extracted via CROSS-LINGUAL TRANSFER even though the model isn't
  officially trained on Persian.

### Throughput — NOT a blocker
Davlan on M1 MPS: **26.6/s single (~95K/hr), 92.7/s batched (~333K/hr)** — far above ingest
(~6.4K/hr). The transformer NER is faster than the current mindful spaCy rate (~3.5K/hr, which is
throttling + per-cycle model load, not model speed).

## Verdict: the real fix is CHEAP + VIABLE (not a hard scoped task)
1. `pip install protobuf sentencepiece` in mlvenv (DONE, additive/harmless) — unblocks xlm sentiment.
2. Swap the non-English NER path `xx_ent_wiki_sm` → `Davlan/xlm-roberta-base-ner-hrl` (English keeps
   the fast `en_core_web_sm`).
3. Flip `NLP_MULTILINGUAL_MODE=on` (or `ATLAS_NLP_MULTILINGUAL=on`) on the M1 worker ONLY. The Fly
   worker stays EN-only light — the #184 embed-contention (heavy models must not co-run with the
   embed service) is why; the M1 has no embed to starve.

## How it connects to the engine (what verified non-English subjects unlock)
```
nlp_pipeline (M1, multilingual on)
  → signals_v2.nlp_persons/nlp_orgs JSONB  (non-English, currently EMPTY)
    → subjects.py build_key_subjects / classify_subject  (NER-typed, verified=true)
      → key_subjects served in /api/v2/focus + /country
        → CountryBrief / EntityPanel / ThemeDetail "Key Subjects"
           FLIP non-English subjects unverified→verified (today all gazetteer=unverified)
```
Direct payoffs, all on work already shipped:
- **Diversity / Voice Mix (WAVE-N, self_voice):** a country's OWN-LANGUAGE coverage gains VERIFIED
  real entities instead of gazetteer guesses — the "covered by its own press" story gets teeth.
- **#150 non-Latin geo-tagging:** the NER `LOC` entities (Yazd, Russia) are the real geo path the
  gazetteer-only cut (high-precision/low-recall) was a stopgap for — the "clean #150 end state."
- **#176/#184 typed subjects:** flips the standing `unverified=true` on non-English subjects across
  all three surfaces — the win the Fly box could never do.
- **Unified engine:** indirect — NER enriches subjects/roles, does not assign topics; the event/
  movement work is untouched.

## Cost / risk
- One-time ~1.1GB model download on M1 (pre-bake into mlvenv, offline flag).
- `nlp_pipeline` change: a transformers NER pipeline for non-English + a label map
  (Davlan PER/ORG/LOC/DATE → PERSON/ORG/GPE-LOC). Bounded, one module.
- protobuf must PERSIST: add to the mlvenv requirements + AtlasLocalWorker sync.
- Prod-affecting: non-English signals change (verified subjects + real sentiment). Flip on M1 with
  monitoring; reversible (flag back to off). Lesson (#184): verify embed health — but embed is on
  Fly, M1 doesn't touch it, so the classic contention does not apply.

## Recommendation
Implement. The evaluation removes the two reasons it was parked. Suggested order: (1) code the
`nlp_pipeline` non-English NER swap + label map, (2) test offline on a labeled non-English sample
(precision vs the gazetteer), (3) pre-bake protobuf + the model into mlvenv, (4) flip multilingual
on the M1 worker, monitor throughput + a spot-check of verified non-English subjects on a surface.
