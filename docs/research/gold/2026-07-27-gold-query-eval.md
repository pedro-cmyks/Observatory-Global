# Gold analyst query eval — run 2026-07-27

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-07-27T19:33:10+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 14%** — 2 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.17** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 2 · 1 → 2 · 0 → 10.
- **Conditional answer rate: 17%** over 12 items — excludes the 2 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-04, GQ-13.

## Control arm (reported separately — never averaged into the number above)

- 6 of 6 controls PASSED (a control passes at level ≤1: an honest absence).
- Control distribution: 3 → 0 · 2 → 0 · 1 → 1 · 0 → 5. Mean = 0.167.
- **K1** (mean ≥ 1.0 ⇒ run VOID): **clear**.
  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six controls return an honest floor scores exactly 1.0 and would be voided for behaving correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved after the fact — and the contradiction is logged for rubric v2.
- **K2** (any control scores 3 ⇒ run VOID): **clear**.

### Pair gaps (twin real item minus its control — a gap near zero is the most damaging finding available)

| Control | Twin | Isolates | Control | Twin | Gap |
|---|---|---|---|---|---|
| GQ-15 | GQ-01 | disaster vocabulary vs measured event | 0 | 2 | **+2** |
| GQ-17 | GQ-04 | governance template vs evidence | 0 | 0 | **+0** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 0 | 2 | **+2** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 1 | 0 | **-1** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 0 | 0 | **+0** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 2 | 1.0 | 0.933 | 95 | 70 | 3 | 0.053 | — | Fontainebleau Forest Fire | Answers the question with attributed evacuation figures but label_status=failed caps at  |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 26 | 17 | 1 | 0.115 | — | Emerging (DE): Berlino: Suv sulla foll | Answers Berlin Pride attack with 26 receipts, all on-topic, but lacks accountability str |
| GQ-03 | SA | 0 | 1.0 | 1.0 | 25 | 16 | 1 | 0.0 | — | DR Congo Ebola Outbreak | Fails: presents death toll spread as live disagreement, violating time-artifact rule. |
| GQ-04 | SA | 0 | 0.0 | 0.0 | 24 | 22 | 1 | 0.0 | G3 | Emerging (PH): Philippines, China trad | Receipts are about Scarborough Shoal clash, not Marcos corruption scandal or SONA. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 27 | 25 | 1 | 0.074 | G5,G3 | Nicaragua Ends Elections | Receipts are entirely about Nicaragua elections, not Colombia's embassy closures. |
| GQ-06 | SA | 0 | 0.0 | 0.0 | 26 | 24 | 1 | 0.077 | G5,G3 | Pentagon Concealed Iran Strike Injurie | No framing of pause; all receipts off-topic; silent empty defect. |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 22 | 22 | 1 | 0.045 | G5,G3 | US Blockade Iran Strait | All receipts are about Trump threats, not the tanker explosion. |
| GQ-08 | SA | 0 | 0.0 | 0.0 | 23 | 17 | 1 | 0.0 | G3 | Emerging (ID): Indonesia arrests ex-pr | Receipts are entirely about unrelated crime stories, not the governor's exit. |
| GQ-09 | SA | 1 | 1.0 | 1.0 | 27 | 25 | 1 | 0.074 | — | Nicaragua Ends Elections | Foreign coverage abundant but domestic silence unaddressed; honest floor. |
| GQ-10 | SA | 0 | 0.0 | 0.0 | 13 | 13 | 1 | 0.0 | G3 | Emerging (RO): Romania shoots down thi | Thread is about drone incidents, not PSD legal action against Bolojan government. |
| GQ-11 | ST | 0 | 0.0 | 0.0 | 24 | 16 | 2 | 0.0 | G3 | Mumbai Tree Collapse Deaths | All 24 receipts are about monsoon rains, not Azad Kashmir elections. |
| GQ-12 | ST | 0 (judge 1, capped) | 0.0 | 0.0 | 24 | 23 | 1 | 0.0 | G5,G3 | Russian Infrastructure Attack Warnings | Adjacent-only: served thread is about Iran-Russia CIA strikes, not Ukraine ship strike. |
| GQ-13 | ST | 1 | 0.625 | 0.625 | 16 | 11 | 2 | 0.688 | G2 | Sudan Conflict Updates | Honest floor: Atlas returns thin, partial signal with no confident answer. |
| GQ-14 | ST | 0 | 1.0 | 1.0 | 25 | 16 | 1 | 0.0 | — | DR Congo Ebola Outbreak | Ignores the comparative language question entirely; serves only English Ebola coverage. |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 24 | 24 | 1 | 0.958 | G2,G5,G3 | Visa Fee Increase | Thread is about visa fee increase, not bushfire evacuation; ROR@all=0.0. |
| GQ-16 | NC | 0 | 0.0 | 0.0 | 41 | 37 | 3 | 0.024 | G3 | Trump Threatens Canada Tariffs Over Wi | No evidence for Lesotho textile closures; served thread is about Canada wildfires. |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 53 | 44 | 3 | 0.491 | G2,G3 | Andy Burnham Prime Minister | Thread is about Andy Burnham and India, not Mongolia coal corruption. |
| GQ-18 | NC | 0 | 1.0 | 1.0 | 26 | 17 | 1 | 0.115 | — | Emerging (DE): Berlino: Suv sulla foll | Confident answer naming no first outlet but fabricating a story outside corpus. |
| GQ-19 | NC | 1 | 1.0 | 1.0 | 22 | 22 | 1 | 0.045 | — | US Blockade Iran Strait | Honest floor: Atlas reports coverage but declines causal or forward price view. |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 44 | 23 | 2 | 0.068 | G5,G3 | US Attacks Iran Retaliation | No receipts address public opinion; all are conflict escalation coverage. |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-898` — DR Congo Ebola Outbreak
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 25 receipts. Verdict: Fails: presents death toll spread as live disagreement, violating time-artifact rule.
- **Corpus control (6h):** `ebola` 49 rows / 22 on-topic from 15 sources · `congo` 39 rows / 15 on-topic from 11 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Receipt 1: '1,405 deaths'; Receipt 2: 'past 1,300'; Receipt 5: '1033'; Receipt 20: '930'
- _Evidence:_ Payload metadata: warnings=["dynamic_topic_member_preview_sample"] but no flag for temporal artifact

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-6403` — Emerging (PH): Philippines, China trade blame after water cannon clash near Scarborough Shoal in South C…
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: Receipts are about Scarborough Shoal clash, not Marcos corruption scandal or SONA.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `marcos` 0 rows / 0 on-topic from 0 sources · `philippines` 0 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Philippines, China trade blame after water cannon clash near Scarborough Shoal'
- _Evidence:_ Receipt 5: 'Marcos condemns China Coast Guard assault'

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-5754` — Nicaragua Ends Elections
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 27 receipts. Verdict: Receipts are entirely about Nicaragua elections, not Colombia's embassy closures.
- **G5:** silent empty: 24h total=0 while 6h total=128 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 128 rows / 29 on-topic from 26 sources · `cuba` 91 rows / 25 on-topic from 23 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Nicaragua's President Ortega says there will be no more elections'
- _Evidence:_ Receipt 3: 'Nicaragua's Parliament Moving to Abolish Elections'

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-5450` — Pentagon Concealed Iran Strike Injuries
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 26 receipts. Verdict: No framing of pause; all receipts off-topic; silent empty defect.
- **G5:** silent empty: 24h total=0 while 6h total=300 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iran` 300 rows / 42 on-topic from 39 sources · `western` 73 rows / 1 on-topic from 1 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ probe_24h total=0 while probe_6h total=300, no degraded marker (G5)
- _Evidence:_ All 26 receipts about US-Iran strikes/injuries, not pause

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-2817` — US Blockade Iran Strait
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 22 receipts. Verdict: All receipts are about Trump threats, not the tanker explosion.
- **G5:** silent empty: 24h total=0 while 6h total=275 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 275 rows / 26 on-topic from 24 sources · `strait` 144 rows / 26 on-topic from 24 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Trump: US will attack Iranian bridge, power plant for every ship targeted in Hormuz'
- _Evidence:_ Harness-detected rule G3: 'ROR@all 0.0 < 0.60 (over-merged)'

### GQ-08 — score 0 (should_answer)

> Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

- **Served:** `dynamic-topic-6727` — Emerging (ID): Indonesia arrests ex-prosecutor after seizing $19 mn and gold
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 23 receipts. Verdict: Receipts are entirely about unrelated crime stories, not the governor's exit.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `indonesia` 0 rows / 0 on-topic from 0 sources · `governor` 300 rows / 3 on-topic from 3 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Indonesia arrests ex-prosecutor after seizing $19 mn and gold
- _Evidence:_ Why Indonesian central bank governor Perry Warjiyo's sudden exit matters (probe only, not served)

### GQ-09 — score 1 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-5754` — Nicaragua Ends Elections
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 27 receipts. Verdict: Foreign coverage abundant but domestic silence unaddressed; honest floor.
- **Corpus control (6h):** `ortega` 11 rows / 4 on-topic from 4 sources · `nicaragua` 36 rows / 7 on-topic from 7 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ distinct_country_codes: 1
- _Evidence:_ distinct_origin_countries: null
- _Evidence:_ origin_country_available: false

### GQ-10 — score 0 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-7013` — Emerging (RO): Romania shoots down third drone that entered its airspace
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 13 receipts. Verdict: Thread is about drone incidents, not PSD legal action against Bolojan government.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 282 rows / 8 on-topic from 6 sources · `bolojan` 13 rows / 10 on-topic from 8 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Romania shoots down third drone that entered its airspace
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic examples: Drone incident, not PSD legal action

### GQ-11 — score 0 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-1740` — Mumbai Tree Collapse Deaths
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: All 24 receipts are about monsoon rains, not Azad Kashmir elections.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `azad` 33 rows / 5 on-topic from 4 sources · `kashmir` 13 rows / 0 on-topic from 0 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Six more killed in KP as monsoon rains and flash floods continue'
- _Evidence:_ Thread label: 'Mumbai Tree Collapse Deaths'

### GQ-12 — score 0 (stretch)

> Ukraine struck an Iranian ship in the Caspian Sea — how is Iran responding?

- **Served:** `dynamic-topic-2724` — Russian Infrastructure Attack Warnings
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: Adjacent-only: served thread is about Iran-Russia CIA strikes, not Ukraine ship strike.
- **G5:** silent empty: 24h total=0 while 6h total=158 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Cap applied:** judge said 1, mechanical rules cap at 0 (G5, G3).
- **Corpus control (6h):** `ukraine` 158 rows / 21 on-topic from 21 sources · `iranian` 262 rows / 118 on-topic from 106 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Reuters: US investigates possible Russian role in Iranian strikes on CIA facilities'
- _Evidence:_ Receipt 5: 'Has Russia helped Iran target CIA sites in the Gulf?'

### GQ-13 — score 1 (stretch)

> The war in Sudan — what has happened this week?

- **Served:** `dynamic-topic-653` — Sudan Conflict Updates
- **Judged:** ROR@20 0.625, ROR@all 0.625 over 16 receipts. Verdict: Honest floor: Atlas returns thin, partial signal with no confident answer.
- **G2:** headline_diversity 0.4 < 0.5; repeated_headline_share 0.688 > 0.35
- **Corpus control (6h):** `sudan` 19 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ label_status: partial
- _Evidence:_ confidence: medium
- _Evidence:_ coherence: null

### GQ-14 — score 0 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `dynamic-topic-898` — DR Congo Ebola Outbreak
- **Judged:** ROR@20 1.0, ROR@all 1.0 over 25 receipts. Verdict: Ignores the comparative language question entirely; serves only English Ebola coverage.
- **Corpus control (6h):** `congo` 36 rows / 13 on-topic from 11 sources · `ebola` 42 rows / 8 on-topic from 6 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ All 20 receipts are in English; none in French or Swahili.
- _Evidence:_ distinct_source_langs: 1 (only English).
- _Evidence:_ The thread label 'DR Congo Ebola Outbreak' does not address the language/origin asymmetry.

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 6 of 20 queries** (GQ-05, GQ-06, GQ-07, GQ-12, GQ-15, GQ-20). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 9 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-03, GQ-05, GQ-06, GQ-07, GQ-08, GQ-10, GQ-11, GQ-12, GQ-14). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
