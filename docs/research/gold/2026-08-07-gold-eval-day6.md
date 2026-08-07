# Gold analyst query eval — day 6, the detail-fix verification run

> **Filename caveat, read first.** This synthesis is filed as `2026-08-06` per the run request, but
> **the run actually executed 2026-08-07T11:07→11:20Z**. The harness-written raw artifacts carry the
> true date: `2026-08-07-gold-query-eval.{jsonl,md}`. Rename this file to `2026-08-07-…` if the
> series should stay date-honest; nothing else in the record depends on the `06`.

**Run at:** 2026-08-07T11:20:41+00:00 (started 11:07:08Z, ~13 min, watched in foreground to exit) ·
**Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1`, sha256 `62ae0df30463ab49…` (byte-identical to all five prior runs),
20/20 run · **Judge:** deepseek / `deepseek-chat` (Anthropic 400 `insight_no_credits` → DeepSeek, the
documented chain) · **Harness:** `gold-query-eval-v1`, unmodified. 148 HTTP calls, `errors: []`.
**Pre-run config verify:** live `/threads` served `meta.fetch_mult=2`, `pool_fetched=2×limit` — M=2
unchanged since the 07-30 flip. ✅

> **THE GAP IS THREE NIGHTS, NOT ONE.** Day 5 ran 08-04, day 6 ran 08-07. Every prior persistence
> reading in this series was **adjacent** (a single night-pair). **This run cannot produce a "3rd
> consecutive night-pair" and no number below should be read as one.** It measures survival across a
> 3-night gap, which is a strictly harder and differently-shaped test. The night-pair series is
> *paused*, not extended.

## VERDICT — the detail fixes worked; the bottleneck moved UP the stack to selection

**The day-5 disease is cured, and cleanly.** Day 5's signature defect was *serving starvation*: live
threads with 41–205 members returning 1–2 receipts. **Day 6 has zero starved payloads.** The minimum
receipt count across all 20 served threads is **9**; `member_sample_starved` fired **zero times**; the
three `degraded` confidences of day 5 are gone (day 6 has no `degraded` anywhere). The two starved
day-5 queries both recovered their evidence: **GQ-08 1r → 13r**, **GQ-12 2r → 31r**. The
starvation-fix (`e55cb08e`, lane union + honest flag) has no counter-evidence in this run.

**But answer persistence still broke, and the mechanism is new again.** This is the third distinct
failure class in three readings:

| Reading | Break mechanism |
|---|---|
| day 3 era | **Identity churn** — the thread was re-founded; the id died |
| day 5 | **Payload starvation** — same id, same label, receipts collapsed to 1–2 |
| **day 6** | **Selector migration** — same story, id still ALIVE, but a *different identity* won serving |

**15 of 20 served slots changed identity — while 12 of those 15 day-5 identities are still `active` in
the store.** `dt-7711` (Berlin Pride), `dt-8057` (Indonesia governor), `dt-3805` (Caspian),
`dt-8631` (Kashmir), `dt-8460`, `dt-5758`, `dt-1999` are all alive and all lost their serving slot to
a *sibling identity covering the same story*. GQ-02 kept its answer by being served
`dt-9156` "Pride Security After Berlin Attack" instead of `dt-7711` "Berlin Gay Pride Attack" — two
live identities for one event.

**And the candidate POOL turned over, not just the argmax inside it.** For **14 of the 15** changed
serves, the day-6 winner was **not in the day-5 candidate pool at all**. This is not the ranker
re-sorting a stable shortlist; the top-40 list itself churned wholesale over three nights, pulling in
older identities (`dt-2831`, `dt-7736`, `dt-898`, `dt-2802` — all born in late July) that day 5 never
considered. The one exception is the junk case in §(e), which is the only *explained* substitution in
the run.

So: **the last mile was fixed and the failure moved one hop upstream.** Answers are no longer lost at
detail-serving; they are lost at *which identity gets selected to serve*. That is argmax dispersion —
the disease named on 07-30 — now visible in the primary metric rather than in the lens.

## Headline

- **Answer rate (roadmap metric): 14% — 2 of 14** real queries ≥2 (**GQ-02**, **GQ-12**, both level 2).
  Series: **14 → 7 → 21 → 29 → 21 → 14%.** At n=14 one query = ±7pp, so 21→14 is a **one-query move**,
  and §(f) shows one of those queries moved on an unchanged payload. Treat as flat-to-soft, not a fall.
- **Honesty rate: 0.25** (floor 0.90) — 3 of 12 real non-answered items earned honest-floor 1s
  (GQ-11, GQ-13, GQ-14). Series: **0.17 → 0.23 → 0.09 → 0.40 → 0.27 → 0.25.** Essentially flat vs day 5.
- **Distribution (real arm):** 3 → 0 · 2 → 2 · 1 → 3 · 0 → 9. **No level-3 for the third consecutive day.**
- **Conditional answer rate: 18%** over 11 items. `not_in_corpus` grew to **3** (GQ-04, GQ-09, GQ-11)
  from day 5's 1 — but the harness's own §caveat flags this as a false-positive-prone verdict, and
  GQ-11 scoring 1 *on served receipts* while being called not-in-corpus is exactly that mode firing.
  **Do not file these as #235 without hand confirmation.**
- **Negative controls: 6/6 PASS.** Distribution 1 → 3 · 0 → 3, mean **0.5** (day 5: 0.33). K1 clear,
  K2 clear. Honest-absence 1s: GQ-16 (Lesotho), GQ-18 (Berlin diffusion), GQ-19 (oil lead/lag).
- **"Informed" analog** (real items ≥1; NOT comparable to the UI eval): **5/14 = 35.7%** (day 5: 42.9%).
- **Pair gaps:** two **negative** gaps (GQ-19 > GQ-08 by 1; GQ-16 > GQ-04 by 1) — a control beating its
  twin is the most damaging shape available, and it fired twice. Three gaps are **+0**.

## (a) ANSWER PERSISTENCE — day-5's answered set {GQ-02, GQ-11, GQ-13}

**1 of 3 held.** Critically, **no break was caused by the defect day 5 diagnosed** — every day-5
starvation signature is absent.

| Query | Day-5 | Day-6 | Held? | Identity | Mechanism |
|---|---|---|---|---|---|
| **GQ-02** Berlin Pride | 2 | **2** | **HELD** | `dt-7711` → **`dt-9156`** (7711 still `active`) | Held **through an identity substitution**. Sibling "Pride Security After Berlin Attack" served instead; ROR@20 1.0 both days. Day-5's held-by-fallback fragility (60r via `list_evidence_samples` after `ann_timeout`) is gone: day 6 served 14r/14 outlets through the normal lane, `medium` confidence, no timeout. **Cleaner hold than day 5's.** |
| **GQ-11** AJK rigging | 2 | **1** | **BROKE** (honestly) | `dt-8631` → **`dt-10323`** (8631 still `active`) | Selector moved off "Kashmir Election Unrest" (ROR@20 0.833) onto "AJK Poll Rigging Allegations" (ROR@20 0.556, G3 over-merged, 9r). Judge: *"receipts are second-phase rigging, not first-phase; Atlas flags thin coverage and partial geography."* **The better thread was alive and not chosen.** |
| **GQ-13** Sudan this week | 2 | **1** | **BROKE** (see §f) | `dt-9000` **SAME**, same label | **The payload is unchanged in every measured dimension** — 15 receipts, 14 outlets, 1 lang, ROR@20 0.933, `thin`, `label_status=partial` on both days. Only the judge's reading moved. **This is instrument variance, not an engine regression.** |

**Adjacent-persistence series:** 07-27→28 **1/2** · 07-28→31 **0/1** · 07-31→08-03 **3/3** ·
08-03→08-04 **2/4** · 08-04→**08-07 (3-night gap)** **1/3**. The last entry is not comparable to the
others and is marked as such.

**Recovered:** **GQ-12 1 → 2** — day 5's second starvation casualty. Served `dt-2802` (a *different*
live identity than day-5's `dt-3805`, same label "Iran Ukraine Caspian Attack"), receipts **2 → 31**,
ROR@20 0.95. Judge: *"Directly answers with receipts holding the Iran-Ukraine connection; capped at 2
by G7."* **This is the single strongest piece of evidence that the detail fixes delivered** — the
query day 5 lost to a 2-receipt payload now answers on 31.

## (b) IDENTITY SURVIVAL across the 3-night gap

**5 of 20 served slots kept the same identity:** GQ-04 (`dt-9462`), GQ-09 (`dt-5758`), GQ-10
(`dt-9058`), GQ-13 (`dt-9000`), GQ-20 (`dt-9414`, control).

**But that number understates the store.** Survival-in-the-store and survival-in-serving have
separated, and the distinction is the finding:

| Fate of the 15 changed day-5 serves | Count | Ids |
|---|---|---|
| Day-5 identity **still `active`**, simply not selected | **10** | `dt-8460`, `dt-7711`, `dt-5758`, `dt-8057`, `dt-8631`, `dt-3805`, `dt-1999` (some serve 2 queries) |
| Day-5 identity **demoted to `candidate`** | 2 | `dt-8478`, `dt-8558` (junk — §e) |
| Day-5 identity **row gone entirely** | 3 | `dt-9474`, `dt-10022`, `dt-10017` — all three were *fresh* ids born around day 5 |

**All four of day-5's answered identities (`dt-7711`, `dt-8057`, `dt-3805`, `dt-9000`) are still
`active` three nights later.** By the day-5 definition — *do the answer identities persist?* — the
answer is **yes, 4/4 across three nights**. Identity-as-a-state continues to hold; the layer that
stopped holding is *which* of several live identities for one story reaches the reader.

Note the ids that vanished are precisely the *newest* ones (`dt-9474`, `dt-10022`, `dt-10017`), while
the survivors are the *older* ones. Fresh promotions are the fragile class; aged identities are not.

## (c) HONESTY 0.27 → 0.25 — decomposition

Day-5 floors: GQ-09, GQ-10, GQ-12. Day-6 floors: GQ-11, GQ-13, GQ-14. **Complete turnover of which
items carry the honesty, at a near-identical rate** — the same pattern day 5 flagged.

- **Gained (3):** GQ-11 (2→1, thin+partial-geography flags cited), GQ-13 (2→1, §f), GQ-14 (0→1 — the
  Ebola serve moved to `dt-10914` with ROR@20 1.0; judge credits the honest coverage while noting it
  *"ignores the language/origin asymmetry question entirely"*).
- **Lost to an answer (1):** GQ-12 1→2 — the good kind of loss.
- **Lost to a confident miss (2), both on UNCHANGED identities:**
  - **GQ-09** (`dt-5758`, same id both days): ROR@20 **0.9 → 0.5** as receipts grew 10 → 32. Day 5:
    *"Foreign coverage only; domestic silence never surfaced"* (honest 1). Day 6: *"no domestic
    Nicaraguan press surfaced, and the silence finding is absent"* (0). **More receipts diluted the
    on-topic rate and cost the honest read.**
  - **GQ-10** (`dt-9058`, same id both days): the **G5 rule newly fired** — *"silent empty: 24h
    total=0 while 6h total=193 on the same probe, no degraded marker"*. Day 5 had no G5. An
    unflagged silent-empty at 24h converted a standing honest adjacency into a 0.

**The day-5 lesson is confirmed and sharpened:** this metric's honesty floor is carried by *payload
self-flags*, and it is fragile in **both** directions — day 5 lost floors when flags disappeared
(fresh promotion, relabel); day 6 lost them when a **new** silent-empty appeared and when **more
evidence lowered precision**. GQ-10's G5 is a live, named, actionable serving bug.

## (d) FIRST ARCHIVED RECEIPT SIGHTING — **NEGATIVE. No archived receipt was served.**

**Zero occurrences of `archived` anywhere in the day-6 ledger** (and zero in day 5's).

This is a real measurement, not a gap in the instrument. The harness records the detail payload's
`warnings[]` verbatim (`run_gold_query_eval.py:805`), and `themes.py:990` appends
**`archived_receipts_served`** to exactly that list whenever the durable lane contributes a row.
The warning never appears → **the durable-receipt lane did not fire on any of the 20 served threads.**

**Why — and it is the expected reason, not a fault.** `themes.py:887-892` gates the lane on
`missing_ids and len(signals_all) < 200`: it fires only when a member's live `signals_v2` row has been
**deleted by the 7-day hot retention**. Day 6's serving is dominated by identities whose members are
all inside retention — including four ids born within 72h (`dt-10568`, `dt-10914`, `dt-10502`,
`dt-10323`). **A 24h-window eval over freshly-served threads is close to the worst possible place to
observe a retention-death lane.** The archived path is built for *aged* stories, and this instrument
does not select for them.

**The durable-receipt lane remains unproven in production serving.** To actually sight it, probe a
thread whose members predate the retention floor directly — not through this harness. The pruning
cadence noted for "tonight" in the 08-04 block is the event that would create the condition.

## (e) DID A JUNK CLASS VISIBLY CHANGE A SERVE? — **YES, exactly once, and it is clean.**

**GQ-15** (negative control, "Australian bushfire evacuation"):

- **Day 5 served `dt-8558` "Ngaro Track Hike"** — the 0.958-syndication hiking-track blob that had
  been serving this control for multiple runs.
- **`dt-8558` is now `is_junk=true`, `junk_reason='category:Local & Community'`, demoted
  `active → candidate` at 2026-08-04 13:20:58** — roughly two hours after the day-5 eval finished.
- **Day 6 serves `dt-592` "H5N1 Bird Flu in Australia"** — and `dt-592` **was already in day-5's
  candidate pool**. This is the **only one of 15 substitutions** where the day-6 winner came from the
  day-5 shortlist: the incumbent was removed and the runner-up stepped up. Every other substitution
  came from outside the pool.

**Honest attribution caveat:** `dt-8558`'s reason is the **category** junk gate, *not* the two new
detectors named in the brief. It was swept in the same 08-04 13:20 batch that ran the
earnings-autogen pass, but crediting `30495460`/`3eb33371` for this specific demotion would be wrong.

**Measured blast radius since 08-04** (junk-flagged rows with a state change): **205 total**, of which
the two new classes account for **~37** — `earnings-autogen` **25** (confidence 65–100%),
`service-content` **12** (53–95%). The bulk (157) is the pre-existing category gate
(Entertainment & Culture 77, Local & Community 40, Obituary 24, Other 16). The brief's "~50 topics"
estimate is the right order of magnitude for the new detectors; the total sweep is ~4× larger.

**Net effect on the metric: one control's confident-wrong serve was replaced by another confident-wrong
serve.** GQ-15 scored **0 on both days** — day 5 on a hiking blob, day 6 on a bird-flu thread
(*"Confident wrong answer: bird flu thread served for bushfire evacuation question, zero on-topic
receipts"*). **The junk gate removed the junk and the control still failed.** Junk removal is
necessary and is working; it is not sufficient, because the replacement is drawn from the same
lexically-adjacent pool.

## (f) INSTRUMENT VARIANCE — a measured bound, and it matters for the headline

**GQ-13 is a natural control on the judge.** Same thread `dt-9000`, same label "Sudan Child Soldiers",
and an **identical structural payload on both days**:

| | receipts | outlets | langs | ROR@20 | confidence | label_status | **score** |
|---|---|---|---|---|---|---|---|
| Day 5 | 15 | 14 | 1 | 0.933 | thin | partial | **2** |
| Day 6 | 15 | 14 | 1 | 0.933 | thin | partial | **1** |

Day 5: *"Thin but honest thread: child soldiers story present, confidence flagged thin, label
partial."* Day 6: *"Honest thin thread, correctly flagged, but does not answer the weekly war
question."* **Both readings are defensible. The input did not move; the output moved one level.**

**Consequence for the headline:** the 21%→14% drop is a two-answer→…-one-answer move (3→2), and
**one of the two lost answers is this** — a level change on an unchanged payload. The real
engine-attributable change this run is **GQ-11 down, GQ-12 up ⇒ net zero.** The series band
(7–29%, n=14) has always been noise-dominated; this run puts a **±1 level on identical input** number
on it for the first time. Every future reading should carry that.

## Confounds to state plainly

1. **Three nights, not one.** Three nightly pipelines, two junk sweeps, a re-census and a condemnation
   run all landed between readings. Nothing here isolates a single change.
2. **Four changes shipped together** (starvation fix, durable receipts, service-content,
   earnings-autogen) and are **not separable** by this instrument. The starvation cure is the only one
   with a clean before/after signature (1r/2r → 13r/31r, zero `member_sample_starved`).
3. **Judge variance is now measured at ±1 level** on an unchanged payload (§f) and is unbudgeted in
   every prior reading in the series.
4. **`not_in_corpus` tripled (1→3)** and the harness itself flags the false-positive mode. GQ-11
   scored 1 on served receipts while being labelled not-in-corpus — internally inconsistent.
5. **K1 rubric defect persists** (reported, not fixed, per the harness): six honest-floor controls
   would score exactly 1.0 and VOID the run for behaving correctly.

## What this run says to do next

1. **The named bottleneck is now identity SELECTION, not detail serving.** Ten live identities lost
   their slot to siblings covering the same story (`dt-7711`/`dt-9156` Berlin;
   `dt-3805`/`dt-2802` Caspian; `dt-898`/`dt-9474`/`dt-10914` Ebola). **Fragment consolidation is the
   lever with the most measured evidence behind it** — this is the 8th-gate landing-predicate work
   showing up in the primary metric.
2. **GQ-10's G5 is a live serving bug with a name:** 24h total=0 while 6h total=193 on the same probe,
   **no degraded marker**. A silent empty at the wider window. Cheapest concrete fix in the run.
3. **The archived lane needs a purpose-built probe**, not this harness (§d). Query a thread with
   pre-retention members directly after a prune.
4. **Restore adjacency.** The next run should be **08-08** so the night-pair series resumes; a second
   3-night gap would leave the persistence question unanswerable in both directions.
5. **Budget judge variance.** Re-judging one fixed payload twice per run would cost ~2 calls and give
   every future headline an error bar it currently lacks.

---

*Raw artifacts (harness-written, same directory): `2026-08-07-gold-query-eval.jsonl` /
`2026-08-07-gold-query-eval.md`. Instrument, gold set and rubric unmodified. Nothing committed.*
