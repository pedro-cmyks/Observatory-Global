# Useful-coverage quality gate (2026-07-09)

**Goal (Pedro):** raise Atlas's *useful* story coverage above 40% — "quiero
incrementar ese 40% pero de cosas útiles, no junk." Push coverage up **and** filter
junk, coupled, so the added coverage is real stories not grab-bags.

**TL;DR.** The recall fix (`9d1b04e7`) took story coverage 0.04% → ~40% but the
relaxed promotion gate admitted junk grab-bags as active anchors. Measured: **38%
of assigned coverage sat in junk topics** — multi-source gravity wells ("Full list
of Welsh beaches" 2021 members, "Celebrity Emotional Statements" 1456, "Mixed:
Economic and Regional Updates" 1203) that vacuum loosely-related signals via the
≥0.88 assign threshold. A content-based junk gate (not label regex) now
(a) **de-anchors** junk in `build_unified_topics` so it stops eating coverage and
(b) **demotes** junk from serving. Controlled A/B (gate off→on, fixed scale):
**junk-held coverage 17.4% → 0.0%, useful coverage +4.1pp, +4,465 real signals
reclaimed to real topics** while 1,522 genuinely-junk signals were correctly
released. Reversible. Guard verified: NATO / Ebola / Ukraine / Heatwave / real
World Cup / elections all survive.

---

## 1. The junk fraction (measured, content-based)

On the live prod `unified-v2` state (52,783 assigned signals), classifying every
anchoring topic (active + `u2-` candidates) with the content gate:

| metric | value |
|---|---|
| anchoring topics with members | 256 |
| **junk topics** | **34 (13.3%)** |
| **signals held in junk topics** | **20,095 = 38.1% of assigned** |
| total coverage (assigned / 24h signals ≈ 123k) | 41.7% *(= the task's "39.7%")* |
| **useful coverage (non-junk / 24h signals)** | **25.8%** |

So ~40% of what the recall fix "covered" is grab-bag fill. The junk is
**heterogeneous** and the biggest threads are junk, so it eats disproportionate
coverage:

```
 2021  [1881] Local & Community         Full list of Welsh beaches crowned best in UK   (listicle)
 1456  [421]  Celebrity & Sports Drama  Celebrity Emotional Statements                  (celebrity grab-bag)
 1529  [1916] Other                     CentralAsia: <mixed>  (Balochistan+Bavaria+…)   (grab-bag)
 1203  [1615] Daily News Roundups       Mixed: Economic and Regional Updates            (roundup, self-declared)
 1607  [1677] Crime and Accidents       Diduga Tenggelam di Sungai Musi (antaranews)    (single-outlet dump, 5 srcs)
 1879  [1639] AI Industry and Policy    통신3사 AI 경영… (k-pop mislabel)                 (few-source dump, 7 srcs)
  826  [1878] Celebrity & Entertainment Who is Ser Torrhen Manderly? (fandom explainer) (listicle/celebrity)
```

## 2. Why the obvious signals do NOT separate junk (measured)

| signal | verdict |
|---|---|
| cohesion / whitened cohesion | **useless** — `build_unified_topics` assigns members at ≥0.88 cosine, so junk cohesion is HIGH by construction (all top topics 0.92–0.97). Confirms the clustering-recall doc: grab-bags are topically tight. |
| student `noise_rate` | **useless** — Celebrity 0.74 but Welsh beaches 0.27, Who-is-Ser-Torrhen 0.00. Spans the whole range. |
| `subject_concentration` (content-entropy #224) | **confounded** — Cyrillic/Greek morphology + the ≥0.88 assign-vacuum drag *good* events down to junk levels (Ukraine 0.12, DR Congo Ebola 0.13 vs Welsh beaches 0.07). Kept upstream for single-outlet emergent roundups; unreliable as the primary unified-v2 signal. |
| label regex alone | **8/597 recall** (measured). Too brittle. |
| source count alone | **useless** — junk Welsh beaches has 33 sources, good Ebola has 47. |

## 3. What DOES separate — the gate (`backend/scripts/topic_junk.py`)

A **union of three content signals**, each measured on the 2026-07-09 population:

1. **Junk category** — the R3.1 DeepSeek typer already made the per-topic
   useful/entertainment/grab-bag judgment; its `category` is the strongest
   separator. Non-useful buckets (`JUNK_CATEGORIES`):
   `Daily News Roundups, Celebrity & Sports Drama, Celebrity & Entertainment,
   Entertainment & Culture, Travel Scams / Lifestyle, Local & Community, Other,
   Obituary & Tribute`.
   Deliberately **excluded** (real news / must-survive): all `Sports*` /
   `World Cup*` / `Football*` / `Tennis*` (real events — damped in ranking, not
   gated), `Politics & Governance`, `Business & Markets`, `Science & Technology`,
   the crisis categories, `Cultural Events`.
2. **Listicle / self-declared-grab-bag label** — catches listicles the typer filed
   under a real category. Pattern: `^Mixed:` (the labeler's own grab-bag marker),
   `full list`, `who is …?`, `live stream`, `match schedule`, `how to watch`,
   `what time`, `where to watch`, `meet the`, `listings`, `horoscope`, `recipe`,
   `starting XI`. Generic words (`results`, `guide`, `explained`) excluded — they
   fire on real news.
3. **Few-source feed-dump** — a LARGE topic carried by very FEW outlets is one
   outlet's feed dumped into a gravity well. **`member_count ≥ 150 AND
   distinct_sources ≤ 8`** (distinct sources over a 60-member sample). Measured:
   junk dumps sit at 1–7 sources across 1000+ members; every real event of that
   size spans ≥12 outlets (Ebola 47, NATO 12, Ukraine 19). The member floor spares
   genuine small regional stories. Catches the mislabeled dumps (Indonesian 5,
   Korean 7, Marcha 5) the category typer trusted.

`is_junk = rule1 OR rule2 OR rule3`. Persisted to `dynamic_topics.is_junk` /
`junk_reason` by `scripts/flag_junk_topics.py` (mig `074`). Reason breakdown of the
59 flagged in the A/B: **category 43, listicle-label 12, feed-dump 4.**

## 4. Coupled wiring (one coordinated change, both scripts)

- **Coverage reclaim** — `build_unified_topics._load_centroids` drops
  `is_junk` topics from the anchor set (both the active and `u2-`candidate lanes,
  since a demoted junk topic is still a `u2-` candidate). Junk gravity wells stop
  vacuuming; their signals reassign to real anchors ≥0.88 or fall to residual.
  Kill-switch `ATLAS_UNIFIED_EXCLUDE_JUNK=off`.
- **Serving** — `flag_junk_topics` demotes active junk → `candidate`;
  `project_dynamic_topics` promotion honors `is_junk` (treated like `is_roundup`:
  never promotes, demotes an active) so it never re-promotes.
- **Coverage push** — `build_unified_topics --max-signals` default **15000 → 40000**
  (the runner still overrides to 60000; the chunked keyset loader survives the
  pooler timeout). With the gate, the extra assigned signals land on REAL
  centroids.
- **Feedback loop** — build → flag (sets `is_junk` from this run's members) → next
  build de-anchors. Converges within one embed cadence. Wired as Step 5 of
  `run-embed-hot-corpus.sh`.

## 5. Result — controlled A/B (gate off → on)

Same fixed config both arms (40k signals, assign 0.88, `--no-new-topics` to isolate
the anchor/assignment effect from residual new-topic formation), only the gate
toggled:

| | assigned | useful | junk-held | useful cov (24h) |
|---|---|---|---|---|
| **Arm A — gate off** | 34,506 | 28,519 | 5,987 (17.4%) | 22.8% |
| **Arm B — gate on** | 32,988 | **32,984** | **4 (0.0%)** | **26.9%** |

**The gate's isolated causal effect:** **junk-held coverage 17.4% → 0.0%**, useful
coverage **+4.1pp**, **+4,465 real signals reclaimed** to real topics, and 1,522
genuinely-junk signals correctly released to residual (total dips 34,506 → 32,988 —
exactly the junk leaving). **74.6% of junk-held signals were real** (reclaimed);
25% were true junk.

**Projection to prod scale** (60k + new-topics): applying the measured 74.6%
reclaim ratio to prod's 20,095 junk-held signals ≈ **+15k useful, ~5k released** →
useful coverage ≈ 25.8% → **~38%** from the gate alone; the coverage push
(40k→60k default, plus the embed backlog draining) closes the gap to **>40%
useful** — landing on the gated (junk-free) anchor set, so it is real coverage.

**Serving after the gate:** active topics 597 → 549 (48 junk demoted, 0 active junk
left). Top served topics are now real events (Ukraine War Escalation, European
Heatwave Crisis, Trump Cancels Iran Strikes, India Weather Alerts, Andalusia
PP-Vox pact, Pune murder trial). The grab-bags (Welsh beaches, Celebrity
Statements, Mixed, Ser Torrhen) are gone.

## 6. Guard — must-survive real stories (verified)

All active, none flagged junk: **NATO Summit in Ankara, DR Congo Ebola strike,
Ukraine War Updates ×2, Russian Attacks on Kyiv, Heatwave Impacts, Καύσωνας,
US-Iran strikes, Morocco World Cup, World Cup 2026 Results, Mundial 2026, Marine
Le Pen 2027.** Locked by `backend/tests/test_topic_junk.py` (7 assertions incl. the
full guard list; run via `mlvenv` — no pytest in the ML venvs).

## 7. Honest limits & follow-ups

- **Absolute useful-% is capped by embed coverage.** A 210k-signal embed backlog is
  draining at ~8/s; ~24h signals that aren't embedded can't be assigned at all. As
  the backlog clears, both total and useful coverage rise — the gate keeps the rise
  useful.
- **The A/B understates prod-scale absolute** (40k + no-new-topics for speed/DB
  safety). The `>40% useful` single number is a projection from the measured
  reclaim ratio, not a same-instant measurement — running the full 60k+new-topics
  build twice under the current embedder load was not DB-safe. The next gated cron
  cycle produces the real prod-scale number.
- **Borderline few-source topics fluctuate.** A topic whose source diversity sits
  near the dump floor (e.g. [1639] Korean AI/business, 5–8 sources across builds)
  flips in/out of the feed-dump rule between builds. Acceptable — it removes the
  clear junk; the residual is a small, borderline set. A stable fix would compute
  distinct sources over the full membership, not a sample (heavier).
- **New-topic formation is where the biggest junk is born** (Welsh beaches was a
  `u2-` residual cluster). `flag_junk_topics` scans `u2-` candidates too, so the
  next build de-anchors them — but adding the content gate *inside*
  `build_unified_topics`' `_looks_junk_cluster` (currently template-spam only)
  would stop them at formation. Follow-up.

## 8. Reversibility

- `ATLAS_UNIFIED_EXCLUDE_JUNK=off` — restore the pre-gate anchor set.
- `UPDATE dynamic_topics SET is_junk=false, junk_reason=NULL;` — clear all flags
  (demoted junk resurrects through the normal lifecycle if it re-qualifies).
- Gate thresholds (`JUNK_CATEGORIES`, `LISTICLE_LABEL`, `DUMP_MIN_MEMBERS=150`,
  `DUMP_MAX_SOURCES=8`) are all in `topic_junk.py`, measured not guessed.

## 9. Files

- `backend/migrations/074_dynamic_topics_is_junk.sql` (applied)
- `backend/scripts/topic_junk.py` (new — pure classifier)
- `backend/scripts/flag_junk_topics.py` (new — persist + demote + measure)
- `backend/scripts/build_unified_topics.py` (de-anchor junk; default 15k→40k)
- `backend/scripts/project_dynamic_topics.py` (promotion honors `is_junk`)
- `backend/tests/test_topic_junk.py` (new — 7 assertions incl. guard)
- `scripts/run-embed-hot-corpus.sh` (Step 5) — synced to `~/AtlasLocalWorker/`
  (scripts + runner byte-identical; runs on the M1 `mlvenv`).
