# GDELT NULL-headline hole — diagnosed, mechanism proven, fixed at the parser

**Date:** 2026-07-30 · **Mode:** read-only measurement first (prod
`SET default_transaction_read_only = on` + a live GDELT file replay), then one
validation rule changed in `backend/app/services/ingest_v2.py`.

**Provoked by:** `docs/research/recall-229/2026-07-30-cjk-length-floor-measurement.md`
§2.1: "3,300 of those 3,583 (92%) are NULL headlines … that is a distinct,
larger data hole (CN is far worse: 41.4% NULL) and out of scope for this fix."
This doc is that investigation.

---

## 0. Verdict

The NULL-headline JP/CJK rows are **one lane and one mechanism**:

- **Lane:** 100% `source_family='gdelt'`, and within GDELT essentially 100%
  `attribution_method='gdelt_gkg_translated'` (the TRANSLINGUAL GKG feed,
  `source_lang='xx'`). The English GKG lane is ~0% NULL. RSS/NewsData never
  produce NULL headlines in these countries at all.
- **Mechanism:** `parse_gkg_row` DOES capture the article title — GDELT ships
  `<PAGE_TITLE>` for ~99.8% of translingual rows — but the title validation
  `len(candidate.split()) >= 4` is **script-blind**. CJK titles contain few or
  no spaces, so a complete Japanese/Chinese headline splits into 1-3 "words"
  and is thrown away. The URL-slug fallback then also fails because CJK press
  URLs are numeric IDs (`asahi.com/articles/ASV7S…`, `agara.co.jp/article/665443`
  — no hyphen/underscore slug), so `headline` lands NULL.

This is the third member of the same bug family (script-blind text heuristics):
`_norm_headline` deleting non-Latin chars (fixed `924174b2`), the flat
`length(headline) >= 20` floor (fixed `7ffdb038`), and now the ≥4-word title
validation at ingestion — the earliest of the three, poisoning the corpus at
capture time.

**Not an encoding failure, not a feed problem, not a parser crash.** The title
is present and decodes fine; the validator rejects it.

## 1. DB measurement (prod, 168h, 2026-07-30)

### 1.1 The NULL set is one source_family

```sql
SELECT country_code, source_family, COUNT(*) FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '168 hours' AND headline IS NULL
  AND country_code IN ('JP','CN','TW','KR','US','TR')
GROUP BY 1,2;
```

Every row: `gdelt`. (CN 16,958 · JP 3,310 · TW 3,140 · US 2,441 · KR 498 ·
TR 47.) RSS/NewsData contribute zero NULL headlines here.

### 1.2 Within GDELT, it is the translingual lane

| CC | `gdelt_gkg_translated` NULL % | `gdelt_gkg` (English) NULL % |
|----|------------------------------:|-----------------------------:|
| CN | **53.3%** (16,916/31,742) | 0.5% |
| TW | **45.5%** (3,138/6,902) | 0.3% |
| JP | **38.5%** (3,305/8,586) | 0.1% |
| US | 12.3% (2,190/17,785) | 0.3% |
| KR | 10.8% (498/4,607) | 0.0% |

Global sizing, all countries, 168h: translated lane **33,248 NULL / 463,349
(7.2%)**; English lane 721 / 278,156 (0.3%). The hole loses ~33k signals'
headlines per week.

The country ordering is itself the mechanism's fingerprint: **Korean uses
spaces** (so most KR titles pass a word-count check), Japanese uses them
rarely, Chinese not at all → KR 10.8% ≪ JP 38.5% < TW 45.5% ≈ CN 53.3%. US's
12.3% is CJK-language coverage OF US stories (china.com, ifeng.com rows with
`country_code='US'`) plus short non-CJK titles.

### 1.3 The NULL set is not one feed

Top `source_name` among JP NULL rows: udn.com 366, mainichi.jp 224,
agara.co.jp 207, asahi.com 147, the-miyanichi.co.jp 123, nikkei.com 117 … —
spread across the whole Japanese (and Chinese-covering-JP) press. Sampled raw
rows: all `attribution_method='gdelt_gkg_translated'`, `source_lang='xx'`,
`snippet` NULL, URLs numeric-ID style.

## 2. Mechanism proven on a live GDELT file

Replayed the exact `parse_gkg_row` title validation over
`20260730150000.translation.gkg.csv` (the then-current 15-min translingual
update, 3,146 rows):

| | count |
|---|---:|
| rows with `<PAGE_TITLE>` | 3,141 (99.8% — the title IS there) |
| pass `len(words) >= 4` | 2,963 |
| **fail** | **178 (5.7% of titled rows)** |
| — of failures, CJK-dominant (>50% chars in CJK blocks) | **160 (89.9%)** |
| — failures rescued by the URL-slug fallback | 46 (26%) |
| — failures that land NULL | 132 |

Sampled failures are complete, real headlines — e.g.
`'維新が4、8区の区割り案まとめる　法定協で3案議論へ　都構想'` (mainichi, 3
"words"), `'【茨城新聞】島国ナウル、「ナオエロ」に改称'` (1 "word"),
`'避難所が暑く、アスファルトの上で寝る被災者　現地入りの医師が見た「猛暑」の熊本地震'`
(sankei, 2 "words"). The 18 non-CJK failures are genuinely short titles in
other scripts (`'Пожежі'`, `'Mirė Kazimiera Prunskienė'`) — a smaller,
separate effect, not fixed this pass (see §5).

JP-domain rows in this one file (asahi/mainichi/nikkei/agara/udn/jiji): 16 of
22 titled rows FAIL the validation — matching the 38-45% DB NULL rates once
slug rescues are netted out.

## 3. The fix, measured before wiring

Same design as `backend/scripts/script_floor.py` (commit `7ffdb038`):
character-composition, keyed to the title TEXT, never to `source_lang`. A
title passes validation if it is **not** a GDELT doc-id (`^\d{6,}`, unchanged)
AND either:

- `len(words) >= 4` (unchanged — Latin path byte-identical), **or**
- the title is CJK-dominant (>50% of characters in Hiragana/Katakana/CJK
  Ideograph/Hangul blocks — the same four ranges as `script_floor.py`) and
  ≥10 characters (the same measured CJK floor).

Replayed against the same live file:

| | old rule | new rule |
|---|---:|---:|
| pass | 2,963 | 3,123 |
| **rescued** | | **+160 (every CJK-dominant failure — all were ≥10 chars)** |
| still fail | 178 | 18 (all non-CJK short titles) |

Junk stays out by construction: the placeholder classes that motivated the
validation (`'Content 23748045'`, `'T20260728 376794'`, `'1000'`) are 100%
ASCII → CJK ratio 0.0 → still rejected; pure doc-ids still hit `^\d{6,}`.
Boilerplate CJK nav titles ("ニュース一覧", 6 chars) stay under the 10-char
floor.

Expected prod effect: the translated-lane NULL rate falls from 53/45/39% to
the residual (no-PAGE_TITLE rows ~0.2% + short non-CJK titles) for CN/TW/JP;
~30k more real headlines captured per week, feeding embedding, NER, dedup and
clustering for exactly the countries the CJK-floor work was rescuing
downstream.

## 4. What was changed

`backend/app/services/ingest_v2.py` (`parse_gkg_row`): the title validation
gains the CJK-dominant branch via a module-level `_cjk_ratio` helper. The
four unicode ranges are duplicated from `backend/scripts/script_floor.py`
with a lockstep comment — `scripts/` is not in the Fly Docker image
(`COPY app ./app`), so the app cannot import it (same precedent as
`thread_intelligence.py:1387`).

Ungated, deliberately: this is a capture-time bug fix, strictly additive
(rows that stored NULL now store the real title; no previously-kept row
changes), same class as the `#264 html.unescape` ingest fixes which also
shipped ungated. Reverting = reverting the commit.

Tests: `backend/tests/test_gkg_cjk_title_validation.py` — real JP/zh titles
kept (1-3 words), junk placeholders/doc-ids still dropped, sub-floor CJK
boilerplate still dropped, Latin path unchanged (3-word English title still
dropped, 4-word kept).

## 5. Honest residuals (documented, not fixed)

- **Historical rows are not backfilled.** ~33k NULL/week accumulated for the
  lane's lifetime. The headlines are mechanically recoverable from the GDELT
  archive (the files still carry PAGE_TITLE; `scripts/archive_gold_miner.py`
  already walks those partitions) — a backfill is a separate, chippable pass.
  7-day retention means prod self-heals within a week of deploy anyway;
  the external archive keeps the NULL rows as-captured.
- **Short non-CJK titles** (18/3,146 in the replay: uk/lt/ne/es one-to-three
  worders) still drop. Different scripts, different floor question, needs its
  own measurement — the word-count validation is still script-blind for
  them, just at ~0.6% incidence instead of 90%.
- **~0.2% of translingual rows genuinely ship no `<PAGE_TITLE>`** — nothing
  to capture; correctly NULL.
- **KR's 10.8%** is the same mechanism at lower incidence (spaces); the fix
  covers Hangul via the same ranges.
- The fix reaches prod on the next Fly deploy of the API/ingest app; until
  then the lane keeps writing NULLs.

## 6. Reproduction

```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
psql "$DATABASE_URL" -c "SET default_transaction_read_only = on" -c "
SELECT country_code, attribution_method, COUNT(*),
       COUNT(*) FILTER (WHERE headline IS NULL)
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '168 hours' AND source_family='gdelt'
  AND country_code IN ('JP','CN','TW','KR')
GROUP BY 1,2;"
```

Live-file replay: fetch the current `…translation.gkg.csv.zip` from
`http://data.gdeltproject.org/gdeltv2/lastupdate-translation.txt`, run the
validation predicate from `parse_gkg_row` over column 26's `<PAGE_TITLE>`.

---

## Post-deploy verification (2026-07-30, live ingest)

Deployed to Fly and measured on FRESH rows (40-minute window, ~2 ingest cycles):
- **JP: 42 rows, 0.0% NULL** (was 23.2%)
- **CN: 133 rows, 1.5% NULL** (was 41.4%)

The hole is closed at the source. Downstream compounding: these rows now also
clear the (env-gated) script-aware length floor and enter the clustering
funnel — the East-Asia information desert loses its largest single cause.
