# Silent-risk: source measurement

**Date:** 2026-07-22 · **Status:** MEASUREMENT ONLY — no code shipped, no engine writes.
**Scope:** 7 read-only probes against prod + 7 independent adversarial verifications.
**Bottom line:** the strongest measured lever is a one-line ingest defect, not a source.

---

## Traceability convention

Every number below carries a tag. `[P1]` = probe 1's own measurement. `[P1-V]` = the
independent verifier that re-pulled prod and re-measured probe 1 without reusing its
artifacts. Where the two disagree the disagreement is reported as a **CONTRADICTION** and
the narrower claim is the one that stands. Nothing is averaged.

| tag | probe |
|---|---|
| P1 / P1-V | matcher validity (is "43.8% zero press coverage" real?) |
| P2 / P2-V | non-Latin script tokenization |
| P3 / P3-V | Wikimedia full pageview API (real 30-day baseline) |
| P4 / P4-V | forum surge (Bluesky + Lemmy + Reddit) |
| P5 / P5-V | intent filter (story vs lookup noise) |
| P6 / P6-V | 2-of-3 ensemble reachability |
| P7 / P7-V | voice-mix wedge (low-self-voice countries as high-value silence) |

Artifacts (scripts, JSON, hand-label tables) live in the session scratchpad:
`/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/173558f6-d703-4019-82c3-fe319154bb0c/scratchpad/`
— indexed per probe in §7.

---

## 1. The question, and why the detector is parked

**SILENT RISK** = a topic with measurable PUBLIC attention and near-zero MEDIA coverage in
the same window. "What is the public searching for / looking up / discussing that the press
is not covering?" It is the "what is missing" half of the product wedge.

Current implementation: `backend/app/services/silent_risk.py` (pure helpers) +
`backend/app/routers/attention_threads.py` (`GET /api/v2/attention/silent-risks`).

It was parked on 2026-06-29 with this stated reason (`docs/methodology/silent-risk-detection.md`,
issue #172): the wiki source is too weak — `wiki_pageviews_v2` stores TOP-N per country
(~17 country codes, ~257 titles/day), so *every top-of-pool title has baseline 0*, velocity
collapses to raw pageviews, and the ranking becomes celebrity/sport noise. A forum pivot was
tried and did not clearly improve.

**Two of the three premises behind that parking decision are now measured false.**

1. "Every top-of-pool title has baseline 0" — **false as a fact about the data**. Fetching a
   true 30-day per-article baseline for all 257 stored titles: only **3/257 = 1.2%** have a
   genuinely zero baseline [P3-V] (P3 measured 5/282 = 1.8% on a slightly different pool —
   consistent). The zero-baseline problem was an artifact of the *top-N store*, not of
   Wikipedia. `backend/app/services/ingest_wiki.py:81` reads `if rank > 25: break` while the
   same API call already returns 995–1000 articles per project [P6-V].
2. "The detector ranks by raw views" — **false as a description of the code**. `attention_threads.py:229-237`
   already ranks by `velocity = v_today / GREATEST(v_base,1)` over a 7-day in-pool baseline,
   and none of the evergreen pages cited as noise (Cookie(informatique), Messi, FIFA World
   Cup, Deaths in 2026) appear anywhere in the served top-25 [P3-V].
3. "Forums do not clearly improve" — **true, and now explained by mechanism** (§3.3).

So the parking was right, for reasons that were partly wrong. This document re-measures the
whole source question from the bottom.

---

## 2. Method

### 2.1 Data

All probes read prod read-only (`statement_cache_size=0`, `SET statement_timeout`, SELECT
only; no writes, no DDL).

- **Attention side:** `trends_v2` — Google Trends "trending now" RSS, rising by construction.
  ~327k rows/14d, 99 countries, ~100–230 distinct keywords/country/24h, fresh to the hour.
  Primary working set = 6,601 (country, keyword) pairs in a 24h window ending 2026-07-22
  (`trends24.json`). Verifiers re-pulled their own windows: 6,973 / 7,109 / 7,277 pairs
  depending on the exact cut, plus two **disjoint earlier windows** (T−72..−48h = 12,300
  pairs; T−96..−72h = 10,070 pairs) used for replication.
- **Press side:** `signals_v2`, non-social. 48h ≈ 305,000–308,400 headlines depending on pull
  time; 168h ≈ 932,000–962,000. Disjoint-window controls at 198,767 / 226,121 / 273,643 rows.
- **Wiki side:** `wiki_pageviews_v2` (425 rows/day, 17 country codes, 12 languages, MAX(rank)=25)
  plus live Wikimedia REST API (`/metrics/pageviews/top/{project}`, `/top-per-country/{CC}`,
  per-article daily, langlinks, Wikidata P31/P106).
- **Forum side:** `signals_v2 WHERE source_family='social'` — 29,996 rows over 7.22 days
  (hot retention caps history at 7d).

### 2.2 The instrument, and how it was validated

The core instrument is a **lexical trend↔press matcher**: fold a keyword, fold a headline,
declare "covered" if the folded phrase is a substring OR all significant tokens appear
(order-free). It is deliberately generous — it biases toward *covered*, so measured silence
is an upper bound on silence and a lower bound on coverage.

**The instrument was validated adversarially before any of its output was believed.** Five
distinct validation moves ran, and four of them found the instrument at fault:

1. **Hand adjudication.** 60 stratified "zero-coverage" items re-tested against prod with 6
   progressively harder retrieval strategies and hand-read [P1]; 120 random *covered*
   keywords hand-labeled as a control [P5-V]; all 98 intent-filter tray items hand-labeled
   exhaustively [P5] and re-adjudicated on a product axis [P5-V].
2. **Ablation on one fixed corpus.** A 2×2 over {raw fold, `html.unescape`} × {buggy candidate
   gate, correct substring semantics} to decompose the correction into named causes [P1-V].
3. **Placebo / null model.** Score the same trend keywords against press from **5–7 days
   before** the trend. If the instrument measures *silence*, current-window coverage should
   greatly exceed stale-window coverage. [P1-V]
4. **Script stratification with a Latin control.** Measure excess silence of non-Latin over
   always-matchable Latin keywords, before and after each fix, and split non-Latin by whether
   the script delimits words with spaces [P7-V].
5. **Replication on disjoint windows.** Every headline correction re-run on 1–3 independent
   days [P1-V, P2-V, P4-V, P5-V, P6-V, P7-V].

**The placebo is the single most important methodological result and is stated up front:**

| matcher arm | silent% vs CURRENT press | silent% vs PRE-TREND press | discriminative gap |
|---|---|---|---|
| original (buggy) | 44.5% | 59.4% | **15.0pp** |
| both bugs fixed | 33.0% | 50.3% | **17.3pp** |
| + idf-coverage ≥0.60 | 26.5% | 42.7% | **16.2pp** |

[P1-V] Correcting the matcher makes it claim ~18pp more coverage but **does not make it
discriminate better**, and the thresholded variant discriminates *worse*. Of the 761 pairs the
bug fix rescues from silence, **465 (61%)** are also "covered" by press published *before* the
keyword trended [P1-V].

> **Therefore: the residual ~32% is a lexical-match rate, not a silence estimate.** Every
> number in §3–§5 must be read under that ceiling. Nothing in this document certifies that any
> individual keyword is genuinely uncovered by the world's press.

### 2.3 Meta-finding on the method itself

**5 of the 7 probes were materially refuted by their own verifier.** In every case the
refutation preserved a narrower true claim and killed an overreaching headline. The failure
modes were consistent and worth naming, because they will recur:

- **No control group.** P5 measured a 22.5% story base rate in the silent set and never
  measured it in the *covered* set (it is 15.8% — not significantly different) [P5-V].
- **Straw-man comparator.** P3 compared its fix against raw-views ranking (3/25 overlap) when
  production ranks by velocity (12/25 overlap) [P3-V].
- **Threshold change sold as a bug fix.** P1's headline 43.8→27.8% requires an idf-coverage
  threshold selected on the same 60 labels it is scored against; the actual bug fixes reach
  32.3% [P1-V].
- **Absence-of-tool read as absence-of-world.** P2 labeled Greece/Israel/Thailand ATLAS-BLIND
  from a decoding artifact; P6 called an ensemble unreachable from a hardcoded `break`
  statement [P2-V, P6-V].
- **Self-scored rules.** P5's lexicon was written while reading the sample it was then scored
  on: dev recall 74.3%, held-out recall 7.1%, gap 0.67; 17 of 25 firing rules match exactly
  one item in all 2,888 [P5, self-caught].

---

## 3. Findings per source

### 3.0 The cross-cutting defect: HTML-entity-encoded GDELT headlines — **STRONG LEVER**

Three probes found this independently, from three different directions (P1 hunting matcher
bugs, P2-V hunting the script blindness, P7 hunting the voice-mix wedge). All four
verifications reproduce it.

**~46.6% of the press corpus stores headlines HTML-numeric-entity encoded, and it is one
ingest lane.**

| measurement | window | encoded share | source |
|---|---|---|---|
| 432,873 / 932,719 | 168h | 46.4% | [P1] |
| 432,800 / 932,271 | 168h | 46.4% | [P1-V] |
| 143,550 / 308,327 | 48h | 46.6% | [P2-V] |
| 143,550 / 308,312 | 48h | 46.6% | [P7] |
| 143,502 / 307,124 | 48h | 46.7% | [P7-V] |

By lane (48h): **gdelt 48.7–51.6%**, independent 2/17,099, wire 0/6,342, state 0/4,307,
api 0/1,207, social 0 [P1-V, P2-V, P7, P7-V]. P7's "100% the GDELT lane" is 99.999% — 2 rows
are tagged `independent` [P7-V]; immaterial.
By declared language (168h): `xx` (unknown) 79.4%, `en` 6.6%, and es/pt/de/fr/ru/ar/ja/ko/id/tr/bn/zh
all 0.0–0.1% [P1, P1-V] — which is why P1 inferred GDELT before P1-V confirmed it by lane.
Stable over 14 days: 41.6 / 44.1 / 44.7 / 44.6 / 47.9 / 44.7 / 45.9 / 44.5% [P2-V]. Reproduces
on a disjoint window at 48.6% [P7-V].

**Root cause, verified in code:** `backend/app/services/ingest_v2.py:427` stores the GDELT
`<PAGE_TITLE>` capture raw (`candidate = m.group(1).strip()`), while the *same function* at
line ~455-458 unescapes the same string for geo-corroboration — with an in-code comment that
literally names the problem ("HTML-entity-encoded non-Latin headlines (e.g. Arabic
`&#x641;&#x644;&#x633;…` = فلسطين)"). One `_html.unescape` + a backfill.
The same bug class has been patched *downstream* in `research_semantic.py:392`,
`daily_publication.py:117`, `thread_packet.py:204`, `community_discussion.py:56` — never at the
write side [P2-V].

**Effect on the press corpus** — script counts, raw → after `html.unescape` (48h):

| script | raw | decoded | source |
|---|---|---|---|
| greek | 0 | 8,182–8,202 | [P2-V, P7, P7-V] |
| hebrew | 0 | 703–715 | [P2-V, P7, P7-V] |
| cyrillic | 2,699–2,730 | 24,589–24,668 | [P2-V, P7, P7-V] |
| arabic | 2,321–2,352 | 8,686–8,691 | [P2-V, P7, P7-V] |
| devanagari | 155–163 | 2,676–3,014 | [P2-V, P7, P7-V] |
| hangul | 2,739–2,745 | 5,779–5,788 | [P2-V, P7, P7-V] |
| han / CJK | 1,500–1,992 | 4,676–5,524 | [P2-V, P7, P7-V] |
| thai | 15 | 466–470 | [P2-V, P7, P7-V] |
| tamil / telugu / malayalam / gujarati / kannada / gurmukhi | 0 | 148 / 136 / 351 / 193 / 67 / 79 | [P2-V] |
| latin | 296,308–297,392 | 247,563–248,298 | [P2-V, P7, P7-V] |

**Effect on measured silence** — the clean decomposition is P1-V's 2×2 on one fixed corpus
(304,763 press rows, 6,601 pairs):

| arm | silent | rate | Δ |
|---|---|---|---|
| A raw fold + buggy candidate gate (= `sr_probe.py` as written) | 2,879 | 43.61% | — |
| B `html.unescape` only | 2,290 | 34.69% | **−8.92pp** |
| C candidate gate fixed only | 2,691 | 40.77% | **−2.85pp** |
| D both | 2,130 | **32.27%** | **−11.35pp** |

Replicated independently: 43.8→34.6% [P7], 43.5→34.5% [P7-V], 44.6→36.3% (their window)
[P5-V]. Replicated on disjoint days: 42.5→32.2% [P1-V], 40.3→32.7% [P7-V].

Per-country correction (before → after unescape) [P7]:
GR 82.3→44.8 (−37.5pp) · UA 70.3→34.1 (−36.3) · BG 63.9→31.3 (−32.5) · EG 68.9→37.8 (−31.1) ·
IL 89.6→59.7 (−29.9) · RU 75.9→47.1 (−28.8) · CO 29.5→13.7 · TR 44.4→31.2 · KR 62.9→50.9 ·
TH 74.1→59.3.
On native-script keywords only [P2-V]: GR 100.0→54.8 · IL 100.0→57.8 · UA 67.7→31.2 ·
RU 69.3→43.4 · EG 74.4→48.8 · TW 54.2→37.5 · KR 53.8→42.7 · TR 39.0→27.9 · TH 97.7→77.3 ·
IR 72.9→68.2 · **JP 89.6→86.4** · IN 27.6→27.0.

**Receipts — stories reported as "silent" that were in the corpus, in the native language,
from a domestic outlet, in the same window** [P2-V]:

- IL `סקר מנדטים` → *"סקר מנדטים: איזנקוט עוקף את נתניהו; הקואליציה רק עם 51"* (srugim.co.il)
- GR `σούδα` → ship collision at Souda, Crete, 14 fuel tankers (e-radio.gr)
- TH `สำราญ นวลมา` → national police chief confirmed 12:0 (bangkokbiznews.com)
- UA `володимир горбатюк` → replacement of the General Staff chief (tsn.ua)
- MX `huracán` → *"Se forma tormenta tropical Fausto en el Pacífico; podría convertirse en huracán"* (razon.com.mx), stored as `hurac&#xE1;n` [P1]

**Blast radius beyond silent-risk (measured, downstream effect unverified):** 4,355 distinct
headline *texts* appear in the corpus BOTH entity-encoded and plain, and
`thread_ranking._norm_headline` does not unescape — so syndication/reprint dedup counts those
as different stories [P1]. Any measurement that reads headline TEXT over the GDELT half of the
corpus — script/language inference, lexical matching, NER, embeddings — has been operating on
mojibake for ~47% of rows [P2-V].

**Label: STRONG LEVER — but not a silent-risk lever.** It is a corpus-integrity fix with a
blast radius far wider than this feature. It removes ~9pp of *measured* silence and it does
**not** improve the instrument's ability to discriminate real silence (§2.2 placebo).

---

### 3.1 Google Trends — **WEAK LEVER**

**Decisive number:** after both matcher defects are fixed, **32.3%** of trend pairs are
unmatched by press [P1-V]; of the intent-filter's 98-item tray, **19/98 = 19.4%** both name a
specific event/issue AND are genuinely absent from Atlas press within 168h — about **16
distinct live candidates per day** [P5-V]. But the placebo shows those 16 are not certified
silent (§2.2).

**Strengths, measured:** it is the only source with breadth. 99 countries, ~6,600 (cc,keyword)
pairs per 24h, fresh to the hour, rising by construction, ~327k rows/14d [P1, P6].

**What the "silence" actually contains — three subtractions:**

1. **~9pp is the encoding defect** (§3.0).
2. **~3pp is the candidate-gate bug** in `sr_probe.py`: the inverted index is keyed on exact
   whitespace tokens but the verifier does a substring test, and
   `min(toks, key=lambda t: len(inv.get(t, ())))` selects a token *absent* from the index
   (len 0 is the minimum) — so any keyword with one out-of-vocabulary token scores 0 by
   construction [P1]. MX `predicción` → 0 hits despite 20 in-window headlines containing the
   substring; TR `otoyol` → 0 despite 8 (Turkish agglutination: otoyolda/otoyolu/otoyolun) [P1, P1-V].
3. **~15% of multi-token "silence" is one extra word.** Drop-one-token test: of 748 media==0
   pairs with ≥3 significant tokens, **164 (21.9%, CI 19.1–25.0)** have same-country press in
   the same 48h window after deleting exactly one query token; hand-reading 20, 14 are the same
   story [P5-V]. Confirmed cases inside the original 48h window: IT `rottamazione quinquies comuni`
   (token `comuni` broke the AND), ZA `sassa social grant review` (`review`), CO `temblor en
   santa marta hoy`, IN `epfo epf scheme 2026 rules`, DE `neue hitzewelle deutschland`.
4. **~18% relative is the window choice.** Holding trends fixed and widening press 48h→168h:
   44.6%→36.3% [P5-V] (also 34.7→29.1 and 45.1→42.1 on two other days).

**A structural bias that makes the silent set look better than it is:** the all-tokens-AND
matcher fails more often on long queries, and long descriptive queries are exactly what
"names a specific event" means. P(media==0) by significant-token count: 1 tok 34.6% → 2 tok
45.4% → 3 tok 54.9% → 4 tok 60.9% → 5 tok 78.0% → 6+ 85.7% [P5-V]. **The silent set is
constructed to be story-enriched.** Any "long queries are more story-shaped" finding built on
it (P5's 2.26× lift) is circular.

**CONTRADICTION [P1] vs [P1-V]:** P1 headlined "the matcher is lying: 34/60 = 56.7% of
zero-coverage keywords do have press coverage" and "43.8% → 27.8%". P1-V refutes both. Only
**12 of P1's own 34 false-silent items** recover when both bugs are fixed inside P1's own 48h
contract; the corpus-wide rescue rate in P1's 15 sampled countries is 20.6%; the 27.8% figure
requires an idf-coverage≥0.60 threshold selected on the same 60 labels used to score it. P1's
flagship entity example (TR `hakan çalhanoğlu`) is a *window* artifact — 0 hits at 48h raw AND
decoded, 2–3 only at 168h — and US `valentin vacherot` scored 1 on replay yet stayed in the
numerator. At least 5 of the 34 adjudications rest on lexical collisions (US `ed harris
yellowstone series involvement` → *"Red Sox complete Brewers' Kyle Harrison trade with College
World Series star"*). **The surviving claim is the −10 to −11pp bug-fix correction, which
replicates on an independent day.**

**Best measured rule, and its ceiling:** no lexical rule reaches acceptable binary accuracy.
Best F1 = 0.74; best silent-precision at usable recall = 61.3% @ 73.1% recall (idf-coverage
≥0.60) vs the current detector's 43.3% @ 100% [P1]. Relaxed entity-anchor rules reach recall
1.00 but suppress 24 of 26 genuine silences [P1]. **~40% false-silence is the honest floor of
this instrument class.** Counter-evidence in the fixes' favour: 706/757 (93.3%) of bug-fix
rescues anchor on a rare token (corpus df<150), so the rescues are not generic-word collisions
[P1-V].

---

### 3.2 Wikimedia full pageview API — **WEAK LEVER**

**Decisive number:** on 2026-07-21, news-relevant AND press-silent items in the top-25 =
**3/25 with the production ranking and 3/25 with a true 30-day baseline** [P3-V]. The
reordering is real; the deliverable is unchanged.

**What survives (and it matters, because it corrects the parking rationale):**

- True baseline == 0 is **3/257 = 1.2%** [P3-V] / 5/282 = 1.8% [P3], not "every title". The
  zero-baseline story was a top-N-store artifact.
- The truncation is one line: `ingest_wiki.py:81 → if rank > 25: break`, discarding 97.5% of a
  response that already contains 995–1000 articles per project per day [P3, P6-V].
- The 17 stored `country_code` values are **12 distinct daily title sets** — AR/CO/MX/ES are
  byte-identical (es.wikipedia), US/GB/IN are byte-identical (en.wikipedia) [P3-V, P6-V]. Any
  country-scoped wiki claim today is unsound *independently* of the baseline question.
- Resolving a candidate to its English Wikipedia label via langlinks before press-matching
  correctly demotes false silents — Drapatyi 0 native hits → 19 English hits, Andy Burnham(el)
  → 3,011, Felipe VI(ar) → 139 [P3, P3-V]. **But it also manufactures coverage for generic
  labels**: `Odissea (film)` → "The Odyssey" 85→753 hits, `21. Juli` → "July 21" 2,517→2,815
  [P3-V]. P3 reported the 33% correction rate with no false-positive rate attached.
- Real per-country breadth exists: `/top-per-country/{CC}` returns data for **78 of 99** trends
  countries; with language-project mapping **91 of 99** have a pool; only 8 have none
  (AL AM AZ BY EE KH KZ MM) [P6-V].

**CONTRADICTION [P3] vs [P3-V]:** P3 claimed the baseline "decisively fixes" the ranking
(3/25 overlap) and that breadth grows 12×–248× "for free".
(a) The 3/25 comparator is raw-views, a ranking production does not use. Against the
**production velocity ranking** the overlap is **12/25** — the fix keeps half the served list
[P3-V]. Across four days: 12/25 (07-21), 9/25 (07-12), 6/25 (07-15), 4/25 (07-18) — mean ~7.75,
and 07-21 is the day where fix and production agree *most*.
(b) The breadth does not transfer. Sampling ranks 26–1000 for de/fr/it (448 titles with ≥10
baseline days): surge top-30 has **median 2,520 views/day**, 24/30 under 5,000 views, and is
dominated by TV-broadcast film lookups, a Wikipedia *user* page, an insect, and Swatch
Internet Time; ~2–3/30 are news-relevant [P3-V]. The `max(baseline,10)` floor is the cause —
pages with true baselines of 1–6 get 100–800× surges on 1,000–8,000 views.
(c) Cost is not free: `api.wikimedia.org/feed/.../featured` (the mostread feed, 69 req/day in
P3's proposed config) returned **HTTP 429 on 8/8 first attempts** at 0.2s spacing and only 200
after a 15s backoff; the MediaWiki action API (needed for both the production category
classifier and the langlinks de-dupe) 429'd on the third sequential request. Only
`rest_v1` pageviews was rate-limit-clean (~1,300 requests, 0 errors) [P3-V].
(d) A new false-positive class the baseline cannot see: `median(views d−36..d−8)` carries no
seasonal term, so annually periodic pages surge by construction — `21. Juli` (a bare date
page) enters the true-surge top-25 at 432×, and the Akashi footbridge crush (21 July 2001) is
the same mechanism [P3-V].

**Also structurally against the mission:** `/top-per-country` returns HTTP 404 (an explicit
WMF suppression, not an empty list) for RU, CN, TR, IR, EG, PK, BD, VN, SA, AE, VE, BY, CU,
SY, IQ, AF, YE, SD, ET, MM, KH, LA, PS, UZ, KZ, AZ, HK, NI, HN, ZW, ZM, MZ, BH — **33
countries** [P3], 8/8 of the low-press-freedom set independently re-tested [P3-V]. That is
precisely the set where "what is the public looking up that the press won't cover" has the most
value.

**Composition, even at the top of a true-surge list:** language-neutral Wikidata typing of the
top-120 → 39 sport, 25 entertainment, **17 news-relevant (14.2%)**, 39 unclassified; news-relevant
AND press-silent = 10/120 = 8.3%, of which 7 are in languages Atlas barely ingests; honest
yield ~3–4 genuine press-silent news events per 120 scored titles [P3]. 9–11 of every top-80 is
an obituary. The production classifier `category_to_lane()` is English-only and laned 95/120 as
"general" — Thai actors, Egyptian scriptwriters and Hungarian chess players all pass through as
analyst-relevant [P3].

---

### 3.3 Forums (Bluesky + Lemmy + Reddit) — **DEAD END**

**Decisive number:** the same social corpus matches **38.07% of press-COVERED trend keywords
and 3.22% of press-SILENT ones** (Latin-only 42.1% vs 4.3%; US 48.9% vs 8.3%) [P4-V].
Replicated on a disjoint window: 33.34% vs 1.96%.

**This kills the source for the opposite reason P4 gave.** P4 concluded "too thin"
(29,996 rows / 7.22d ≈ 4,150/day). A corpus too thin to be matched cannot hit 38%. The binding
constraint is that **social attention is press-derivative**: it lights up on exactly the
keywords the press already covers. Scaling forum ingest would not fix it [P4-V].

**Second structural finding, missed by P4 and load-bearing:** `signals_v2` has **no engagement
column** (no score/upvote/reply — verified against the full column list), and both ingesters
sample *supply*, not attention: `ingest_lemmy.py:74,114` pulls `sort=New&type_=Local`
`PER_INSTANCE_LIMIT=30`; `ingest_bluesky.py:58-59` `COLLECT_SECONDS=25 MAX_POSTS=300` [P4-V].
Forum public attention is engagement; post count is supply. **A post-count surge metric over a
supply-sampled feed is a bot detector by construction** — that, not the 1.27 posts/author
figure, is why the surge list *is* the bot list.

**What P4 measured that survives:** of the top-150 deduped surging terms, 57 have zero press
hits; hand-labeled ≈45 automated feeds, ≈12 sport/fandom/commerce, **0 genuine unreported
civic/risk stories** [P4]. #1 cluster = one Bluesky account posting EU CVE disclosures (69
posts/7d) producing 11 of the top 12 terms by surge ratio; then NWS weather-alert bots, an
AirNow AQI bot (53×), a radio bot (126×), a Dutch job bot, Pokémon-restock and Amazon-deal bots.

**The strongest rescue attempt fails.** An author-diversity gate (surge terms with ≥3 distinct
Bluesky DIDs) leaves 51 of 110 press-silent surge terms, and the ≥5-author band is dominated by
**multi-account automation rings** — a templated geeknews/affiliate ring posting identical
UUID-bearing text from 4 accounts, a Dutch job-ad network (6 accounts), an Amazon-affiliate ring
(5 accounts). Zero civic/risk stories survive [P4-V].

**CONTRADICTION [P4] vs [P4-V]:** P4's "the only terms that clear a surge threshold are single
automated feed accounts" is factually false (51/110 have ≥3 distinct authors), and its stated
mechanism (author atomization) predicts the diversity gate should work — it does not. P4's
1.39% corroboration figure was also computed with a *strict* matcher against a silent set
defined by a *generous* one; symmetric re-measurement gives 3.22% token-AND / 1.99% strict
[P4-V]. Magnitude survives, method did not.

**The surviving corroborating role points the wrong way.** Of the 84 press-silent keywords with
social presence, ~76 are sport/weather/news-brand-navigational/gaming noise (highest hit count
in the whole silent set is `weather radar`, AU, 14 hits) and only ~8 are civic
(`drones shahed` FR, `lars klingbeil` DE, `mykhailo fedorov` GB, `sonntagsfrage` DE,
`tánaiste of ireland` IE, `impôt` CA, `πετρέλαιο` GR, `πρόστιμο` GR) = **0.31% of press-silent
keywords**, most at 1–3 hits [P4-V]. Empirically, social presence on a silent candidate predicts
**noise**. The licensed use is de-noising, not corroboration.

**Social absence is uninformative and must never be read as silence:** 80.3% of social rows are
`country_code='XX'` (bluesky has no instance home); only 5 countries clear 50 rows/day. Rows/day:
KE 0.9 · PE 0.9 · EG 1.0 · ID 1.4 · TH 1.4 · ZA 1.7 · VN 1.7 · PH 2.0 · PK 2.0 · BR 4.3 · CO 5.9 ·
MX 7.0 · NG 7.7 · IN 8.7 · DE 13.1 · TR 14.1 · JP 24.7 · **US 137.1 (max)** [P4].

---

### 3.4 The 2-of-3 ensemble — **DEAD END (as a gate)**

**Decisive number:** **0 of 8** hand-verified overlooked leads gain a second source even against
a wiki pool 280× larger than the one stored [P6-V]. Every agreement axis measured is
**anti-correlated with silence**.

**CONTRADICTION [P6] vs [P6-V] — the reachability half is refuted.** P6 concluded "not
reachable" from 69/2,888 = 2.4% joint coverage and "56% of the silent set is in a country where
no second source exists". Both numbers measure `ingest_wiki.py:81`'s `break` and the 17-entry
hardcoded `COUNTRY_WIKI_MAP`, not the sources:

| pool | same-country wiki agreement on the silent set | joint ≥2 sources |
|---|---|---|
| T0 stored (rank ≤25) | 11 (0.4%) | 66 (2.3%) |
| T1 un-truncated, same 12 projects (64,533 rows) | 344 (11.9%) | 535 (18.5%) |
| T2 + top-per-country + 20 more projects (117,530 rows) | 607 (**21.0%**) | 822 (**28.5%**) |

[P6-V] Under a stricter matcher (≥2 shared significant tokens) T2 = 14.3%; under exact
folded-keyword == folded-title equality with zero fuzziness, same-country hits go 3 (0.10%) →
262 (**9.07%**) — a ~90× lift with no matcher slack. Silent pairs in a country with genuinely
no wiki pool = **84 (2.9%)**, not 1,618 (56%). The 56% figure is precisely the
Atlas-blindness-reported-as-absence error the honesty rails forbid. Replicated on 2026-07-19:
1.9% → 24.3% loose / 12.9% strict.

**The value half survives and replicates, and it is what kills the ensemble.**

Cross-country agreement (`n_countries_trending`) vs silence, **controlled for script and token
count** (Latin/Cyrillic-class, 2–3 token keywords, 2,737 keywords) [P6-V]:
n_cc=1 → 60.2% silent · 2 → 41.2% · 3–4 → 31.1% · 5–9 → 12.7% · 10+ → **3.7%**.
Uncontrolled [P6]: 54% → 29% → 25% → 14% → 11%.
Wiki agreement is mildly anti-correlated too: 25.7% silent with same-cc strict wiki agreement
vs 38.8% without (base 36.4%); median press hits 7 vs 2 [P6-V].

**What cross-country agreement actually detects: syndication.** Hand-labeling the top-45 by
`n_countries_trending`: ≈24 sport fixtures (53%), ≈9 weather/utility (20%), 4 commercial
product, **2 genuine political news (4%)** [P6]. The head of the list is
`nottm forest vs blackburn rovers` (21cc, media=0), `new zealand vs west indies` (17cc),
`fenerbahçe – górnik zabrze` (17cc), plus `weather` (24cc), `weather tomorrow` (18cc),
`pogoda` (15cc), `garmin cirqa smart band` (16cc). The only genuine news in the top-45 is
already heavily covered — `daniel ortega` 15cc/media=150, `openai` 13cc/media=220,
`pete hegseth` 8cc/media=91.

**Cost of the gate:** 4,604/5,151 unique keywords (89.4%) and 2,475/2,888 silent pairs (85.7%)
are `n_cc=1` [P6]. All 8 known-good leads have `n_cc=1`; 7 of 8 sit where no ensemble can fire
[P6]. The 69 two-source survivors are junk: wiki agreement is footballers (Lamine Yamal, Pau
Cubarsí, Leandro Paredes); social agreement is cross-country false friends — `liquid glass`
(an iOS feature) firing in ET/LK/KW/NP off ONE English Bluesky post [P6].

Persistence is a mild **inverse** predictor (1 hourly bucket 28.3% signal vs 8+ buckets 12.1%
[P5-adjacent], 46%→31% silent [P6]) and its head is daily ritual utility: `اذان المغرب` (call
to prayer, OM, 22 buckets), `météo pour demain` (SN, 21). Volume carries no intent information
(20.7–33.3% across all bands) [P5].

**Narrower surviving claim:** *a 2-of-3 ensemble is reachable (≈9–28% of the silent set,
depending on matcher strictness, once wiki is un-truncated) but selects encyclopedia-shaped and
syndicated attention, and systematically misses the vernacular administrative queries that
silent-risk exists to surface.* Do **not** record "not reachable" — that would freeze a
`break` statement into a permanent finding about the world.

### 3.5 Voice-mix as a ranking wedge — **DEAD END**

**Decisive number:** r(self_voice_ratio, corrected silent%) = **−0.185** across 89 countries
[P7], independently replicated at **−0.253** across 60 countries (−0.289 excluding no-space
scripts) [P7-V]. The sign is *opposite* the wedge hypothesis. r(log domestic press, silent%) =
+0.028 [P7]. The attention/supply ratio ranking is a pure denominator artifact:
r(log press, log silent-per-1k-press) = **−0.816** [P7].

Silent% by self-voice band is non-monotonic: 0–.2 → 30.3% · .2–.4 → 45.0% · .4–.6 → 46.8% ·
.6–.8 → 27.8% · .8–1.0 → 33.8% [P7].

**CONTRADICTION [P7] vs [P7-V] — the causal joint is a non-sequitur.** P7's headline reads
"the voice-mix framing fails **because** what actually produced the non-Latin silence was our
own encoder". P7's own correlations are computed *on the corrected silence*, so a bug already
removed from the dependent variable cannot explain why the predictor fails against it. Two
independent results welded by a false connective; both survive **separately** (P7-V replicates
the voice-mix null from scratch).

**And the scope claim is refuted at the stated strength.** Against a Latin-script control
[P7-V]:

| cohort | raw silent% | decoded silent% | excess over Latin, raw → decoded | encoder explains |
|---|---|---|---|---|
| Latin control (5,253 pairs) | 33.8% | 28.8% | — | — |
| all non-Latin (1,600 pairs) | 76.2% | 54.1% | +42.4pp → +25.3pp | **40%** |
| space-delimited non-Latin (1,268) | 72.9% | 46.4% | +39.0pp → +17.5pp | **55%** |
| no-space: CJK/kana/Thai (332) | 88.9% | 83.7% | +55.0pp → **+54.9pp** | **0%** |

P7's per-country correction table lists ten countries and every one is a space-delimited script;
JP, TW and CN are absent. Japan — the largest non-Latin silent country in both windows — barely
moves: 88.8→88.3% (−0.5pp) and 92.7→90.9% on a disjoint window [P7-V].

---

## 4. The intent filter

**Question:** can rules separate a real overlooked STORY from lookup noise inside the 2,888
media==0 keywords? Built on 280 hand labels across two independent random samples, plus
exhaustive labeling of all 98 filter-kept items [P5].

### 4.1 Base rate — and the control that removes its meaning

| set | n | permissive signal (REAL-STORY incl. bare institution + HAZARD) | strict (query names an event/issue) |
|---|---|---|---|
| media==0 (silent) | 280 | **22.5%** (Wilson 18.0–27.7) [P5] | **10.0%** [P5] |
| media>0 (COVERED) — the control P5 never ran | 120 | **15.8%** (10.4–23.4) [P5-V] | **9.2%** (5.2–15.7) [P5-V] |
| difference | | z = 1.51, **not significant** | z = 0.26, **not significant** |

**22.5% is a property of Google Trends, not of press silence.** P5's headline "real stories are
far more common in the silent set" has no measured contrast to be more common than [P5-V].

The base rate is stable across P5's two independent samples (23.3% seed-42, 21.5% seed-1234)
and is honestly bracketed by P5: under the strict reading it is 10.0%, not 22.5%, because P5's
convention counts a bare governance/security institution (police district, anti-corruption
commission, army, court, ministry) as REAL-STORY-inferred. Full class base rates (n=280):
SPORT 25.7% · REAL-STORY 20.0% · COMMERCIAL-UTILITY 14.3% · ENTERTAINMENT 13.2% ·
PERSON-ONLY-AMBIGUOUS 10.4% · OTHER-NOISE 7.9% · ROUTINE-WEATHER 5.4% · HAZARD-LOOKUP 2.5% ·
LOTTERY 0.7%.

### 4.2 Precision and recall

| metric | P5 | P5-V (product axis) |
|---|---|---|
| tray precision | **93.9%** (92/98, exhaustive hand-label, CI 87.3–97.2) | **19.4%** (19/98, CI 12.8–28.3) |
| recall | **7–14%** (held-out 2/28 = 7.1%, CI 2.0–22.6; tray-side 11.5–14.2%) | — |
| filter split over 2,888 | DROP 2,500 (86.6%) · UNRESOLVED 290 (10.0%) · KEEP 98 (3.4%) | — |

**CONTRADICTION [P5] vs [P5-V].** These measure different axes and both are stated, not
averaged. 93.9% = "is this item signal under my labeling convention", scored by the rule author
against his own convention. 19.4% = "does it name a specific event/issue AND is Atlas press
genuinely missing it at ≤168h" — the axis a silent-risk product needs. P5-V's exhaustive
re-adjudication of all 98: shape = EVENT 40 / GENERIC 36 / INSTITUTION 18 / acknowledged-FP 4;
coverage = COVERED-STORY 32 / COVERED-CONCEPT 35 / COVERED-ELSEWHERE 1 / NOT-FOUND 30. **21 of
the 40 genuine EVENT items (53%) are already in Atlas press.** 69/98 tray items (69%) have
Atlas press within 168h.

Further tray defects [P5-V]: 98 keeps = **88 distinct query strings** (`unwetterwarnung adria`
kept 3×, `حكومة` 3×, `colisión` 3×; `dubbo earthquake` and `earthquake dubbo` are the same AU
event twice). Tray size is not stable — 98 keeps on P5's day but **45 and 41** on two earlier
days *despite larger pair counts* (keep rate 1.2%, not 3.4%), so the proposed "388 items/day"
operating point is a best-day number.

**And the filter does not preferentially fire on the silent set.** Keep-rate silent vs covered:
3.39% vs 2.76% (z=1.40, ns) on P5's day; 1.20% vs 1.24% (ns) at T−72..−48h; **1.26% vs 3.03%
(z=−5.07, significant IN REVERSE — the covered set was 2.4× more story-dense)** at T−120..−96h
[P5-V].

### 4.3 Residual failure modes

- **Overfitting, self-caught.** Lexicon written while reading sample A, then scored on sample A:
  recall 74.3%. Held out: **7.1%**. Gap 0.67. 17 of the 25 distinct rules that fired on dev match
  **exactly one item** in all 2,888 — hapax rules minted from the item they were meant to catch
  [P5]. A single-sample probe would have reported 74% recall.
- **False negatives (26 held-out misses): 19 (73%) LEXICON GAP** across ~17 language-script pairs
  (EE `слезоточивый газ`, IN `ஓய்வூதியம்` pension/Tamil, LT `nelaimė`, RS `војска србије`,
  TW `無人機` drone, TR `yolcu uçağı`, KZ `неблагоприятные метеорологические условия`),
  **7 (27%) ENTITY GAP** — a bare named entity with no common noun to match at all
  (DE `tesla gigafactory berlin-brandenburg`, IR `Natanz`, IN `Almatti` dam level). Two of the
  misses were English (`woodlands hdb electric vehicle fire`, `flight cancellation and delay`) —
  the gap is not only non-English [P5].
- **The hard ceiling: bare named entities.** 47–55% of silent queries are a bare entity with no
  event predicate; they carry 23–43% of all true signal; the filter caught 1 of 12 in held-out
  [P5]. No rule approach reaches these.
- **59% of the tray names no event at all** — 36/98 are a bare common noun or standing daily
  lookup (`حكومة` government, `граница` border, `полиция`, `القتل`, `colisión`, `군대` army,
  `изтребител`), 18/98 a bare institution/service name (RCMP, West Mercia Police, Hospital
  Infantil de México, Tribunal de Contas SC, MACC, ICJ) [P5-V]. This is exactly P5's
  "REAL-STORY inferred" tier doing the work.
- **Named false positives, each a distinct mechanism** [P5]: two hospitals (service-provider
  lookup on `risk:hospital`); IQ `الحدود الدنيا` = exam minimum thresholds matched on
  *ḥudūd*=borders (**polysemy**); KR `Uiseong-**gun**` matched on `gun`=army (**homograph**);
  DZ army enlistment registrations; US `cher mary bono royalties lawsuit`.
- **Noise-reason naming is poor even when the DROP is correct**: the filter names the right noise
  class for 20.6% of SPORT, 9.5% of COMMERCIAL-UTILITY and 0% of ENTERTAINMENT/OTHER-NOISE; only
  PERSON-ONLY-AMBIGUOUS (93.3%) and ROUTINE-WEATHER (66.7%) are well-named [P5].
- **The "language-agnostic" length predictor is circular** (§3.1): ≥4 tokens = 42.2% signal vs
  ≤3 = 18.7% [P5], but P(media==0) itself rises from 34.6% to 85.7% with token count [P5-V].

### 4.4 What survives, concretely

**One component transfers cleanly: hazard-precedence over routine-weather.** 31 hazard keeps
with **zero** routine-weather false positives in the tray [P5, confirmed P5-V]. Kept:
`gempa hari ini` (ID), `canicule prévisions` (FR), `nível do guaíba` (BR river level),
`temblor hoy antofagasta` (CL), `unwetterwarnung adria`, `tornado warning near me`,
`huracán fausto` (MX). Dropped: `weather melbourne`, `clima`, `météo pour demain`,
`pogoda elbląg`, `accuweather`, `aurores boréales`. The only hazard misses were lexicon gaps
(RU, Kannada), never confusions with forecast lookups.

**The full surviving candidate set for 2026-07-22** — 19 items, ~16 distinct live stories after
de-duplication (one is a 2001 disaster anniversary, one is the same AU earthquake twice)
[P5-V]:

> CZ `policie zasahuje na pražském magistrátu` · KE `senate ntsa traffic regulations annulment` ·
> DE `kilometer steuer für elektroautos` · ID `kenaikan harga bbm` · RU `отключение света
> владивосток` · UA `ціни на пальне` · TR `asgari ücret` · US `united flight diversion arizona
> military base` · FI `kontulan puukottaja` · BR `nível do guaíba` · IN `flood situation near
> disang river` · LT `kepenų transplantacija` · FR `manon harrois accident` · LV `latvijas
> robežas` · CH `unwetterwarnung adria` · AU `dubbo earthquake` (×2) · JP `名神高速道路事故` ·
> JP Akashi footbridge (anniversary, not news)

Three of the 19 come from countries with <200 press rows/168h, and LV's are Russian-language
queries against a Latvian corpus — i.e. part of the surviving yield is **unverifiable**, not
overlooked (§5).

---

## 5. ATLAS-BLIND vs PRESS-SILENT

This is the honesty rail that decides whether the feature can ship at all. **"No match" has at
least four causes and the current detector conflates all of them into "silence".**

### 5.1 The four classes

| class | definition | measured share / status | fixable? |
|---|---|---|---|
| **ENCODING-BLIND** | Atlas holds the press, mangled beyond matching | ~9pp of measured silence; 46.6% of GDELT rows | **YES — one line** |
| **SEGMENTATION-BLIND** | matcher cannot tokenize the script | 0% of no-space excess explained by encoding; 3-gram arm recovers CJK 80.1→70.6, JP 88.3→84.6, TW 59.8→45.5 | partly — needs script-aware matcher |
| **SUPPLY-BLIND** | Atlas holds ~no press in that language/country | JP kana = 0.277% of corpus; KE = 0.152% | NO — needs ingest |
| **PRESS-SILENT** | press exists in-corpus, in-language, and still does not cover it | the residue; ~19% of the intent tray, uncertified (§2.2 placebo) | — the actual product |

### 5.2 In-script press supply after decoding (48h, headlines about that country) [P7-V]

**The fix works — for space-delimited scripts:**
GR **76.7%** · RU **75.5%** · KR **82.4%** · TW **83.7%** in-script.

**It does not reach these — they are SUPPLY-BLIND:**
JP **26.5%** · TH **33.5%** · IR **17.5%** · IN **17.0%** · RS **13.7%** · IL **12.8%**.

Japanese-kana headlines *anywhere* in the 307,124-row 48h corpus: **851 = 0.277%**
(mainichi.jp 224, asahi.com 144, nhk.or.jp 83). Greek-script: **8,264**. That is the difference
between "press Atlas ingests and mangles" (Greece) and "press Atlas does not ingest" (Japan) —
and P2's original ATLAS-BLIND labels had them the same way round [P7-V, P2-V].

**Domestic outlets Atlas already holds in the countries P2 called blind** [P2-V]: GR **3,809**
headlines from Greek-origin outlets (iefimerida.gr, newsbomb.gr, skai.gr, tanea.gr,
naftemporiki.gr, efsyn.gr, in.gr) of which 3,702 are Greek once decoded; IL **708** from
Israeli outlets (ynet, walla, mako, haaretz, globes, srugim, kikar), 468 Hebrew; TH **159**
Thai-origin, 116 Thai. P2's own artifact recorded GR with 3,809 domestic headlines and
`dom_native_pct = 0.0` — a domestic Greek outlet publishing 3,809 items of which zero are in
Greek is a pipeline impossibility, and it was reported as blindness instead of triggering a
decode check.

### 5.3 Press supply per country — the gradient the current desert flag misses

Per-country press, 24h, 220 countries [P7]:
p5 = **2** · p10 = **5** · p25 = **19** · p50 = **86** · p75 = **419** · p90 = **2,263** ·
p95 = **4,179** · max = **23,625**.

Per-country press, 168h [P5-V]: OM **135** · LB **167** · EE **655** · LV **890** ·
DZ **975** · SY **1,333** · KE **1,447** · IQ **1,616** — versus US **136,198** ·
GB **50,079** · IN **46,808** · RU **37,414** · IT **36,794** · DE **35,223** · IR **32,367**.
At 48h, KE = 462 rows = **0.152%** of the corpus vs US 45,019 = **14.8%** — a ~100× floor [P1].

**`_INFO_DESERT_FLOOR = 40` (`attention_threads.py:80`, consumed at line 246) is miscalibrated
and inverted** [P7]:

- 40 signals/24h sits at ~**p31** of the real distribution; it labels **74/220** countries a
  desert and **0 of the 99** countries that actually have Google-Trends attention.
- It is not predictive, and the sign is backwards. Silent% among Latin-script (always-matchable)
  keywords: **17.9%** at 0–50 press/48h · 15.3% at 50–100 · 27.4% at 400–800 · **33.6%** at
  800–1600 · 27.1% at 6400+. r(log total press, silent%) = **+0.168**; threshold sweep at 40/24h
  gives lift **0.33**.
- After the encoding fix, the only surviving desert axis is *in-script supply = 0* — 50.0% silent
  vs a 34.6% baseline, but **n = 18 pairs** (it was 351 pairs / 79.8% silent *before* the fix).
  Too thin to calibrate a threshold on [P7].

P1's ATLAS-BLIND control ("all 15 sampled countries have real press, so residual silence is
genuine") is a binary that cannot distinguish a 100× coverage floor from press silence, yet KE
civic queries were reported as PRESS-SILENT under it [P1-V]. **A binary desert flag is not
sufficient; the gradient is.**

### 5.4 Blindness on the attention side too

- **Wiki:** 17 stored country codes = 12 language lists [P3-V, P6-V]; `/top-per-country` 404s for
  33 countries [P3], including 8/8 of the low-press-freedom set re-tested [P3-V]. There is no
  usable wiki country axis today.
- **Social:** 80.3% `XX`-ungeocoded; KE 0.9 rows/day, ZA 1.7 [P4]. Absence of a Kenyan story from
  the forum corpus is not evidence Kenyans are not discussing it.
- **`source_lang` is unusable as a primary baseline:** ~60% of press rows are `xx` (unknown)
  [P2, P5-adjacent]. All language-level numbers here are lower bounds; script computed from the
  headline text (post-decode) is the reliable axis.
- **A secondary GDELT defect, unquantified downstream:** 0.53% of GDELT rows fall back to a URL
  slug because `<PAGE_TITLE>` failed the ≥4-word check — CN 11.9%, TW 5.0%, JP 2.3% [P7]
  (`ingest_v2.py:429-441`).

---

## 6. Open questions a spec must answer, and what is not measurable yet

### 6.1 Must be answered before any silent-risk surface ships

1. **What certifies silence, given that lexical matching cannot?** Best measured F1 = 0.74;
   best silent-precision at usable recall = 61.3%; ~40% false-silence floor [P1]; and the
   placebo shows corrections do not improve discrimination [P1-V]. A second stage
   (entity linking / cross-lingual embedding retrieval over `signal_embeddings`) is the obvious
   candidate and **has not been measured at all**.
2. **What are the output bands?** The honesty rails forbid a binary. Minimum viable contract,
   supported by §5: ENCODING-BLIND (until backfilled) / SEGMENTATION-BLIND / SUPPLY-BLIND /
   ENTITY-COVERED-ANGLE-NOT / PRESS-SILENT — each with its receipt and its per-country supply
   number. P1's proposed third band ("entity covered, angle not") is exactly the 6 `E` items it
   hand-labeled and the 35 COVERED-CONCEPT items P5-V found.
3. **What replaces `_INFO_DESERT_FLOOR = 40`?** It is inverted and fires on zero trends
   countries [P7]. A gradient (per-country in-script press supply, post-decode) is measured and
   available; a threshold on it is not calibrated.
4. **What window?** 48h→168h alone moves silence 44.6%→36.3% [P5-V]. The window is currently an
   unexamined constant.
5. **Does the ingest fix get a backfill, and how far back?** Retention is 7d hot; the archive is
   separate. Un-decoded rows already in `signal_embeddings` are the open question below.

### 6.2 Adjacent defects surfaced, not yet investigated

- **Does the encoding bug corrupt the e5 substrate?** ~47% of GDELT rows were embedded from
  mojibake. Not verified [P7 caveat]. This is a far larger blast radius than silent-risk and
  should be probed before anything else in this document is acted on.
- **`thread_ranking._norm_headline` does not unescape**, and 4,355 distinct headline texts exist
  in the corpus in both forms → syndication dedup may be mis-splitting live threads [P1,
  downstream effect unverified].
- **`sr_probe.py`'s candidate-gate bug pattern** (index narrower than the verifier;
  `min` over an absent key returning 0) may exist in other lexical matchers in the codebase —
  unaudited.

### 6.3 Hypotheses that remain untested

- **Recurrence baseline for trends.** `trends_v2` holds 327k rows/14d, so a per-(country,keyword)
  recurrence baseline is computable and would plausibly separate standing utility queries
  (`météo pour demain`, `اذان المغرب`, `clima`) from event queries. **Reasoned from the measured
  shape, never measured** [P6 §8, explicitly flagged by P6 as unmeasured].
- **Attention/coverage RATIO, or a local-source lane** — the original 2026-06-29 parked
  hypothesis. Still unmeasured.
- **Whether the surviving ~16 candidates/day are real overlooked stories.** There is no external
  ground truth anywhere in this measurement. All 400 labels (280 + 120) are single-annotator,
  no second rater, no kappa [P5, P5-V].
- **Whether un-truncated wiki + true baseline + English-title resolution changes the
  deliverable over a week.** Measured on one day: no change (3/25 → 3/25) [P3-V]. Four days of
  ranking overlap exist; four days of *outcome* do not.

### 6.4 Not measurable with the current pipeline

- **Press silence for no-space scripts (JP, TW, CN, TH).** Segmentation blindness and supply
  blindness are confounded: the 3-gram matcher still leaves JP at 84.6% and CJK at 70.6% —
  2.5–3× the Latin baseline [P7-V] — while Atlas holds 851 kana headlines total. Neither can be
  isolated until Japanese/Thai press ingest exists. The no-space cohort is 5.5% of all pairs but
  **12.0% of all residual post-fix silence** [P7-V].
- **Forum engagement.** `signals_v2` has no engagement column and both ingesters sample supply
  [P4-V]. Whether engagement-weighted forum attention would work is **unmeasurable** with the
  current ingest, at any corpus size.
- **Language-level claims.** ~60% of press is `source_lang='xx'`.
- **Seasonality.** Every headline number rests on 24h trend windows in mid-July, with an
  Adriatic storm, Iberian heatwaves, an Indonesian earthquake and Hurricane Fausto running
  concurrently, plus a World Cup window and a Nolan film release [P5, P3]. Hazard and
  entertainment base rates in particular are inflated relative to a quiet week.

### 6.5 What the measurements support, and what they do not

**Supported:**

- Fix `ingest_v2.py:427` (`html.unescape` the `<PAGE_TITLE>` capture) + backfill. Four independent
  measurements of the defect; root cause verified in code; the same function already unescapes
  the same string 30 lines later. This is corpus integrity, not a silent-risk feature.
- Any silent-risk surface must classify into the §5.1 bands rather than emit a binary.
- Do **not** ship a 2-of-3 ensemble gate: it costs 85.7% of the silent set and 8 of 8 known-good
  leads, and every agreement axis is anti-correlated with silence [P6, P6-V].
- Do **not** ship forums as a silent-risk source, in either direction beyond de-noising: presence
  on a silent candidate predicts noise (0.31% civic) and absence is uninformative
  (80.3% ungeocoded) [P4-V].
- Do **not** ship voice-mix as a ranking driver: r = −0.185 / −0.253, sign opposite the
  hypothesis [P7, P7-V].
- `_INFO_DESERT_FLOOR = 40` must be recalibrated or removed before it is trusted anywhere.

**Not supported by anything measured here:**

- "Silent-risk is viable at N candidates/day." The ~16/day figure is one day, one annotator, no
  external check, and sits under an instrument that discriminates current from 5-day-stale press
  by only 17.3pp.
- "The encoding fix resurrects silent-risk." It removes ~9pp of measured silence and improves
  discrimination by 2.3pp [P1-V].
- "The wiki full API resurrects the wiki lane." Deliverable unchanged, 3/25 → 3/25 [P3-V].
- Any claim that a specific country is press-silent without its post-decode in-script supply
  number attached.

---

## 7. Artifact index

All artifacts are in
`/private/tmp/claude-501/-Users-pedro-Desktop-PEDRO-Cursos-ObservatorioGlobal/173558f6-d703-4019-82c3-fe319154bb0c/scratchpad/`
(session-scoped; copy anything load-bearing before it is reaped).

| probe | key artifacts |
|---|---|
| P1 | `sr_probe1_labeled_sample.csv` (the 60 hand adjudications — the deliverable table), `sr_falsesilence.py/.json`, `sr_rule_eval.py`, `sr_window_check.py`, `sr_matcher_audit.py/.json` |
| P1-V | `rx_refutation.md`, `rx_ablate.py/.json` (the 2×2), `rx_placebo.py`, `rx_strat.py`, `rx_labels.py`, `rx_flagship.py`, `rx_flip.py`, `rx_otherday.py`, `rx_rescue_quality.py` |
| P2 | `scriptfold.py`, `probe2.py`, `probe2_summary.tsv/.json`, `probe2_out.json`, `labels.json` |
| P2-V | `ref/REFUTATION.md`, `ref/rpull.py`, `ref/a1`–`a9.py`, `ref/data.pkl`, `ref/dec.pkl`, `ref/match.pkl` |
| P3 | `wiki_surge_ranking.tsv`, `wiki_breadth.py/.json`, `wiki_surge.py/.json`, `wiki_e2e.py/.json`, `wiki_wikidata.py`, `wiki_final.json` |
| P3-V | `rf2_FINDINGS.md`, `rf2_prod_rank.json`, `rf2_true.json`, `rf2_days.json`, `rf2_outcome.json`, `rf2_transfer.json`, `rf2_endpoints.json`, `rf2_atlas_langmix.json` |
| P4 | `PROBE4-forums-verdict.md`, `fx_vol.py`, `social_vol.json`, `fx_surge2.py`, `social_surge_dedup.json`, `fx_bot_corrob.py` |
| P4-V | `RR-PROBE4-refutation.md`, `rr_symmetric.py`, `rr_strat.py`, `rr_surge.py/.json`, `rr_window.py`, `rr_compose.py`, `rr_schema.py` |
| P5 | `p5_filter.py`, `p5_labels.py`, `p5_labels_b.py`, `p5_tray_labels.py`, `p5_sample.json`, `p5_sample_b.json`, `p5_kept_full.json`, `p5_eval_rows.json` |
| P5-V | `rr5_INDEX.json`, `rr5_control_labels.py`, `rr5_tray_adjudication.py`, `rr5_match.py`, `rr5_marquee.py`, `rr5_windows.json`, `rr5_l1dump.py`, `rr5_concept.json` |
| P6 | `probe6_findings.md`, `probe6.py`–`probe6e.py`, `probe6_overlap.json`, `probe6_crosscountry.json`, `social48.json`, `wiki3d.json` |
| P6-V | `rf_probe6_refutation.md`, `rf_wiki_tiers.py`, `rf_wiki_full.json`, `rf_wiki_full_0719.json`, `rf_w2_measure.py`, `rf_w2_direction.py`, `rf_strict_examples.json` |
| P7 | `p7_findings.md`, `p7_pull.py`, `p7_rematch.py/.json`, `p7_rematch_percc.json`, `p7_calib.py`, `p7_desert.py`, `p7_press24.json`, `p7_voice.py`, `p7_script.py` |
| P7-V | `RR-PROBE7-refutation.md` |

Code touched by findings (read-only; nothing modified):
`backend/app/services/ingest_v2.py:427,455-458` · `backend/app/services/ingest_wiki.py:81` ·
`backend/app/services/silent_risk.py` · `backend/app/routers/attention_threads.py:80,229-237,246` ·
`backend/app/services/ingest_lemmy.py:74,114` · `backend/app/services/ingest_bluesky.py:58-59` ·
`backend/app/services/thread_ranking.py` (`_norm_headline`).
