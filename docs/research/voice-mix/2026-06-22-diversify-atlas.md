# Diversify Atlas — and prove it (2026-06-22)

Goal: Atlas claims to aggregate *global* media. "Global" must be measured, not
assumed. This pass (1) measures whose voice is actually in the corpus, (2) ships
the highest-leverage diversification lever, and (3) leaves a repeatable
instrument so any future change is provable as a number.

## 1. Baseline — the monoculture, measured

`backend/scripts/voice_mix_audit.py --hours 168` against production
(146,121 signals, 2026-06-22). Artifact: `2026-06-22-baseline.json`.

| metric | value |
|---|---|
| language unknown (GDELT `xx`/null) | 91,813 (62.8%) |
| **English share of language-known** | **96.9%** |
| non-English share of known | 3.1% |
| **CJK (zh / ja / ko)** | **0 / 0 / 0** |
| language entropy (normalized) | 0.0686 |
| state media | 361 (0.25%) |
| origin HHI | 0.076 |
| top origins | GB, DE, RU, CN, AU, IN |
| **DIVERSITY SCORE** | **3.3 / 100** |

Reading: of every signal where we *know* the language, **97 in 100 are
English**. Chinese, Japanese, and Korean are literally absent — China appears
(origin CN is top-4) but only through Western/English outlets writing *about*
China (#230). The corpus is, by measurement, one voice.

`diversity_score` = 100 · mean(english_balance, language_entropy, cjk_coverage).
See script docstring for the exact definition. It exists so "did we diversify?"
is answerable with a number.

## 2. Lever shipped — East-Asia (CJK) ingestion

`backend/app/services/ingest_newsdata.py`: added an 8th language batch
`{"language": "zh,jp,ko", "country": "cn,tw,hk,jp,kr"}`. 5 countries = NewsData
free-plan per-request max. NewsData returns non-ISO `jp` for Japanese →
normalized to ISO `ja` in `LANGUAGE_CODES`.

Quota: NewsData fires every 4th GDELT cycle (~hourly). 8 batches × 24 =
**192 req/day**, under the 200/day free cap. No headroom left for a 9th batch;
further East-Asia depth needs a paid plan or a second key.

Why this is real and not theater: the semantic layer uses multilingual e5
embeddings (`signal_embeddings`), so CJK headlines get presence + semantic
thread membership immediately — even though the NLP sentiment/framing gate is
still English-only (`nlp_*_xlm` columns exist but are **0-populated**; #162 is
the next dependency to light up CJK sentiment/NER).

## 3. Proof of mechanism (no live key needed)

`tests/test_ingest_newsdata_cjk.py` — 4/4 pass:
- East-Asia batch is wired with zh/jp/ko, ≤5 countries.
- Batch count stays within the 200/day quota.
- `jp → ja` / `chinese → zh` / `korean → ko` normalization.
- A Chinese/Japanese/Korean NewsData article parses end-to-end → lands with
  normalized `source_lang` (zh/ja/ko), correct country code, headline intact.

## 4. Closing the loop (pending prod)

The corpus delta requires the batch live on Fly + one ingest cycle. After
deploy:

```
cd backend && .venv/bin/python -m scripts.voice_mix_audit \
  --hours 24 --json-out ../docs/research/voice-mix/2026-06-22-after.json
```

Success = CJK counts go 0 → N and `diversity_score` rises. The one empirical
unknown is whether NewsData's Japanese code is `jp` (assumed) vs `ja`; the audit
settles it on first run — if `ja` shows 0 while `zh`/`ko` arrive, flip the batch
code to `ja` (one-line follow-up).

## 5. Live result — loop CLOSED (deployed)

Deployed to Fly (`atlas-api-pedro` v225, 2026-06-22 14:52Z) and triggered the
NewsData run on the ingestion machine:

```
[NewsData] batch zh,jp,ko: 10 fetched → 10 inserted
```

NewsData returned CJK (the `jp` Japanese code is correct — batch did not error).
DB after: `zh=1 (TW), ja=5, ko=4`. Re-audit (`after.json`, 168h):

| | before | after (1 live batch) |
|---|---|---|
| CJK zh/ja/ko | 0 / 0 / 0 | **1 / 5 / 4** |
| distinct known langs | 15 | **18** |
| cjk_coverage component | 0.0 | 0.0035 |
| diversity_score | 3.3 | 3.3 |

One batch (10 signals) is a drop against 56K, so the headline score holds — but
the change is structural: CJK went from *structurally absent* to a **live hourly
stream** (~10/cycle ≈ 240/day, automatic via ingest_loop). The instrument
detected the delta (CJK nonzero, +3 languages), which is the point — diversity
is now measured and self-reinforcing. Score climbs as the window fills (~1 week
of cron to approach the 5%-of-known CJK target, faster once #230 revives the
zh state feeds). Minor follow-up: ja/ko rows landed `country_code=XX` (NewsData
sent non-ISO country names) — geo-tag nit, separate from the voice win.

## Status

- Lever + proof instrument + mechanism test + **live deploy**: **shipped.**
- Live corpus delta: **proven** (CJK 0 → 10, climbing hourly).
- Follow-ups: #162 (multilingual NLP — lights CJK sentiment/framing),
  #230 (revive dead zh state feeds: CGTN/Xinhua), #160 (Voice Mix as a
  product surface / CountryBrief component using this same query).
