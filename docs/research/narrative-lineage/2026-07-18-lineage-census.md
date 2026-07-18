# The Narrative Lineage Census — 2026-07-18

**What this is.** The first full census of the *giant threads* in Atlas: which
narratives actually persisted across the archive's nine weeks (2026-05-04 →
2026-07-03), which of them are still alive in today's serving layer, and which
the world dropped. Not one forced super-thread — a population count of the
lineages that exist, with measured thresholds, a negative control, worked
biographies, and a first-class negative result (the Icelandic blob).

**Status of these numbers: PRE-FLOOR.** The Lane A per-country / per-language
floors had **not landed** when this census ran (polled 2026-07-18; no
floor-bearing commit or doc exists in the repo). Every number below is
computed with a single global threshold. The Icelandic-blob finding (§6) is
exactly why per-language floors are needed; when Lane A lands, append the
post-floor deltas in Appendix B — do not overwrite the tables.

Produced by `backend/scripts/narrative_lineage_census.py` (read-only against
serving; all vector work local on the M1). The live `narrative_lineage` table
(mig 084, 7,406 rows = 1,055 topic↔unit + 6,351 unit↔unit edges) is loaded
from the exact edges file pinned in §8. Gate verdict on the load:
`leaks[5]` — five suspected cross-story leaks — so **every row is
`candidate: true`**; nothing in this census is served as verified.

---

## 1. Method

Chain: **index → centroids → space-consistency proof → thresholds → union-find
census**.

### 1.1 One space, proven — not assumed

The stitch never compares e5 to OpenAI. Everything lives in
`openai/text-embedding-3-small` (1536-d):

- **Archive units** (`archive_story_units`, Stage-B): vec = mean of member
  headline vectors, L2-normalized. 6,473 units, 2026-05-04 → 2026-07-03,
  9 ISO weeks.
- **Live topics** (866 active `dynamic_topics`, none junk): member headlines
  (role='evidence', both engine versions; `dynamic_topic_members` →
  `emergent_clusters.sample_signal_ids` fallback for under-floor topics) are
  normalized with the archive pipeline's *verbatim* `_norm`/`_is_junk`,
  sha1'd, and looked up in the durable OpenAI shards on
  `/Volumes/Ext/Atlas/Embeddings`. Centroid = mean of matched vectors,
  L2-normalized — the same construction as the units.

**The hot-window reality (measured, not designed around):** the shards end
2026-07-10 while topic evidence joinable to `signals_v2` IS the hot 168 h
window — overlap ≈ zero. So of 40,646 member norms, only **271 hit the
shards**; **40,375 were embedded fresh** via the API with the same model,
normalization, and truncation (`centroid-provenance.json`), cached under
`lineage-index/` so re-runs are free.

**Space-consistency check — the cos = 1.0 proof.** 24 shard-HIT norms were
re-embedded via the API and compared to their shard vectors:
`cos_min = 1.0000, cos_median = 1.0000` (4-dp rounding). The shard vectors and
the fresh API vectors are the same space by measurement, so mixing them inside
one centroid is legitimate.

All 866 active topics cleared the ≥5-matched-vectors floor
(coverage median **1.00** — the live-embed path closes what the shard lag
opened).

### 1.2 Thresholds: honestly NON-bimodal, p75 fallback, control-anchored

The threshold finder looks for the valley between two modes of the
best-adjacent-week-match cosine distribution (the umbrella-0.98 idiom:
never guess, find the gap). **It found no valley.** Both distributions are
unimodal (histograms preserved in `method.theta_measurement` of the edges
file), so the finder fell back — *flagged, not silent* — to the 75th
percentile:

| edge type | θ | basis |
|---|---|---|
| unit ↔ unit | **0.862** | p75 fallback, `bimodal: false`, "treat with caution" |
| topic ↔ unit | **0.858** | p75 fallback, `bimodal: false`, "treat with caution" |

A bare percentile is never trusted alone: a **negative control** of 164,564
pairs ≥3 weeks apart with disjoint `top_cc` gives
p50 0.207 / p95 0.374 / p99 0.477 / **p99.9 0.598**. The effective threshold
is `max(p75, control-p99.9)` — the p75 won by a wide margin (0.862 ≫ 0.598),
i.e. the cut sits far above anything the junk background produces. What p75
does NOT guarantee is a natural story boundary — that is why the sensitivity
band (§3) and the all-candidate posture exist, and why the per-language floors
matter (§6).

### 1.3 Lineage assembly

Union-find over three edge kinds at θ_uu: **intra-week** (2,675 edges — same
story, different day), **adjacent-week** (3,575), and **gap-bridge** (101 —
component-era centroid vs centroid across a single missing week, so a
one-week reporting hole does not sever a lineage). Components that are a
single unit with no live topic attached are not counted as lineages.
Topic→unit edges (1,055 at θ_tu) attach live topics to lineages: a lineage
with ≥1 attached active topic is **living**; a lineage spanning ≥3 weeks with
≥400 signals and no attachment is **dead-big**.

---

## 2. The census

**762 lineages** over 6,473 units / 9 weeks.

| measure | count |
|---|---|
| lineages, total | **762** |
| span ≥ 4 weeks | **91** |
| span ≥ 8 weeks | **19** |
| living (≥1 active topic attached) | **226** |
| living AND span ≥ 4 weeks | **43** |
| living AND span ≥ 8 weeks | 11 |
| dead-big (span ≥ 3 w, ≥400 signals, no living descendant) | **11** |

Span distribution: 394 one-week · 277 at 2–3 w · 72 at 4–7 w · 19 at 8–9 w.
Persistence is rare and real: only 12 % of lineages survive a month, 2.5 %
survive (nearly) the whole archive. Median within-lineage minimum
week-over-week drift cosine is 0.895 (n = 368 multi-week lineages) — lineages
hold their subject while the wording churns.

Top living lineages by volume (lineage → strongest attached topic):

| lineage | span | signals | attached topic (sim) |
|---|---|---|---|
| lin-88 | 9 w | 2,152 | Trump Cancels Iran Strikes (0.915) |
| lin-272 | 9 w | 1,695 | Ali Hamaney Cenaze Töreni (0.933) |
| lin-606 | 8 w | 1,209 | Ebola Outbreak Congo (0.939) |
| lin-113 | 6 w | 1,145 | Oyo Pupils Rescue Update (0.884) |
| lin-49 | 9 w | 1,022 | Tentato Omicidio a Ivrea (0.953) |
| lin-67 | 9 w | 1,016 | Albanian Anti-Government Protests (0.943) |

---

## 3. Sensitivity: θ_uu ± 0.02

Span counts only (singletons are span-1 and cannot move these):

| θ_uu | span ≥ 4 w | span ≥ 8 w |
|---|---|---|
| 0.84 | 97 | 26 |
| 0.86 | 90 | 22 |
| **0.862 (used)** | **91** | **19** |
| 0.88 | 72 | 16 |

Reading: the ≥4-week population is stable (±7 %) across the band — the
month-scale giants are not a threshold artifact. The ≥8-week count is more
threshold-sensitive (16–26), because at nine weeks a single severed
adjacent-week edge can drop a lineage below the bar. Quote "~90 month-scale
lineages" with confidence; quote "19 archive-spanning" with the band attached.
(The 0.86-row/0.862-headline mismatch is real: the sensitivity grid rounds θ
to 2 dp, and 0.002 of threshold moves a handful of edges.)

---

## 4. Three worked biographies

### 4.1 Ukraine strike war — lin-79 → lin-2058, unioned by the live layer

Two archive lineages, one war:

**lin-79** (5 w, 642 signals, 2026-05-04 → 2026-06-01, min drift 0.920) is the
spring escalation ladder: ceasefire-violation accusations (May-04, RU/UA/MD) →
the largest Ukrainian drone attack on Moscow in a year (May-11) → Oreshnik
hypersonic strike on Kyiv (May-18) → announced strike waves on Kyiv (May-25,
now surfacing in Spanish-language press) → mass strikes, ≥13 dead (Jun-01).

**lin-2058** (5 w, 579 signals, 2026-06-01 → 2026-06-29, min drift 0.868)
picks up as the story pivots to the energy war: Ukrainian drones on a
St-Petersburg oil terminal during Putin's "Davos" (Jun-01) → stalled
armistice hopes (Jun-08, Romanian press) → Black Sea strike deaths (Jun-15,
German press) → Putin admits tapping fuel reserves (Jun-22) → Russia forced
to import gasoline from India (Jun-29, Croatian press).

**The union note.** In the archive graph these are *separate components* —
the Jun-01 handoff week scores below θ_uu between their era centroids (the
subject genuinely rotated: strikes-on-cities vs strikes-on-energy). What
unions them is the **live layer**: both attach to the same active topics —
`3433` Ukraine War Updates (0.924 / 0.915), `37` Major Russian Strikes on
Ukraine (0.915 / 0.911), `1751` St-Petersburg Oil Terminal (0.928 / 0.907).
The stitch is therefore honest at both levels: two archive-tight sub-arcs,
one living macro-narrative, and the union is *labeled as coming from the
topic attachments*, not forced into a single archive component. (Also
visible here: `438` "Lightning Strike Injures Child" attaches to lin-2058 at
0.8635 — one of the gate's five flagged leaks; strike-vocabulary adjacency,
exactly the class the candidate posture exists for.)

### 4.2 Venezuela earthquake — lin-2910, born big, still alive

2 weeks in-archive, 529 signals, min drift 0.957. Week of Jun-22: "Venezuela
quakes deaths reach 1,400" (VE/MX/ES/CO). Week of Jun-29: the miracle rescue
— a survivor pulled from rubble after 8 days (VE/MX/CL/US) — as the toll
climbs past 3,300. The archive stops at Jul-03, but the lineage does not: it
attaches to **five** active topics (`248` Venezuela Earthquake Death Toll
0.929, `529` Terremotos en Venezuela 0.910, `517`, `522` ONU afectados,
`523` Spanish deaths — all last-seen 2026-07-17). This is the census's best
demonstration of the stitch crossing the Jul-04 unit hole: a two-week archive
tail correctly hands off to a live umbrella family that is still moving
today. It is also the coverage-asymmetry marquee case from the 07-06 flagship
dogfood, now with a measured spine under it.

### 4.3 A death: the MV Hondius hantavirus outbreak — lin-73

3 weeks, 768 signals, no living descendant. **What it was:** week of May-04, a
hantavirus outbreak aboard the cruise ship *MV Hondius* — 387 signals in its
first week, led by Spanish and Argentine press with Dutch and South African
echo, a genuine multi-country health scare at sea. Week of May-11 it holds
(321 signals): a French passenger evacuated, tests positive; French press
takes the lead. Week of May-18 it collapses to 60 signals — the ship
approaches Rotterdam under live-blog coverage ("DIRECT... en approche du port
de Rotterdam") — and then **nothing**. No week-4 units, no gap-bridge, no
active topic within 0.858 of its centroid. **When the world dropped it:** the
moment the ship docked. The story's engine was the confined-vessel drama;
resolution killed it in one news cycle. Drift stayed ≥0.953 throughout — it
died coherent, not diffuse. This is what a *dead* lineage means in this
census: not junk, a real story with a beginning, a peak, and an end the
serving layer has (correctly) forgotten.

The other ten dead-big lineages tell similar stories — lin-1527 (Peru:
Fujimori–Sánchez recount, 6 w, dies at final-count resolution), lin-3
(Armenia-Azerbaijan diplomacy in Armenian-language press, 9 w, 1,773 signals
— dead-by-attachment but see §6: it is also a language-cohesion case), lin-72
(flotilla activist affair), plus a sports/markets tail (Red Sox, Signature
Bank, Moto3) that the dead-big bar honestly includes because deadness is
about attachment, not editorial worth.

---

## 5. What the biographies validate

- Week-over-week drift cosines within lineage run 0.87–0.99 — narrative
  continuity is measurable and high while the *language of coverage rotates*
  (EN → ES → RO → DE → HR inside one lineage), which is the diversity program
  paying off inside the lineage layer.
- The topic attachments recover live continuations across the Jul-04 hole
  without any unit evidence in it — the two-layer design (archive graph +
  live attachments) is what makes the hole survivable.
- Deaths are legible events (docking, final count), not decay artifacts.

---

## 6. Negative result, first-class: the Icelandic blob (lin-5)

**lin-5**: 9 weeks, 42 units, 490 signals, present every single week, min
drift **0.974** — the *tightest* long lineage in the census. It is also
**not a story.** Its weekly representatives: municipal accessibility policy →
a footballer's season → police taser oversight → a utility-board chairmanship
→ a labor dispute → math-textbook procurement → a school phone-ban debate →
an abortion-access award → a coast-guard vessel's history. The only constant
is `IC` and the Icelandic language.

**Why it chains:** in OpenAI embedding space, Icelandic headlines sit closer
to *each other* — regardless of subject — than the global p75 threshold
expects, because the language itself is a dominant component for a
low-resource script the model saw comparatively little of. A single global
θ = 0.862, calibrated on the mixed (English-heavy) distribution, is
simultaneously too strict for cross-language continuations of one story
(the lin-79/2058 split) and too loose within a small-language pocket
(lin-5). lin-3 (nine weeks of Armenian-script units, drift ≥0.988) is the
same mechanism one notch less pure — there is a real Armenia-Azerbaijan
diplomacy arc in it, but its 1,773-signal mass is inflated by
Armenian-language cohesion.

**Consequence — this is the Lane A mandate:** thresholds must carry
**per-language (and where volume allows, per-country) floors**, measured the
wild-junk-quantile way *within* each language pocket, before any lineage
edge is promoted from `candidate` to verified. Until those floors exist, the
all-candidate posture of mig 084 is not caution theater — it is the correct
label for numbers produced under a threshold known to be miscalibrated at
the language margins. This finding is why.

---

## 7. Caveats (read before quoting)

1. **All-candidate.** Gate verdict `leaks[5]`; every edge row is
   `candidate: true`. Nothing here is verified lineage.
2. **Pre-floor thresholds.** Single global θ, p75 fallback on a non-bimodal
   distribution (§1.2), known language-pocket miscalibration (§6).
3. **Member coverage / mixed vector provenance.** 99.3 % of topic-member
   vectors came from the live-embed path, 0.7 % from shards — proven to be
   the same space (cos 1.0, §1.1) but provenance-mixed; the
   coverage-median-1.0 headline reflects the API fill, not shard reach.
4. **Stage-B week holes.** Units end **2026-07-03**; 2026-07-04 → present has
   NO archive units. Lineage `last_week` ≤ 2026-06-29 by construction;
   "still alive" claims ride exclusively on topic attachments. Gap-bridges
   also paper over at most ONE missing week inside the archive window —
   two-week reporting holes sever lineages.
5. **Hot-tier volume semantics.** Archive-side `n_signals` counts *clustered
   unit members* (Stage-B clusters); live-topic `agg_n_signals` counts
   *assignments*. The two volume columns are different measurements — never
   sum them across the tier boundary (same tier-honesty rule as
   `/deep-history`).
6. **Attachment ≠ identity.** A topic attaching at 0.86+ means semantic
   adjacency to the lineage centroid, not editorial sameness — see the
   Lightning-Strike leak in §4.1.
7. **Dead-big is attachment-dead.** Sports and market-note lineages clear
   the bar; deadness is a serving-layer fact, not a newsworthiness judgment.

---

## 8. Provenance pin

The live `narrative_lineage` table and every number in this document derive
from ONE edges file, snapshotted so the nightly lineage-refresh step in
`run-scoped-snapshot.sh` can never orphan this artifact:

- **Snapshot:** `docs/research/narrative-lineage/snapshots/lineage-edges-2026-07-18.json`
- **sha256:** `24386a2bbc8efe9a921bcbc97c4ead33d229b5ea295fd59e7ee8eefd3b7ef553`
- **Generated:** 2026-07-18, by `narrative_lineage_census.py all`
  (θ_uu 0.862 / θ_tu 0.858, `--min-matched 5 --cap 500`,
  `--dead-min-signals 400`)
- **Contents:** 1,055 topic↔unit edges + 6,351 unit↔unit edges
  (2,675 intra / 3,575 adjacent / 101 gap-bridge) + 762 lineage records =
  the 7,406 rows of mig 084 at load time.
- Companion run artifacts (M1-local, not in repo):
  `/Volumes/Ext/Atlas/Embeddings/lineage-index/{census-summary.json,
  centroid-provenance.json, topic-coverage.jsonl, topic-centroids.npz}`.

If `lineage-edges.json` at the top level ever diverges from this sha, the
tables in this document describe the **snapshot**, not the live table.

## Appendix A — threshold measurement dump

Full histograms, control percentiles (n = 164,564), and the flagged
`bimodal: false` fallback notes are preserved verbatim in
`method.theta_measurement` inside the pinned snapshot.

## Appendix B — post-floor deltas (RESERVED)

Empty by design. When Lane A's per-language / per-country floors land, re-run
`census` with the floored thresholds and append: (a) the new census table,
(b) the delta vs §2, (c) lin-5's fate (expected: dissolved), (d) whether the
lin-79 ↔ lin-2058 archive split heals. Do not edit §2–§6.
