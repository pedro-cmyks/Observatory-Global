# CJK length-floor fix — measured, then wired (env-gated, default off)

**Date:** 2026-07-30 · **Branch:** `eclipse-dramatic-moment` · **Mode:** read-only
measurement (`SET default_transaction_read_only = on`), then one file changed
(`backend/scripts/run_scoped_snapshot.py`) behind a new reversible flag.

**Provoked by:** `docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md`
§1 side finding: "the R1 pull requires `length(headline) >= 20`, and 27.3% of
Japanese signals are shorter than 20 characters — a full Japanese sentence
often is."

---

## 0. Verdict

The underlying finding is real but the 27.3% headline number **conflates two
different things**: NULL headlines (a separate, larger data-quality issue,
unfixable by any length floor) and genuinely-short non-NULL headlines (the
actual script-blind-floor effect). Once separated, the pure script-blind
effect is smaller than 27.3% but still clearly present and clearly
CJK-shaped: **JP 2.6%, KR 2.2%, TW 3.8%, CN 15.0%** of non-NULL headlines
fall under the flat 20-char floor, vs **US 0.95%, TR ~0.5%**. Random sampling
of the "short" bucket shows it is a mix of (a) genuine complete CJK
headlines and (b) non-CJK scraper-junk placeholders ("Content 23748045",
digit-string scrapes) that are short for an unrelated reason. A
**character-composition** fix (script-aware floor keyed to the headline
TEXT, not `source_lang`) rescues (a) and correctly leaves (b) untouched,
because junk placeholders are ASCII and never classify as CJK-dominant.

Fixed at the two sites that gate the R1 scoped-snapshot pull
(`backend/scripts/run_scoped_snapshot.py`), behind `ATLAS_CJK_LEN_FLOOR`
(default **off** — byte-identical to the pre-existing flat floor).

---

## 1. Every `length(headline)` site found, and which stage each gates

| File | Line(s) | Predicate | Stage gated | Live? | Fixed? |
|---|---|---|---|---|---|
| `backend/scripts/run_scoped_snapshot.py` | 110 (`_COUNTRIES`), 133 (`_FETCH_PAGE`) | `length(s.headline) >= 20` | **R1 clustering eligibility** (which countries clear `--min-embedded`) **and per-country clustering input** (the actual signals HDBSCAN sees) | Yes — nightly `com.atlas.scoped-snapshot`, the diagnosis's own subject | **Yes** |
| `backend/scripts/backfill_lexicon_topics.py` | 111, 224, 313 (`DEFAULT_MIN_HEADLINE_LEN = 20`) | `length(headline) >= $2` | lexicon topic-assignment eligibility (`atlas_topics`, method=`lexicon`) | Yes — 30-min `run-atlas-topic-classifier.sh` Step 1 | No (see §4) |
| `backend/enrichment/nlp_pipeline.py` | 348, 394, 441, 501 | `LENGTH(headline) > 10` | sentiment/NER/framing eligibility | Yes — NLP fleet (M1 + Fly) | No (see §4) |
| `backend/enrichment/lexicon_sentiment.py` | 340 | `LENGTH(headline) > 10` | lexicon fast-lane sentiment eligibility | Yes — ingest-time fast lane | No (see §4) |
| `backend/scripts/snapshot_emergent_topics.py` | 96, 109 | `length(headline) >= 20` | the pre-R1 global HDBSCAN pass (`_pull_signals`, `_pull_embedded_stratified`) | **No** — `com.atlas.emergent-snapshot` is not loaded in `launchctl list` (superseded by R1/scoped-snapshot, per CLAUDE.md 2026-07-01) | No (dormant) |
| `backend/scripts/emergent_poc.py` | 92 | `length(headline) >= 20` | its own standalone `_pull_signals` | **No** — only pure helpers (`_apply_gate`, `_cluster`, …) are imported by the live scripts; this module's own pull is never called from them | No (dead code path) |
| `backend/scripts/recall_scoped_estimate.py` | 40, 49 | `length(s.headline) >= 20` | read-only recall-estimate harness ("R0 → the decisive number") | No cron/launchd reference found | No (research harness) |
| `backend/scripts/topic_classifier_baseline.py` | 44 | `length(headline) >= $2` | eval baseline harness | No | No (frozen eval methodology) |
| `backend/scripts/eval_multilingual_ner.py` | 30 | `length(headline) >= 25` | NER eval harness | No | No (frozen eval methodology) |
| `backend/scripts/embedding_input_ablation.py` | 99 | `length(headline) >= 25` | embedding-ablation research harness | No | No (frozen research artifact) |
| `backend/scripts/ensemble/phase_c_agreement.py` | 40 | `length(headline) >= 25` | taxonomy-revision agreement harness | No | No (frozen research artifact) |
| `backend/scripts/a0_coverage_split.sql` | 16 | `length(headline) >= 20` | one-off coverage-split query | No | No (throwaway SQL) |
| `backend/scripts/mine_lexicon_vocab.py` | 138 | `LENGTH(headline) > 10` | lexicon-vocab mining tool | No | No (one-off tool) |
| `backend/scripts/restore_and_reclassify_reviewed.py` | 139 | `len(headline) < min_headline_len` (Python-side) | reviewed-label restore tool | No | No (one-off tool) |

`backend/enrichment/fast_lane.py`'s `SELECT_SQL` was also grepped (it appears
in `test_fast_lane.py`) but carries **no** length filter at all — the test
`test_fast_lane_selector_matches_pending_method_index` asserts
`"LENGTH(headline)" not in SELECT_SQL`, i.e. that file is a true negative,
not a site.

**Fix scope: `run_scoped_snapshot.py` only.** It is the exact site the
diagnosis measured, it is the highest-leverage stage (clustering
eligibility — a country that never clears `--min-embedded`, or a signal
that never reaches HDBSCAN, cannot become a thread at all), and it
auto-syncs to the M1 worker via the runner's own committed-state
`git archive HEAD` step — no manual ALW copy needed. The `backfill_lexicon_topics.py`
and NLP-pipeline sites are also live, but changing them was out of scope
this pass (see §4 for why, and what would be needed).

---

## 2. Measurement

### 2.1 The 27.3% figure, decomposed

Re-running the diagnosis's own JP row at 168h (2026-07-30, one day later than
the diagnosis — totals shift naturally with the corpus, see the diagnosis's
own day-over-day instability finding):

| | count |
|---|---:|
| JP subject-country, 168h | 14,220 |
| — NULL headline | 3,300 (23.2%) |
| — non-NULL, `length < 20` | 283 (2.0% of total, 2.6% of non-NULL) |
| passes `headline IS NOT NULL AND length >= 20` | 10,637 |

`14,220 − 10,637 = 3,583` → **25.2%** "dropped" by the compound predicate —
close to the diagnosis's 27.3% (a day of corpus churn plus the diagnosis's
exact 14,787/10,754 baseline explains the residual gap; not re-litigated
here). But **3,300 of those 3,583 (92%) are NULL headlines** — signals with
no headline text captured at all. No length floor, script-aware or not, can
rescue a NULL headline; that is a distinct, larger data hole (`CN` is far
worse: 41.4% NULL) and out of scope for this fix.

The genuine script-blind-floor effect — non-NULL headlines shorter than 20
chars — is **283/14,220 (2.0%) for JP**, not 27.3%. Still real, still worth
fixing, just smaller than the headline number suggested.

### 2.2 Non-NULL short-headline rate by country, 168h (2026-07-30)

```sql
SELECT country_code, COUNT(*) AS total,
       COUNT(*) FILTER (WHERE headline IS NULL) AS null_headline,
       COUNT(*) FILTER (WHERE headline IS NOT NULL AND length(headline) < 20) AS short_not_null
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '168 hours' AND country_code = 'CC'
GROUP BY country_code;
```

| CC | total | null_headline (%) | short_not_null / non-null (%) |
|----|------:|-------------------:|-------------------------------:|
| US | 116,850 | 2.1% | **0.95%** |
| TR | 20,059 | 0.2% | **0.53%** |
| CN | 40,829 | 41.4% | **15.02%** |
| JP | 14,220 | 23.2% | **2.59%** |
| TW | 11,447 | 27.2% | **3.75%** |
| KR | 12,335 | 4.0% | **2.21%** |
| CO / VE / BO / ML | thousands | ≤1.4% | ≤1.4% |

CJK-subject countries (CN/JP/TW/KR) show a 2-15× higher short-headline rate
than Latin-script witnesses (US/TR/CO/VE), even after removing the NULL
confound. CN's 15% is the largest gap and is investigated in §2.3.

### 2.3 Is the "short" bucket real CJK, or junk?

Random sample, JP and CN, non-NULL headlines `< 20` chars:

```
JP  '日本30年來8次震度7劇震 熊本占3次'   (19 chars — real: "Japan had 8 mag-7+
                                          quakes in 30yr, 3 in Kumamoto")
JP  '국회 제02차 정무위원회 전체회의'   (18 chars — real: National Assembly
                                          committee session, complete headline)
JP  'Content Ovkbr6Cgeq'                (18 chars — scraper junk placeholder)
JP  '1000'                              (4 chars — junk)
CN  'Content 23748045'                  (16 chars — junk placeholder, repeats)
CN  'T20260728 376794'                  (16 chars — junk, date+id scrape)
CN  '072026 1927143'                    (14 chars — junk)
```

The junk placeholders are 100% ASCII — a script-aware floor keyed to
headline TEXT COMPOSITION (not `source_lang`, which is frequently `xx`/
untagged for exactly these GDELT rows) leaves them at the 20-char floor
untouched, while rescuing the genuine dense CJK sentences that happen to
sit at 10-19 characters.

### 2.4 The fix, measured before wiring

Built `cjk_ratio`/`is_cjk_dominant`/`effective_headline_floor` (>50% of a
headline's characters in Hiragana/Katakana/CJK-Ideograph/Hangul unicode
blocks → floor 10, else floor 20 — the "Simplest robust" design), plus a SQL
mirror (`headline_floor_sql`) using the identical four unicode ranges in a
`regexp_replace`-based CASE expression. Ran the **exact generated SQL**
against prod (read-only) alongside the flat floor, 168h:

| CC | non-NULL | old floor (`>= 20`) kept | new floor (script-aware) kept | rescued |
|----|---------:|-------------------------:|-------------------------------:|--------:|
| US | 114,416 | 113,327 | 113,345 | **+18** (0.02%) |
| TR | 20,008 | 19,955 | 19,955 | **+0** |
| CN | 23,915 | 20,324 | 20,401 | **+77** (0.32%) |
| KR | 11,839 | 11,577 | 11,753 | **+176** (1.49%) |
| JP | 10,920 | 10,637 | 10,686 | **+49** (0.45%) |
| TW | 8,323 | 8,011 | 8,225 | **+214** (2.57%) |

Breaking the rescue down by whether the headline is CJK-dominant (the only
population the fix can touch):

| CC | CJK-dominant headlines | of those, `< 20` chars | rescued (`10 ≤ len < 20`) | still excluded (`len < 10`) |
|----|------------------------:|------------------------:|---------------------------:|------------------------------:|
| JP | 3,449 (31.6% of non-null) | 49 | **49** | 0 |
| KR | 8,549 (72.2%) | 192 | **176** | 16 |
| TW | 6,906 (83.0%) | 214 | **214** | 0 |
| CN | 2,993 (12.5%) | 77 | **77** | 0 |
| US | 1,956 (1.7%, mostly genuine CJK-language coverage of US stories) | 18 | 18 | 0 |
| TR | 4 | 0 | 0 | 0 |

Every rescued row is CJK-dominant text between 10 and 19 characters; junk
placeholders (0% CJK) never move. US's 1,956 "CJK-dominant" hits are real —
sampled and confirmed genuine Chinese/Japanese/Korean-language press
coverage of US stories (e.g. `"美国二季度GDP增速放缓至1.5%..."`), correctly
long enough to already pass either floor.

**Net effect over 168h:** roughly +49 JP, +176 KR, +214 TW, +77 CN signals
become eligible for the R1 pull per week — modest in absolute terms, but
this is exactly the eligibility stage (`--min-embedded`, default 100) the
2026-07-29 diagnosis showed is not the binding constraint for JP today
(§2, Stage 2 of that doc: JP already clears `min_embedded` with room to
spare). The rescue matters most for thinner CJK-subject countries close to
the eligibility line, and it removes a structural, permanent bias from the
corpus regardless of today's binding constraint.

---

## 3. The fix

`backend/scripts/script_floor.py` (new, pure — no DB/network):

- `cjk_ratio(headline) -> float` — fraction of characters in the four CJK
  unicode blocks (Hiragana+Katakana contiguous U+3040-U+30FF, CJK Ext-A
  U+3400-U+4DBF, CJK Unified Ideographs U+4E00-U+9FFF, Hangul Syllables
  U+AC00-U+D7A3).
- `is_cjk_dominant(headline)` — ratio `> 0.5` (strict majority).
- `effective_headline_floor(headline)` — `10` if CJK-dominant else `20`.
- `headline_floor_sql(column)` — the identical logic as a raw SQL CASE
  expression (`regexp_replace` + the same four ranges), for use inside a
  `WHERE` clause.
- `headline_length_predicate(column)` — the call-site entry point: returns
  the flat `length(<col>) >= 20` when `ATLAS_CJK_LEN_FLOOR` is unset/off
  (**default**, byte-identical to before), or `headline_floor_sql(column)`
  when on.

Wired into `backend/scripts/run_scoped_snapshot.py`: `_COUNTRIES` and
`_FETCH_PAGE` (the country-eligibility count and the per-country keyset
pull) became functions (`_countries_sql()`, `_fetch_page_sql()`) that build
their `WHERE` clause via `headline_length_predicate('s.headline')`, so the
gate is read fresh on every call. No other predicate in either query moved.

**Gate:** `ATLAS_CJK_LEN_FLOOR`, default **off**. The runner
(`scripts/run-scoped-snapshot.sh`) already re-syncs `backend/scripts` from
this repo's committed `HEAD` via `git archive` at the top of every nightly
run ("Step -1: COMMITTED-STATE SYNC"), so no manual AtlasLocalWorker copy is
needed — the fix ships to the M1 automatically once this commit lands on
the branch that runner's `ATLAS_REPO_DIR` tracks. Flip on with
`ATLAS_CJK_LEN_FLOOR=on` in `/Users/pedro/AtlasLocalWorker/.env` (or the
plist) when ready; the same guard reverts it.

## 4. Why the other live sites were left alone this pass

- **`backfill_lexicon_topics.py`** shares the same `>= 20` value and is also
  cron-live (30-min classifier), but (a) it gates a *different* mechanism
  (lexicon topic ASSIGNMENT, not clustering eligibility), (b) it is
  parametrized (`DEFAULT_MIN_HEADLINE_LEN`, passed as `$2`) rather than
  hard-coded, and (c) `test_backfill_lexicon_topics.py` freezes the exact
  SQL text (`assert "length(headline) >= $2" in src`) — changing the
  predicate shape would need that test rewritten too. Same fix pattern
  would apply; flagged as a natural follow-up, not done here to keep this
  change to the one measured, diagnosed site.
- **`nlp_pipeline.py` / `lexicon_sentiment.py`** use `> 10`, a much more
  lenient floor gating a different mechanism (sentiment/NER/framing
  eligibility, not clustering/embedding eligibility) — no measurement this
  pass showed a comparable CJK penalty at that floor, and it wasn't the
  site the diagnosis named.
- **`snapshot_emergent_topics.py` / `emergent_poc.py`** are dormant/dead in
  the current production path (confirmed via `launchctl list` and via
  import-graph inspection — see §1 table); fixing dead code doesn't change
  prod behavior.
- **Research/eval/backfill one-off scripts** (`recall_scoped_estimate.py`,
  `topic_classifier_baseline.py`, `eval_multilingual_ner.py`,
  `embedding_input_ablation.py`, `ensemble/phase_c_agreement.py`,
  `a0_coverage_split.sql`, `mine_lexicon_vocab.py`,
  `restore_and_reclassify_reviewed.py`) are frozen-methodology harnesses or
  throwaway tools, not the recurring engine path; changing their filters
  would move the goalposts on whatever they measured, not fix a live bug.

## 5. Reproduction

```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
psql "$DATABASE_URL" -c "SET default_transaction_read_only = on" -c "SET statement_timeout='120s'" -c "<query>"
```

The exact generated predicate for a re-run:

```python
from backend.scripts.script_floor import headline_floor_sql
print(headline_floor_sql("headline"))
```

Tests: `backend/tests/test_script_floor.py` (pure logic, real ja/zh/ko
examples + boundary + junk-not-rescued, runs in `backend/.venv`) and
`backend/tests/test_scoped_cjk_floor.py` (wiring — the two SQL builders
respond to the gate, runs in the M1 mlvenv like the sibling
`test_scoped_*.py` files, `hdbscan`/`asyncpg` required).
