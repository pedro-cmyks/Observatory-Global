# Gold analyst query eval — day 3 (2026-07-31), FIRST measurement under fetch-mult M=2

**Run at:** 2026-07-31T13:33:14+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1`, sha256 `62ae0df30463ab49…`, 20/20 run · **Judge:** deepseek / `deepseek-chat`
**Harness:** `gold-query-eval-v1`, unmodified — same instrument as 07-27 and 07-28 (protocol frozen).
**Raw artifacts:** `2026-07-31-gold-query-eval.{jsonl,md}` (harness-written, same directory).
**Serving-side context:** `ATLAS_THREADS_FETCH_MULT=2` live since 07-30 (verified pre-run: `meta.fetch_mult=2`,
`pool_fetched=2×limit`); post-flip composition verify: entailed-share 47.2%→65.0% global
(`docs/research/label-court/2026-07-30-fetchmult-flip-postverify.md`). This is the only deliberate
serving-side change since the 07-28 run. Attribution caveat below — nightly identity churn also moved.

## Headline

- **Answer rate (roadmap metric): 21% — 3 of 14** real queries scored ≥2 (GQ-02 = 2, GQ-08 = 2, GQ-12 = **3**).
  Day series: **14% (07-27) → 7% (07-28) → 21% (07-31)**. At n=14 one query = ±7pp: 21% is the top of the
  band, one query above 07-27; treat as *band 7–21%*, not a trend.
- **GQ-12 is the first level-3 in the metric's history** (`dynamic-topic-3805` "Ukrainian Drone Strikes on
  Russian Ships": ROR@20 1.0, ROR@all 1.0, 24 receipts / 20 outlets, no defect, no cap).
- **Honesty rate: 0.09** (floor 0.90) — of the 11 real items that did not answer, only GQ-14 failed honestly
  (level 1); 10 failed at level 0. **Worst of the three days** (0.17 → 0.23 → 0.09) — see the composition
  section: the same shift that raised the answer rate lowered the honesty rate.
- **Distribution (real arm):** 3 → 1 · 2 → 2 · 1 → 1 · 0 → 10.
- **Conditional answer rate: 25%** over 12 items (not_in_corpus: GQ-09, GQ-13 — both to be hand-confirmed,
  the probe has a known false-positive mode on generic remaining tokens).
- **Negative controls: 6/6 PASS** (distribution 1 → 3 · 0 → 3, mean 0.5; K1 clear, K2 clear). Three controls
  earned honest-floor 1s (GQ-16/17/19) — the most honest-absence controls of any run.
- **"Informed" rate: not computable on this arm.** *Informed (≥1b)* is a rubric-v2 UI-arm rung
  (`rubric-v2-ui.md`); the API harness runs rubric v1, which has no 1b. Nearest v1 analog — share of real
  items at level ≥1 (answered + honest floor) — is **4/14 = 28.6%**. Do not compare that number to the UI
  eval's 71.4% informed rate; different instrument, different rung.

## PERSISTENCE — the day-over-day answer-persistence metric (the run's primary question)

Queries ever answered before this run: **GQ-01** (07-27 AND 07-28 — the only stable answer) and **GQ-02**
(07-27, vanished 07-28 — the named instability witness).

| Query | 07-27 | 07-28 | 07-31 | Persistence verdict |
|---|---|---|---|---|
| **GQ-01** wildfires FR/ES | **2** (Fontainebleau Forest Fire) | **2** (Spain Wildfires Force Evacuations) | **0** (Tour de France Wildfire Impact) | **BROKEN.** The only query answered on both prior days lost its answer. Nuance below — the right thread still exists and was served. |
| **GQ-02** Berlin Pride | **2** (Emerging (DE) thread) | **0** (Klopp coaching thread) | **2** (`dynamic-topic-7647` "Berlin Pride Terror Attack", ROR 1.0, 13 outlets, entailed, tier tight) | **RETURNED** after a one-day disappearance. The 07-28 comparison called the story still-in-corpus; today the engine serves it as a clean, correctly-labelled thread again. |
| GQ-08 Indonesia governor | 0 | 0 | **2** (`dynamic-topic-8057` "Perry Warjiyo Resigns") | Newly answered. |
| GQ-12 Caspian ship strike | 0 (judge 1, capped) | 1 (adjacent bucket) | **3** (`dynamic-topic-3805`) | Newly answered, at the top level. |

- **Adjacent-day persistence: 0/1** — GQ-01 was the only query answered on the prior measurement day
  (07-28) and it is not answered today. Series to date: 07-27→07-28 persisted 1/2; 07-28→07-31 persisted 0/1.
- **No query has been answered on all three measurement days. The intersection of answered sets is ∅**
  (union = 4: GQ-01, GQ-02, GQ-08, GQ-12). The answer SET churns wholesale day to day even as the RATE sits
  in band — the instability finding of `2026-07-28-rerun-comparison.md` is now witnessed in both directions:
  answers vanish (GQ-01) and resurrect (GQ-02).
- **GQ-01's break is a selection margin call, not a thread-existence failure — reported precisely.** The
  served list today CONTAINED the right thread (`dynamic-topic-353` "Wildfires Force Mass Evacuations in
  France and Spain", 54 receipts, receipt-fit 0.6125, lexical-on-topic@20 0.9) and the harness opened it. The
  frozen receipts-first selector (rubric G4 — never select by label) scored `dynamic-topic-7744` "Tour de
  France Wildfire Impact" instead (9 receipts, fit 0.6625): a 100% receipt hit-rate on 9 narrow receipts
  out-fit an 88.9% hit-rate on 54 broad ones, by 0.05. The judge then correctly scored the Tour-de-France
  thread 0 for the evacuations question. Protocol is frozen, the score stands; but the failure mode is
  "a niche entailed sibling out-competed the broad answer thread in candidate selection", not "the answer
  disappeared from serving". An analyst scanning the same list would likely have clicked dt-353.

## Per-query results (verbatim from the harness report)

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 0.0 | 0.0 | 9 | 9 | 1 | 0.0 | G3 | Tour de France Wildfire Impact | Thread is Tour de France rerouting, not evacuations or fire front; ROR@20=0.0. |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 13 | 13 | 1 | 0.0 | — | Berlin Pride Terror Attack | Answers the Berlin Pride attack with receipts, but accountability strand absent |
| GQ-03 | SA | 0 | 0.0 | 0.0 | 88 | 72 | 4 | 0.023 | G3 | US Bombards Iran Over Ormuz Attack | Thread is entirely about US-Iran conflict, not Ebola. |
| GQ-04 | SA | 0 | 0.85 | 0.87 | 23 | 8 | 1 | 0.0 | G2 | SONA 2026 Coverage | Receipts cover SONA logistics, not the corruption scandal; question unanswered. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 11 | 9 | 1 | 0.0 | G3 | Julián Álvarez Transfer Standoff | Served thread is about a soccer dispute, not the embassy closures. |
| GQ-06 | SA | 0 | 0.0 | 0.0 | 13 | 12 | 1 | 0.0 | G3 | US Control of Strait of Hormuz | Thread is about frozen assets, not paused strikes; no framing receipts. |
| GQ-07 | SA | 0 | 0.0 | 0.0 | 13 | 12 | 1 | 0.0 | G3 | US Control of Strait of Hormuz | No receipts address the tanker explosion; all about frozen assets. |
| GQ-08 | SA | 2 | 1.0 | 1.0 | 11 | 10 | 1 | 0.0 | — | Perry Warjiyo Resigns | Answers the resignation but lacks rupiah/policy-consequence strand. |
| GQ-09 | SA | 0 | 0.0 | 0.0 | 352 | 204 | 4 | 0.028 | G3 | Iran Attacks Condemned | Entirely Iran conflict; zero Nicaragua receipts, no honest floor surfaced. |
| GQ-10 | SA | 0 | 0.0 | 0.0 | 20 | 15 | 2 | 0.05 | G3 | Russian Ambassador Summoned | Russian drone story, not PSD lawsuit; no honest floor. |
| GQ-11 | ST | 0 | 0.125 | 0.125 | 8 | 7 | 1 | 0.0 | G3 | AJK Elections 2026 First Phase | Receipts are polling/results, not rigging allegations; ROR@20=0.125 fails level 1. |
| GQ-12 | ST | 3 | 1.0 | 1.0 | 24 | 20 | 1 | 0.0 | — | Ukrainian Drone Strikes on Russian Ships | Directly answers; 20+ outlets, ROR 1.0, no defects. |
| GQ-13 | ST | 0 | 0.0 | 0.0 | 25 | 23 | 1 | 0.12 | G5,G3 | Netanyahu Mamdani Feud | Confident grab-bag with zero Sudan receipts and no thinness flag. |
| GQ-14 | ST | 1 | — | — | 0 | 0 | 0 | — | — | *(no candidate thread)* | Honest floor only: no thread; probes show coverage exists. |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 30 | 30 | 1 | 0.967 | G2,G3 | Supporting Australian Theatre | Confident off-topic answer on a control. (Control PASSES at ≤1: score 0 = pass.) |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 50 | 35 | 3 | 0.02 | G3 | US Tariffs on Brazil | Honest absence: zero Lesotho receipts. PASS. |
| GQ-17 | NC | 1 | 0.0 | 0.0 | 31 | 20 | 1 | 0.0 | G5,G3 | Supreme Court Rules on Police Force… | Honest absence: no Mongolia thread. PASS. |
| GQ-18 | NC | 0 | 1.0 | 1.0 | 13 | 13 | 1 | 0.0 | — | Berlin Pride Terror Attack | Names no first outlet but renders a spread sequence. PASS (≤1). |
| GQ-19 | NC | 1 | 0.0 | 0.0 | 15 | 14 | 1 | 0.0 | G3 | Iran Oil Sales During War | Honest floor: declines coverage-price causality. PASS. |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 15 | 14 | 1 | 0.0 | G3 | Iran Oil Sales During War | Oil-sales thread for a public-opinion question. PASS (≤1). |

Pair gaps: GQ-18→GQ-02 **+2**, GQ-19→GQ-08 **+1**, GQ-17/16→GQ-04 −1, others 0. For the first time two
twins beat their controls — the pair design starts to inform as the real arm answers.

## Composition under M=2 — what visibly changed vs the 07-28 run

These are the composition-sensitive observations the M=2 flip predicts (more court-entailed rows on served
/threads pages). All confirmed against the 07-28 per-query notes; none can be *causally* pinned to M=2 alone
(see caveats).

1. **The mega-blob stopped being the default answer.** On 07-28 ONE 934-receipt blob
   (`dynamic-topic-8072` "Iran Attack on US Bases and Regional Fallout", repeated_headline_share 0.353,
   G2-fired) was the scored thread for FIVE different real queries (GQ-03/05/07/09/14). Today 14 real
   queries resolve to 13 distinct threads (only GQ-06/07 share one — both Hormuz questions, appropriately),
   receipt sets are 8–88 rows (one 352), and repeated_headline_share is ≤0.12 on every real item. G2 fired
   once on the real arm (07-28: four times).
2. **Scored threads are now court-entailed almost everywhere.** 15 of 19 scored threads today carry
   `label_status=entailed` (plus 2 partial); on 07-28 the scored metadata repeatedly showed
   `label_status: failed` (GQ-10/11/12). This is exactly the composition M=2 was flipped to produce —
   the eval sees it end-to-end at the analyst surface.
3. **Event-neighborhood precision improved even where scores did not move.** The most striking class:
   - GQ-04: 07-28 served a Trump-tariffs thread (ROR 0.0); today "SONA 2026 Coverage" — the right event,
     ROR@20 **0.85** — still 0 because the receipts cover SONA logistics, not the corruption strand.
   - GQ-11: 07-28 served UK-Pakistan grooming (honest floor); today "AJK Elections 2026 First Phase" — the
     right election, but receipts are results-not-rigging (ROR 0.125; the one rigging receipt is #5).
   - GQ-08: "Bank Earnings Growth 2026" blob → "Perry Warjiyo Resigns" (answered, 2).
   - GQ-12: adjacent "Iran Attacks UAE Tankers" bucket → precise Caspian thread (answered, 3).
   The failure mode moved one level down: from *wrong thread class entirely* to *right event, wrong strand*.
4. **The honesty-rate collapse is the same shift seen from the other side.** When Atlas misses now, it
   misses with a SPECIFIC, entailed, tight-cohering thread about something else (Julián Álvarez transfer for
   the Colombia embassies question; Netanyahu–Mamdani for Sudan; Russian-ambassador drones for the PSD
   lawsuit) — the judge reads these as confident grab-bags (0), where 07-28's misses often carried
   `label_status: failed` / thin flags and earned honest-floor 1s. **Answer rate up AND honesty rate down
   are one phenomenon: the served page got more confident.** With M=2 the burden moves to per-thread honesty
   surfaces (court chips reach the UI, but nothing in the payload says "this thread is not about your
   query" — that is a retrieval-fit gap, not a label-court gap).
5. **GQ-02's recovery rode a clean identity.** `dynamic-topic-7647` "Berlin Pride Terror Attack"
   (entailed, coherence tight, 18 sources) — and its candidate list still shows the T11 witness
   "Austrian Arrested for Fraud" as a sibling candidate, which the receipts-first selector correctly passed
   over. The finder-v2 diagnosis (anchor quality, not finder) is consistent with what this run served.

## Three most notable per-query changes (vs 07-28)

1. **GQ-01 wildfires: 2 → 0 — the stable answer broke, by selector margin.** The evacuations thread exists
   and was served (dt-353, 54 receipts); a 9-receipt entailed "Tour de France Wildfire Impact" sibling
   out-fit it 0.6625 vs 0.6125 under the frozen receipts-first selection. Persistence metric takes the hit
   as computed; the mechanism is niche-sibling crowding, which more entailed niche threads on the page
   (M=2's effect) plausibly makes MORE likely, not less. Watch this exact mode on day 4.
2. **GQ-02 Berlin Pride: 0 → 2 — the named instability witness resurrected.** Answered 07-27, vanished
   07-28 (Klopp thread), answered again today with ROR 1.0 on a tight entailed thread. Answers do not just
   vanish; they come back — persistence is genuinely a state that oscillates with the nightly identity churn.
3. **GQ-12 Caspian: 1 → 3 — the metric's first level-3.** From "adjacent bucket, honestly flagged" to a
   direct answer with 20+ outlets and ROR 1.0. Together with GQ-08 (0 → 2 via a newly-formed specific
   thread), the two new answers both came from small, tight, entailed threads — the exact row class M=2
   promotes into the visible pages.

## Honest caveats

- **Attribution is NOT clean.** M=2 is the only deliberate serving-side change since 07-28, but the nightly
  lifecycle re-founded identities three times between runs; every thread id in this run differs from 07-28's.
  A single day cannot separate "M=2 changed the composition" from "the field churned into a better day".
  The composition observations (§ above) are the M=2-consistent signal; the answer-rate move (one query
  above the 07-27 level) is within single-query noise. Day 4+ under the same config is the test.
- **7-day series so far is 3 points on 2 configs**: 14% / 7% (M=1) → 21% (M=2). Band statement: 7–21%,
  n=14, ±7pp per query.
- **Honesty rate 0.09 is a lower bound** (the v1 judge conflates 1(b) neighbouring-story with 0 — documented
  since 07-27, deliberately unfixed mid-series). But even as a lower bound the direction is real: today's
  misses genuinely carry fewer self-flagged defects than 07-28's, because the served threads are
  individually healthier while still off-query.
- **GQ-13/GQ-09 `not_in_corpus`** verdicts come from the probe intersection with its known generic-token
  false-positive mode; both need hand confirmation before any #235 filing (GQ-13's 6h `sudan` probe found
  8 rows / 1 on-topic — genuinely thin, but "thin" ≠ "absent").
- Single-rater judge, κ not computed (K4 caveat attached as required). K3 time-shifted placebo still not run.
- The harness-generated header still says "First computation ever." — a hardcoded line in `render_report`,
  false since 07-28; cosmetic, flagged for the next harness touch (do not edit mid-series).
- G5 silent-empty reproduced on 2/20 probes today (07-28: 4/20); the verbatim-question probe returned 0 on
  20/20 — both known defects, unchanged.
- The controls arm scored its best honest-absence profile yet (three level-1 floors). Whatever M=2 did to
  the real arm, it did NOT make the controls confabulate: K2 clear, no control above 1.

## Where this leaves the metric

The primary metric now has: a 3-day series (7–21%), a persistence metric with witnesses in both directions
(GQ-01 broke, GQ-02 resurrected, intersection-across-days = ∅), the first level-3, and a measured
composition shift at the analyst surface consistent with the M=2 flip. The instability finding is now the
strongest structural claim the series supports: **the day-to-day answer SET churns wholesale while the rate
stays in band** — exactly the failure class the entity-overlap identity work is scoped to fix, and the
day-4 run (same config) is the cheapest next data point.
