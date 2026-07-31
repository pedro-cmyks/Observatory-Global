# Gold analyst query eval — run 2026-07-31

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-07-31T13:33:14+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 21%** — 3 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.09** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 1 · 2 → 2 · 1 → 1 · 0 → 10.
- **Conditional answer rate: 25%** over 12 items — excludes the 2 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-09, GQ-13.

## Control arm (reported separately — never averaged into the number above)

- 6 of 6 controls PASSED (a control passes at level ≤1: an honest absence).
- Control distribution: 3 → 0 · 2 → 0 · 1 → 3 · 0 → 3. Mean = 0.5.
- **K1** (mean ≥ 1.0 ⇒ run VOID): **clear**.
  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six controls return an honest floor scores exactly 1.0 and would be voided for behaving correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved after the fact — and the contradiction is logged for rubric v2.
- **K2** (any control scores 3 ⇒ run VOID): **clear**.

### Pair gaps (twin real item minus its control — a gap near zero is the most damaging finding available)

| Control | Twin | Isolates | Control | Twin | Gap |
|---|---|---|---|---|---|
| GQ-15 | GQ-01 | disaster vocabulary vs measured event | 0 | 0 | **+0** |
| GQ-17 | GQ-04 | governance template vs evidence | 1 | 0 | **-1** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 0 | 2 | **+2** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 1 | 2 | **+1** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 1 | 0 | **-1** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 0.0 | 0.0 | 9 | 9 | 1 | 0.0 | G3 | Tour de France Wildfire Impact | Thread is Tour de France rerouting, not evacuations or fire front; ROR@20=0.0. |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 13 | 13 | 1 | 0.0 | — | Berlin Pride Terror Attack | Answers the Berlin Pride attack with receipts, but accountability strand absent and sing |
| GQ-03 | SA | 0 | 0.0 | 0.0 | 88 | 72 | 4 | 0.023 | G3 | US Bombards Iran Over Ormuz Attack | Thread is entirely about US-Iran conflict, not Ebola; no answer to the question. |
| GQ-04 | SA | 0 | 0.85 | 0.87 | 23 | 8 | 1 | 0.0 | G2 | SONA 2026 Coverage | Receipts cover SONA logistics, not the corruption scandal; question unanswered. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 11 | 9 | 1 | 0.0 | G3 | Julián Álvarez Transfer Standoff | Served thread is about a soccer dispute, not the embassy closures; zero receipts on topi |
| GQ-06 | SA | 0 | 0.0 | 0.0 | 13 | 12 | 1 | 0.0 | G3 | US Control of Strait of Hormuz | Thread is about frozen assets, not paused strikes; no framing receipts; ROR=0. |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 13 | 12 | 1 | 0.0 | G3 | US Control of Strait of Hormuz | No receipts address the tanker explosion; all are about frozen assets, so the question i |
| GQ-08 | SA | 2 | 1.0 | 1.0 | 11 | 10 | 1 | 0.0 | — | Perry Warjiyo Resigns | Thread answers the resignation but lacks rupiah/policy-consequence strand and non-Indone |
| GQ-09 | SA | 0 | 0.0 | 0.0 | 352 | 204 | 4 | 0.028 | G3 | Iran Attacks Condemned | Served thread is entirely Iran conflict; zero Nicaragua receipts, no honest floor surfac |
| GQ-10 | SA | 0 | 0.0 | 0.0 | 20 | 15 | 2 | 0.05 | G3 | Russian Ambassador Summoned | Served thread is Russian drone story, not PSD lawsuit; ROR@all=0.0, no honest floor. |
| GQ-11 | ST | 0 | 0.125 | 0.125 | 8 | 7 | 1 | 0.0 | G3 | AJK Elections 2026 First Phase | Receipts are about polling/results, not rigging allegations; ROR@20=0.125 fails level 1. |
| GQ-12 | ST | 3 | 1.0 | 1.0 | 24 | 20 | 1 | 0.0 | — | Ukrainian Drone Strikes on Russian Shi | Directly answers with tight Iran-Ukraine Caspian thread; 20+ outlets, ROR 1.0, no defect |
| GQ-13 | ST | 0 | 0.0 | 0.0 | 25 | 23 | 1 | 0.12 | G5,G3 | Netanyahu Mamdani Feud | Confident grab-bag on Netanyahu/Mamdani with zero Sudan receipts and no thinness flag in |
| GQ-14 | ST | 1 | None | None | 0 | 0 | 0 | None | — | — | Honest floor only: no thread, probes show coverage exists but question unanswered. |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 30 | 30 | 1 | 0.967 | G2,G3 | Supporting Australian Theatre | Confident off-topic answer: theatre thread served for bushfire evacuation question, no r |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 50 | 35 | 3 | 0.02 | G3 | US Tariffs on Brazil | Honest absence: probes return zero Lesotho receipts; served thread is Brazil tariffs, co |
| GQ-17 | NC | 1 | 0.0 | 0.0 | 31 | 20 | 1 | 0.0 | G5,G3 | Supreme Court Rules on Police Force Du | Honest absence: no Mongolia thread, probes show thin/degraded coverage, no fabricated an |
| GQ-18 | NC | 0 | 1.0 | 1.0 | 13 | 13 | 1 | 0.0 | — | Berlin Pride Terror Attack | Confident grab-bag on a negative control; names no first outlet but renders a spread seq |
| GQ-19 | NC | 1 | 0.0 | 0.0 | 15 | 14 | 1 | 0.0 | G3 | Iran Oil Sales During War | Honest floor: Atlas reports Iran oil sales thread but declines coverage-price causality  |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 15 | 14 | 1 | 0.0 | G3 | Iran Oil Sales During War | Confident grab-bag: oil-sales thread labeled as answering public-opinion question, zero  |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-01 — score 0 (should_answer)

> Wildfires in France and Spain — how many people have been evacuated, and where is the fire front now?

- **Served:** `dynamic-topic-7744` — Tour de France Wildfire Impact
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 9 receipts. Verdict: Thread is Tour de France rerouting, not evacuations or fire front; ROR@20=0.0.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `wildfires` 130 rows / 45 on-topic from 42 sources · `france` 292 rows / 41 on-topic from 38 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Thread label: Tour de France Wildfire Impact
- _Evidence:_ 1. [FR|en|wtvq.com] France trims Tour de France finale while battling historic wildfires

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-8727` — US Bombards Iran Over Ormuz Attack
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Thread is entirely about US-Iran conflict, not Ebola; no answer to the question.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `ebola` 31 rows / 14 on-topic from 13 sources · `congo` 31 rows / 12 on-topic from 11 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: US Bombards Iran Over Ormuz Attack
- _Evidence:_ ROR@20 = 0.0 ROR@all = 0.0
- _Evidence:_ Off-topic examples: About US-Iran attacks, not Ebola

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-7801` — SONA 2026 Coverage
- **Judged:** ROR@20 0.85, ROR@all 0.87 over 23 receipts. Verdict: Receipts cover SONA logistics, not the corruption scandal; question unanswered.
- **G2:** headline_diversity 0.4 < 0.5
- **Corpus control (6h):** `marcos` 78 rows / 3 on-topic from 3 sources · `philippines` 27 rows / 3 on-topic from 3 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Receipt 2: '[In the Public Square] Marcos SONA 2026: Reality check'
- _Evidence:_ Receipt 4: 'FULL TEXT: President Ferdinand Marcos Jr.’s SONA 2026'
- _Evidence:_ Payload metadata: country_count=1, distinct_country_codes=1

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-4985` — Julián Álvarez Transfer Standoff
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 11 receipts. Verdict: Served thread is about a soccer dispute, not the embassy closures; zero receipts on topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 68 rows / 36 on-topic from 36 sources · `cuba` 24 rows / 3 on-topic from 3 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Julián Álvarez Transfer Standoff
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic example: 'About soccer coach dispute, not embassies'

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-4713` — US Control of Strait of Hormuz
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 13 receipts. Verdict: Thread is about frozen assets, not paused strikes; no framing receipts; ROR=0.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iran` 300 rows / 72 on-topic from 66 sources · `western` 116 rows / 8 on-topic from 8 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: US Control of Strait of Hormuz
- _Evidence:_ ROR@20 = 0.0 ROR@all = 0.0
- _Evidence:_ Off-topic example: 'About frozen assets, not paused strikes'

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-4713` — US Control of Strait of Hormuz
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 13 receipts. Verdict: No receipts address the tanker explosion; all are about frozen assets, so the question is unanswered.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 54 rows / 4 on-topic from 4 sources · `strait` 106 rows / 8 on-topic from 8 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Iran warns countries against using frozen assets under Trump plan
- _Evidence:_ Trump says future maritime damages will be paid by US-controlled Iranian assets
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0

### GQ-09 — score 0 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-8763` — Iran Attacks Condemned
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Served thread is entirely Iran conflict; zero Nicaragua receipts, no honest floor surfaced.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `ortega` 11 rows / 0 on-topic from 0 sources · `nicaragua` 4 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Iran Attacks Condemned
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ 1. [IR|en|vietnamtribune.com] Drone hangars, fuel depot destroyed at US base in Kuwait: IRGC

### GQ-10 — score 0 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-6354` — Russian Ambassador Summoned
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 20 receipts. Verdict: Served thread is Russian drone story, not PSD lawsuit; ROR@all=0.0, no honest floor.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 183 rows / 4 on-topic from 4 sources · `bolojan` 12 rows / 6 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Thread label: Russian Ambassador Summoned
- _Evidence:_ Off-topic examples: {"i": 1, "why": "Russian ambassador drone scandal, not PSD lawsuit"}

### GQ-11 — score 0 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-8315` — AJK Elections 2026 First Phase
- **Judged:** ROR@20 0.125, ROR@all 0.125 over 8 receipts. Verdict: Receipts are about polling/results, not rigging allegations; ROR@20=0.125 fails level 1.
- **G3:** ROR@all 0.125 < 0.60 (over-merged)
- **Corpus control (6h):** `azad` 19 rows / 3 on-topic from 3 sources · `kashmir` 19 rows / 2 on-topic from 2 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.125  ROR@all = 0.125
- _Evidence:_ Off-topic examples: {"i": 1, "why": "Results, not rigging allegations"}
- _Evidence:_ Receipt 5: "First phase of AJK polls underway in Mirpur division amid allegations of rigging"

### GQ-13 — score 0 (stretch)

> The war in Sudan — what has happened this week?

- **Served:** `dynamic-topic-8818` — Netanyahu Mamdani Feud
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 25 receipts. Verdict: Confident grab-bag on Netanyahu/Mamdani with zero Sudan receipts and no thinness flag in served payload.
- **G5:** silent empty: 24h total=0 while 6h total=8 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `sudan` 8 rows / 1 on-topic from 1 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Netanyahu accuses Mamdani of 'fomenting hate' and calls ICC war-crimes charges 'bogus'
- _Evidence:_ coherence.warning=null

### GQ-14 — score 1 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `no candidate thread` — —
- **Judged:** ROR@20 None, ROR@all None over 0 receipts. Verdict: Honest floor only: no thread, probes show coverage exists but question unanswered.
- **Corpus control (6h):** `congo` 32 rows / 13 on-topic from 12 sources · `ebola` 33 rows / 16 on-topic from 15 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Best answer attempt: no candidate thread in the served lists; floor probe only
- _Evidence:_ probe_24h: total 134, coverageTier ok, lexical_on_topic_rows 55
- _Evidence:_ Verbatim-question probe: total 0, coverageTier thin, warnings query_thread_thin_coverage

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 2 of 20 queries** (GQ-13, GQ-17). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 8 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-01, GQ-03, GQ-04, GQ-05, GQ-06, GQ-07, GQ-10, GQ-11). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
