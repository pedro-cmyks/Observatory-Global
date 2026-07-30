# The threading floor — why small countries are structurally thread-less

**Date:** 2026-07-29 · **Branch:** `eclipse-dramatic-moment` · **Mode:** read-only
(`SET default_transaction_read_only = on`), no code changed, nothing implemented.
**Witnesses:** BO, ML, MM (the gold-eval failures) + CO/JP/NG/VE (the doors
question) vs **TR** (healthy contrast).
**Provoked by:** `docs/research/gold/2026-07-29-gold-external-5.md` — 4/5 external
gold failures had the material IN-CORPUS and still served zero threads.

---

## 0. Verdict in one paragraph

The threading floor is **not a signal-volume floor and not a cluster-size floor.**
Bolivia and Mali produce clusters of the same size as the United States
(tier-invariant: mean 12.2 vs 12.7 members, median 10 vs 11). What kills them is
the **lifecycle clock**: `snapshots_since_seen` advances **2–4 times per night**
(measured, `n_snapshots_processed` = 2,3,3,3,4,4,4 over the last seven runs) while
a tail country is **clustered only on weekend-mode nights** (150-min weekday budget
defers 130–154 countries; 480-min weekend budget defers 0). A topic outside the
night's pass therefore ages through `stale_k=2` (deprecate) **and** `retire_m=4`
(retire) in a **single missed pass**. Measured consequence: **1,007 topics whose
last match was the 07-27 snapshot sit at `snapshots_since_seen = 4` and are
RETIRED after exactly one elapsed snapshot**, and **1,353 retired topics pass every
quality bar** (persist ≥2, volume ≥12, cohesion ≥0.50, not roundup, not junk,
noise < 0.85) and were matched within the last two passes. Only **30 of 168
clustered countries** can currently serve a thread. **The CO/JP/NG/VE doors are an
honest zero** — the post-`55e11be7` SQL pre-image is genuinely 0 active rows; the
defect is entirely upstream. Myanmar is a different and rarer case: it is the one
witness where the literal floor binds — it forms **zero gated clusters on every
pass**.

**Do not lower `min_kept`, `cohesion_min`, `volume_min` or `noise_max`.** The
measurements say the quality bars are not what is binding. The proposal below
removes *operational* penalties only.

---

## 1. Funnel trace, per witness

### Stage 1 — signals (`signals_v2`, subject `country_code`, last 168 h)

| CC | 24 h | 7 d | headline ≥ 20 | distinct sources | langs |
|----|-----:|----:|--------------:|-----------------:|------:|
| **BO** | 64 | 714 | 711 | 136 | 5 |
| **ML** | 80 | 560 | 553 | 203 | 11 |
| **MM** | 19 | 194 | 182 | 76 | 4 |
| BF | 13 | 386 | 386 | 128 | 4 |
| NE | 16 | 145 | 145 | 60 | 3 |
| SN | 122 | 1 543 | 1 540 | 228 | 5 |
| CI | 68 | 545 | 545 | 83 | 4 |
| **CO** | 530 | 5 734 | 5 682 | 618 | 5 |
| VE | 454 | 5 110 | 5 073 | 1 099 | 14 |
| NG | 899 | 7 470 | 7 393 | 450 | 7 |
| JP | 1 943 | 14 787 | **10 754** | 2 914 | 18 |
| **TR** | 2 709 | 21 062 | 20 958 | 1 183 | 12 |

Side finding (JP): the R1 pull requires `length(headline) >= 20`, and **27.3 % of
Japanese signals are shorter than 20 characters** — a full Japanese sentence often
is. Every other witness loses ≤ 6 %. This is a script-blind exclusion that only
bites CJK; it is not what kills the JP door today (see §3) but it is a real
structural bias filed here for the record.

### Stage 2 — R1 eligibility (`signal_embeddings` ⋈ `signals_v2`, the exact `_COUNTRIES` predicate)

`run_scoped_snapshot.py:105-113` admits a country at `COUNT(*) >= --min-embedded`
(runner default **100**).

| CC | eligible embedded / 7 d | ≥ 100 → in the pass? |
|----|------------------------:|:---------------------|
| BO | 604 | ✅ |
| ML | 492 | ✅ |
| **MM** | **162** | ✅ (clears the gate — see §2.3) |
| BF | 350 | ✅ |
| NE | 126 | ✅ |
| SN | 1 452 | ✅ |
| CI | 488 | ✅ |
| CO | 5 224 | ✅ |
| VE | 4 476 | ✅ |
| NG | 6 783 | ✅ |
| JP | 7 656 | ✅ |
| TR | 18 651 | ✅ |

**No witness is excluded at the eligibility gate.** `min_embedded=100` is not the
floor. (Bolivia's 80 % self-voice and 5 domestic outlets do reach the clusterer.)

### Stage 3 — R1 clustering: does the pass actually reach the country?

`emergent_clusters` by snapshot, last 10 passes (`R1 DONE` lines,
`~/AtlasLocalWorker/logs/scoped-snapshot.{out,err}.log`):

| snapshot | mode | clusters | primary countries | deferred | elapsed |
|----------|------|---------:|------------------:|---------:|--------:|
| 07-20 | weekend | 3 754 | 148 | 19 | — |
| 07-21 | weekday | 2 369 | 20 | 163 | — |
| 07-22 | weekday | 2 517 | 135 | 19 | 9 001 s |
| 07-23 | weekday | 2 190 | 21 | 143 | 9 037 s |
| 07-24 | weekend | 2 395 | 130 | 21 | 9 025 s |
| 07-25 | weekend | 3 854 | 144 | **0** | 15 389 s |
| 07-26 | weekend | 3 593 | 146 | **0** | 11 107 s |
| **07-27** | weekend | 3 475 | **152** | **0** | 10 937 s |
| 07-28 | weekday | 2 032 | **16** | 154 | 9 025 s |
| 07-29 | weekday | 863 | **32** | 132 | 9 084 s |

The 150-min weekday `ATLAS_SNAPSHOT_RUN_BUDGET_MIN` is exhausted **every weekday
night**; the 480-min weekend budget fits the whole world. Rotation fairness
(`order_countries`) puts last pass's deferrals first, so weekday nights run the
**big** countries and the tail waits for the weekend.

Which countries were present, last three passes:

- **07-27 (weekend, full):** 152 countries incl. BO, ML, BF, NE, SN, CI
- **07-28 (weekday):** BR CA CN DE ES FR GB GR ID IN IR IT RU TR UA US — 16, no tail
- **07-29 (weekday):** AR AT AU BD BE BG CH CL CO EG FI HR HU IE IL JP KR MK MX NG NL PE PH PK PL RO RS SA SE TW VE VN — 32, still no tail

Per-country log outcomes for the witnesses (each line one pass):

```
[81/168]  BO: n=745 clusters=5      [103/168] BO: n=711 clusters=4      [92/168] BO: n=742 clusters=2
[89/168]  ML: n=571 clusters=5      [110/168] ML: n=606 clusters=6      [102/168] ML: n=609 clusters=7
[102/168] BF: n=373 clusters=2      [126/168] BF: n=381 clusters=3      [119/168] BF: n=391 clusters=1
[133/168] NE: n=133 clusters=1      [156/168] NE: n=145 clusters=2      [150/168] NE: n=136 clusters=2
[130/168] MM: no gated clusters     [158/168] MM: no gated clusters     [154/168] MM: no gated clusters
```

**BO and ML cluster fine when the pass reaches them.** MM never does (§2.3).

### Stage 4 — `dynamic_topics` lifecycle (primary country = `top_country_codes[1]` of the topic's latest member cluster)

| CC | state | topics | avg `n_snapshots` | ≥2 | avg `since_seen` | roundup/junk | **pass every quality bar** |
|----|-------|-------:|------------------:|---:|-----------------:|-------------:|---------------------------:|
| **BO** | candidate | 2 | 1.0 | 0 | 0.0 | 1 | 0 |
| **BO** | retired | 2 | 3.5 | 2 | **6.5** | 0 | **2** |
| **ML** | candidate | 4 | 10.0 | 4 | 0.5 | **4** | 0 |
| **ML** | retired | 2 | 13.0 | 2 | **4.0** | 0 | **2** |
| **MM** | candidate | 1 | 1.0 | 0 | 1.0 | 0 | 0 |
| **MM** | retired | 1 | 3.0 | 1 | **4.0** | 0 | **1** |
| BF | candidate / retired | 2 / 2 | 1.0 / 3.5 | 0 / 2 | 0.0 / **6.5** | 1 / 0 | 0 / **2** |
| NE | retired | 4 | 5.0 | 4 | **4.0** | 0 | **4** |
| CI | candidate / retired | 5 / 1 | 9.0 / 3.0 | 5 / 1 | 0.0 / **4.0** | **5** / 0 | 0 / **1** |
| SN | **active** / cand / ret | **2** / 4 / 14 | 6.0 / 4.0 / 6.3 | 2/1/14 | 1.0 / 0.0 / 4.2 | 0/0/0 | 2 / 0 / **14** |
| **CO** | candidate | 15 | 5.3 | 12 | 0.1 | **12** | 0 |
| **CO** | retired | 23 | 6.5 | 23 | **4.2** | 0 | **23** |
| JP | candidate / retired | 19 / 29 | 5.4 / 4.1 | 13 / 26 | 0.2 / **4.7** | 11 / 0 | 2 / **26** |
| NG | candidate / retired | 45 / 102 | 2.4 / 4.5 | 20 / 102 | 0.1 / **4.4** | 19 / 0 | 0 / **102** |
| VE | candidate / retired | 16 / 40 | 4.7 / 7.7 | 12 / 38 | 0.0 / **4.5** | 10 / 0 | 0 / **38** |
| **TR** | **active** | **47** | 5.5 | 39 | **0.0** | 0 | **39** |
| **TR** | candidate / retired | 46 / 35 | 11.0 / 4.7 | 37 / 34 | 0.0 / 5.3 | 20 / 0 | 9 / 34 |

Read the **retired** rows. Across CO (23), JP (26), NG (102), VE (38), SN (14),
NE (4), BO (2), ML (2) — these topics **pass every promotion condition** and are
retired purely on the staleness counter. TR, which is in essentially every pass,
sits at `since_seen = 0.0` with 47 active.

The **candidate** rows carry the second, smaller lane: what actually survives the
clock in a tail country is its *wire feed*. ML's 4 candidates are **4/4
roundup/junk** with `n_snapshots ≈ 10`; CI's are 5/5; CO's top six by volume are
`Colombian Lottery Results`, `Colombia News July 2026`, `Sinuano Lottery Results`,
`Quiniela Lottery Results`, `Motilón Lottery Results` (`is_roundup = t`) plus junk.
The junk/roundup detectors are doing their job — they are correctly blocking these
— but the effect is that the only thing persistent enough to promote in a tail
country is the thing that must never be promoted.

### Stage 5 — serving (post-`55e11be7` country door)

Replicating `_DYNAMIC_TOPICS_COUNTRY_SQL`'s `EXISTS` predicate in the DB, and
curling prod:

| CC | door SQL pre-image (active rows) | prod `/threads?country_code=` (limit 40) |
|----|---------------------------------:|-----------------------------------------:|
| BO | 0 | 0 |
| ML | 0 | 0 |
| MM | 0 | 0 |
| **CO** | **0** | **0** |
| **JP** | **0** | **0** |
| **NG** | **0** | **0** |
| **VE** | **0** | **0** |
| SN | 1 | 1 |
| **TR** | **39** | **26** |
| US | 65 | 27 |

---

## 2. The binding constraint, per witness

### 2.1 BO, ML (and BF, NE, CI, SN) — **the lifecycle clock**

Signals arrive, embeddings exist, R1 clusters them into 1–7 gated clusters
whenever the pass reaches them. They die between passes.

Two independent multipliers stack:

**(a) The pass reaches them only on weekend-mode nights.** 130–154 countries
deferred every weekday night; 0 deferred on weekend nights. The tail's real
clustering cadence is ~3 nights in 7, and the last full pass was **07-27**.

**(b) The lifecycle tick fires 2–4× per night, not once.**
`project_dynamic_topics.py:878` iterates `group_by_snapshot(new_clusters)` and
calls `process_snapshot` once **per distinct `snapshot_at` that still holds
un-ingested clusters**. Every such group is a full tick: `t.since_seen = 0 if seen
else t.since_seen + 1`. Measured `n_snapshots_processed` in the last seven
projection summaries: **4, 3, 4, 3, 2, 3, 4** — never 1, although exactly one
snapshot is produced per night (verified: `COUNT(DISTINCT snapshot_at)` = 1 per day
for the last 17 days, except 07-19 and 07-15).

The extra groups are **straggler clusters at older `snapshot_at`**. Current residue:

| snapshot | clusters never ingested | members |
|----------|------------------------:|--------:|
| 07-25 | 6 | 77 |
| 07-26 | 5 | 82 |
| 07-27 | 17 | 280 |
| 07-28 | 44 | 671 |

Four un-ingested snapshot groups waiting → the next projection run will fire four
phantom ticks before it even reaches 07-29. The stragglers concentrate in
RU (10), ES (7), GR (6), FR (5), UA (5), IR (5) — the countries that *have*
umbrellas — and `build_umbrella_topics.py:517` **`DELETE FROM
dynamic_topic_members WHERE dynamic_topic_id IN (…umbrellas…)`** rebuilds umbrella
membership every night. `hydrate_topics` already documents the swallow cycle in
place (`project_dynamic_topics.py:709-715`: *"their member rows are cleared +
rebuilt from children every night, so a cluster that attaches directly to one …
loses its membership at the next rebuild"*). The orphans re-enter `new_clusters` at
their **original** `snapshot_at` and manufacture a tick for every topic in the
world. **Leading hypothesis, strongly supported by the country distribution and the
in-code note; worth one confirming run before the fix lands.**

**The arithmetic that kills the tail.** `stale_k = 2`, `retire_m = 4`. At 2–4
ticks/night, one missed pass ⇒ `since_seen` 2–4 ⇒ deprecated *and* retired the
same night. Direct evidence — `since_seen` by last-matched snapshot:

| last matched | `since_seen` | state | topics |
|--------------|-------------:|-------|-------:|
| 07-28 | 0 | active | 1 007 |
| 07-28 | 0 | candidate | 981 |
| 07-27 | 0 | candidate | 646 |
| 07-27 | 1 | active | 15 |
| **07-27** | **4** | **retired** | **1 007** |
| 07-26 | 4 | retired | 353 |

Exactly **one** snapshot (07-28) elapsed after 07-27, yet 1 007 topics show
`since_seen = 4`. That is impossible under a once-per-pass counter.

Because retirement lands before the next pass, a tail topic can never hold
`active` long enough to matter, and by the time its country is clustered again the
story is 3–4 days old, outside the 168 h corpus, and no longer centroid-matches
(`MATCH_THRESHOLD 0.88` + `ANCHOR_THRESHOLD 0.93`) — so it re-founds as a fresh
1-snapshot, 8-member candidate that fails `persist_min=2` *and* `volume_min=12`,
which is exactly what BO's and MM's candidate rows look like.

**Refuted en route (state it plainly):** re-match rate is *not* the problem. On the
07-27 pass, clusters attaching to a pre-existing identity: BO 3/3 (100 %),
ML 6/6 (100 %), NE 2/2, CI 6/6, SN 12/12, CO 33/34 (97 %), TR 65/68 (96 %),
US 161/182 (89 %). Identity resolution works fine for small countries — better
than for the US.

**Also refuted: per-country cluster-size deficit.** Cluster size on the 07-27 pass,
by how many clusters the country produced:

| country tier | countries | clusters | mean members | median | ≥ 12 members |
|--------------|----------:|---------:|-------------:|-------:|-------------:|
| A: ≥ 40 clusters | 25 | 2 612 | 12.7 | 11 | 40.8 % |
| B: 15–39 | 14 | 312 | 12.6 | 10 | 39.1 % |
| C: 5–14 | 47 | 402 | 12.5 | 11 | 41.5 % |
| D: 1–4 (tail) | 66 | 149 | 12.2 | 10 | 30.9 % |

**A Bolivian cluster is the same size as an American one.** This is the single most
important control in this document, and it **kills the obvious proposal**: a
per-country adaptive `volume_min` would be tuning a threshold that is not
differentially binding. What differs is the number of clusters (2.3/country in the
tail) and the number of ticks they survive.

### 2.2 CO, JP, NG, VE — **the same clock, one tick later**

Identical mechanism, one rotation slot better. All four were in the 07-29 pass —
which **has not been projected**: `dynamic_topic_members` stops at 07-28 while
`emergent_clusters` holds 863 clusters at 07-29 04:16, all 863 never ingested. So
their newest evidence is not in serving yet either.

CO is the clean specimen: 33/34 clusters re-matched on 07-27, 23 retired topics
that pass every bar (`Putin Trump Calls on Ukraine` agg 230, `Colombia 42-Hour
Workweek` agg 115, `ELN Mass Kidnapping in Chocó` agg 82), `last_seen = 07-27`,
`last_state_change = 07-28`, `since_seen = 4`. Retired in one night.

### 2.3 MM — **the literal floor: the clustering/precision gate**

Myanmar is the only witness where the floor binds where the name suggests. It
clears eligibility (162 embedded ≥ 100), it is **not** deferred (log positions
130–158 of 168, i.e. it is reached), and it returns **`no gated clusters` on every
pass** — 4/4 in the log, and only 2 of the last 11 snapshots ever produced an MM
cluster.

At ~146–182 deduped eligible signals over 168 h, HDBSCAN(`mcs=5`, `ms=2`, `leaf`)
finds candidates, then `_apply_gate(..., min_kept=8)`
(`emergent_poc.py:357-358`) drops every cluster whose post-gate keep is < 8 —
*"cannot honestly claim 90 % precision on a thin keep."* The gate is right to say
so. The floor for MM is **corpus mass inside the window**, and the honest lever is
**more time**, not a lower bar (§4, P4).

### 2.4 TR — why the contrast is healthy

TR is in essentially every pass (rotation priority when deferred, and it is a
weekday-budget country). `since_seen = 0.0`, 47 active, 39 of them passing every
bar. Nothing about TR's *data* is different from BO's per cluster; only its
position in the run budget is.

---

## 3. The CO / JP doors verdict: **honest zero, no residual defect**

The `55e11be7` fix is working as designed. Evidence:

1. **The SQL pre-image is genuinely empty.** Re-running
   `_DYNAMIC_TOPICS_COUNTRY_SQL`'s `EXISTS` clause verbatim returns **0 active
   rows** for CO, JP, NG, VE (and BO/ML/MM). There is no row for
   `thread_matches_country` to drop — the Python arbiter is not reachable.
2. **The upstream cause is measured and sufficient.** CO/JP/NG/VE have
   0 active / many candidate / many retired topics (§1 stage 4). A door cannot
   serve what the lifecycle has retired.
3. **The SQL↔Python agreement holds where rows exist.** TR: 39 pre-image rows →
   26 served at `limit=40`. The gap is **not** label dedupe (all 39 labels are
   distinct and non-null) and **not** the candidate LIMIT (320 at `limit=40`). It
   is the single `continue` in `fetch_threads` (`thread_intelligence.py:1672`) —
   the #238 subject re-key correctly dropping 13 threads that Turkish outlets cover
   but whose verified subject is elsewhere. That is the designed behaviour, not the
   dark-door defect.

**Verdict: not a defect. Fix the lifecycle and the doors light up on their own.**

**One honest residual to watch, not to act on yet:** the #238 subject arm removes
**33 % of TR's door candidates** (13/39). If subject-geography verification is
systematically more available for foreign-subject stories than domestic ones, this
becomes a *second* attrition lane pointed at exactly the countries this document is
about. Unmeasured here; worth its own pass once the lifecycle fix lands and the
tail has rows to measure.

---

## 4. Proposed floor change

**Framing.** The measurements refute the intuitive fix. Cluster sizes are
tier-invariant, `min_embedded` excludes nobody, and identity re-match is ~100 % in
small countries. There is nothing to lower. The proposal removes **operational**
penalties — a topic must not be punished for a budget deferral or for an
umbrella-rebuild artifact — and buys MM's class **volume with time, not with a
lower bar**.

### P1 — one lifecycle tick per snapshot pass (root fix, no threshold moves)

Make `process_snapshot` advance the clock once per **pass**, not once per
`group_by_snapshot` group. Two parts:

- **P1a.** Stop the umbrella rebuild from orphaning member rows (or make orphaned
  clusters re-attach without re-entering `new_clusters` at their original
  `snapshot_at`). The swallow cycle is already documented at
  `project_dynamic_topics.py:709-715`; this closes it.
- **P1b.** Guard regardless: `since_seen` may increment at most once per distinct
  snapshot pass **not previously ticked**, tracked on the topic (e.g. compare
  against the last snapshot the topic was aged for) rather than implied by
  iteration count. Belt-and-braces, so any future straggler source cannot
  re-open the hole.

Measured headroom: **1 353 retired topics** currently pass every quality bar and
were matched within the last two passes.

### P2 — a per-country lifecycle clock (this is the actual "thin-country lane")

`snapshots_since_seen` should increment only on ticks where the topic's country was
**actually clustered**. A country the run budget deferred did not fail to produce a
story; Atlas failed to look. The scoped snapshot already knows exactly which
countries ran (`ck.done`, and the `deferred_ccs` / `timegap_ccs` ledger) — pass that
set to the projection and skip aging for topics whose primary country is not in it.

This lowers **no** quality bar. `persist_min`, `volume_min`, `cohesion_min`,
`noise_max`, roundup and junk all stay exactly where they are.

### P3 — make the tail's cadence deterministic

Reserve a slice of the weekday run budget for the tail (e.g. last 20 %, or the
countries below the `subproc_min_n` threshold) so a small country is clustered
**every** night rather than only in weekend mode. The tail is cheap: the 66
tail countries produced 149 clusters total on 07-27; their O(n²) cost is
negligible against US/IN/CN. This is a scheduling change, not a quality change,
and it is what makes `persist_min=2` reachable for BO and ML at all.

### P4 — the MM class: buy volume with time, never with `min_kept`

For countries below a measured eligible-signal threshold, cluster over a **longer
window** (e.g. 336 h instead of 168 h) while leaving `mcs`, `ms`, the precision
gate and `min_kept=8` untouched. A 14-day Myanmar corpus is ~360 eligible signals —
enough for the gate to have something to keep — and the ≥ 90 %-precision claim is
preserved by construction because the gate itself does not move.

### Honesty risk and how each proposal guards it

| Risk | Guard |
|------|-------|
| A lower floor promotes junk | **No floor is lowered.** `min_kept=8`, `cohesion_min=0.50`, `volume_min=12`, `noise_max=0.85`, `persist_min=2`, roundup and junk detectors all unchanged. |
| A per-country clock resurrects dead stories | Keep an absolute wall-clock recency bound (`last_seen` inside the serving window) independent of the tick counter — the existing `#250` 72 h floor and the `regrade` freshness guard already encode this pattern. |
| Un-aging tail topics floods serving with wire feeds | ML's 4/4 and CI's 5/5 persisting candidates are roundup/junk **today** — the detectors already catch them, and they must stay ON and be measured on the *new* actives (gate TF-2). This is the specific failure mode to watch. |
| Longer windows create stale blobs (MM class) | Cap the extension; gate on the same K2 ≤ 2 % false-merge bar used by the witness-reconvergence work; measure the false side in the same pass as the recall side. |
| P1 doubles the active set and dilutes the front page | Ranking is unchanged; gate TF-4 pre-registers a no-regression bar for US/TR. |

---

## 5. DRAFT pre-registered gate

**Written before any run. Kill rules are fixed here; do not move them afterwards.**

**Baselines frozen 2026-07-29** (measured above, to be re-measured identically):

- countries with ≥ 1 servable thread: **30**
- active non-umbrella topics: **1 022** (`since_seen` avg 0.01)
- retired-but-fully-qualifying, matched within 2 passes: **1 353**
- BO / ML / MM / CO / JP / NG / VE served threads: **0 / 0 / 0 / 0 / 0 / 0 / 0**
- TR / US served threads: **26 / 27**
- unlabelled non-umbrella topics: candidate 486 (17.3 %), retired 205 (7.3 %)

| Gate | Assertion | KILL rule |
|------|-----------|-----------|
| **TF-1** *(tick correctness — P1)* | For every topic, `snapshots_since_seen` ≤ number of snapshot passes elapsed since its last member snapshot. | KILL if **any** topic violates by ≥ 1 on **two consecutive** nights. |
| **TF-2** *(honesty — the load-bearing one)* | Of topics newly `active` and attributable to the change, hand-label a random **40**: ≥ 90 % must be a real story, the label court `failed` rate must not exceed the current active population's, and the roundup+junk rate among them must be **≤** the current active rate. | KILL the change if **either** the 90 % bar or the roundup/junk comparison fails. Coverage bought with junk is a failure, not a partial win. |
| **TF-3** *(coverage — the point)* | Countries with ≥ 1 served thread rises **30 → ≥ 60**, and **BO and ML each serve ≥ 1 thread** whose label-court verdict is not `failed`. | KILL if TF-3 passes while TF-2 fails. TF-3 alone is never a GO. |
| **TF-4** *(no big-country regression)* | US and TR served-thread counts and mean cohesion fall by **≤ 10 %** vs baseline. | KILL if either drops > 10 %. |
| **TF-5** *(MM class, P4 only)* | Window extension for sub-threshold countries keeps the pooled false-merge rate **≤ 2 %** (the K2 bar from `2026-07-29-witness-reconvergence.md`), measured on the same pass as the recall gain. | KILL P4 independently of P1–P3; P4 failing must not block the rest. |
| **TF-6** *(persistence)* | Day-over-day answer persistence: a tail-country thread served on day *N* still serves on day *N+1* for **≥ 70 %** of cases, measured over ≥ 2 consecutive days. | KILL if < 70 % — it would mean the clock fix moved the churn rather than removing it. |

**Run protocol:** P1 and P2 measured **separately** before being measured together
(P1 alone should already recover a large share of the 1 353; if it does not, the
straggler hypothesis in §2.1(b) is wrong and must be re-diagnosed before P2).
Every gate measures the false side in the same pass as the recall side. Gold runs
span ≥ 2 consecutive days per the standing instability finding.

---

## 6. Additional findings surfaced en route (not part of the proposal)

1. **Five-night total label blackout, 07-22 → 07-26.** Every cluster in every
   country came back `(label failed)`:

   | run | countries with clusters | labelled | label FAILED |
   |-----|------------------------:|---------:|-------------:|
   | 07-20 22:00 | 148 | 148 | 0 |
   | 07-21 02:30 | 20 | 20 | 0 |
   | 07-22 02:30 | 135 | 135 | 0 |
   | 07-22 22:00 | 21 | 0 | **21** |
   | 07-23 22:00 | 130 | 0 | **130** |
   | 07-24 22:00 | 144 | 0 | **144** |
   | 07-25 22:00 | 146 | 0 | **146** |
   | 07-26 22:00 | 152 | 0 | **152** |
   | 07-27 22:00 | 16 | 16 | 0 |
   | 07-28 22:00 | 32 | 32 | 0 |

   Residue: **486 candidate (17.3 %) and 205 retired topics carry a NULL/empty
   label** — visible directly in CO's candidate list. Actives are 0 % unlabelled,
   so serving is protected, but fragment merging was inert for five nights
   (`labels_compatible(None, None)` is False). **Explicitly not claimed:** that
   labeling caused the budget exhaustion. The correlation does not hold — 07-20
   and 07-22 02:30 labelled 148 and 135 countries inside the same budget. The two
   are co-occurring defects, not cause and effect.

2. **The 07-29 snapshot is unprojected.** 863 clusters / 32 countries sit in
   `emergent_clusters` with zero member rows. Whether this is normal timing (the
   runner projects after R1 exits) or a skipped step is not established here;
   it means today's serving state is one pass stale for CO/JP/NG/VE.

3. **CJK headline exclusion.** `length(headline) >= 20` removes **27.3 %** of
   Japanese signals from the R1 pull (vs ≤ 6 % for every other witness). A
   character-count floor is script-blind. Not binding on the JP door today, but
   it is a real ~7 000-signal-per-week hole in the corpus for CJK countries.

---

## 7. Reproduction

Read-only, no harness file left behind beyond the throwaway psql wrapper.

```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
psql "$DATABASE_URL" -c "SET default_transaction_read_only = on" -c "SET statement_timeout='120s'" -c "<query>"
```

Per-country queries must be issued **one country at a time** — an `IN (...)` list
over 12 countries defeats `idx_signals_v2_country_time` and times out at 120 s,
while a single-country count runs in ~250 ms.

Logs: `~/AtlasLocalWorker/logs/scoped-snapshot.{out,err}.log`
(`R1 DONE`, `RUN BUDGET`, `TIME LEDGER`, `n_snapshots_processed`, per-country lines).

Prod doors: `curl -s "https://atlas-api-pedro.fly.dev/api/v2/threads?hours=168&limit=40&country_code=CC"`.
