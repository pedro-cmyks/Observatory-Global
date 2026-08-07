# Gold analyst query eval — run 2026-08-07

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-08-07T11:20:41+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 14%** — 2 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.25** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 2 · 1 → 3 · 0 → 9.
- **Conditional answer rate: 18%** over 11 items — excludes the 3 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-04, GQ-09, GQ-11.

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
| GQ-17 | GQ-04 | governance template vs evidence | 0 | 0 | **+0** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 1 | 2 | **+1** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 1 | 0 | **-1** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 1 | 0 | **-1** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 0.0 | 0.0 | 15 | 14 | 1 | 0.067 | G3 | Climate Change Wildfires | Receipts are climate-attribution stories, not evacuation/fire-front coverage; ROR@20=0.0 |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 14 | 14 | 1 | 0.0 | — | Pride Security After Berlin Attack | Thread is specific to Berlin Pride attack aftermath; accountability strand absent, so le |
| GQ-03 | SA | 0 | 1.0 | 1.0 | 47 | 40 | 1 | 0.043 | — | DR Congo Ebola Outbreak | Fails falsification check: presents death toll spread as live disagreement, not ingest a |
| GQ-04 | SA | 0 | 0.0 | 0.0 | 12 | 7 | 1 | 0.0 | G3 | Philippines UN Maritime Claim | Thread is about Philippines UN maritime claim, not Marcos corruption SONA; zero receipts |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 14 | 13 | 1 | 0.071 | G3 | Cuba Blackouts | Served thread is about Cuba blackouts, not Colombia embassy closures; zero receipts on-t |
| GQ-06 | SA | 0 | 0.0 | 0.0 | 14 | 14 | 1 | 0.0 | G3 | Iran Warns Ukraine | Thread is a different story (Iran-Ukraine ship incident), not the asked US-Iran pause fr |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 33 | 29 | 2 | 0.03 | G3 | Iran Hormuz Threat | No receipts address the tanker explosion; all are Trump-Hormuz threats. Corroboration ve |
| GQ-08 | SA | 0 | 0.0 | 0.0 | 13 | 10 | 2 | 0.0 | G3 | Indonesia All Stars vs Aston Villa | Served thread is a football match story, zero receipts on the central bank governor or r |
| GQ-09 | SA | 0 | 0.5 | 0.656 | 32 | 26 | 2 | 0.0 | — | Nicaragua Electoral Reform | Fails the core question: no domestic Nicaraguan press surfaced, and the silence finding  |
| GQ-10 | SA | 0 | 0.0 | 0.0 | 25 | 16 | 2 | 0.04 | G5,G3 | Fitch Maintains Romania Rating | Served thread is Fitch rating, not PSD lawsuit; ROR@all=0.0, silent empty at 24h unflagg |
| GQ-11 | ST | 1 | 0.556 | 0.556 | 9 | 5 | 1 | 0.0 | G3 | AJK Poll Rigging Allegations | Honest floor: receipts are second-phase rigging, not first-phase; Atlas flags thin cover |
| GQ-12 | ST | 2 | 0.95 | 0.968 | 31 | 27 | 2 | 0.0 | — | Iran Ukraine Caspian Attack | Directly answers with receipts holding the Iran-Ukraine connection; capped at 2 by G7. |
| GQ-13 | ST | 1 | 0.933 | 0.933 | 15 | 14 | 1 | 0.2 | — | Sudan Child Soldiers | Honest thin thread, correctly flagged, but does not answer the weekly war question. |
| GQ-14 | ST | 1 | 1.0 | 1.0 | 69 | 54 | 1 | 0.116 | — | DR Congo Ebola Outbreak | Thread covers Ebola outbreak but ignores the language/origin asymmetry question entirely |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 28 | 21 | 1 | 0.071 | G3 | H5N1 Bird Flu in Australia | Confident wrong answer: bird flu thread served for bushfire evacuation question, zero on |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 24 | 24 | 1 | 0.167 | G3 | New Mexico Epstein Lawsuit | Honest absence: no Lesotho textile thread; probes return thin, off-topic signals only. |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 31 | 22 | 1 | 0.032 | G3 | NEET Protest Case Withdrawals | Served NEET protest thread, zero relevance to Mongolia coal corruption; no honest absenc |
| GQ-18 | NC | 1 | 0.786 | 0.786 | 14 | 14 | 1 | 0.0 | — | Pride Security After Berlin Attack | Honest floor: Atlas served a labelled thread but never named a first outlet or diffusion |
| GQ-19 | NC | 1 | 1.0 | 1.0 | 33 | 29 | 2 | 0.03 | — | Iran Hormuz Threat | Honest floor: Atlas reports coverage volume and Trump threat headlines, declines price c |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 19 | 18 | 1 | 0.0 | G3 | Iranian Cyberattack on Minnesota Water | Confident grab-bag on cyberattacks, zero receipts on Iranian public opinion; no honest a |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-01 — score 0 (should_answer)

> Wildfires in France and Spain — how many people have been evacuated, and where is the fire front now?

- **Served:** `dynamic-topic-8872` — Climate Change Wildfires
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 15 receipts. Verdict: Receipts are climate-attribution stories, not evacuation/fire-front coverage; ROR@20=0.0, no honest flag.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `wildfires` 80 rows / 9 on-topic from 8 sources · `france` 191 rows / 7 on-topic from 7 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Expert warns Western Europe warming faster than global average as wildfire risk escalates
- _Evidence:_ Climate Change Made Spanish, French Fires Much More Likely: Scientists

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-898` — DR Congo Ebola Outbreak
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 47 receipts. Verdict: Fails falsification check: presents death toll spread as live disagreement, not ingest artifact.
- **Corpus control (6h):** `ebola` 97 rows / 59 on-topic from 52 sources · `congo` 48 rows / 36 on-topic from 29 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Ebola kills 1,700 in eastern Congo as fastest-growing outbreak surges
- _Evidence:_ Ebola death toll in DR Congo surpasses 1,700
- _Evidence:_ Ebola death toll in DR Congo tops 1,600 — WHO

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-9462` — Philippines UN Maritime Claim
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 12 receipts. Verdict: Thread is about Philippines UN maritime claim, not Marcos corruption SONA; zero receipts on-topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `marcos` 92 rows / 2 on-topic from 2 sources · `philippines` 27 rows / 1 on-topic from 1 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Philippines deposits Bajo de Masinloc chart with UN amid China objections
- _Evidence:_ PH strengthens claim, files WPS map at UN
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-9856` — Cuba Blackouts
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 14 receipts. Verdict: Served thread is about Cuba blackouts, not Colombia embassy closures; zero receipts on-topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 69 rows / 9 on-topic from 8 sources · `cuba` 23 rows / 2 on-topic from 2 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Protests Erupt Across Cuba Amidst Widespread Blackouts
- _Evidence:_ Cuba says electric grid reconnected after nationwide blackout
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-7736` — Iran Warns Ukraine
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 14 receipts. Verdict: Thread is a different story (Iran-Ukraine ship incident), not the asked US-Iran pause framing.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iran` 300 rows / 24 on-topic from 22 sources · `western` 47 rows / 9 on-topic from 8 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: 'Iran Warns Ukraine'
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Iran Pauses Retaliation After Ukraine Claims Vessel Attack Was Mistake'

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-2831` — Iran Hormuz Threat
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 33 receipts. Verdict: No receipts address the tanker explosion; all are Trump-Hormuz threats. Corroboration verdict absent.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 26 rows / 4 on-topic from 3 sources · `strait` 105 rows / 49 on-topic from 44 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0 ROR@all = 0.0
- _Evidence:_ Off-topic examples: {"i": 1, "why": "About Trump threats, not tanker explosion"}
- _Evidence:_ 1. [IR|en|breitbart.com] Trump Warns: Hormuz Will Open 'Very Soon' or Iran Will Get 'Hit Hard'

### GQ-08 — score 0 (should_answer)

> Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

- **Served:** `dynamic-topic-10568` — Indonesia All Stars vs Aston Villa
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 13 receipts. Verdict: Served thread is a football match story, zero receipts on the central bank governor or rupiah.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `indonesia` 154 rows / 3 on-topic from 3 sources · `governor` 300 rows / 8 on-topic from 7 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Indonesia All Stars vs Aston Villa
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic example: Football match, not central bank

### GQ-09 — score 0 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-5758` — Nicaragua Electoral Reform
- **Judged:** ROR@20 0.5, ROR@all 0.656 over 32 receipts. Verdict: Fails the core question: no domestic Nicaraguan press surfaced, and the silence finding is absent.
- **Corpus control (6h):** `ortega` 5 rows / 0 on-topic from 0 sources · `nicaragua` 4 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ country_count: 1
- _Evidence:_ distinct_country_codes: 1
- _Evidence:_ subject_countries: ["NI"]

### GQ-10 — score 0 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-9058` — Fitch Maintains Romania Rating
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 25 receipts. Verdict: Served thread is Fitch rating, not PSD lawsuit; ROR@all=0.0, silent empty at 24h unflagged.
- **G5:** silent empty: 24h total=0 while 6h total=193 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 193 rows / 13 on-topic from 10 sources · `bolojan` 32 rows / 15 on-topic from 12 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0 ROR@all = 0.0
- _Evidence:_ Off-topic examples: {"i": 1, "why": "About Fitch rating, not PSD lawsuit"}
- _Evidence:_ probe_24h: {"total": 0, "coverageTier": "thin", "warnings": ["query_thread_match_degraded", "query_thread_thin_coverage"]}

### GQ-11 — score 1 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-10323` — AJK Poll Rigging Allegations
- **Judged:** ROR@20 0.556, ROR@all 0.556 over 9 receipts. Verdict: Honest floor: receipts are second-phase rigging, not first-phase; Atlas flags thin coverage and partial geography.
- **G3:** ROR@all 0.556 < 0.60 (over-merged)
- **Corpus control (6h):** `azad` 11 rows / 2 on-topic from 2 sources · `kashmir` 13 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: AJK Poll Rigging Allegations
- _Evidence:_ Payload metadata: confidence=thin, subject_geography_status=partial
- _Evidence:_ Receipt 6: PPP alleges rigging, irregularities in second phase of AJK polls

### GQ-13 — score 1 (stretch)

> The war in Sudan — what has happened this week?

- **Served:** `dynamic-topic-9000` — Sudan Child Soldiers
- **Judged:** ROR@20 0.933, ROR@all 0.933 over 15 receipts. Verdict: Honest thin thread, correctly flagged, but does not answer the weekly war question.
- **Corpus control (6h):** `sudan` 41 rows / 3 on-topic from 3 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ confidence=thin
- _Evidence:_ label_status=partial
- _Evidence:_ Thread label: Sudan Child Soldiers

### GQ-14 — score 1 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `dynamic-topic-10914` — DR Congo Ebola Outbreak
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 60 receipts. Verdict: Thread covers Ebola outbreak but ignores the language/origin asymmetry question entirely.
- **Corpus control (6h):** `congo` 48 rows / 37 on-topic from 30 sources · `ebola` 96 rows / 56 on-topic from 49 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: DR Congo Ebola Outbreak
- _Evidence:_ distinct_source_langs: 1
- _Evidence:_ sample_headlines: ["Congo's Ebola Outbreak Surpasses 4k Cases", "Ebola i DR Congo: Over 4000 bekræftede smittetilfælde og 1850 døde"]

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 1 of 20 queries** (GQ-10). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 7 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-01, GQ-03, GQ-05, GQ-06, GQ-07, GQ-08, GQ-10). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
