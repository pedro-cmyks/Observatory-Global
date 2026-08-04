# Gold analyst query eval — run 2026-08-04

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-08-04T11:25:33+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 21%** — 3 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.27** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 3 · 1 → 3 · 0 → 8.
- **Conditional answer rate: 23%** over 13 items — excludes the 1 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-09.

## Control arm (reported separately — never averaged into the number above)

- 6 of 6 controls PASSED (a control passes at level ≤1: an honest absence).
- Control distribution: 3 → 0 · 2 → 0 · 1 → 2 · 0 → 4. Mean = 0.333.
- **K1** (mean ≥ 1.0 ⇒ run VOID): **clear**.
  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six controls return an honest floor scores exactly 1.0 and would be voided for behaving correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved after the fact — and the contradiction is logged for rubric v2.
- **K2** (any control scores 3 ⇒ run VOID): **clear**.

### Pair gaps (twin real item minus its control — a gap near zero is the most damaging finding available)

| Control | Twin | Isolates | Control | Twin | Gap |
|---|---|---|---|---|---|
| GQ-15 | GQ-01 | disaster vocabulary vs measured event | 0 | 0 | **+0** |
| GQ-17 | GQ-04 | governance template vs evidence | 0 | 0 | **+0** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 0 | 2 | **+2** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 1 | 0 | **-1** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 1 | 0 | **-1** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 1.0 | 1.0 | 19 | 18 | 1 | 0.0 | — | France Spain Wildfire Battle | Grab-bag: 19 receipts, 1 country code, 1 language, no evacuation figures, no fire-front  |
| GQ-02 | SA | 2 | 1.0 | 0.65 | 60 | 47 | 3 | 0.017 | — | Berlin Gay Pride Attack | Thread is specific to Berlin Pride attack, ROR@20=1.0, 47 outlets, but degraded confiden |
| GQ-03 | SA | 0 | 0.95 | 0.667 | 110 | 88 | 3 | 0.045 | — | Ebola Outbreak Congo | Fails built-in falsification check: presents death toll spread as live disagreement, not |
| GQ-04 | SA | 0 | 0.0 | 0.0 | 12 | 7 | 1 | 0.0 | G3 | Philippines UN Maritime Claim | Thread is about UN maritime claim, not Marcos corruption SONA; ROR@20=0.0. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 10 | 10 | 2 | 0.0 | G3 | Nicaragua Electoral Reform | Served thread is about Nicaragua elections, not Colombia embassy closures; zero receipts |
| GQ-06 | SA | 0 | 1.0 | 0.719 | 57 | 56 | 1 | 0.088 | — | Trump announces Iran talks, Iran denie | No framing side-by-side; single US-Iran talks thread, no Gulf/Arab lane, no state-media  |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 12 | 11 | 1 | 0.0 | G3 | CENTCOM Hormuz Strike Halt | No receipts address the tanker explosion; all cover Hormuz blockade threats, so ROR=0 an |
| GQ-08 | SA | 0 | 1.0 | 1.0 | 1 | 1 | 1 | 0.0 | — | Indonesia Central Bank Governor Resign | Single receipt, one outlet, one country; no rupiah strand; fails independence and G1 cap |
| GQ-09 | SA | 1 | 0.9 | 0.9 | 10 | 10 | 2 | 0.0 | — | Nicaragua Electoral Reform | Foreign coverage only; domestic silence never surfaced, so the actual question is unansw |
| GQ-10 | SA | 1 | 0.0 | 0.0 | 21 | 15 | 2 | 0.048 | G3 | Fitch Maintains Romania Rating | Adjacent-only thread (Fitch rating) honestly served; PSD legal offensive absent, floor p |
| GQ-11 | ST | 2 | 0.833 | 0.833 | 12 | 10 | 1 | 0.0 | — | Kashmir Election Unrest | Answers rigging allegations via Pakistani framing; Indian PoK framing absent, so level 2 |
| GQ-12 | ST | 1 | 1.0 | 1.0 | 2 | 2 | 1 | 0.0 | — | Iran Ukraine Caspian Attack | Adjacent-only: two receipts on the Iran-Ukraine Caspian story, but no Iran response thre |
| GQ-13 | ST | 2 | 0.933 | 0.933 | 15 | 14 | 1 | 0.2 | — | Sudan Child Soldiers | Thin but honest thread: child soldiers story present, confidence flagged thin, label par |
| GQ-14 | ST | 0 | 0.95 | 0.667 | 110 | 88 | 3 | 0.045 | G5 | Ebola Outbreak Congo | Answers a different question: summarizes Ebola coverage, never addresses French/Swahili  |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 24 | 24 | 1 | 0.958 | G2,G3 | Ngaro Track Hike | Confident off-topic answer; no bushfire coverage, no honest floor. |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 57 | 56 | 1 | 0.088 | G3 | Trump announces Iran talks, Iran denie | Honest absence: Lesotho probe returns 0; served thread is Iran, correctly not answering. |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 81 | 52 | 4 | 0.012 | G5,G3 | Ukrainian drone attacks on Russian tar | Served thread is about Ukraine/Russia drones, not Mongolia coal corruption; no evidence  |
| GQ-18 | NC | 0 | 1.0 | 0.65 | 60 | 47 | 3 | 0.017 | — | Berlin Gay Pride Attack | Confident grab-bag on a negative control; names no first outlet but fabricates answerabi |
| GQ-19 | NC | 1 | 1.0 | 1.0 | 16 | 16 | 1 | 0.0 | — | Oil Prices Surge on US-Iran Tensions | Honest floor: Atlas reports coverage of oil falling on Iran pause, declines lead/lag and |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 17 | 16 | 1 | 0.0 | G3 | Iranian Cyberattack on Minnesota Water | Served a cyberattack thread, not Iranian public opinion on ceasefire; no honest absence. |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-01 — score 0 (should_answer)

> Wildfires in France and Spain — how many people have been evacuated, and where is the fire front now?

- **Served:** `dynamic-topic-8460` — France Spain Wildfire Battle
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 19 receipts. Verdict: Grab-bag: 19 receipts, 1 country code, 1 language, no evacuation figures, no fire-front location.
- **Corpus control (6h):** `wildfires` 300 rows / 57 on-topic from 56 sources · `france` 195 rows / 7 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ country_count: 1
- _Evidence:_ distinct_country_codes: 1
- _Evidence:_ distinct_source_langs: 1

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-9474` — Ebola Outbreak Congo
- **Judged:** ROR@20 0.95, ROR@all 0.667 over 60 receipts. Verdict: Fails built-in falsification check: presents death toll spread as live disagreement, not ingest artifact.
- **Corpus control (6h):** `ebola` 28 rows / 25 on-topic from 25 sources · `congo` 32 rows / 24 on-topic from 24 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Payload metadata: temporal_signature=resurrected
- _Evidence:_ Receipt 3: 'República Democrática del Congo eleva a 1.621 la cifra de muertos por ébola'
- _Evidence:_ Receipt 11: 'Έμπολα στο Κονγκό: 3.532 κρούσματα και 1.556 νεκροί'

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-9462` — Philippines UN Maritime Claim
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 12 receipts. Verdict: Thread is about UN maritime claim, not Marcos corruption SONA; ROR@20=0.0.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `marcos` 61 rows / 7 on-topic from 7 sources · `philippines` 24 rows / 2 on-topic from 2 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Philippines deposits Bajo de Masinloc chart with UN amid China objections
- _Evidence:_ Thread label: Philippines UN Maritime Claim

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-5758` — Nicaragua Electoral Reform
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 10 receipts. Verdict: Served thread is about Nicaragua elections, not Colombia embassy closures; zero receipts on-topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 37 rows / 5 on-topic from 5 sources · `cuba` 21 rows / 5 on-topic from 5 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic example: 'About Ortega's election rhetoric, not Colombia's embassy closures'
- _Evidence:_ Thread label: Nicaragua Electoral Reform

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-10022` — Trump announces Iran talks, Iran denies negotiations
- **Judged:** ROR@20 1.0, ROR@all 0.719 over 57 receipts. Verdict: No framing side-by-side; single US-Iran talks thread, no Gulf/Arab lane, no state-media markers.
- **Corpus control (6h):** `iran` 300 rows / 21 on-topic from 16 sources · `western` 43 rows / 4 on-topic from 4 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: 'Trump announces Iran talks, Iran denies negotiations'
- _Evidence:_ country_count: 1
- _Evidence:_ distinct_country_codes: 2

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-8478` — CENTCOM Hormuz Strike Halt
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 12 receipts. Verdict: No receipts address the tanker explosion; all cover Hormuz blockade threats, so ROR=0 and the question is unanswered.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 268 rows / 33 on-topic from 29 sources · `strait` 109 rows / 70 on-topic from 63 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Iran warns continued US maritime blockade could shut Strait of Hormuz, other waterways
- _Evidence:_ Cargo ship reports being struck in Strait of Hormuz as US, Iran claims about talks diverge

### GQ-08 — score 0 (should_answer)

> Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

- **Served:** `dynamic-topic-8057` — Indonesia Central Bank Governor Resigns
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 1 receipts. Verdict: Single receipt, one outlet, one country; no rupiah strand; fails independence and G1 caps at 1.
- **Corpus control (6h):** `indonesia` 128 rows / 1 on-topic from 1 sources · `governor` 181 rows / 7 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ receipts: 1
- _Evidence:_ distinct_outlets: 1
- _Evidence:_ distinct_country_codes: 1

### GQ-09 — score 1 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-5758` — Nicaragua Electoral Reform
- **Judged:** ROR@20 0.9, ROR@all 0.9 over 10 receipts. Verdict: Foreign coverage only; domestic silence never surfaced, so the actual question is unanswered.
- **Corpus control (6h):** `ortega` 10 rows / 0 on-topic from 0 sources · `nicaragua` 1 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ distinct_origin_countries: null, origin_country_available: false
- _Evidence:_ probe_6h: lexical_on_topic_rows: 0, sample_headlines: []
- _Evidence:_ probe_24h: lexical_on_topic_rows: 3, sample_headlines: ["More than 100 days without water..."]

### GQ-10 — score 1 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-9058` — Fitch Maintains Romania Rating
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 21 receipts. Verdict: Adjacent-only thread (Fitch rating) honestly served; PSD legal offensive absent, floor probes show real signals.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 100 rows / 5 on-topic from 4 sources · `bolojan` 13 rows / 8 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Fitch Maintains Romania Rating
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ probe_24h sample: 'Bucharest court suspends five more government decisions at PSD request'

### GQ-12 — score 1 (stretch)

> Ukraine struck an Iranian ship in the Caspian Sea — how is Iran responding?

- **Served:** `dynamic-topic-3805` — Iran Ukraine Caspian Attack
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 2 receipts. Verdict: Adjacent-only: two receipts on the Iran-Ukraine Caspian story, but no Iran response thread; structural absorption.
- **Corpus control (6h):** `ukraine` 165 rows / 18 on-topic from 16 sources · `iranian` 268 rows / 172 on-topic from 148 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Iran demands International Maritime Organization to condemn Ukrainian attack on its ship
- _Evidence:_ Kyiv warns Iran against escalation after Ukraine’s Caspian Sea attack
- _Evidence:_ signal_count: 65, lifetime_signal_count: 205, source_count: 15, country_count: 1

### GQ-14 — score 0 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `dynamic-topic-9474` — Ebola Outbreak Congo
- **Judged:** ROR@20 0.95, ROR@all 0.667 over 60 receipts. Verdict: Answers a different question: summarizes Ebola coverage, never addresses French/Swahili vs English asymmetry.
- **G5:** silent empty: 24h total=0 while 6h total=32 on the same probe, no degraded marker
- **Corpus control (6h):** `congo` 32 rows / 24 on-topic from 24 sources · `ebola` 28 rows / 25 on-topic from 25 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Ebola Outbreak Congo
- _Evidence:_ Receipt 1: 'Mientras el ébola azota el Congo...' (Spanish)
- _Evidence:_ Receipt 4: 'Ebola-Ausbruch im Kongo: WHO warnt – Lage verschärft sich' (German)

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 2 of 20 queries** (GQ-14, GQ-17). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 8 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-01, GQ-03, GQ-04, GQ-05, GQ-06, GQ-07, GQ-08, GQ-14). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
