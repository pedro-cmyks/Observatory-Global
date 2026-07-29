# Lever A0 — court-enforcement modes simulated over the served field (2026-07-29)

**Question.** The 07-29 blind-spot audit found 702/1058 active topics court-FAILED
and still serving. Lever A proposes to enforce that verdict in `/threads`. Which
enforcement mode clears pre-registered gate **GA**, and does the page it produces
actually look better?

**Answer: no mode clears GA — and the premise is wrong in a way that matters.**
The court damp Lever A proposes to add **already ships and is live** (rank v2,
`ac4a4881`, `ATLAS_RANK_V2` defaults ON and is unset in `fly.toml` and in Fly
secrets). Measured today it removes three court-failed rows from the global
visible fold. The reason 47% of the served page is still court-failed is not a
missing damp — it is that **`/threads` selects its page by volume BEFORE the
scorer runs**, so a rank damp can reorder the page but can never change which
rows are on it. Every mode-1 factor moves top-40 composition by **+0.0pp** at
every door, by construction. Exclusion (mode-2) does move it, by +6–8pp, at the
cost of 45–100% of every country door's rows. **Lever A as specified does not
proceed.**

---

## Pre-registration (frozen — plan `2026-07-29-identity-three-levers.md` §A0)

> **Gate GA:** adopt the strongest mode that raises top-40 entailed-share by
> ≥20pp while (a) no country door loses >25% of its served rows and (b) the
> global top-40 never drops below 30 rows. **Kill:** if every mode violates
> (a)/(b), enforcement waits for relabel/court-recovery — record and stop.

Nothing below moves that bar. Where the measurement surfaced an option the gate
did not enumerate (§8), it is reported as post-hoc and explicitly **not** scored
as adopted.

## Harness

`backend/scripts/measure_court_enforcement.py` — read-only
(`SET default_transaction_read_only = on`, asserted on the live session; the
Supabase pooler drops startup `server_settings`, so the setting is applied and
verified in-session). It reproduces serving rather than modelling it: the same
population (`_fetch_dynamic_threads_with_conn`), the same scorer
(`rank_threads`), the same same-event collapse (`dedupe_same_event_threads`).
The only variable is the court multiplier table (patched on
`thread_ranking._COURT_DAMP`, restored in a `finally`) and, for mode-2, which
rows may occupy the fold. Pools are deep-copied per mode — `rank_threads`
writes into `quality{}` and the dedupe merges survivors in place, so a shared
pool would leak state across modes.

```bash
set -a; source ~/AtlasLocalWorker/.env; set +a
backend/.venv/bin/python backend/scripts/measure_court_enforcement.py \
  --out docs/research/label-court/2026-07-29-court-enforcement-simulation.json \
  --doors "GLOBAL:-:40,US:US:24,TR:TR:24,CO:CO:24,DE:DE:24,MX:MX:24,AR:AR:24"
```

**Doors.** GLOBAL (page 40, the audit's frame) + US / TR / CO (requested) + two
thin doors chosen by served-row count: **DE** (9 rows) and **MX** (1 row), with
**AR** (2 rows) as a third. The originally-planned thin doors (VE, NG) serve
**zero** rows — see §9, which is why the thin set was re-picked from measured
served counts rather than from candidate counts.

**Two fetch variants**, because fetch depth turned out to be the binding
constraint:

| variant | pool depth | what it models |
|---|---|---|
| **S** (shallow) | pool == page | today's serving contract: `/threads?limit=L` fetches exactly L candidates (`ORDER BY recent_n_signals DESC LIMIT $2`) and ranks within them. This is what A1 as specified would run against. |
| **D** (deep) | pool == 3 × page | serving would have to over-fetch. Shows the ceiling of enforcement. |

**Modes.** `mode-0-nocourt` (counterfactual, no court term) · `mode-0`
(= today: failed 0.50 / partial 0.85) · `mode-1-f{0.7,0.5,0.3}` (failed × f,
partial held at the shipped 0.85) · `mode-2-nofetch` (exclude failed, no
over-fetch) · `mode-2-backfill` (exclude failed, backfill from the deep pool).
`unchecked` is never damped in any mode — atlas rows, umbrellas and any
unjudged topic keep multiplier 1.0, so enforcement cannot punish the unjudged.

**Field state.** Active labeled topics: failed 702 · partial 197 · entailed 145
· unchecked 14 — identical to the audit's census.

---

## 1. The baseline is not "no enforcement"

`_COURT_DAMP = {"failed": 0.5, "partial": 0.85}` has been live since 07-18.
Measured effect on the **global visible fold (top 10)** today:

| # | without the damp (counterfactual) | today (damp live) |
|---|---|---|
| 1 | `unchecked` Iran Strikes US Facilities in Bahrain, Jordan (931) | `unchecked` Iran Strikes US Facilities in Bahrain, Jordan (931) |
| 2 | `partial` Global heatwaves, wildfires, and power outages (130) | `unchecked` EU Sanctions, US Arrests, Defense & Energy News (89) |
| 3 | `unchecked` EU Sanctions, US Arrests… (89) | `unchecked` Wildfires Ravage Greece, Europe on High Alert (151) |
| 4 | **`failed` Tax Evasion in Private Schools (59)** | `partial` Global heatwaves, wildfires, and power outages (130) |
| 5 | `unchecked` Wildfires Ravage Greece… (151) | `unchecked` Oil Drops as U.S.-Iran Hostilities Pause (105) |
| 6 | `partial` Wildfires Rage in Spain and France (333) | `unchecked` Financial Market Updates and Stock Movements (69) |
| 7 | **`failed` Daily Earthquake Updates (48)** | `partial` Wildfires Rage in Spain and France (333) |
| 8 | `unchecked` Oil Drops as U.S.-Iran Hostilities Pause (105) | **`entailed` Carney Calls Byelections (27)** |
| 9 | `unchecked` Financial Market Updates… (69) | `unchecked` Trump touts tariffs, visits Michigan GM plant (23) |
| 10 | **`failed` 100 Days to Midterms (22)** | `partial` Trump 50% Tariffs on Canada (27) |

Court-failed rows in the visible fold: **3 → 0**. Entailed: **0 → 1**. The
instrument is not being ignored; it is already doing the only thing a damp can
do. What Lever A adds on top of that is the subject of the rest of this
document.

## 2. Mode results — variant S (today's serving contract)

Global door, page 40. Baseline serves 38 rows (dedupe collapses 2).

| mode | rows | E | P | F | U | entailed-share | Δpp | failed-share | in/out |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mode-0-nocourt | 38 | 3 | 8 | 18 | 9 | 7.9% | +0.0 | 47.4% | 0/0 |
| **mode-0 (today)** | 38 | 3 | 8 | 18 | 9 | **7.9%** | — | **47.4%** | — |
| mode-1-f0.7 | 38 | 3 | 8 | 18 | 9 | 7.9% | **+0.0** | 47.4% | 0/0 |
| mode-1-f0.5 | 38 | 3 | 8 | 18 | 9 | 7.9% | **+0.0** | 47.4% | 0/0 |
| mode-1-f0.3 | 38 | 3 | 8 | 18 | 9 | 7.9% | **+0.0** | 47.4% | 0/0 |
| mode-2-nofetch | **20** | 3 | 8 | 0 | 9 | 15.0% | +7.1 | 0.0% | 0/18 |
| mode-2-backfill | **21** | 3 | 9 | 0 | 9 | 14.3% | +6.4 | 0.0% | 1/18 |

Country doors, rows served vs baseline (page 24):

| mode | US | TR | CO | DE | MX | AR |
|---|---:|---:|---:|---:|---:|---:|
| baseline rows | 11 | 16 | **0** | 8 | 1 | 2 |
| mode-1 (any f) | 11 (1.00×) | 16 (1.00×) | 0 | 8 (1.00×) | 1 (1.00×) | 2 (1.00×) |
| mode-2-nofetch | 6 (**0.55×**) | 7 (**0.44×**) | 0 | 2 (**0.25×**) | 0 (**0.00×**) | 1 (**0.50×**) |
| mode-2-backfill | 6 (**0.55×**) | 7 (**0.44×**) | 0 | 2 (**0.25×**) | 0 (**0.00×**) | 1 (**0.50×**) |
| mode-1 entailed Δpp | +0.0 | +0.0 | — | +0.0 | +0.0 | +0.0 |
| mode-2 entailed Δpp | +7.6 | +32.1 | — | +37.5 | +0.0 | +0.0 |

## 3. Gate GA — scored

| condition | mode-1-f0.7 | mode-1-f0.5 | mode-1-f0.3 | mode-2-nofetch | mode-2-backfill |
|---|---|---|---|---|---|
| top-40 entailed-share ≥ +20pp | **+0.0 FAIL** | **+0.0 FAIL** | **+0.0 FAIL** | **+7.1 FAIL** | **+6.4 FAIL** |
| (a) no country door loses >25% rows | pass (0% loss) | pass | pass | **FAIL** (US −45%, TR −56%, DE −75%, MX −100%, AR −50%) | **FAIL** (same) |
| (b) global top-40 ≥ 30 rows | pass (38) | pass (38) | pass (38) | **FAIL** (20) | **FAIL** (21) |
| **adoptable** | no | no | no | no | no |

**VERDICT: NO-GO. No mode satisfies GA.** Note the kill sentence as written
("if every mode violates (a)/(b)") does not literally fire — mode-1 violates
neither (a) nor (b), it simply delivers nothing. The adopt clause finds no
candidate, which is the operative result: **A1/A2 do not proceed as specified.**

## 4. Why mode-1 is exactly +0.0pp — the structural finding

This is not a small effect that failed to clear a bar. It is **zero by
construction**, and it is the most useful thing this run produced.

`/threads?limit=L` runs `ORDER BY recent_n_signals DESC LIMIT $2` — the page is
chosen by **volume**, then `rank_threads` orders the rows already chosen. When
pool == page (the serving contract), the court multiplier cannot add or remove a
single row; it only permutes. Composition metrics — entailed-share, failed-share,
`stamped_counts` — are therefore **invariant under any damp factor**, at any
door, forever. Gate GA's headline criterion is unreachable by a rank term as long
as the fetch is shallow.

Confirmation from the same run: give the ranker a deeper pool (variant D, 120
candidates for a 40-row page) and the *already-shipped* damp swings the global
top-40 from **12.5% entailed (nocourt) to 32.5% (mode-0) = +20.0pp**, with
failed-share 50.0% → 5.0%. Same factor, same code, different fetch depth. **The
un-enforced surface is the fetch, not the factor.**

## 5. What actually enters and leaves — the qualitative read

Mode-1 produces no enter/exit at all (§4). Mode-2 produces exits only — the 18
court-failed rows on the page, with nothing to put in their place. The only
configuration with both is the deep pool, so the labels below come from
comparing today's served page against the same shipped damp over a 3× pool
(§8); 16 of the 18 failed rows leave there too, the other 2 survive on score.

**Exits (20: 16 `failed`, 3 `partial`, 1 `unchecked`).** They read like their
verdict: *100 Days to Midterms* · *US Blockade Iran Strait* · *Typhoon Bavi
Landfall* · *CJP Protest Violence* · *Ann Widdecombe Hammer Attack* · *Trump
Threatens Tariffs Over Canada Wildfires* · *França Aprova Eutanásia* · *Burnham
Vows to Challenge Trump* · *Wangchuk Hunger Strike* · *Ramaphosa Impeachment
Court Bid* · *State Pension Increases* · *OPEKEPE Sentencing* · *Febrie
Adriansyah Case* · *Klopp Appointed Germany Coach* · *Ayala Olmo Apology
Dispute* · *Health Q&A with Doctors* — plus `unchecked` *Global Sports,
Pageants, and Entertainment News*.

**Five concrete before/after cases, judged:**

1. **CLEAN WIN — *Klopp Appointed Germany Coach* (`failed`, 24) leaves the
   page.** This is the row class that displaced Berlin Pride in the 07-28 gold
   run (GQ-02 instability). Today the real Berlin story — *CSD Berlin Vehicle
   Attack* (`partial`, 29) — is served at rank 14 while the court-failed Klopp
   row sat nearby. Enforcement removes the impostor and leaves the story.

2. **CLEAN WIN — *Trump 50% Tariffs on Canada* (`partial`, 27) → *Trump Imposes
   50% Tariffs on Canada* (`entailed`, 41).** The same event has two surviving
   identities; enforcement picks the entailed one, which is also the bigger one.
   Strictly better copy of the same story. (It also exposes an under-merge the
   same-event dedupe did not catch — a Lever C observation, not a Lever A cost.)

3. **MIXED — *Spanish Wildfires* (`partial`, 39) leaves; *Emergency Declared for
   Madrid and Avila Fires* (`entailed`, 15) and *Orés Wildfire Update*
   (`partial`, 83) enter.** A vague label is replaced by specific, receipted
   ones — but the page already carries *Wildfires Rage in Spain and France*
   (333), *Wildfires Ravage Greece* (151) and *Global heatwaves, wildfires and
   power outages* (130). Enforcement promotes **fragments of an
   already-fragmented event**: the reader gets four wildfire rows instead of
   three. Verdict quality improved; page quality did not.

4. **FAILURE — *Emerging (US): Report: Chiefs OC Eric Bieniemy's wife shot at
   home* (`entailed`, 14) enters at **rank 8** of the world front page.** A
   small NFL-adjacent crime story with a pipeline-artifact label prefix
   ("Emerging (US): Report:") is now the 8th story in the world. The court
   entailed it because the label honestly describes its receipts. Court-entailed
   is a statement about label↔receipt agreement, **not** about newsworthiness.

5. **FAILURE — *Harga Emas Antam Harian* (`partial`, 21) and *Stock Moves Around
   Moving Averages* (`entailed`, 19) enter.** A daily Indonesian gold-price
   ticker and a moving-average roundup. Both are honestly labeled. Neither is a
   story. Also promoted: *Chris Brown Pleads Guilty* (`entailed`) and *Pogacar
   Wins Fifth Tour* (`entailed`) — the latter slipped the lifestyle/sport lane
   damp, whose keyword set has no cycling token.

**Judgment: the exit set is unambiguously good; the entry set is roughly half
real reporting (Madrid/Ávila fires, Westminster Bridge police-boat crash, Sikkim
tunnel collapse, Assam floods, Indian crew struck at Odesa, North Korean troops
for Russia) and half small honest non-news.** Enforcement is a genuine filter on
the way out and a weak selector on the way in. It is necessary, not sufficient —
it needs a newsworthiness term beside it, which today is only the volume the
enforcement is fighting.

## 6. The confound the gate cannot see

`entailed` is systematically **smaller** than `failed`:

| verdict | n (active) | mean lifetime signals | median lifetime signals | median current-window (global deep pool) |
|---|---:|---:|---:|---:|
| entailed | 145 | 61 | **44** | 16 |
| partial | 197 | 156 | 83 | 19 |
| failed | 702 | 110 | 93 | 18 |
| **unchecked** | 14 | **2569** | **711** | **69** |

A small, narrow topic is easy for the court to entail; a large one accumulates
the stray receipts that demote it. So "raise entailed-share" is **partly a proxy
for "prefer small topics"** — which is precisely what examples 4 and 5 above
look like from the inside. GA's headline metric cannot distinguish the two.
Any future enforcement gate needs a size-neutral or newsworthiness-paired
criterion.

## 7. The head of the page is out of reach — Lever B is the binding lever

Ranks **1–7 of the global page are byte-identical under every mode measured**,
because six of them are `unchecked` — the umbrella lane, median 711 lifetime
signals, max 931. Enforcement by construction never touches them (and should
not: the court never judged them).

This is the audit's coverage finding restated as a serving fact: **the court can
only act on the rows it has judged, and the rows it has judged are never the
biggest ones.** No court-enforcement factor reaches the front page. **Lever B
(umbrella verdicts) is not a parallel workstream to Lever A — it is its
prerequisite.** The plan's order (A0 → C1 → C2 → B1 → A1) should become
**B1 → (re-measure A0) → A1**.

## 8. Post-hoc mode-3 (over-fetch) — passes GA's letter, fails its spirit

Not pre-registered; reported as a finding, **not adopted**. Fetch 3× the page,
rank with today's shipped damp, cut to the page:

| door | rows | entailed-share | failed-share |
|---|---|---|---|
| GLOBAL | 38 → 40 (1.05×) | 7.9% → **32.5%** (**+24.6pp**) | 47.4% → **5.0%** |
| US | 11 → 24 (2.18×) | 9.1% → 8.3% (**−0.8pp**) | 45.5% → **62.5%** |
| TR | 16 → 24 (1.50×) | 25.0% → 16.7% (**−8.3pp**) | 56.2% → **62.5%** |
| DE | 8 → 24 (3.00×) | 12.5% → 4.2% (**−8.3pp**) | 75.0% → **83.3%** |
| MX / AR / CO | unchanged | — | — |

Scored against GA it **passes all three conditions** (+24.6pp global; no door
loses rows — every door gains; global 40 ≥ 30). It should still not be adopted
on that basis, and naming why matters more than the number: **GA constrains
country doors only by row COUNT, never by composition.** At the country doors
over-fetch is a coverage lever, not an enforcement lever — the deeper tail is
70–83% court-failed, so filling the page pulls in exactly the rows the court
convicted, and three of five doors get *worse* by the very metric GA maximises
globally. GA is under-specified; a mode that exploits that is not a pass.

If over-fetch is pursued, it needs its own pre-registered gate (A0b) with a
per-door composition condition, and it is an implementation change to
`_fetch_dynamic_threads_with_conn` (fetch N×, rank, cut), **not** the
`rank_threads` change A1 describes.

## 9. Thin doors — 13 of 34 are DARK, and GA condition (a) is vacuous there

The scan (`door_scan` in the JSON) compares what the country SQL believes exists
against what the door actually serves:

| door | candidates (72h) | served | | door | candidates | served |
|---|---:|---:|---|---|---:|---:|
| RU | 200 | 17 | | PL | 17 | **0** |
| UA | 152 | 20 | | BE | 14 | **0** |
| IR | 124 | 20 | | IE | 12 | **0** |
| GB | 116 | 18 | | MX | 10 | 1 |
| US | 110 | 12 | | IL | 15 | 2 |
| ES | 93 | 15 | | AR | 17 | 2 |
| IN | 86 | 21 | | AU | 9 | **0** |
| GR | 78 | 19 | | JP | 9 | **0** |
| FR | 75 | 18 | | EG | 9 | **0** |
| DE | 67 | 9 | | PK | 9 | 1 |
| ID | 60 | 21 | | CO | 8 | **0** |
| TR | 55 | 18 | | SA | 8 | 1 |
| IT | 55 | 16 | | VE | 7 | **0** |
| BR | 44 | 20 | | SE | 7 | **0** |
| CA | 43 | 16 | | CL / ZA | 5 / 5 | **0** |
| CN | 37 | 11 | | NG / NZ | 4 / 3 | **0** |

**1,563 candidates → 278 served (17.8%). 13 of 34 doors serve zero rows despite
having candidates.** There is a sharp cliff: every door with ≤17 candidates
serves ≤2 rows.

**Mechanism (verified, not inferred).** The country query's `EXISTS` matches
`ecc.top_country_codes[1] = $3` over **all** snapshots, while the served
`top_country_codes` is scoped to the **latest** snapshot — then
`thread_matches_country` re-filters on the served value and drops the row. Topic
4237 *"20 de Julio Desfile Cierres"* (a Colombian national-holiday story) is a
CO candidate because its 07-20/22/24 clusters were CO; its 07-25/26/27/28
clusters are **ES**, so it is rejected from the CO door. Same for 4244 (CO →
FR → ES) and 4249 (CO → ES → MX → VE → ES). Spanish-language coverage of a
Colombian story drifts to ES as its primary country. (A second latent hazard in
the same expression: `ARRAY(SELECT DISTINCT code … LIMIT 5)` has no `ORDER BY`,
so on a topic with >5 distinct codes the country can be dropped arbitrarily.)

**Consequence for the gate:** condition (a) is a percentage of *served* rows, so
a door already at 0 can never violate it. CO — one of the three doors this
measurement was asked to cover — scores "pass" on every mode while serving
nothing. GA's country-door protection is partly measuring an already-dark
surface. This is a serving defect independent of the court and worth its own
chip; it is *not* a reason to relax GA.

## 10. Recommendation

1. **Stop Lever A as written.** No mode clears GA. Do not implement A1's
   `ATLAS_COURT_ENFORCE` factor: the damp it would add is already live, and at
   the current fetch depth **no factor value can change what the page contains.**
   If a factor must be picked for the record: **none** — and if enforcement is
   ever revisited at shallow fetch, the shipped **0.5** is already at the point
   where the visible fold is clear of failed rows, so f=0.3 buys ordering churn
   for no measured composition gain.
2. **Re-order the plan to B → A.** §7: ranks 1–7 are unjudged umbrella rows,
   identical under every mode. Lever A cannot reach the front page until the
   umbrella lane carries verdicts. B1 first, then re-run this harness.
3. **If serving depth is pursued, gate it separately (A0b)** with a per-door
   composition condition, not just row count (§8).
4. **File the dark-door defect** (§9) — 13/34 country doors serve zero rows for
   a snapshot-scoping reason unrelated to the court.
5. **Do not treat entailed-share as a quality metric on its own** (§6) — it
   correlates with small, and the rows it promotes include a gold-price ticker
   and a moving-average roundup.

## 11. Caveats

- **One field snapshot, one night.** `dynamic_topic_members` MAX(snapshot_at) is
  **2026-07-28 03:28** while `emergent_clusters` MAX is **2026-07-29 04:16** —
  the projection lag documented in CLAUDE.md is live right now, so the served
  field measured here rides the 07-28 projection. Day-over-day variance is
  unmeasured; the 07-28 gold run showed served threads can change completely
  overnight.
- Composition invariance under mode-1 (§4) is structural and will hold on any
  snapshot; the specific pp values will not.
- The qualitative read (§5) is a single judge (Claude), non-blind — I knew each
  row's verdict while reading its label. The exit/entry *sets* are mechanical
  and reproducible from the JSON; the "is this better" call is not.
- Mode-2's exclusion is applied **before** the same-event collapse so a clean
  duplicate can still represent an event whose top row is failed. Excluding
  after the collapse would lose those events entirely and score worse.
- `dedupe_same_event_threads` collapses 2 rows at the global door, which is why
  a 40-row page serves 38 at baseline.

*Read-only throughout: no writes, no LLM calls, no engine changes. Artifacts:
this file + `2026-07-29-court-enforcement-simulation.json`; harness
`backend/scripts/measure_court_enforcement.py`. Not committed.*
