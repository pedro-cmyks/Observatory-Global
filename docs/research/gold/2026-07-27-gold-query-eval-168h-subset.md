# Gold analyst query eval — run 2026-07-27

**Metric:** query-conditional investigation recall (roadmap Phase 2, target ≥80%). **First computation ever.**
**Run at:** 2026-07-27T20:03:10+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 168h
**Gold set:** `gold-query-set-v1` (docs/research/gold/gold-query-set-v1.json), sha256 `62ae0df30463ab49…`, 5 of 20 queries run
**Judge:** deepseek / `deepseek-chat` (chain Anthropic→DeepSeek via `insight_llm.generate_insight`) · **Harness:** `gold-query-eval-v1`

## Headline

- **Answer rate (the roadmap number): 0%** — 0 of 5 real (non-control) queries scored ≥2.
- **Honesty rate: 0.20** (pre-registered floor 0.90) — of the real items that did not answer, the share that failed HONESTLY (level 1) rather than falsely (level 0).
- **Distribution (real arm):** 3 → 0 · 2 → 0 · 1 → 1 · 0 → 4.
- **Conditional answer rate: 0%** over 4 items — excludes the 1 item(s) whose story is not in the corpus at all (an ingestion gap, #235, not an engine miss). not_in_corpus: GQ-13.

## Control arm (reported separately — never averaged into the number above)

- 0 of 0 controls PASSED (a control passes at level ≤1: an honest absence).
- Control distribution: 3 → 0 · 2 → 0 · 1 → 0 · 0 → 0. Mean = None.
- **K1** (mean ≥ 1.0 ⇒ run VOID): **clear**.
  - _Rubric defect, reported not fixed:_ K1 is written as `mean(controls) ≥ 1.0 ⇒ VOID`, but §2 defines level 1 (honest floor) as a control **PASS**. A run where all six controls return an honest floor scores exactly 1.0 and would be voided for behaving correctly. K1 is computed here exactly as pre-registered — thresholds cannot be moved after the fact — and the contradiction is logged for rubric v2.
- **K2** (any control scores 3 ⇒ run VOID): **clear**.

## Per-query results

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-04 | SA | 0 | 0.0 | 0.0 | 24 | 22 | 1 | 0.0 | G3 | Emerging (PH): Philippines, China trad | Receipts are about Scarborough Shoal clash, not Marcos corruption scandal. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 27 | 25 | 1 | 0.074 | G3 | Nicaragua Ends Elections | Receipts are entirely about Nicaragua elections, not Colombia's embassy closures. |
| GQ-08 | SA | 0 | 0.0 | 0.0 | 23 | 17 | 1 | 0.0 | G3 | Emerging (ID): Indonesia arrests ex-pr | No receipts address the governor's exit or rupiah; all off-topic. |
| GQ-11 | ST | 0 | 0.0 | 0.0 | 24 | 16 | 2 | 0.0 | G3 | Mumbai Tree Collapse Deaths | Receipts are about monsoon rains, not Azad Kashmir elections or rigging allegations. |
| GQ-13 | ST | 1 | 0.444 | 0.444 | 9 | 1 | 1 | 0.889 | G2,G3 | Legacy of the Father Emir | Honest floor: Atlas returns thin, degraded thread with no war update. |

## Failures — every real item that did not answer (score <2), and every control that did

### GQ-04 — score 0 (should_answer)

> The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

- **Served:** `dynamic-topic-6403` — Emerging (PH): Philippines, China trade blame after water cannon clash near Scarborough Shoal in South C…
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: Receipts are about Scarborough Shoal clash, not Marcos corruption scandal.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h, probe `marcos`):** 90 rows, 17 on-topic from 16 sources → story IS in the corpus (engine miss)
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Off-topic examples: 'Scarborough Shoal clash, not corruption scandal'
- _Evidence:_ Receipt 1: 'Philippines, China trade blame after water cannon clash near Scarborough Shoal'

### GQ-05 — score 0 (should_answer)

> Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

- **Served:** `dynamic-topic-5754` — Nicaragua Ends Elections
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 27 receipts. Verdict: Receipts are entirely about Nicaragua elections, not Colombia's embassy closures.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h, probe `colombia`):** 119 rows, 29 on-topic from 27 sources → story IS in the corpus (engine miss)
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Receipt 1: 'Nicaragua's President Ortega says there will be no more elections'
- _Evidence:_ Receipt 2: 'Nicaragua's President Ortega says there will be no more elections'

### GQ-08 — score 0 (should_answer)

> Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

- **Served:** `dynamic-topic-6727` — Emerging (ID): Indonesia arrests ex-prosecutor after seizing $19 mn and gold
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 23 receipts. Verdict: No receipts address the governor's exit or rupiah; all off-topic.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h, probe `indonesia`):** 0 rows, 0 on-topic from 0 sources → story IS in the corpus (engine miss)
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Off-topic examples: 'About ex-prosecutor arrest, not central bank governor.'
- _Evidence:_ Headline 1: 'Indonesia arrests ex-prosecutor after seizing $19 mn and gold'

### GQ-11 — score 0 (stretch)

> First phase of the Azad Kashmir elections — what are the rigging allegations?

- **Served:** `dynamic-topic-1740` — Mumbai Tree Collapse Deaths
- **Judged:** ROR@20 0.0, ROR@all 0.0 over 24 receipts. Verdict: Receipts are about monsoon rains, not Azad Kashmir elections or rigging allegations.
- **G3:** ROR@all 0.0 < 0.60 (over-merged)
- **Corpus control (6h, probe `azad`):** 35 rows, 5 on-topic from 4 sources → story IS in the corpus (engine miss)
- _Evidence:_ ROR@20 = 0.0, ROR@all = 0.0
- _Evidence:_ Six more killed in KP as monsoon rains and flash floods continue
- _Evidence:_ 7 dead, 20 injured as rains lash Pakistan

### GQ-13 — score 1 (stretch)

> The war in Sudan — what has happened this week?

- **Served:** `dynamic-topic-4422` — Legacy of the Father Emir
- **Judged:** ROR@20 0.444, ROR@all 0.444 over 9 receipts. Verdict: Honest floor: Atlas returns thin, degraded thread with no war update.
- **G2:** headline_diversity 0.4 < 0.5; repeated_headline_share 0.889 > 0.35
- **G3:** ROR@all 0.444 < 0.60 (over-merged)
- **Corpus control (6h, probe `sudan`):** 17 rows, 0 on-topic from 0 sources → NOT IN CORPUS (ingestion gap #235)
- _Evidence:_ confidence: degraded
- _Evidence:_ probe_6h coverageTier: limited
- _Evidence:_ probe_24h coverageTier: ok with only 5 on-topic rows

## How to read this, honestly

- n=14 real items: one item moving is ±7pp, the honest interval is ~±10pp. 16/20 vs 15/20 is noise.
- The gold set is drawn from headlines Atlas already ingested, so it **cannot** contain a story Atlas never saw. The feed gap (#235) is excluded by construction and this number therefore **overstates** how well Atlas serves an analyst.
- Single-rater judging: κ (rubric K4) has not been computed. The rubric says do not publish a single-rater number without that caveat attached — here it is.
- K3 (time-shifted placebo: re-run against a window 7 days back; if the score barely drops, the number is vocabulary coverage, not recall) has **not** been run.
