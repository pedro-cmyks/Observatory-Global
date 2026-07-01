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

## Execution — steps 1–3 SHIPPED (offline, safe), step 4 gated on Pedro (2026-07-01)
- **Step 1 (code):** `nlp_pipeline.py` — `_extract_entities_hf` (Davlan HF token-classification,
  label map PER/ORG/LOC → PERSON/ORG/LOC, DATE/MISC dropped); flag `NLP_MULTILINGUAL_NER=xlm`
  (default) routes non-English to it, `en` stays `en_core_web_sm`. DORMANT — only fires when
  `NLP_MULTILINGUAL_MODE` ∈ {shadow,on}; mode is OFF, so zero behaviour change until the flip.
- **Step 2 (offline eval, `scripts/eval_multilingual_ner.py`, DeepSeek-judged):** on real
  non-English headlines, xlm vs the current `xx_ent_wiki_sm`:

  | lang | xx extract-rate | xlm extract-rate | xlm precision (judged) |
  |---|---:|---:|---:|
  | zh | 0% | 100% | 100% (11/11) |
  | fa | 12.5% | 100% | 91.7% (11/12) |
  | ko | 0% | 37.5% | 100% (4/4) |
  | ar | 25% | 87.5% | 70.6% (12/17) |
  | pt | 87.5% | 100% | 84.6% (11/13) |
  | de | 50% | 75% | 85.7% (6/7) |
  | ru | 0% | 12.5% | **0% (0/3)** |
  | **overall** | — | — | **82.1%** |

  Huge recall lift for non-Latin (zh/fa/ar/ko were ~0 with `xx`) at 70–100% precision. **ru was the
  one gap** — Davlan HRL has no Russian; Cyrillic transfer fails (0/3).
  → **ru gap CLOSED (2026-07-01, task #2):** `Babelscape/wikineural-multilingual-ner` covers
  Russian — measured **100% extract, 87.5% precision (14/16)** on ru headlines (vs Davlan 0/3).
  The pipeline now routes Cyrillic langs (`NLP_CYRILLIC_LANGS=ru`) to wikineural, everything-else-
  non-English to Davlan, English to `en_core_web_sm` — a lazy second model loaded only when a ru
  row is present (bounds M1 memory). No single model covers everything (Davlan = non-Latin
  transfer; wikineural = ru + European), so the two-model route is the measured optimum. wikineural
  pre-baked in mlvenv. Follow-up: validate uk/bg (same family, untested).
- **Step 3 (pre-bake):** `protobuf 7.35.1` + `sentencepiece` installed in mlvenv (persists — it IS
  the M1 worker venv); Davlan model cached (~1.1GB). `nlp_pipeline.py` synced to AtlasLocalWorker
  (dormant).
- **Step 4 (DONE 2026-07-01, Pedro's go):** flipped `ATLAS_NLP_MULTILINGUAL=on` in the M1 `.env`
  (runner maps → `NLP_MULTILINGUAL_MODE=on`). **Discovery:** the M1 NLP fleet had been DOWN since
  06-29 (SIGTERM, never reloaded) — so NER was starved AND the flip required (re)starting it.
  Bootstrapped `com.atlas.nlp-fleet`; shadow `--once` validated live first (Catalan/Norwegian NER
  correct), then flipped to on. **VERIFIED:** production non-English `nlp_persons` writing
  (`NER[xlm-v1]`; it/es/fr/ko/tr in the first minutes; ko = non-Latin via Davlan). **Memory guard:**
  multilingual workers are heavier than the EN-only ones `burst=2` was sized for → changed the
  supervisor floor `max(2,…)`→`max(1,…)` + set `ATLAS_NLP_BURST_WORKERS=1` (the 8GB M1 crashed at
  load 177 once; 54% free with 1 worker). Reversible (`ATLAS_NLP_MULTILINGUAL=off` + restart).
  Follow-up: throughput is lower under multilingual (per-cycle model loads ~300s); model-caching
  across cycles + a bump back to burst=2 once RAM is confirmed comfortable are the optimisations.

## Post-flip live monitoring (2026-07-01, task #5) — honest state
The flip WRITES production non-English `nlp_persons`, but two findings temper the immediate payoff:
1. **Surface payoff ACCUMULATES, not instant.** After ~30 min only ~26 non-English signals were
   NER'd (gentle/burst=1 multilingual rate ~300s/cycle). The served `key_subjects` (e.g. prod
   `/country/IT`) still show the OLD GDELT-unverified pool ("margo evardson unsplash", "benvenuti
   lapresse sipa" = photo credits typed as people) — the large existing pool dominates the
   window-aggregation until the verified NER accumulates over hours/days. The flip is correct but
   its surface value is a slow drain, not a switch.
2. **Live NER noise on sports / entity-dense headlines.** Spot-check showed `England`→PERSON,
   `LaLiga`→PERSON, `il motto…`→PERSON on ⚽ football headlines — worse than the 82% general-news
   eval, because (a) sports headlines are entity-dense/ambiguous and (b) at SERVING NER-wins-over-
   gazetteer (`merge_entity_rows`), so a NER mistype of a known place/org is NOT corrected. News
   headlines are fine; sports (a damped lane) is the weak spot.

**Follow-ups (Track A, prioritised):** (a) at serving, prefer the gazetteer type when a NER-PERSON
exact-matches a known place/org (fixes England→PERSON leaking as verified) — a `subjects.py`
change; (b) the existing GDELT non-English subject noise (photo credits) is what verified NER
replaces AS IT ACCUMULATES — re-check the surfaces in a day; (c) model-caching + burst=2 to speed
the drain.
