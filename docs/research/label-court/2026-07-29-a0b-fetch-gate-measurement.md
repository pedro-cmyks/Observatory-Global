# A0b — the fetch-side enforcement gate, measured (2026-07-29)

**Question.** GA killed Lever A and named the reason: `/threads` selects its page
by `recent_n_signals` **before** the scorer runs, so the shipped court damp can
reorder a page but never change what is on it. A0b tests the one intervention
that closes that loophole — fetch `M × limit` candidates, apply the SHIPPED
ranking (including the live damp, no new rank code), serve the top `limit`.

**Answer: ADOPT M = 2.** It is the smallest multiplier and it satisfies every
frozen condition: global top-40 entailed-share **25.0% → 42.5% (+17.5pp)**,
court-failed share **41.7% → 5.0%**, no scored door worse than **−3.3pp**, no
door anywhere loses a single row, top-10 median volume **unchanged**, and the
topic SQL cost is **flat in M** (23–67 ms at every depth). M=3 and M=4 also pass
on the numbers and buy more entailed-share — and both promote the GA
non-newsworthiness witness (*Chiefs OC Eric Bieniemy's wife shot at home*) into
the **visible fold** at rank 9 / rank 8, which M=2 does not. The gate's
tie-break ("smaller M = cheaper, prefer it") and the qualitative read agree.

**GA's verdict is not overturned — its prerequisite was satisfied.** GA §7 said
"Lever B is not a parallel workstream to Lever A, it is its prerequisite."
Between GA and now, Lever B stamped the umbrella lane (25 of 36 active umbrellas
carry a verdict) and the dark-door fix landed. On *that* field the same
intervention that "paper-passed" GA now passes a gate written specifically to
catch a paper-pass.

---

## Pre-registration

`docs/superpowers/specs/2026-07-29-a0b-fetch-gate-preregistration.md`, frozen
before this measurement (commit `99cd1eac`). Conditions verbatim:

- **C1** global top-40 entailed-share ≥ **+15pp** vs baseline.
- **C2** across the 5 most populated doors (incl. US, TR, DE), no door's top-N
  entailed-share drops by more than **5pp**.
- **C3** global top-10 median `recent_n_signals` ≥ **50%** of baseline's.
- **C4** no door loses >25% of its served rows; global top-40 ≥ 30 rows.
- **C5** the over-fetched SQL at M× LIMIT stays within the endpoint's existing
  budget (no new timeout class; report p50/p95 vs baseline).
- **Kill** if no M satisfies C1–C5.

### Operational decisions, recorded before scoring (conditions untouched)

1. **Which five doors are "the 5 most populated (incl. US, TR, DE)".** By
   candidate depth the five most populated are RU 142 · UA 110 · IR 102 · GB 86
   · IN 78 — which excludes all three doors the gate names. The parenthetical is
   binding, so the **scored C2 set = US, TR, DE + RU, UA** (the two deepest
   remaining). Every other alive door was measured anyway and is reported as an
   unscored **shadow-C2**: a door outside the scored five that gets worse is
   named beside the verdict, not hidden by the frame.
2. **Thin-but-alive doors = AR and IL** (1 served row each). They are the only
   alive thin doors left: after the dark-door fix, 16 doors serve 19–24 rows and
   the remainder serve 0. GA's thin picks (DE, MX) are no longer thin/alive
   respectively — DE now serves 16 and is in the scored set.
3. **C5 is measured two ways** because they answer different questions:
   server-side `EXPLAIN (ANALYZE, BUFFERS)` (transfers to prod) and wall-clock
   of the shipped fetch from this laptop (WAN-inflated; reports the cost *shape*).

## Harness

`backend/scripts/measure_court_enforcement.py --a0b` — the GA harness extended,
not rewritten (`run_a0b`, `a0b_serve`, `median_signals`, `A0B_DOORS`). Cost lives
in a companion script, `backend/scripts/measure_a0b_fetch_cost.py`, so a timeout
in the cost pass cannot cost the door sweep (it did, once — see C5).

Read-only: `SET default_transaction_read_only = on`, asserted on the live session.
The served arm is serving verbatim —

```python
def a0b_serve(pool, page):                       # == fetch_threads's dynamic path
    return _rank_with_damp(pool, thread_ranking._COURT_DAMP)[:page]
#   dedupe_same_event_threads(rank_threads(pool))[:limit]
```

— so the **only** variable across arms is the depth handed to
`_fetch_dynamic_threads_with_conn`. Pools are deep-copied per arm (`rank_threads`
writes into `quality{}`; the dedupe merges survivors in place).

```bash
set -a; source ~/AtlasLocalWorker/.env; set +a
backend/.venv/bin/python backend/scripts/measure_court_enforcement.py --a0b \
  --out docs/research/label-court/2026-07-29-a0b-fetch-gate-measurement.json
backend/.venv/bin/python backend/scripts/measure_a0b_fetch_cost.py \
  --page 40 --mults 2,3,4 --reps 3 --out <cost json>
```

**Field at measurement time.** Active children: failed 675 · partial 188 ·
entailed 147 · unchecked 12. Active umbrellas: **entailed 12 · failed 8 ·
partial 5 · unchecked 11** (Lever B, latest stamp 17:48Z, maintained by the
30-min cron). `dynamic_topic_members` MAX(snapshot_at) = 2026-07-28 03:28 while
`emergent_clusters` MAX = 2026-07-29 04:16 — the projection lag is live, so the
served field rides the 07-28 projection (same caveat as GA).

---

## 1. Verdict table — every condition, every M

| condition | bar | **M2** | M3 | M4 |
|---|---|---|---|---|
| **C1** global top-40 entailed-share Δ | ≥ +15pp | **+17.5pp PASS** | +30.0pp PASS | +37.5pp PASS |
| **C2** worst scored-door Δ | ≥ −5pp | **−3.3pp (TR) PASS** | −3.3pp (TR) PASS | −3.3pp (TR) PASS |
| **C3** global top-10 median volume | ≥ 50% of base | **100% (79→79) PASS** | 100% (79) PASS | 93.7% (79→74) PASS |
| **C4** door rows / global rows | ≥ 75% · ≥ 30 | **≥100% all doors · 40 PASS** | ≥100% · 40 PASS | ≥100% · 40 PASS |
| **C5** fetch cost | inside budget | **PASS** (SQL flat; see §5) | PASS | PASS |
| **ADOPTABLE** | | **YES — smallest** | yes | yes |

**Adopted: M = 2.** Three M values clear the gate; the gate says take the
smallest, and §4 shows the smallest is also the only one that keeps the
non-news witnesses out of the visible fold.

### Global door (page 40)

| arm | rows | E | P | F | U | entailed-share | Δpp | failed-share | unchecked-share | med top-10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline (today) | 36 | 9 | 3 | 15 | 9 | 25.0% | — | **41.7%** | 25.0% | 79 |
| **M2** | 40 | 17 | 12 | **2** | 9 | **42.5%** | **+17.5** | **5.0%** | 22.5% | 79 |
| M3 | 40 | 22 | 10 | 0 | 8 | 55.0% | +30.0 | 0.0% | 20.0% | 79 |
| M4 | 40 | 25 | 8 | 0 | 7 | 62.5% | +37.5 | 0.0% | 17.5% | 74 |

The failed-share collapse (41.7% → 5.0%) is the larger honest win; C1's metric
does not name it. Rows go **up** (36 → 40) because a deeper pool has more
survivors after the same-event collapse.

### Per-door entailed-share Δpp (rows as × of baseline)

| door | base rows | base E% | M2 | M3 | M4 |
|---|---:|---:|---|---|---|
| **US** * | 20 | 10.0 | **+2.5** / 1.20× | +2.5 / 1.20× | +2.5 / 1.20× |
| **TR** * | 20 | 20.0 | **−3.3** / 1.20× | −3.3 / 1.20× | −3.3 / 1.20× |
| **DE** * | 16 | 6.2 | **−2.1** / 1.50× | −2.1 / 1.50× | −2.1 / 1.50× |
| **RU** * | 16 | 6.2 | **−2.1** / 1.50× | +10.4 / 1.50× | +14.6 / 1.50× |
| **UA** * | 13 | 15.4 | **+3.7** / 1.62× | +13.8 / 1.85× | +17.9 / 1.85× |
| AR (thin) | 1 | 0.0 | 0.0 / 1.00× | 0.0 / 1.00× | 0.0 / 1.00× |
| IL (thin) | 1 | 0.0 | 0.0 / 1.00× | 0.0 / 1.00× | 0.0 / 1.00× |
| IR | 9 | 33.3 | +12.1 / 1.22× | +6.7 / 1.67× | −3.3 / 2.22× |
| GB | 19 | 42.1 | +7.9 / 1.26× | +16.2 / 1.26× | +24.6 / 1.26× |
| IN | 18 | 16.7 | **−4.2** / 1.33× | +16.7 / 1.33× | +20.8 / 1.33× |
| ES | 14 | 14.3 | −1.8 / 1.71× | +6.5 / 1.71× | +6.5 / 1.71× |
| GR | 19 | 10.5 | +2.0 / 1.26× | +6.1 / 1.26× | +6.1 / 1.26× |
| FR | 14 | 21.4 | +3.6 / 1.71× | +3.6 / 1.71× | +3.6 / 1.71× |
| ID | 18 | 5.6 | +6.9 / 1.33× | +11.1 / 1.33× | +11.1 / 1.33× |
| IT | 22 | 4.5 | +8.0 / 1.09× | +8.0 / 1.09× | +8.0 / 1.09× |
| BR | 18 | 0.0 | +4.2 / 1.33× | +4.2 / 1.33× | +4.2 / 1.33× |
| CA | 18 | 33.3 | −1.7 / 1.06× | −1.7 / 1.06× | −1.7 / 1.06× |
| CN | 12 | 8.3 | 0.0 / 1.00× | 0.0 / 1.00× | 0.0 / 1.00× |

`*` = scored C2 door. **Shadow-C2: not one of the 13 unscored doors drops more
than 5pp at any M** (worst is IN −4.2pp at M2, IR −3.3pp at M4). The gate's
paper-pass loophole was closed and the intervention did not walk through it —
this is the condition GA's mode-3 would have failed (US −0.8, TR −8.3, DE −8.3).

**Why the country doors behave differently from global.** A country door is a
**coverage** surface today: **all 18 country doors serve fewer rows than their
24-row page** (US 20/24, DE 16/24, UA 13/24, IR 9/24). Over-fetch first FILLS
the page, and the tail it fills from is court-failed — measured on the scored
five at M2, the rows that ENTER are **55–100% `failed`** (UA 6/11, US 7/10,
RU 8/11, TR 6/8, **DE 9/9**), so composition dilutes even while the head
improves. Where the door has depth beyond the page (RU 142 / UA 110 candidates),
M3/M4 turn selection back on and composition jumps (+10.4 / +17.9pp).

---

## 2. The visible fold — what the page-level metric cannot see

C1/C2 score the whole page. A reader sees ten rows. Top-10 verdict census:

| door | baseline | M2 | reading |
|---|---|---|---|
| GLOBAL | E4 P2 F0 **U4** | E4 P2 F0 **U4** | unchanged — the head is umbrella, see §3 |
| US | E1 P5 **F4** | E3 P5 **F2** | better |
| TR | E3 P4 **F3** | E4 P5 **F1** | better (despite −3.3pp on the page) |
| **DE** | E1 P2 **F7** | E1 P2 **F7** | **unchanged — pure tail dilution, the honest cost** |
| RU | E1 P3 **F5** U1 | E1 P5 **F3** U1 | better |
| UA | E2 P4 **F4** | E4 P4 **F2** | better |
| IR / GB / IN / ES / GR / FR / ID / IT / BR / CA | — | — | better at all ten |
| CN | E1 P3 F6 | E1 P3 F6 | unchanged (pool exhausted at 12 rows) |

**At M2 the visible fold improves at 14 of 19 doors, holds at 5, and gets worse
at none** (improve = fewer `failed` or more `entailed` in the top 10; held =
GLOBAL, DE, CN and the two thin doors). TR is the case that matters: its page-level entailed-share falls
3.3pp while its fold gains an entailed row and sheds two failed ones. The scored
metric and the reader's experience point in opposite directions there, and the
gate condition is the more conservative of the two — which is why it should stay
the condition, with this table beside it.

---

## 3. The unchecked share — who still rides undamped

The court never damps `unchecked`, so it is the ceiling on any enforcement.

| surface | baseline unchecked | M2 | M3 | M4 |
|---|---|---|---|---|
| GLOBAL page (40) | 25.0% (9 rows) | 22.5% (9 rows) | 20.0% (8) | 17.5% (7) |
| GLOBAL **top-10** | **4 of 10** | **4 of 10** | 4 of 10 | 3 of 10 |
| every country door | 0.0–7.1% | 0.0–9.1% | same | same |

The absolute count of unchecked rows on the global page is **unchanged (9)** —
over-fetch dilutes their share, it never removes them. Country doors are
structurally near-zero because `_DYNAMIC_TOPICS_COUNTRY_SQL` filters
`is_umbrella = false`; the unchecked lane is a **global-page phenomenon**.

**Those 9 rows are the 11 remaining unstamped umbrellas** — and they are the
biggest things in the field. In the deepest global pool:

| verdict | n | mean signals | median | max |
|---|---:|---:|---:|---:|
| **unchecked** | 9 | **138.7** | **27** | **931** |
| entailed | 40 | 26.7 | 17 | 283 |
| partial | 30 | 28.4 | 17 | 151 |
| failed | 81 | 18.5 | 15 | 69 |

Rank 1 of the world front page under every arm is `unchecked` *Iran Strait
Tensions, Russia-Ukraine Strikes, Iran Drone Attacks* (931 signals). GA §7's
finding therefore **survives in reduced form**: the top of the page is still
partly out of the court's reach — but no longer entirely. Lever B moved
*Wildfires Rage in Spain and France* (entailed, 484) to rank 3 and put verdicts
on the failed umbrellas (*Daily Earthquake Updates*, *Wangchuk Hunger Strike*,
*Typhoon Bavi Landfall*) that over-fetch then pushes off the page. **Finishing
the umbrella lane — the 11 unchecked / withheld — is the next increment of reach,
and it is worth more than raising M.**

---

## 4. Qualitative — what enters, what leaves, judged

Non-blind, single judge (Claude): I knew each row's verdict while reading its
label. The enter/exit *sets* are mechanical and reproducible from the JSON; the
"is this better" call is not.

At the global door M2 **enters 20 rows (9 entailed · 9 partial · 1 unchecked ·
1 failed) and exits 16 (14 failed · 1 entailed · 1 unchecked)**.

**1. CLEAN WIN — the whole court-failed tail leaves the world page.** Exiting at
M2: *100 Days to Midterms* · *Typhoon Bavi Landfall* · *CJP Protest Violence* ·
*Ann Widdecombe Hammer Attack* · *Trump Threatens Tariffs Over Canada Wildfires*
· *França Aprova Eutanásia* · *Burnham Vows to Challenge Trump* · *Wangchuk
Hunger Strike* · *Ramaphosa Impeachment Court Bid* · *State Pension Increases* ·
*OPEKEPE Sentencing* · *Klopp Appointed Germany Coach* · *Ayala Olmo Apology
Dispute* · *Health Q&A with Doctors*. Fourteen rows the court convicted, gone,
with real reporting in their place (*Sikkim Tunnel Collapse*, *Assam Floods
Worsen*, *Michigan Cyclosporiasis Outbreak*, *Indian Crew Struck at Odesa*,
*North Korean Troops for Russia*, *Earthquake Reports Indonesia*). The *Klopp*
row is the same class that displaced Berlin Pride in the 07-28 gold run.

**2. CLEAN WIN — TR gains its best story by gaining rows.** *Turkish Journalist
Arrested Again* (`entailed`, 60 signals) enters the Turkey door at **rank 8** —
it was not served at all at baseline — along with *Turkey S-400 Sale
Sensitivity* at rank 3, while *MasterChef Türkiye Ana Kadro* and *2026 Dünya
Kupası Tartışmaları* leave. This is the door that scores **−3.3pp**. The number
says "worse"; the page says the opposite. Report both.

**3. FAILURE — DE gets eight court-failed rows and nothing else.** The German
door fills 16 → 24 with rows that are *all* `failed`: *Bangkok Bar Fire* (a Thai
story on the German door — geo mis-scope), *Ukraine War Escalation*, *Violent
Crimes in Germany* (a generic bucket), *Police and Justice Oddities*, *Germany
Raises Security Alert*. Its top-10 does not move a single row. **DE is the pure
cost case: over-fetch bought coverage-shaped noise and zero quality.** −2.1pp
understates it; the fold table (§2) is where it shows.

**4. FAILURE avoided at M2, incurred at M3/M4 — the Bieniemy witness.**
*Emerging (US): Report: Chiefs OC Eric Bieniemy's wife shot at home*
(`entailed`, 14 signals — a small NFL-adjacent crime story carrying a pipeline
artifact in its label) is **rank 9 at M3 and rank 8 at M4** of the world front
page. At M2 it is not in the top 20. GA §6 named exactly this: court-entailed is
a statement about label↔receipt agreement, **not** about newsworthiness, and
`entailed` skews small. The gate's C3 (median volume) does not catch it — the
median holds at 79 because the umbrella head carries it. **The smallest-M rule
is what keeps this row off the fold, and that is the strongest single argument
for M=2 over M=3.**

**5. MIXED — honest non-news enters the tail at M2 too, and should be named.**
*Stock Moves Around Moving Averages* (`entailed`, rank 30), *Harga Emas Antam
Harian* (an Indonesian daily gold-price ticker, `partial`, rank 36), *Samsung
Galaxy Z Fold8 Launch* (rank 40), *Chris Brown Pleads Guilty* (rank 33) and
*Lindsay Clancy Trial Begins* (`failed`, rank 37 — a court-failed row that
survives on score). All honestly labeled; none is a story. **A numeric pass did
promote junk — it landed at ranks 30-40 instead of ranks 8-9, which is the
difference between M2 and M3, not a difference between enforcement and none.**

**6. REAL LOSS — an entailed umbrella leaves the page.** *Febrie Adriansyah
Case* (`entailed`, 54 signals) exits at every M, as does `unchecked` *Mixed
Global Sports Results* (48 — no loss). A bigger pool changes the min-max
normalisation and the page is still capped at 40, so a mid-ranked entailed row
can be displaced by better-scoring newcomers. Not a defect, but the honest
statement is that over-fetch is not monotone-better row by row.

**7. UNDER-MERGE EXPOSED (a Lever C observation, not an A0b cost).** At the RU
door *EU Fails to Agree 21st Sanctions Package* (`entailed`, 84) enters while
*EU 21st Russia Sanctions Package* (`entailed`, 72) exits; at UA *Drapatyi
Appointed Commander-in-Chief* (29) replaces *Mykhailo Drapatyi Appointed
Commander-in-Chief* (17). Same event, two surviving identities, the deeper pool
picking the bigger copy. Strictly better rows — and evidence the same-event
collapse is missing pairs.

**8. GEO NOISE in country tails.** The UA door's new tail carries *Jens Spahn
Resigns Over Surrogacy*, *New Car Launches and Reviews* and *Heatwaves and
Wildfires in France*; the DE door gets *Bangkok Bar Fire*. Country doors admit
by **coverage** geography, so a deeper page surfaces more rows whose subject is
elsewhere. Over-fetch does not create this; it makes it more visible.

**Judgment.** The exit set is unambiguously good at every door. The entry set is
roughly two-thirds real reporting and one-third honest non-news, and its
position matters more than its share: at M2 the non-news lands below the fold;
at M3/M4 it reaches rank 8-9. Enforcement is still a strong filter on the way
out and a weak selector on the way in — GA's conclusion, unchanged. What changed
is that the filter can now act at all, and at M=2 its collateral stays where a
reader will not meet it first.

---

## 5. C5 — cost

**Server-side (`EXPLAIN (ANALYZE, BUFFERS)`, prod, read-only).**

| depth ($2) | topic SQL execution | planning | rows |
|---|---|---|---|
| 40 (baseline) | 67.4 ms | 2.8 ms | 40 |
| 80 (**M2**) | **29.1 ms** | 1.8 ms | 80 |
| 120 (M3) | 23.4 ms | 1.4 ms | 120 |
| 160 (M4) | 26.3 ms | 1.3 ms | 160 |

**The topic SQL is flat in M** — it does not get more expensive, and the 67 ms at
depth 40 is first-touch, not a depth effect. The mechanism: the expensive part is
the `candidate_topics` CTE, capped at `LEAST(GREATEST($2*8, 80), 400)`, so it is
already at 320 rows at the baseline depth and saturates at 400 from M=2 on. The
`$2` LIMIT only decides how many of those already-computed rows are returned.
Against the shipped 15 s `asyncpg` cap, every depth uses **<0.5% of budget**.

**What does scale is the per-row fan-out.** `_fetch_dynamic_threads_with_conn`
issues **one `_EMERGENT_SAMPLE_SIGNALS_SQL` per returned row** (35.7 ms median
server-side, 49.3 ms max), so M× rows = M× round trips. Wall clock of the shipped
fetch, from this laptop against the Supabase pooler, 3 interleaved reps:

| depth | p50 | min | max | timeouts |
|---|---|---|---|---|
| 40 | 5.24 s | 5.04 | 16.15 (first, cold) | 0 |
| 80 (**M2**) | **16.54 s** | 13.13 | 21.24 | 0 |
| 120 | 23.66 s | 18.93 | 24.85 | 0 |
| 160 | 27.46 s | 23.71 | 28.64 | 0 |

These are **not prod numbers** — they are a laptop's WAN latency × row count, and
prod runs Fly→Supabase behind a 5-minute Redis cache, so this is a cold-miss cost
only. They are reported because the *shape* transfers: total latency grows
roughly linearly in M while SQL time does not.

**Two honest cautions.**
1. The first cost pass (run inside the door harness, with a second connection
   from the same laptop active) **raised `TimeoutError` on a sample-signal query**
   — the shipped 8 s per-query cap. It did not recur in 12 clean attempts, and
   the cap is *per query* and independent of M (each query is the same size), so
   it is a concurrency artifact rather than an M effect. Recorded, not scored.
2. `fetch_threads` is shared by `/threads`, the L1 Brief (`briefing.py`,
   limit 10), `country_edition` (limit 24) and `research_leads`. Live callers ask
   for 4–24 rows, one asks for 40 (`FrameStrip`). At M=2 that is 8–48 rows —
   the 160-row arm above is a worst case no caller reaches.

**The fan-out is removable, and cheaply.** A harness probe (not shipped code) ran
ONE `_EMERGENT_SAMPLE_SIGNALS_SQL` over the union of the pool's sample ids
instead of the per-row loop, same connection, back to back:

| pool | per-row loop (shipped) | one batched query |
|---|---|---|
| 40 rows / 932 ids | 4.57 s | **0.44 s** |
| 80 rows / 1,675 ids | 16.51 s | **0.56 s** |

Batching makes the over-fetch essentially free (the topic SQL being flat
already). **This is a recommendation, not part of the adopted change** — it is a
separate, independently reversible perf fix and should not be bundled into the
enforcement flip.

**C5 verdict: PASS at every M**, with M=2 the cheapest, and one named residual —
cold-miss latency scales with M until the sample fetch is batched.

---

## 6. If adopted — the exact implementation shape (NOT implemented here)

Env knob **`ATLAS_THREADS_FETCH_MULT`**, integer, **default 1** (= today,
byte-identical serving). Adopt at **2**.

**Where the change goes.** `app/services/thread_intelligence.py`, inside
`fetch_threads._merged`, the dynamic branch only:

```python
# today
dynamic = await _fetch_dynamic_threads_with_conn(
    active_conn, hours=hours, limit=limit, country_code=single_country,
)
...
if dynamic:
    return dedupe_same_event_threads(rank_threads(dynamic))[:limit]
```

The fetch depth becomes `limit * mult`; **the `[:limit]` cut and everything else
stay exactly as they are.** No change to `rank_threads`, no new court factor, no
change to `_DYNAMIC_TOPICS_SQL` or `_DYNAMIC_TOPICS_COUNTRY_SQL` (the `$2` LIMIT
is already parameterised and the candidate CTE cap already bounds the cost).

**Rules the shape must respect:**
- Read the multiplier once, clamp it (`1 <= mult <= 4`) and floor it at 1 on any
  unparseable value — a typo must degrade to today, never to an unbounded fetch.
- Apply it to the **dynamic** path only. The `atlas_only` branch
  (`topic_slug` / multi-country) and the emergent fallback keep `limit`;
  they were not measured.
- Apply it to **both** the global and single-country calls — the country doors
  are where the measured coverage gain is (16 of 19 serve short pages).
- It must not touch `limit` itself: the served page size, the Redis cache key
  (`threads:list:{hours}:{limit}:{country}:{person}`) and the response contract
  are unchanged, so the flip is invisible to every caller and to the cache.
- Blast radius by construction: `/threads`, the L1 Brief's `top_threads`,
  `country_edition`, `research_leads`. All four get the same treatment; all four
  were exercised at their live limits by this measurement's door set.
- **Two-night watch before staying on** (pre-registration §"If adopted"): re-run
  this harness on two consecutive days and compare against tonight's numbers —
  C1's margin is 2.5pp on one snapshot (see §7).

**Reversal:** `ATLAS_THREADS_FETCH_MULT=1` + let the 5-minute Redis TTL expire.

---

## 7. Caveats

- **One field snapshot, one night.** C1 clears its bar by **+2.5pp** at M=2.
  Day-over-day variance in this field is known to be large (the 07-28 gold run
  saw the served thread set change completely overnight), so a re-run could put
  M=2 under +15pp. The pre-registered two-night watch is not a formality here;
  if M=2 misses on a later night, M=3 is the documented fallback **with** its
  named cost (the Bieniemy class at rank 9).
- **The projection lag is live** (`dynamic_topic_members` 07-28 03:28 vs
  `emergent_clusters` 07-29 04:16), so this measures the 07-28 projection.
- **Umbrella stamping is mid-flight.** 25 of 36 active umbrellas carry verdicts
  and the 30-min cron keeps stamping; 11 unchecked ride undamped (§3). The
  entailed-share numbers will move as coverage completes — in the direction of
  *more* reach, not less.
- **C2's five doors were chosen by a rule the gate under-specified** (§"Operational
  decisions"). The shadow-C2 sweep over the 12 other alive doors is the guard
  against that choice mattering; none of them fails either.
- **The qualitative read is one non-blind judge.**
- **`AR` and `IL` are thin to the point of vacuity** — 1 candidate each, so
  every arm serves the identical single row and C2/C4 are trivially satisfied
  there. Reported for completeness, not as evidence.
- Doors are measured at page 24 (`country_edition._MAX_THREADS`) and global at
  page 40 (the audit frame). `/threads` defaults to `limit=10`; the M effect at
  smaller pages was not separately measured.

---

*Read-only throughout: no writes, no LLM calls, no engine changes. Artifacts:
this file + `2026-07-29-a0b-fetch-gate-measurement.json`. Harness:
`backend/scripts/measure_court_enforcement.py --a0b` (extended) +
`backend/scripts/measure_a0b_fetch_cost.py` (new). Not committed.*
