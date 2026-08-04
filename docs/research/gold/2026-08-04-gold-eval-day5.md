# Gold analyst query eval — day 5 (2026-08-04), THE persistence-as-state test

**Run at:** 2026-08-04T11:25:33+00:00 (started 11:01:23Z, ~24 min, watched to exit 0) · **Base URL:**
`https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1`, sha256 `62ae0df30463ab49…` (identical to all prior runs), 20/20 run ·
**Judge:** deepseek / `deepseek-chat` · **Harness:** `gold-query-eval-v1`, unmodified — same frozen
instrument as 07-27, 07-28, 07-31 and 08-03. 151 HTTP calls, `errors: []`.
**Raw artifacts:** `2026-08-04-gold-query-eval.{jsonl,md}` (harness-written, same directory).
**Pre-run config verify:** live `/threads` served `meta.fetch_mult=2`, `pool_fetched=2×limit` — M=2
unchanged since the 07-30 flip.
**Single question this run was pre-assigned:** after day 4's first-ever 3/3 adjacent-persistence hold —
**is persistence now a STATE?**

## VERDICT — persistence split into two layers, and they answered differently

**Identity persistence: YES — it now behaves like a state.** All FOUR of day-4's answered thread
identities served again today on the same queries (`dt-7711`, `dt-8057`, `dt-3805`, `dt-9000`), and 7 of
day-4's 12 distinct real-arm scored identities re-served overall. The layer that churned wholesale in the
day-3 era (day 3: zero id survival; day 4: first 4; day 5: 7 + all four answer ids) has held two
consecutive nights.

**Answer persistence: NO — 2 of 4 held (GQ-02, GQ-13); GQ-08 broke 2→0 and GQ-12 broke 2→1.** But the
break mechanism is NEW and narrower than anything in the series: **both breaks happened ON the surviving
identity, at the detail-serving layer, not by churn and not by story death.**

- **GQ-08 (`dt-8057`, same id, same label): served receipt sample collapsed 11 → 1** while the thread
  itself is ALIVE — lifetime members 41→41, 24h signal_count 31→**35**, trend flipped fading→**surging**,
  confidence medium→`degraded`. The judge correctly refused a single-receipt answer ("Single receipt, one
  outlet... fails independence"). The story did not end; the payload starved.
- **GQ-12 (`dt-3805`, same id, same label): sample 30 → 2** (lifetime 205→205; 24h signal_count 132→65 —
  genuinely fading, but 65 signals ≠ 2 receipts), confidence medium→`thin`. Judge read the 2 receipts as
  honest adjacency → level 1 with the thin flag cited. Honest downgrade, not a confident wrong answer.
- **GQ-02 (`dt-7711`, held at 2) survived the SAME defect only via a harness fallback:** its detail
  member sample came back **0** (`semantic_members_ann_timeout` on the payload, both days) and the
  harness's `list_evidence_samples` fallback supplied 60 receipts (47 outlets, 3 langs — its richest
  serving ever). A product surface without that fallback lane would have shown an empty thread.
- **GQ-13 (`dt-9000`, held at 2): the identity was RELABELED overnight** — "Sudan War Atrocities" →
  "Sudan Child Soldiers" (same dt-id, label arc's relabel loop visible in the primary metric) — and the
  answer survived the relabel: 15 receipts, `thin` + `partial` carried visibly, judge: "Thin but honest."

**So the structural claim updates: the day-3 disease (identity churn) is in remission; the day-5
bottleneck moved DOWN the stack to detail receipt serving** — `dynamic_topic_member_preview_sample`
lanes returning 0–2 receipts for threads with 41–205 live members. Whether that collapse traces to the
overnight blob-sweep stamps, the continuing census surgery, member quarantine, or the preview-sample /
ann-timeout path is **not separable from the eval surface** — it is a serving-layer question with named
candidates, and it is the cheapest next diagnosis: the answers that exist are being lost at the last
mile, on threads that still hold the receipts.

## Headline

- **Answer rate (roadmap metric): 21% — 3 of 14** real queries ≥2 (GQ-02, GQ-11, GQ-13, all level 2).
  Series: **14% → 7% → 21% → 29% → 21%.** Band 7–29%; the three readings since the M=2 flip are all
  ≥21% (n=14, one query = ±7pp — 21↔29 is a two-query swing).
- **Honesty rate: 0.27** (floor 0.90) — 3 of 11 real non-answered items earned honest-floor 1s (GQ-09,
  GQ-10, GQ-12). Series: **0.17 → 0.23 → 0.09 → 0.40 → 0.27.** The day-3 collapse did not repeat; today
  sits mid-band. Decomposition below.
- **Distribution (real arm):** 3 → 0 · 2 → 3 · 1 → 3 · 0 → 8.
- **Conditional answer rate: 23%** over 13 items (not_in_corpus: GQ-09 only, same as day 4).
- **Negative controls: 6/6 PASS** (distribution 1 → 2 · 0 → 4, mean 0.33; K1 clear, K2 clear). GQ-16
  (Lesotho) and GQ-19 (oil lead/lag) earned honest-absence 1s — same two as day 4.
- **"Informed" analog** (real items ≥1, NOT comparable to the UI eval): **6/14 = 42.9%** (day 4: 57.1%).
- **No level-3** for the second consecutive day.

## (a) ADJACENT PERSISTENCE day-4 → day-5, the four day-4 answers

| Query | Day-4 | Day-5 | Held? | Identity | Mechanism |
|---|---|---|---|---|---|
| GQ-02 Berlin Pride | 2 | **2** | **HELD** | `dt-7711` same | Detail sample 0 (`ann_timeout`); saved by the harness `list_evidence_samples` fallback → 60 receipts/47 outlets/3 langs. Held, but through a fallback lane. |
| GQ-08 Indonesia governor | 2 | **0** | **BROKE** | `dt-8057` same | Serving starvation: receipt sample 11→1 on a LIVE thread (41 members, 24h count 31→35, surging, conf→`degraded`). Judge refuses single-receipt independence. Not churn, not story death. |
| GQ-12 Caspian ship strike | 2 | **1** | **BROKE** (honestly) | `dt-3805` same | Sample 30→2 (24h count 132→65, fading; conf→`thin`). Judge: adjacent-only on 2 receipts, thin flag cited → honest floor 1, not a confident 0. |
| GQ-13 Sudan this week | 2 | **2** | **HELD** | `dt-9000` same, RELABELED | "Sudan War Atrocities"→"Sudan Child Soldiers" overnight; 15 receipts, thin+partial visible. Answer survived a relabel on a stable id. |

Adjacent-persistence series: 07-27→28 **1/2** · 07-28→31 **0/1** · 07-31→08-03 **3/3** · 08-03→08-04
**2/4**. Day 4's perfect hold did not repeat, but the failure class changed entirely: day-3-era breaks
were *different thread served / identity re-founded*; both day-5 breaks are *same thread, starved
payload*. One new answer was gained: **GQ-11 (AJK rigging) 0→2** via a DIFFERENT thread — day-4's
`dt-8315` "AJK Elections 2026" (0, second-phase-heavy, ROR@20 0.3) was replaced by `dt-8631` "Kashmir
Election Unrest" (ROR@20 0.833, answers the rigging allegations via Pakistani framing; Indian PoK
framing absent blocks 3).

## (b) THREAD-IDENTITY SURVIVAL — day-4 scored set → day-5

Day-4's real arm scored 12 distinct identities. **7 re-served today, on the same queries:**

| Identity | Day-4 query (score) | Day-5 query (score) | Note |
|---|---|---|---|
| `dt-8460` France Spain Wildfire | GQ-01 (0) | GQ-01 (0) | Stable miss, stable id — receipts 30→19, still single-country/English |
| `dt-7711` Berlin Gay Pride Attack | GQ-02 (2), GQ-18 | GQ-02 (2), GQ-18 | 3rd day serving (re-found on day 4) |
| `dt-5758` Nicaragua Electoral Reform | GQ-05 (0), GQ-09 (1) | GQ-05 (0), GQ-09 (1) | Same double-serve, same scores |
| `dt-8057` Indonesia Governor | GQ-08 (2) | GQ-08 (0) | Id survived; payload starved (11→1 receipts) |
| `dt-9058` Fitch Romania Rating | GQ-10 (1) | GQ-10 (1) | Same honest adjacency |
| `dt-3805` Iran Ukraine Caspian | GQ-12 (2) | GQ-12 (1) | Id survived; sample 30→2 |
| `dt-9000` Sudan (relabeled) | GQ-13 (2) | GQ-13 (2) | Survived a RELABEL — id-persistence through label change |

Plus one control identity (`dt-8558` Ngaro Track, GQ-15 — the 0.958 syndication blob, still serving).
Not re-served: `dt-2344` (failed-label Ebola → replaced by fresh `dt-9474` "Ebola Outbreak Congo", 110
receipts/88 outlets/6 ccs, entailed), `dt-7801` (Marcos SONA → replaced by an off-topic maritime thread),
`dt-9760`, `dt-2614`, `dt-8315`. Day 3 had ZERO id survival; day 4 had 4; **day 5 has 7 of 12 including
all four answered identities — identity persistence is the series' first structural property to hold two
consecutive night-pairs.**

## (c) HONESTY 0.40 → 0.27 — decomposition

Day-4 floors: GQ-04, GQ-09, GQ-10, GQ-14 (4/10). Day-5 floors: GQ-09, GQ-10, GQ-12 (3/11).

- **Kept (2):** GQ-09 (same `dt-5758`, foreign-only coverage read honestly) and GQ-10 (same `dt-9058`
  Fitch adjacency).
- **Gained (1):** GQ-12 — the break itself was HONEST (thin flag + adjacent read → 1, not a confident 0).
  A degradation that self-declares is the counterweight working as designed.
- **Lost (2), both via serving composition, not judge mood:**
  - GQ-04: day-4's floor came from the RIGHT neighbourhood self-flagging (`dt-7801`, conf `thin`); today
    the selector served a wrong thread entirely (`dt-9462` "Philippines UN Maritime Claim", ROR 0.0,
    entailed+confident) → 0.
  - GQ-14: day-4's floor came from a VISIBLE `label_status=failed` (`dt-2344`); overnight the Ebola
    serving moved to fresh, entailed, confident `dt-9474` — and with the failed label went the honesty
    credit. **Both losses are the same lesson: this metric's honesty floor is currently carried by
    payload self-flags; when the flag disappears (fresh promotion, relabel), the honesty goes with it.**

The day-3 collapse mode ("misses became specific-and-confident") remains visible in residue: GQ-03
(historical death-toll spread as live disagreement, now on the fresh umbrella), GQ-05, GQ-06 (no framing
side-by-side), GQ-07 (blockade-threat receipts for a tanker-explosion question), GQ-14 — all confident 0s.

## ANSWER-SET CHURN — five days

| Day | Answered set (≥2) |
|---|---|
| 07-27 | GQ-01, GQ-02 |
| 07-28 | GQ-01 |
| 07-31 | GQ-02, GQ-08, GQ-12 |
| 08-03 | GQ-02, GQ-08, GQ-12, GQ-13 |
| 08-04 | **GQ-02, GQ-11, GQ-13** |

- 08-04 ∩ 08-03 = {GQ-02, GQ-13}: **2 of 4 retained, 1 gained (GQ-11), 2 lost (GQ-08, GQ-12 — both to
  serving starvation on surviving ids, one honestly).**
- **GQ-02 is now answered 4 of 5 days** — the series' first quasi-stable answer, and today it needed the
  fallback lane to stay one.
- Union across 5 days: 6 of 14 (GQ-01, 02, 08, 11, 12, 13). Intersection across all 5 days: still ∅
  (GQ-02 misses only day 2).

## (d) CONFOUND NOTE — stated up front, per series protocol

**This is not a same-field day, by design.** Between the day-4 run (08-03 08:19 local) and this run
(08-04 06:01 local) the nightly ensemble changed at least four ways: **country-clock night-1** (armed
fail-open, allowlist in both runner copies), **blob-veto sweep first pass** (mig 095, ~372 stamps),
**continuing effects of the 72-topic census surgery** (08-03 morning), and a **fresh-promotion wave
(~179 topics)** — visible in this run as the high-id fresh threads that took over five queries
(`dt-9474`, `dt-10022`, `dt-10017`, `dt-9414`, `dt-8631`) and as the first **UNCHECKED-label thread in a
scored set since the series began** (`dt-10017`, GQ-17's control serve, `label_status=None` — a fresh
promotion the court hasn't stamped yet). The ensemble evolves nightly by design; day-5 measures the
ensemble, not any single lever. What day 5 CAN say cleanly: identity survival held across two different
overnight ensembles, and the answer breaks have a common serving-layer signature that no overnight
change claims credit for yet.

## Composition notes (vs day 4)

1. **Label-court composition:** entailed on 14 of 20 scored rows, partial on 5 (dt-5758 ×2, dt-10022 ×2,
   dt-9000), **1 unchecked** (dt-10017 — first ever in a scored set; fresh-promotion wave). Zero
   failed-label serves today (day 4 had 2) — because the failed-label thread was replaced, which is also
   why GQ-14's honesty floor vanished.
2. **G5 silent-empty is BACK, twice:** GQ-14 probe (24h total=0 while 6h total=32, no degraded marker)
   and GQ-17 probe (0 vs 5). The class the 07-28 fixes addressed resurfaced at the floor-probe surface.
3. **`semantic_members_ann_timeout`** on the dt-7711 payload both days (GQ-02/GQ-18) — the C5 depth-80
   watch item is now directly implicated in a near-loss of the series' most stable answer.
4. **GQ-15's control thread remains the 0.958 repeated-headline syndication blob** (24 outlets, one
   headline) — third run serving; control still passes.
5. Confidence `degraded` appeared on 3 scored payloads (dt-7711, dt-8057, dt-8478) — day 4 had 1.

## Honest caveats

- Attribution is confounded by design and stated above (four overnight levers; no single-day allocation).
- **Judge variance remains a measured ±1 term** (day 4 proved it on GQ-12's 3→2; unchanged protocol,
  single rater, no κ; K3 time-shifted placebo still not run). GQ-08's 0 (vs the G1 cap wording "caps at
  1" in its own verdict) is a harsh-side call; protocol frozen, score stands.
- Honesty 0.27 remains a lower bound (v1 judge conflates 1(b) with 0 in the other direction; unchanged
  mid-series by design — the harness's own report documents GQ-10's answer-key mismatch class).
- GQ-09 `not_in_corpus` still needs hand confirmation before any #235 filing.
- Verbatim-question probe returned 0 on 20/20 (substring matcher, known defect, unchanged).
- Harness header still prints "First computation ever." — hardcoded, false since 07-28, cosmetic,
  deliberately unfixed mid-series.
- Run executed as a single watched process to exit 0 (~24 min), 20/20 queries, `errors: []`, judge chain
  fell to DeepSeek as expected (Anthropic dry).

## Where this leaves the metric

Five days: answered 14% → 7% → 21% → 29% → **21%**; honesty 0.17 → 0.23 → 0.09 → 0.40 → **0.27**;
adjacent persistence 1/2 → 0/1 → 3/3 → **2/4**. The pre-assigned question gets a split answer:
**identity persistence IS now a state** (two consecutive holds, 4/4 answered ids re-served, one answer
surviving a relabel) — the first positive structural claim the series can make. **Answer persistence is
NOT yet a state**, and the reason is no longer the identity layer: both day-5 breaks are detail-payload
receipt starvation on live, surviving threads (samples 11→1 and 30→2; GQ-02 rescued only by a fallback
lane the product UI may not share). The series' bottleneck has moved twice now — retrieval → identity →
**detail serving** — each time to a narrower, more diagnosable layer. The cheapest next probe is not
another eval day: it is asking `/api/v2/theme/{id}` why a 41-member surging thread serves one receipt.
