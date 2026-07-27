# Semantic-into-search feasibility — MEASURED, and the answer is no

**Date:** 2026-07-27 · read-only measurement, no code shipped
**Question:** the primary metric came back 14% (2/14) with `/search/thread` returning
`total=0` on 20/20 gold queries. Would wiring the existing semantic lane into search
recover the failures?

## Verdict: NO. Answer rate stays 14%.

Two structural reasons, both measured:

1. **For 5 of 12 failures the thread does not exist in ANY lifecycle state.** No retrieval
   method returns a thread that was never formed. Direct label scans over `dynamic_topics`:
   - **GQ-05** Colombia breaking relations with Cuba/Nicaragua — **633 signals / 116 outlets
     produced ZERO topic**, while `Colombian Lottery Results` and `Colombia World Cup 2026`
     are live threads.
   - **GQ-08** no Perry Warjiyo / BI-governor topic (only `Rupiah Exchange Rate Fluctuations`)
   - **GQ-11** no Azad-Kashmir topic · **GQ-12** `%caspian%` matches nothing in any state
   - **GQ-10** no PSD-legal-action topic, only the adjacent `PSD Salary Law Opposition`
2. **`/search/thread` is the FLOOR instrument in this rubric, not the answer instrument.**
   A receipt list with no label, no `coherence`, no `label_status` cannot clear level 2,
   which requires label⊥receipts entailment.

## Failure decomposition (the number that decides what to build)

| Kind | Count | Queries | Can semantic fix it? |
|---|---|---|---|
| **clustering** — story in the raw corpus, no topic exists | **5** | GQ-05, 08, 10, 11, 12 | **No** |
| **synthesis** — ROR@20 already 1.00, failed downstream | **3** | GQ-03, 09, 14 | **No** |
| **retrieval** — thread exists, semantic surfaces it | **2** | GQ-06, 07 | Yes (both still capped by non-retrieval gates) |
| other — corpus-thin / probe unreliable | 2 | GQ-04, 13 | — |

## What semantic WOULD buy: honesty, not answers

At **signal** level the lane recovers the story cleanly for **4 of the 5 clustering cases**
— in Serbian, Bengali, Urdu, Indonesian and Slovak, which the LIKE matcher structurally
cannot do. It found the exact Hormuz mine-strike headline at rank 1, the AJK rigging story
from dawn.com, the Caspian strike with Iran's response, and the rupiah-consequence strand.

Moving those from *a confident wrong thread* (0) to *a real sourced multilingual receipt
set* (1) takes honesty **0.17 → ~0.50**. The rubric explicitly says a high answer rate with
honesty <0.90 is a WORSE product. So this is worth doing — as a floor, not as an answer.

## Taus, measured

**Raw e5 at the shipped tau does not discriminate.** At `SEMANTIC_MIN_SIMILARITY = 0.80`
over the full 2,719-topic pool: **124 topics admitted per real query, 59 per negative
control**; 14/14 real and 6/6 controls fire. (Reproduces at query level what
`2026-07-05-tau-recalibration.md` found with pseudo-queries: junk p50 0.8646 > tau 0.80.)

**Whitened signal space separates:**

| tau | real fires | control fires |
|---|---|---|
| 0.42 | 10/12 | 1/6 |
| **0.44** | **10/12** | **0/6** |
| 0.50 | 8/12 | 0/6 |

Control max 0.4342 — one query wide of 0.44, so treat as provisional (n=6).
Whitened *centroid* space is worse: fires on exactly the queries that already work.

**A tau only protects against Type-I (absent event).** GQ-18/GQ-19 *should* retrieve —
their substrate is real — and must not answer for epistemic reasons no threshold can
encode. Sharpest warning: **GQ-15, an Australia bushfire question, returns confident,
well-formed Bordeaux evacuation receipts.** Semantic retrieval is **country-blind**
(GQ-10 Romania drifted to Serbian, Indian and Bangladeshi parliamentary stories) — a geo
filter is required, not optional.

## Recommended build order

1. **Fix G5 first (~10 lines, worth more than the whole semantic lane).** `search.py:380`
   swallows the timeout and returns an empty thread with **no `degraded` marker**. That
   alone forced score 0 on GQ-05, 06, 07, 12 ("an empty that cannot prove it is honest is
   not honest"). Add `degraded_reason` to the payload.
2. **Then clustering / topic formation — this is where the metric lives.**
3. **Then semantic, as a FLOOR lane**: tau 0.44 in whitened space, labelled `UNVERIFIED`,
   never presented as an answer. `research_semantic.py` does NOT apply whitening today.
4. **Never ship it on raw e5 cosine.**

## Defect found: `fetch_topic_centroids` serves 3.7% of the field, guard reports healthy

`research_semantic.py:171-194` — `ORDER BY last_seen DESC LIMIT 100`.

`last_seen` is a **batch stamp from the nightly snapshot**, not per-topic recency:

| Fact | Value |
|---|---|
| Rows matching the WHERE | 2,719 |
| Rows sharing the single newest `last_seen` | **2,714** |
| Rows the lane actually sees | **100 → 3.7%**, planner-arbitrary, unstable between calls |

**The guard can never fire.** `research.py:275` passes `substrate_min_centroids=80`;
`research_anchor_discovery.py:374` tests `len(topics) < 80`, but `len(topics)` is capped at
100 by the LIMIT → `100 < 80` is always false. It measures the LIMIT, not the substrate,
and reports "healthy ≥80".

**Measured impact:** across all 20 gold queries the best-matching centroid was inside the
production 100-slice in **1 of 20** cases. GQ-01 misses `Spanish Wildfires` (the top match,
0.6195); GQ-09 misses `Nicaragua Ends Elections`.

**Blast radius:** one call site — `POST /api/v2/research/plan` → the L3 Workbench
"ATLAS SUGGESTS" panel. Search is unaffected (it never had a semantic lane).

**Fix:** rank by something real (`agg_n_signals DESC, id DESC`) or drop the LIMIT and score
all 2,719 in Python (a 2,719×768 fetch + one matmul, well under a second); and test the
true pool size with a `count(*)`, not `len(topics)` post-LIMIT.

## Second defect: ivfflat `probes = 20` against a 6s budget

`fetch_semantic_signal_matches` sets `ivfflat.probes = 20` with `timeout=6`. Measured:
**1.5s idle but repeatedly >100s under nightly load** (4 queries timed out twice each);
the same queries at `probes=10, LIMIT 40` returned in 2.1–2.9s. The production signal lane
silently returns `[]` whenever the DB is loaded. The 2026-07-13 note justifying probes=20
measured recall on an idle box — it never measured latency under load.

## Not verified
168h window (process died); signal-lane headlines for GQ-01/02/03/04/09; GQ-13/14 signal
lane. Single measurement per query — treat similarities as ±0.02.
