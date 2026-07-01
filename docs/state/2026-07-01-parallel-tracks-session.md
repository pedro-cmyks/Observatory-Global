# Session handoff — 2026-07-01 (parallel tracks: multilingual NLP + event sources + papers)

**Status:** ALL SHIPPED + VALIDATED. Git clean + pushed (`origin/v3-intel-layer`). 16 commits
(`992b445` → `004a101`). Validation this date: **69 tests pass** (disasters/subjects/relationship/
threads-shape), **prod 4/4 endpoints 200** (stats/threads/heat/relationship), **M1 multilingual
worker healthy** (`NER[xlm-v1]`, error=no, ~169s/cycle), **250 disaster events + 659 CAMEO binds +
10 disaster binds** live.

This session ran as **two explicit parallel tracks** (Pedro's ask — "que no se me pierda el uno o
el otro"): **Track A = multilingual NLP** and **Track B = papers (PR3 experiments)**, using a
visible task list + background jobs. Both advanced every turn.

---

## Track A — multilingual NLP: evaluated → flipped LIVE → quality-fixed

**The finding that unblocked it** (`docs/research/multilingual-nlp/2026-07-01-real-fix-evaluation.md`,
`3d7f9be`): the 2026-06-25 "not worth it" conclusion was WRONG on both blockers.
- Blocker A ("xlm sentiment crashes py3.14") = a **missing `protobuf`**, not an incompatibility.
  `pip install protobuf sentencepiece` → xlm-roberta loads, multilingual sentiment sane.
- Blocker B ("multilingual NER doesn't work") = they only tried the free spaCy `xx_ent_wiki_sm`
  (useless for non-Latin). **`Davlan/xlm-roberta-base-ner-hrl`** works: measured **82.1% precision**
  (DeepSeek-judged), huge non-Latin recall lift (zh/fa/ar/ko ~0→37–100%). Throughput a non-issue
  (95K/hr single on M1 MPS).

**Shipped (steps 1–4):**
1. `nlp_pipeline.py` `_extract_entities_hf` (Davlan token-classification + label map PER/ORG/LOC),
   flag `NLP_MULTILINGUAL_NER=xlm` (`f388859`).
2. Offline eval `scripts/eval_multilingual_ner.py` (DeepSeek-judged).
3. Pre-baked protobuf + models in mlvenv.
4. **ru gap** (Davlan HRL has no Russian, 0/3) → `Babelscape/wikineural-multilingual-ner` covers ru
   (87.5% measured). Pipeline routes Cyrillic(`NLP_CYRILLIC_LANGS=ru`)→wikineural, else→Davlan,
   en→spaCy; lazy 2nd model (`7877539`).

**THE FLIP (LIVE, `35e5f65`):** `ATLAS_NLP_MULTILINGUAL=on` in the M1 `.env`.
- **Discovery:** the M1 NLP fleet had been DOWN since 06-29 (SIGTERM, never reloaded) — NER was
  starved AND the flip required (re)starting it. Bootstrapped `com.atlas.nlp-fleet`.
- Validated live via a shadow `--once` cycle first, then flipped. Production non-English
  `nlp_persons` now writing (`NER[xlm-v1]`; it/es/fr/ko/tr; ko = non-Latin via Davlan).
- **Memory guard:** multilingual workers are heavier than the EN-only ones `burst=2` was sized for →
  supervisor floor `max(2,…)`→`max(1,…)` (`scripts/nlp_fleet_supervisor.py`) + `ATLAS_NLP_BURST_
  WORKERS=1`. The 8GB M1 crashed at load 177 once; 54% free with 1 worker.

**Quality fix from live monitoring (`980ff1c`, DEPLOYED):** the flip surfaced a serving bug —
`subjects.classify_subject` returned the NER type without checking the gazetteer, so NER mistypes on
sports/entity-dense headlines (England→PERSON, LaLiga→PERSON) leaked as verified persons. Fix:
**gazetteer checks FIRST, then NER**; the curated sets are unambiguous non-persons so the override is
safe (real people not in the gazetteer keep NER's type). Added the offenders (football leagues→org,
team-nations→place). 38 tests pass.

**Honest state of the flip:**
- Surface payoff **ACCUMULATES over days**, not instant — the mindful multilingual drain is
  ~169–300s/cycle; the large existing GDELT-unverified pool dominates the window-aggregation until
  verified NER accumulates. Prod `/country/IT` still showed old GDELT noise (photo credits as
  people) at check time — **re-check the surfaces in a day.**
- ru handled via wikineural; other Cyrillic (uk/bg) untested (same family, guarded).

**Track A follow-ups:** (a) model-caching across cycles (speed the ~169s drain); (b) bump burst
back to 2 once RAM is confirmed comfortable under multilingual; (c) uk/bg Cyrillic validation;
(d) re-check surfaces show verified non-English subjects after a day of drain.

**REVERSIBLE:** `ATLAS_NLP_MULTILINGUAL=off` in the M1 `.env` + restart `com.atlas.nlp-fleet`.

---

## Event sources — disaster ingest + precise binding (#232)

**Disaster events (`80b3c37`, `c219302`, DEPLOYED):** the natural-hazard gap CAMEO can't represent.
- mig 062 `disaster_events_v2`; `app/services/ingest_disasters.py` (USGS FDSN + GDACS RSS, no key)
  wired into `ingest_loop` every 8th cycle. **250 events live** (USGS quakes @max M6.0 + GDACS
  hazards).
- `scripts/bind_disaster_movement.py` — geo-temporal binding (type→category + dominant-evidence-
  country + window). **Zero fan-out** (JP quakes→"Japan Earthquakes", PH→"Philippines 7.8 Tsunami",
  BR flood→"Heavy Rains in Pernambuco"). Runner Step 4b (M1).
- **Latent bug fixed:** `_TOPIC_ROLE_COUNTS_SQL` (relationship endpoint) filtered ALL roles by the
  v1-compat engine_version, so movement was NEVER counted → now counts any `member_kind='event'`.
  Japan Earthquakes: evidence 17, movement 8.

**F3 event-binding UNION (`51e83a0`):** the eval assumed unified-v2 = full membership, but measured
it's a precise SUBSET (8495/104) near-DISJOINT from the sample (overlap 5). So `compute_event_
movement.py` `dyn_sig` now UNIONs sample + unified-v2 → +57% ceiling; realized 83→101 topics,
470→609 events, 520→659 members. As unified-v2 grows the union widens with no code change.

---

## #241 embed throughput (measured; 1 lever shipped, 1 review-gated)

`docs/research/embed-throughput/2026-07-01-hnsw-insert-bottleneck.md` (`992b445`): the bottleneck is
HNSW graph maintenance per insert (~80× the raw write; <16/s on the 276K graph).
- **Lever 2 (recency) SHIPPED:** `embed_hot_corpus._pending_rows` now `ORDER BY timestamp DESC` —
  the scarce embed budget goes to the served (recent) window, not alphabetical. Zero-risk, synced ALW.
- **Lever 1 (drop/rebuild) READY, OFF:** `--bulk-reindex` drops the HNSW index → bulk-insert ~22K/s →
  single-threaded rebuild (~4min/276K). **DELICATE (drops the prod vector index) — Pedro reviews +
  a supervised first run before enabling in the cron.** NOT enabled.

---

## Track B — papers: the PR3 experiment backlog RUN + WRITTEN

All four experiments P1/P8 required are built, measured, and folded into the papers. Ledger:
`docs/research/atlas-paper/2026-07-01-paper-staleness-ledger.md`. Artifacts under
`docs/research/embedding-ablation/`.

- **PR3-05 gdelt_hint_ablation** (`0cb9f25`): theme-hint-dependent assignments 20.2% correct ≪ 40.9%
  baseline = NET NOISE; lexicon-standalone lifts to 48.3%; semantic recovers 86–100% of the small
  true-loss (cliff in the [0.73,0.80] band). Verdict REMOVE-OK. The 41.6% reproducibility gate.
- **PR3-09 external baseline** (`d4cc9ac`): HDBSCAN-global (BERTopic core) cliffs at every mcs
  (mega-blob/collapse, 0/8 top overlap = scoped-design justification); flat KMeans/Agglo reach
  in-sample coherence parity but no identity/lifecycle. Honest: Atlas's edge is scoping + lifecycle,
  not raw one-shot coherence.
- **PR3-10 (4 of 5)** (`0cc47b7`, `70dd9e8`, `358d0d7`): bootstrap+Wilson CIs (Δ ablated−baseline
  +7.4pp [5.2,9.6], excludes 0); Fleiss κ 0.734 (gold reliable); **crisis-only precision = the
  successor to 41.6% = 48% (unanchored) – 54% (hinted)** (anchoring control: the category hint was
  ~5.6pp optimistic; out-of-scope force-fits are 49% of usable at 27%). Temporal hold-out
  DATA-LIMITED (batch-03 has no timestamp + signals purged). Only `role_noise_rate` remains.
- **PR3-11 heat ablation** (`1330b16`): Kendall-τ(composite vs volume) = −0.198, top-8 overlap 0/8 —
  "volume≠importance" measured; `surprise_kl`+`source_diversity` drive the divergence.
- **Papers write-up** (`004a101`): P1 result skeleton "Open baselines" marked RESOLVED + a "PR3
  experiment results" section; P3 (master plan) got the heat ablation.

---

## Commits this session (chronological)
`992b445` #241 levers · `80b3c37`+`c219302` disaster events · `51e83a0` F3 union · `0cb9f25` PR3-05 ·
`3d7f9be` multilingual eval · `f388859` NER swap · `d4cc9ac` PR3-09 · `0cc47b7` PR3-10 CIs ·
`70dd9e8` crisis-only+κ · `1330b16` PR3-11 · `35e5f65` flip+burst · `7877539` ru/wikineural ·
`358d0d7` monitoring+anchoring · `980ff1c` gazetteer-override · `004a101` papers write-up.

## Open follow-ups (next session)
1. **Multilingual:** re-check surfaces show verified non-English subjects after a day of drain;
   model-caching across cycles; burst=2 once RAM confirmed; uk/bg Cyrillic.
2. **#241 Lever 1:** supervised first run of `--bulk-reindex` on prod (Pedro-gated), then enable in
   the embed cron.
3. **Papers:** `role_noise_rate` calibration (last PR3-10 item); temporal hold-out needs a fresh
   labeled window; BERTopic-proper (py3.12) is a non-blocking PR3-09 follow-up.
4. **Engine:** theme-hint removal is now unblocked (PR3-05 verdict) — a v2 engine dropping theme-hints
   + applying the reject class clears well above 41.6%.

## Verify commands
```bash
# tests
cd backend && .venv/bin/python -m pytest tests/test_ingest_disasters.py tests/test_subjects.py tests/test_topic_relationship.py -q
# M1 multilingual worker
grep -E "NER\[xlm-v1\]|Cycle.*done" ~/AtlasLocalWorker/logs/nlp-fleet.err.log | tail -2
# prod
curl -s https://atlas-api-pedro.fly.dev/api/v2/topic/dynamic-topic-680/relationship | python3 -m json.tool
# revert the flip if needed: set ATLAS_NLP_MULTILINGUAL=off in ~/AtlasLocalWorker/.env + restart com.atlas.nlp-fleet
```
