# Gold analyst query eval — run 2026-07-28

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-07-28T13:33:34+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 20 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 7%** — 1 of 14 real (non-control) queries scored ≥2.
- **Honesty rate: 0.23** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 1 · 1 → 3 · 0 → 10.
- **Conditional answer rate: 8%** over 12 items — excludes the 2 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-09, GQ-13.

## Control arm (reported separately — never averaged into the number above)

- 6 of 6 controls PASSED (a control passes at level ≤1: an honest absence).
- Control distribution: 3 → 0 · 2 → 0 · 1 → 0 · 0 → 6. Mean = 0.
- **K1** (mean ≥ 1.0 ⇒ run VOID): **clear**.
  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six controls return an honest floor scores exactly 1.0 and would be voided for behaving correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved after the fact — and the contradiction is logged for rubric v2.
- **K2** (any control scores 3 ⇒ run VOID): **clear**.

### Pair gaps (twin real item minus its control — a gap near zero is the most damaging finding available)

| Control | Twin | Isolates | Control | Twin | Gap |
|---|---|---|---|---|---|
| GQ-15 | GQ-01 | disaster vocabulary vs measured event | 0 | 2 | **+2** |
| GQ-17 | GQ-04 | governance template vs evidence | 0 | 0 | **+0** |
| GQ-18 | GQ-02 | same substrate, answerable vs not | 0 | 0 | **+0** |
| GQ-19 | GQ-08 | measurable finance vs forecast | 0 | 0 | **+0** |
| GQ-20 | GQ-06 | evidence vs opinion, same corpus | 0 | 0 | **+0** |
| GQ-16 | GQ-04 | low-volume region: no data vs no evidence | 0 | 0 | **+0** |

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 2 | 0.95 | 0.983 | 157 | 90 | 4 | 0.019 | — | Spain Wildfires Force Evacuations Near | Meets ROR@20≥0.75 and outlet diversity but collapses evacuation numbers without attribut |
| GQ-02 | SA | 0 | 0.0 | 0.0 | 17 | 16 | 1 | 0.059 | G3 | Klopp Appointed Germany Coach | Thread is about Klopp coaching appointment, not Berlin Pride attack. |
| GQ-03 | SA | 0 | 0.0 | 0.0 | 934 | 427 | 6 | 0.353 | G2,G3 | Iran Attack on US Bases and Regional F | Thread is about Iran attack, not Ebola; ROR@20=0.0. |
| GQ-04 | SA | 0 | 0.0 | 0.0 | 95 | 84 | 4 | 0.105 | G5,G3 | Trump tariff policies impact global tr | No receipts support the Marcos corruption question; all are off-topic. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 934 | 427 | 6 | 0.353 | G2,G3 | Iran Attack on US Bases and Regional F | Thread is about Iran-Ukraine conflict, not Colombia's embassy closures. |
| GQ-06 | SA | 0 | 0.0 | 0.0 | 16 | 15 | 1 | 0.0 | G3 | Iran Oil Sales During War | No receipts about strike pause; all off-topic oil sales stories. |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 934 | 427 | 6 | 0.353 | G2,G3 | Iran Attack on US Bases and Regional F | No receipt addresses the tanker mine question; all are off-topic. |
| GQ-08 | SA | 0 | 0.0 | 0.0 | 15 | 10 | 2 | 0.0 | G3 | Bank Earnings Growth 2026 | No receipts address the governor's exit or rupiah; all off-topic. |
| GQ-09 | SA | 0 | 0.0 | 0.0 | 934 | 427 | 6 | 0.353 | G2,G3 | Iran Attack on US Bases and Regional F | Thread is about Iran conflict, not Nicaragua elections; ROR@20=0.0, ROR@all=0.0. |
| GQ-10 | SA | 1 | 0.0 | 0.0 | 45 | 21 | 2 | 0.022 | G2,G3 | Romania Expels Russian Diplomat, Mosco | Honest floor: no thread on PSD legal offensive; adjacent thread flagged as failed. |
| GQ-11 | ST | 1 | 0.0 | 0.0 | 29 | 26 | 1 | 0.0 | G7,G3 | UK-Pakistan Grooming Gang Dispute | Honest floor: Atlas flagged no thread, served thin probe material. |
| GQ-12 | ST | 1 | 1.0 | 0.98 | 51 | 46 | 2 | 0.118 | — | Iran Attacks UAE Tankers | Adjacent-only: reuses existing Iran-Ukraine bucket, does not surface new relation. |
| GQ-13 | ST | 0 (judge 1, capped) | 0.0 | 0.0 | 298 | 215 | 4 | 0.124 | G5,G3 | Trump escalates Iran tensions over Hou | Honest empty: Atlas returned an off-topic thread with thin coverage flags. |
| GQ-14 | ST | 0 | 0.0 | 0.0 | 934 | 427 | 6 | 0.353 | G2,G5,G3 | Iran Attack on US Bases and Regional F | Thread is about Iran conflict, not Congo Ebola; ROR@20=0.0. |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 173 | 111 | 7 | 0.156 | G3 | Wildfires Rage Across Spain and France | Answered Spain/France wildfires, not Australian bushfire evacuations. |
| GQ-16 | NC | 0 | 0.0 | 0.0 | 49 | 39 | 1 | 0.0 | G3 | Trump escalates tariffs on Canada amid | No receipts about Lesotho textile factories; all off-topic. |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 39 | 26 | 2 | 0.051 | G3 | Support for Sonam Wangchuk | Completely off-topic; no Mongolia coal corruption coverage. |
| GQ-18 | NC | 0 | 0.0 | 0.0 | 20 | 16 | 2 | 0.1 | G3 | AfD Wahlkampf in Sachsen-Anhalt | Atlas served an off-topic thread about CSD parades, not the Berlin Pride attack story. |
| GQ-19 | NC | 0 | 0.0 | 0.0 | 16 | 15 | 1 | 0.0 | G5,G3 | Iran Oil Sales During War | Served thread is off-topic; Atlas did not answer the question. |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 16 | 15 | 1 | 0.0 | G3 | Iran Oil Sales During War | Thread is about oil sales, not public opinion; ROR@all=0.0; no honest empty floor. |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-02 — score 0 (should_answer)

> The Berlin Pride attack — what happened, and why are German authorities being criticised?

- **Served:** `dynamic-topic-6984` — Klopp Appointed Germany Coach
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 17 receipts. Verdict: Thread is about Klopp coaching appointment, not Berlin Pride attack.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `berlin` 88 rows / 17 on-topic from 16 sources · `pride` 37 rows / 17 on-topic from 14 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Klopp named new head coach of Germany men's football team'
- _Evidence:_ Receipt 2: 'Klopp replaces Naglesman as German head coach'

### GQ-03 — score 0 (should_answer)

> The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

- **Served:** `dynamic-topic-8072` — Iran Attack on US Bases and Regional Fallout
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Thread is about Iran attack, not Ebola; ROR@20=0.0.
- **G2:** headline_diversity 0.457 < 0.5; repeated_headline_share 0.353 > 0.35
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `ebola` 68 rows / 29 on-topic from 26 sources · `congo` 26 rows / 19 on-topic from 15 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Trump: Iranian Funds to Pay for Ship Damages'
- _Evidence:_ Receipt 2: 'China urges US to cancel tariffs'

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-8110` — Trump tariff policies impact global trade and industries
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: No receipts support the Marcos corruption question; all are off-topic.
- **G5:** silent empty: 24h total=0 while 6h total=86 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `marcos` 86 rows / 7 on-topic from 7 sources · `philippines` 14 rows / 1 on-topic from 1 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Off-topic examples: 'About Trump tariffs, not Marcos corruption scandal'
- _Evidence:_ Receipt 1: 'A forced-labor crackdown or an end-run around Congress? Dissecting Trump's new tariffs'

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-8072` — Iran Attack on US Bases and Regional Fallout
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Thread is about Iran-Ukraine conflict, not Colombia's embassy closures.
- **G2:** headline_diversity 0.457 < 0.5; repeated_headline_share 0.353 > 0.35
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `colombia` 28 rows / 6 on-topic from 6 sources · `cuba` 12 rows / 1 on-topic from 1 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0 (60 of 60 receipts off-topic)
- _Evidence:_ Receipt 1: 'Trump: Iranian Funds to Pay for Ship Damages'
- _Evidence:_ Receipt 4: 'Pentagon changes how it releases casualty data as Iran conflict continues'

### GQ-06 — score 0 (should_answer)

> The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

- **Served:** `dynamic-topic-7727` — Iran Oil Sales During War
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 16 receipts. Verdict: No receipts about strike pause; all off-topic oil sales stories.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iran` 300 rows / 39 on-topic from 34 sources · `western` 81 rows / 2 on-topic from 2 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Off-topic examples: [{"i": 1, "why": "About oil sales, not strike pause"}, {"i": 16, "why": "About Norway oil profits, not US-Iran"}]
- _Evidence:_ Verbatim-question probe returned 0 results with thin coverage warning

### GQ-07 — score 0 (should_answer)

> Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

- **Served:** `dynamic-topic-8072` — Iran Attack on US Bases and Regional Fallout
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: No receipt addresses the tanker mine question; all are off-topic.
- **G2:** headline_diversity 0.457 < 0.5; repeated_headline_share 0.353 > 0.35
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `iranian` 84 rows / 9 on-topic from 8 sources · `strait` 76 rows / 31 on-topic from 25 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic examples: 'About Trump funding ship damages, not mine explosion'
- _Evidence:_ Receipt 1: 'Trump: Iranian Funds to Pay for Ship Damages'

### GQ-08 — score 0 (should_answer)

> Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

- **Served:** `dynamic-topic-3091` — Bank Earnings Growth 2026
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 15 receipts. Verdict: No receipts address the governor's exit or rupiah; all off-topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `indonesia` 108 rows / 8 on-topic from 5 sources · `governor` 280 rows / 5 on-topic from 4 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Alasan Dude Harlino Balikin Honor PT DSI Rp5,25 M ke Bareskrim'
- _Evidence:_ Receipt 15: 'Hasil Investasi Tugure Tertekan Pasar, Baru Capai 38% Target Semester I-2026'

### GQ-09 — score 0 (should_answer)

> Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

- **Served:** `dynamic-topic-8072` — Iran Attack on US Bases and Regional Fallout
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Thread is about Iran conflict, not Nicaragua elections; ROR@20=0.0, ROR@all=0.0.
- **G2:** headline_diversity 0.457 < 0.5; repeated_headline_share 0.353 > 0.35
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `ortega` 15 rows / 2 on-topic from 2 sources · `nicaragua` 6 rows / 1 on-topic from 1 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0  ROR@all = 0.0
- _Evidence:_ Off-topic examples: [{"i": 1, "why": "About Trump and Iran funds, not Nicaragua elections"}]
- _Evidence:_ First 20 receipts all from IR (Iran), none about Nicaragua.

### GQ-10 — score 1 (should_answer)

> Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

- **Served:** `dynamic-topic-302` — Romania Expels Russian Diplomat, Moscow Vows Response
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 45 receipts. Verdict: Honest floor: no thread on PSD legal offensive; adjacent thread flagged as failed.
- **G2:** headline_diversity 0.467 < 0.5
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `romania` 269 rows / 14 on-topic from 10 sources · `bolojan` 15 rows / 12 on-topic from 5 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Harness-detected rule triggers: {'G2': 'headline_diversity 0.467 < 0.5', 'G3': 'ROR@all 0.0 < 0.60 (over-merged)'}
- _Evidence:_ Payload metadata: {"label_status": "failed", "confidence": "thin"}
- _Evidence:_ Probe_6h sample_headlines: "Romanian Social Democrats file criminal complaint against government" (adjacent, not the thread served)

### GQ-11 — score 1 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-235` — UK-Pakistan Grooming Gang Dispute
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 29 receipts. Verdict: Honest floor: Atlas flagged no thread, served thin probe material.
- **G7:** window signal_count 8 < 10 while lifetime 207 > 100
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `azad` 40 rows / 12 on-topic from 7 sources · `kashmir` 25 rows / 4 on-topic from 4 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Harness-detected rule triggers: {'G7': 'window signal_count 8 < 10 while lifetime 207 > 100', 'G3': 'ROR@all 0.0 < 0.60 (over-merged)'}
- _Evidence:_ Payload metadata: {"label_status": "failed", "confidence": "thin"}
- _Evidence:_ Probe_6h sample headlines: 'Bilawal accuses state of favouring PML-N, alleges rigging in AJK polls'

### GQ-12 — score 1 (stretch)

> Ukraine struck an Iranian ship in the Caspian Sea — how is Iran responding?

- **Served:** `dynamic-topic-2802` — Iran Attacks UAE Tankers
- **Judged:** ROR@20 1.0, ROR@all 0.98 over 51 receipts. Verdict: Adjacent-only: reuses existing Iran-Ukraine bucket, does not surface new relation.
- **Corpus control (6h):** `ukraine` 162 rows / 20 on-topic from 18 sources · `iranian` 94 rows / 31 on-topic from 23 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ Thread label: Iran Attacks UAE Tankers
- _Evidence:_ label_status: failed
- _Evidence:_ label_proposed: IR: Ukraine, Caspian, Iran — from 8 receipts

### GQ-13 — score 0 (stretch)

> The war in Sudan — what has happened this week?

- **Served:** `dynamic-topic-8070` — Trump escalates Iran tensions over Houthi attacks
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Honest empty: Atlas returned an off-topic thread with thin coverage flags.
- **G5:** silent empty: 24h total=0 while 6h total=31 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Cap applied:** judge said 1, mechanical rules cap at 0 (G5, G3).
- **Corpus control (6h):** `sudan` 31 rows / 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ probe_24h: total=0, coverageTier='thin', warnings=['query_thread_match_degraded', 'query_thread_thin_coverage']
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0 (receipts are about US-Iran tensions, not Sudan war)
- _Evidence:_ coherence.warning: 'This thread's coverage does not cohere — it likely conflates unrelated stories.'

### GQ-14 — score 0 (stretch)

> Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

- **Served:** `dynamic-topic-8072` — Iran Attack on US Bases and Regional Fallout
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 60 receipts. Verdict: Thread is about Iran conflict, not Congo Ebola; ROR@20=0.0.
- **G2:** headline_diversity 0.457 < 0.5; repeated_headline_share 0.353 > 0.35
- **G5:** silent empty: 24h total=0 while 6h total=28 on the same probe, no degraded marker
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h):** `congo` 28 rows / 18 on-topic from 15 sources · `ebola` 78 rows / 32 on-topic from 29 sources → story IS in the corpus (engine miss)  _(the verdict uses the better of the two probes; a probe whose remaining query tokens are generic verbs can under-count — see caveats)_
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Trump: Iranian Funds to Pay for Ship Damages'
- _Evidence:_ Receipt 3: 'Iran funds will cover ship damage: Trump'

## Measured side-effects of the run (findings in their own right)

- **The analyst's own question retrieves nothing.** `/api/v2/search/thread` with the question pasted verbatim returned `total=0` on **20 of 20** queries. The endpoint is a substring matcher over normalised headline/source/theme/person text, so a natural-language sentence can only match if a headline contains that sentence. Every floor number in this report therefore comes from a derived keyword probe, not from the question as asked.
- **G5 silent empty reproduced at scale: 4 of 20 queries** (GQ-04, GQ-13, GQ-14, GQ-19). The same probe returns hundreds of rows at 6h and exactly 0 at 24h, carrying only `query_thread_thin_coverage` and no degraded marker — the known `search.py` timeout swallow. It is not monotonic in window size (GQ-08's probe is 0 at 6h and 300 at 24h), which is what proves it is a timeout and not a data fact.
- **Threads served for a query but off it:** 8 real items scored 0 while the raw signal for their story was demonstrably in the corpus (GQ-02, GQ-03, GQ-04, GQ-05, GQ-06, GQ-07, GQ-08, GQ-14). Those are clustering/ranking misses, not ingestion gaps.

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- **The honesty rate is a LOWER BOUND, and the judge is the reason.** Rubric level 1(b) is "the only thread is a genuinely neighbouring story, correctly labelled" — an honest miss. This judge scored several such cases 0. The hard evidence: GQ-10 ships with a documented answer key of level 1 and this run scored it 0; and of the real items scoring 0, most had a working honest floor. The **answer rate is unaffected** (0 and 1 are both "not answered"), but the honesty rate should be read as "at least this". Fixing the pass-2 prompt to separate 1(b) from 0 is the first change for v2 — deliberately NOT made after seeing these results, because moving the instrument after the measurement is how this project's earlier numbers went bad.
- **Window mismatch — raised, then MEASURED, and it is not the explanation.** The gold queries were drawn from a 7-day corpus while the retrieval protocol serves 24h, so week-scale questions (a SONA speech, a first-phase election, "what happened this week") were arguably being asked of a one-day index. A supplementary run of the five most window-sensitive items at `--hours 168` returned **identical scores** (GQ-04/05/08/11 = 0, GQ-13 = 1); artifact `2026-07-27-gold-query-eval-168h-subset.{jsonl,md}`. What the wider window DID change is retrievability: `/api/v2/theme/{id}` timed out at 110s on 9 detail calls (0 timeouts at 24h), so at week windows thread detail is effectively unopenable — rubric D6 territory.
- **`not_in_corpus` has a false-positive mode.** The corpus control intersects the probe's rows with the question's REMAINING tokens client-side. When those remaining tokens are generic verbs ("what has happened this week"), nothing matches and a present story can be labelled an ingestion gap. Treat every `not_in_corpus` verdict as a hypothesis to confirm by hand, not as a #235 filing.
- **Pair gaps are uninformative in this run.** They assume a real arm that mostly answers. Three gaps are 0 and one is negative — not because the controls confabulated (all six passed) but because their real twins failed. Read them again when the answer rate is high enough for the comparison to mean anything.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
