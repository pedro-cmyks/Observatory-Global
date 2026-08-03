# Gold analyst query eval — run 2026-08-03

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-08-03T13:32:59+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 29%** — 4 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.40** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 4 · 1 → 4 · 0 → 6.
- **Conditional answer rate: 31%** over 13 items — excludes the 1 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-09.

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
| GQ-17 | GQ-04 | governance template vs evidence | 0 | 1 | **+1** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 0 | 2 | **+2** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 1 | 2 | **+1** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 1 | 1 | **+0** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 1.0 | 1.0 | 30 | 27 | 1 | 0.0 | — | France Spain Wildfire Battle | Receipts are all English, single country code ES; fails multilingual and multi-country o |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 31 | 26 | 2 | 0.065 | — | Berlin Gay Pride Attack | Thread is specific to Berlin Pride attack, receipts on-topic, but no accountability stra |
| GQ-03 | SA | 0 | 1.0 | 1.0 | 43 | 37 | 1 | 0.14 | — | Ebola Death Toll Reaches 600 | Fails built-in falsification check: presents historical death-toll spread as live disagr |
| GQ-04 | SA | 1 | 0.85 | 0.889 | 27 | 11 | 1 | 0.0 | G2 | Marcos SONA 2026 Coverage | Honest floor: receipts cover SONA generally but not the corruption scandal question; sin |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 20 | 20 | 2 | 0.0 | G3 | Nicaragua Electoral Reform | Thread is about Nicaragua electoral reform, not Colombia's embassy closures; zero receip |
| GQ-06 | SA | 0 | 1.0 | 1.0 | 33 | 30 | 1 | 0.091 | — | US-Iran Talks Continue | No framing side-by-side; all receipts are US-centric Trump strike-cancellation headlines |
| GQ-07 | SA | 0 | 0.35 | 0.318 | 22 | 15 | 1 | 0.0 | G3 | Iran Stops Hormuz Ships | No independent confirmation; all receipts trace to Iranian state media, no mine-explosio |
| GQ-08 | SA | 2 | 1.0 | 1.0 | 11 | 10 | 1 | 0.0 | — | Indonesia Central Bank Governor Resign | Thread directly answers governor exit and rupiah implications; 10 outlets but only 1 cou |
| GQ-09 | SA | 1 | 0.95 | 0.95 | 20 | 20 | 2 | 0.0 | — | Nicaragua Electoral Reform | Rich foreign coverage but zero domestic Nicaraguan press surfaced; the measured silence  |
| GQ-10 | SA | 1 | 0.0 | 0.0 | 24 | 17 | 2 | 0.042 | G3 | Fitch Maintains Romania Rating | Adjacent Fitch thread, honestly labelled, does not answer PSD lawsuit question. |
| GQ-11 | ST | 0 | 0.3 | 0.391 | 23 | 10 | 1 | 0.0 | G2,G3 | AJK Elections 2026 | Receipts are second-phase heavy; ROR@20=0.3 fails; no honest floor surfaced. |
| GQ-12 | ST | 2 | 1.0 | 1.0 | 30 | 24 | 1 | 0.0 | — | Iran Ukraine Caspian Attack | Directly answers with receipts, but single-country coverage and no origin-country data c |
| GQ-13 | ST | 2 | 0.778 | 0.778 | 18 | 17 | 1 | 0.167 | — | Sudan War Atrocities | Thin thread honestly flagged; answers Sudan war this week with caveats. |
| GQ-14 | ST | 1 | 1.0 | 1.0 | 43 | 37 | 1 | 0.14 | — | Ebola Death Toll Reaches 600 | Thread answers the Ebola outbreak, not the language/origin asymmetry question; honest bu |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 24 | 24 | 1 | 0.958 | G2,G3 | Ngaro Track Hike | Confident off-topic answer: hiking trail receipts, zero bushfire relevance, no honesty f |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 39 | 30 | 1 | 0.0 | G3 | Planning Applications Refused | Honest absence: probes return zero Lesotho signals; served thread is unrelated UK planni |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 43 | 38 | 1 | 0.163 | G3 | Seattle Police Chief Resigns | Fabricated answer on a different story; zero receipts on Mongolia corruption. |
| GQ-18 | NC | 0 | 1.0 | 1.0 | 31 | 26 | 2 | 0.065 | — | Berlin Gay Pride Attack | Confident grab-bag answers a first-outlet question with no outlet named and no temporal  |
| GQ-19 | NC | 1 | 1.0 | 1.0 | 22 | 15 | 1 | 0.0 | — | Iran Stops Hormuz Ships | Honest floor: Atlas reports coverage volume and outlet claims, declines lead/lag and pri |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 15 | 14 | 1 | 0.067 | G3 | Iran Warns Ukraine | Confident grab-bag: thread about ship attack, not public opinion on ceasefire; ROR@all=0 |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-01 — score 0 (should_answer)

> Wildfires in France and Spain — how many people have been evacuated, and where is the fire front now?

- **Served:** `dynamic-topic-8460` — France Spain Wildfire Battle
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 30 receipts. Verdict: Receipts are all English, single country code ES; fails multilingual and multi-country origin requirements.
- **Corpus control (6h):** `wildfires` 213 rows / 53 on-topic from 50 sources · `france` 287 rows / 12 on-topic from 11 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ distinct_country_codes: 1
- _Evidence:_ distinct_source_langs: 1
- _Evidence:_ country_count: 1

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-2344` — Ebola Death Toll Reaches 600
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 43 receipts. Verdict: Fails built-in falsification check: presents historical death-toll spread as live disagreement, no response strand.
- **Corpus control (6h):** `ebola` 16 rows / 9 on-topic from 7 sources · `congo` 25 rows / 11 on-topic from 8 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Ebola Death Toll Reaches 600
- _Evidence:_ Receipt 3: Ebola deaths surpass 1,500 in DRC as outbreak continues to spread
- _Evidence:_ Receipt 20: DR Congo Ebola death toll tops 1,400 as vaccine trials start

### GQ-04 — score 1 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-7801` — Marcos SONA 2026 Coverage
- **Judged:** ROR@20 0.85, ROR@all 0.889 over 27 receipts. Verdict: Honest floor: receipts cover SONA generally but not the corruption scandal question; single-country, thin confidence.
- **G2:** headline_diversity 0.407 < 0.5
- **Corpus control (6h):** `marcos` 55 rows / 3 on-topic from 3 sources · `philippines` 28 rows / 2 on-topic from 2 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Marcos highlights energy, tax, and infrastructure reforms in SONA 2026
- _Evidence:_ Philippines SONA 2026: Marcos Targets Lower Power Bills, Nuclear Energy, Anti-Corruption and Jobs as Filipinos Demand Results
- _Evidence:_ distinct_country_codes: 1

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-5758` — Nicaragua Electoral Reform
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 20 receipts. Verdict: Thread is about Nicaragua electoral reform, not Colombia's embassy closures; zero receipts answer the question.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 17 rows / 2 on-topic from 2 sources · `cuba` 65 rows / 42 on-topic from 38 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic examples: 'About Ortega's election rhetoric, not Colombia's embassy closures.'
- _Evidence:_ Thread label: Nicaragua Electoral Reform

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-9760` — US-Iran Talks Continue
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 33 receipts. Verdict: No framing side-by-side; all receipts are US-centric Trump strike-cancellation headlines, no Iranian or Gulf/Arab voices.
- **Corpus control (6h):** `iran` 300 rows / 70 on-topic from 67 sources · `western` 47 rows / 3 on-topic from 3 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: US-Iran Talks Continue
- _Evidence:_ Receipt 1: [IR|en|thechronicle.com.gh] Trump cancels Iran strikes subject to deal being made 'rapidly'
- _Evidence:_ Receipt 20: [IR|en|bbc.com] Trump says he is cancelling strikes on Iran subject to 'rapidly' making deal

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-2614` — Iran Stops Hormuz Ships
- **Judged:** ROR@20 0.35, ROR@all 0.318 over 22 receipts. Verdict: No independent confirmation; all receipts trace to Iranian state media, no mine-explosion story served.
- **G3:** ROR@all 0.318 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 300 rows / 36 on-topic from 32 sources · `strait` 96 rows / 44 on-topic from 39 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.35  ROR@all = 0.318
- _Evidence:_ Off-topic examples: {"i": 1, "why": "Twin incidents, not mine explosion"}
- _Evidence:_ Thread label: Iran Stops Hormuz Ships

### GQ-09 — score 1 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-5758` — Nicaragua Electoral Reform
- **Judged:** ROR@20 0.95, ROR@all 0.95 over 20 receipts. Verdict: Rich foreign coverage but zero domestic Nicaraguan press surfaced; the measured silence is omitted.
- **Corpus control (6h):** `ortega` 12 rows / 0 on-topic from 0 sources · `nicaragua` 1 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ country_count: 1
- _Evidence:_ distinct_country_codes: 1
- _Evidence:_ distinct_origin_countries: null

### GQ-10 — score 1 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-9058` — Fitch Maintains Romania Rating
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: Adjacent Fitch thread, honestly labelled, does not answer PSD lawsuit question.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 139 rows / 7 on-topic from 6 sources · `bolojan` 22 rows / 10 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Fitch Maintains Romania Rating
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ probe_6h sample: "Romanian Court suspends six Bolojan Government Decisions After PsD Challenge"

### GQ-11 — score 0 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-8315` — AJK Elections 2026
- **Judged:** ROR@20 0.3, ROR@all 0.391 over 23 receipts. Verdict: Receipts are second-phase heavy; ROR@20=0.3 fails; no honest floor surfaced.
- **G2:** headline_diversity 0.435 < 0.5
- **G3:** ROR@all 0.391 < 0.60 (over-merged)
- **Corpus control (6h):** `azad` 30 rows / 6 on-topic from 6 sources · `kashmir` 30 rows / 6 on-topic from 5 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.3  ROR@all = 0.391
- _Evidence:_ Off-topic examples: {"i": 1, "why": "About second phase, not first"}
- _Evidence:_ PPP alleges rigging, irregularities in second phase of AJK polls

### GQ-14 — score 1 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `dynamic-topic-2344` — Ebola Death Toll Reaches 600
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 43 receipts. Verdict: Thread answers the Ebola outbreak, not the language/origin asymmetry question; honest but adjacent.
- **Corpus control (6h):** `congo` 25 rows / 9 on-topic from 7 sources · `ebola` 16 rows / 9 on-topic from 7 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Ebola Death Toll Reaches 600
- _Evidence:_ distinct_source_langs: 1
- _Evidence:_ sample_headlines: ["DR Congo facing largest ever Ebola outbreak  WHO", ...]

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 0 of 20 queries** (none). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 6 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-01, GQ-03, GQ-05, GQ-06, GQ-07, GQ-11). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
