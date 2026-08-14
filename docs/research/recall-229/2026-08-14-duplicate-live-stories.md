# Two live stories for one event — measured, plus a pre-registered rule

**Date:** 2026-08-14
**Status:** MEASUREMENT + PRE-REGISTRATION. **No engine behaviour was changed.**
No merge, no lifecycle write, no migration. Read-only SELECTs and HTTP GETs only.
**For Pedro's eye before anything is built.**

**Trigger:** Pedro read the live Stories rail and found two active, unsibling'd
identities for the same real-world event:

| | id | label | agg_n_signals |
|---|---|---|---|
| A | `dynamic-topic-242` | 7.4-Magnitude Earthquake Kills Dozens in Colombia | 323 |
| B | `dynamic-topic-12927` | Colombia Declares Disaster After Deadly Earthquake | 2,257 |

**The headline correction to the brief:** B is not a leaf story. **B is an R2
umbrella** (`is_umbrella = true`, `identity_key = 'umbrella:510'`, 8 children).
That single fact explains most of what follows, and it changes what the fix has
to be.

---

## 1. Are they siblings under the current relation? — **No, in neither direction**

Route: `GET /api/v2/story/{dynamic-topic-N}/siblings`
(`backend/app/routers/story.py:300`; the bare int is rejected at `story.py:320`
with `unsupported_anchor_type`).

| request | HTTP | time | siblings | notes |
|---|---|---|---|---|
| `/api/v2/story/dynamic-topic-242/siblings` | 200 | 3.414 s | 11 | `[]` |
| `/api/v2/story/dynamic-topic-12927/siblings` | 200 | 1.281 s | 11 | `["umbrella_resolved_via_child"]` |

Exact substring check on both raw payloads: **`dynamic-topic-12927` does not
appear anywhere in 242's payload, and `dynamic-topic-242` does not appear
anywhere in 12927's** — not in `siblings`, not in any `folded` list.

**dt-242's neighborhood** (anchor `entailed`, countries `["CO"]`, `is_blob=false`):

| # | id | label | weight | deg | kinship |
|---|---|---|---|---|---|
| 1 | dt-523 | Venezuela Earthquake Death Toll | 0.6360 | 1 | hermano |
| 2 | dt-680 | Earthquake Reports | 0.6299 | 1 | hermano |
| 3 | dt-3307 | Incendio a Bruxelles | 0.5895 | 1 | hermano |
| 4 | dt-9055 | Japan Earthquake Death Toll | 0.5835 | 1 | hermano |
| 5 | dt-4292 | Peru Earthquake 5.1 Magnitude | 0.5767 | 1 | hermano |
| 6 | dt-1787 | Venezuela Earthquake Death Toll | 0.5746 | 1 | hermano |
| 7 | dt-248 | Colombia Earthquake Death Toll Rises Past 130 | 0.4545 | 2 | primo |
| 8 | dt-517 | Colombia Earthquake Death Toll Rises to 132 | 0.4405 | 2 | primo |
| 9–11 | dt-8151, dt-3967, dt-6781 | Japan / Mexico quakes | 0.414→0.406 | 2 | primo |

**dt-12927's neighborhood contains no earthquake topic at all** — wildfires in
France/Spain, Ceuta migrants, an Indonesian ferry fire, Greek wildfire primos.

**Why, from the code — two independent structural reasons:**

1. `_TOPICS_SQL` (`backend/app/routers/story.py:73-77`) filters
   `AND NOT is_umbrella`. The walk cannot **seed** on dt-12927, so
   `_resolve_umbrella_anchor` (`story.py:218`) substitutes the largest *active*
   child by `agg_n_signals` (`_UMBRELLA_CHILD_SQL`, `story.py:208-215`) →
   **dt-528 "Venezuela Earthquake Death Toll"**. Every sibling returned is
   dt-528's, not dt-12927's. dt-528↔dt-242 whitened cosine is only **0.3765**,
   far below the k=6 neighbor cut — hence wildfires.
2. The reverse direction is **structurally impossible**: the same `NOT
   is_umbrella` predicate removes dt-12927 from the candidate array, so it can
   never be *returned* as anyone's sibling. This is not a ranking miss; it is
   exclusion from the universe.

> **Stale comment to fix:** `story.py:193-194` asserts "An umbrella row has no
> `centroid_vec` of its own." **False for this row** — dt-12927 carries a valid
> 768-dim unit-norm centroid. The exclusion is purely the predicate.

**Counterfactual (measured):** dt-242↔dt-12927 whitened cosine = **0.6489**,
which *exceeds* dt-242's current #1 hermano edge (dt-523, 0.6360). Had umbrellas
not been filtered out, dt-12927 would have entered dt-242's top-6 **ranked
first**. (Adding a node also perturbs the blob-entropy pass, so primo ordering
downstream could shift.)

*Whitening reproduction check: locally recomputed 242↔523 = 0.635983 vs the
payload's rendered `0.64`, and 242↔680 = 0.629897 vs `0.63`. The local space
matches production.*

---

## 2. Direct pair evidence

### Centroid similarity
`dynamic_topics.centroid_vec` is `real[]`, not pgvector — both pulled and
computed in numpy. Both unit-norm, dim 768.

| measure | value | percentile in the active field |
|---|---|---|
| **raw cosine** | **0.901811** | ~p99 |
| **whitened cosine** (the ranking space) | **0.648901** | above p99.9 (0.5974) |

### Lifecycle

| column | dt-242 | dt-12927 |
|---|---|---|
| `identity_key` | `dyn-2026-06-25T05:00:06.525849+00:00-6` | **`umbrella:510`** |
| `state` | active | active |
| `is_umbrella` | **false** | **true** |
| `parent_id` | NULL | NULL |
| `first_seen` | 2026-06-25 05:00:06 | 2026-07-01 03:36:10 |
| `last_seen` | 2026-08-13 03:27:59 | 2026-08-14 03:08:12 |
| `n_snapshots` | 17 | 1 |
| `agg_n_signals` | 323 | 2,257 |
| `mean_cohesion` | 0.970335 | 0.975118 |
| `label_status` | entailed | entailed |
| `category` | Earthquake or volcanic disaster | Earthquake or volcanic disaster |
| `facet` | death-toll | NULL |
| `revived_at` | **2026-08-08 07:40:00** | NULL |
| `revival_count` | 0 | 0 |
| `blob_confirmed_at` | NULL | NULL |
| `umbrella_basis` | NULL | `llm-same-event-v1+label-fold-v1+child-guard-v1` |

**dt-12927's 8 children:** dt-528 (VE, active, 468) · dt-510 (Magnitude 7.4
Earthquake Strikes Colombia, active, 410) · dt-516 (candidate, 336) · dt-517
(CO, active, 331) · dt-1787 (active, 284) · dt-523 (active, 222) · dt-527
(active, 135) · dt-4258 (active, 71). dt-242 has no children and is nobody's
child.

**Three of those children (dt-523 #1, dt-1787 #6, dt-517 #8) are already
returned as dt-242's own siblings.** dt-242 is measurably adjacent to the
umbrella's family — it was simply never folded into it. *This is the hook the
proposal in §4 hangs on.*

### Overlap: countries and entities are both **EMPTY**

| | dt-242 | dt-12927 | shared |
|---|---|---|---|
| evidence countries | `{CO: 19}` | `{DE: 24, VE: 24}` | **∅**, Jaccard 0.0000 |
| persons | 12 distinct (`alejandro eder` 16, `jorge eduardo rojas` 16, …) | 2 (`joseph alejandro teran` 4, `catia sea` 1) | **∅** |
| orgs | 12 (`colombia geological service` 11, `u s geological` 10, …) | 16, all malformed German/Spanish NER (`a bank worldwide`, `school to engineers to venezuela`) | **∅** |

The zero overlaps are **artifacts, not evidence of distinctness**: the two topics
carry *different-language* coverage of one event, NER runs per language, and the
`DE` tag is outlet-origin fallback (German outlets covering Colombia).
**Centroid cosine is the only signal linking them.**

### Time window — overlapping
- dt-242 members: `2026-08-10 16:00` → `2026-08-11 02:00`
- dt-12927 members: `2026-08-10 13:30` → `2026-08-13 20:53`
- **10.0 h overlap; dt-242's window is entirely contained in dt-12927's.**

### Headlines side by side — same event

**dt-242** (English, tagged CO):
- `Magnitude-7.4 quake hits western Colombia, collapsing buildings and killing at least 79 people` — dailyexcelsior.com, 08-11 02:00
- `74 killed as 7.4-magnitude earthquake devastates western Colombia` — albawaba.net, 08-10 23:45
- `At least 77 killed after powerful earthquake hits western Colombia` — spokesman.com, 08-10 21:45

**dt-12927** (German):
- `Erdbeben in Kolumbien: Mehr als 72 Stunden seit Erdbeben vergangen, Zahl der Toten steigt` — zeit.de, 08-13 20:53
- `Kolumbien: Zahl der Toten nach Erdbeben steigt auf 265` — faz.net, 08-13 01:03
- `Stärke 7,4: Mehr als 130 Tote nach schwerem Erdbeben in Kolumbien` — faz.net, 08-11 15:41

Same magnitude, same country, same day, same rising toll. **Same event —
confirmed by hand.**

### ⚠ But "duplicate" needs qualifying
Of dt-12927's 48 evidence rows: **20 mention Colombia only, 19 Venezuela only,
9 neither — and 4 are Ebola in the DRC** (`Ebola-Ausbruch: Mehr als 2000
Todesfälle…`, spiegel.de). The Venezuela rows are a **different earthquake**
(the June 24 double quake, 6,301 dead).

**Honest statement: dt-242 duplicates dt-12927's Colombia lane (~42% of its
evidence). dt-12927 also carries a second earthquake and off-topic noise.**
Merging them naively would import that contamination. Its `is_blob = true /
candidate_unconfirmed` flag is pointing at something real, and the dilution is
exactly why its whitened cosine to dt-242 is only 0.65.

---

## 3. How many other active pairs look like this today?

**Universe:** `state='active' AND NOT is_umbrella AND centroid_vec IS NOT NULL`,
mirroring `story.py:73-77`. **N = 3,088 topics → 4,766,328 pairs.**

> The `story.py:48-51` comment assumes "~1.6k active rows". The real field is
> **nearly 2×** that.

> ⚠ **The dt-242/dt-12927 pair is NOT in this universe** — dt-12927 is an
> umbrella. The sweep measures the story↔story class; the case itself is
> story↔umbrella, a **separate and unmeasured population**.

### Distribution first (before choosing any threshold)

| pct | RAW cosine | WHITENED cosine |
|---|---|---|
| p1 | 0.7724 | −0.1687 |
| p25 | 0.8164 | −0.0281 |
| **p50** | **0.8355** | **0.0302** |
| p75 | 0.8558 | 0.0975 |
| p95 | 0.8865 | 0.2366 |
| p99 | 0.9103 | 0.3919 |
| p99.9 | 0.9404 | 0.5974 |
| min / max / mean | 0.7058 / 1.0000 / 0.8366 | −0.3982 / 1.0000 / 0.0426 |

**The raw space is severely compressed** — the *minimum* cosine over 4.77 M pairs
is 0.7058 and the median is 0.8355. **"cos ≥ 0.90" is merely the 99th
percentile, not a duplicate signal.** Whitening de-compresses it (median 0.0302).

### Threshold table — pairs meeting **all three** conditions
(cosine ≥ T **AND** shared dominant evidence country **AND** overlapping
`[first_seen, last_seen]`)

| T | RAW ≥T | RAW + country + window | WHITENED ≥T | **WHITENED + country + window** |
|---|---|---|---|---|
| 0.85 | 1,493,968 | 46,574 | 170 | **48** |
| 0.90 | 98,452 | 11,915 | 95 | **29** |
| 0.93 | 11,068 | 3,191 | 64 | **21** |
| 0.95 | 2,079 | 833 | 44 | **16** |
| 0.97 | 298 | 96 | 27 | **12** |
| 0.99 | 53 | 19 | 13 | **5** |

Supporting filter stats: only **1,887 of 3,088 topics (61.1%)** have any 7-day
evidence-country footprint (1,201 can never satisfy the country filter);
**79.4% of pairs** overlap in time, so the window filter is nearly non-binding.

**Stated operating point: whitened ≥ 0.90 → 29 pairs.** Whitened because it is
the space the production ranker uses, and because raw cosine at any usable
threshold is unusable (11,915 filtered pairs at ≥0.90 — a queue nobody can work).

### Hand-checked examples (up to 5 real headlines read per side)

| # | pair | raw | whitened | cc | verdict |
|---|---|---|---|---|---|
| 1 | dt-9395 ↔ dt-9399 · "Ceuta Migrant Crisis" / "Ceuta Migrant Crisis" | 0.9936 | 0.9442 | ES | **TRUE-DUPLICATE** — identical labels; they literally **share a member signal** (`Mitten in Ceuta-Chaos…`, 08-07 15:30) |
| 2 | dt-11491 ↔ dt-11489 · "Katter's Beast Warning" ×2 | 0.9855 | 0.9192 | AU | **TRUE-DUPLICATE** — one syndicated Mark Kenny op-ed across ACM mastheads (Yass Tribune, Blayney Chronicle, Lithgow Mercury in *both*). Same class as the "Las Vegas Travel Guide" case |
| 3 | dt-8594 "Japan Earthquake Death Toll" ↔ dt-8603 "Kumamoto Earthquake Death Toll" | 0.9871 | 0.9067 | JP | **TRUE-DUPLICATE** — top-5 headlines byte-identical on both sides |
| 4 | dt-12103 "Colombia Earthquake Kills 20" ↔ dt-8602 "Japan Earthquake Death Toll" | 0.9959 | 0.9808 | CO | **TRUE-DUPLICATE, wrong label** — dt-8602's members are Albanian/Croatian/Bengali **Colombia** quake copy. **Two more orphan fragments of this very event** |
| 5 | dt-4082 "Rethymno Fire DEDDIE Prosecution" ↔ dt-3150 "Kypseli Murder Arrest" | **1.0000** | **1.0000** | GR | **TRUE-DUPLICATE by centroid + shared members, but BOTH labels are wrong** — neither describes the served evidence (a British man beaten at Rethymno port). Blob-vs-blob |

**Verdict on precision: 5 of 5 hand-checked pairs at whitened ≥ 0.90 were true
duplicates** (plus a 6th, dt-7748 ↔ dt-7750 Brazil/Argentina, identical
centroids and a shared member). The 29-pair set is small enough to review by
hand.

**The real problem is recall, not precision:**
- dt-4081 ↔ dt-4038 ("…Locking Teen in Chania Home" / "Man Arrested in Chania for
  Locking Teen Ex-Girlfriend"): **byte-identical top-5 headlines**, raw 0.9782,
  **whitened 0.8487 — below 0.90, missed.**
- **The case itself sits at whitened 0.6489.** Lowering T to 0.85 adds only 19
  pairs and still misses both.

**Separate data defect worth its own chip: 3 pairs (6 topics) in the active
field have byte-identical `centroid_vec` arrays** yet distinct labels, distinct
categories and distinct `agg_n_signals` — dt-4082/dt-3150, dt-9161/dt-8868,
dt-7748/dt-7750.

---

## 4. Which mechanism owns this class, and why it did not fire

**Owner: `merge_duplicates`**,
`backend/scripts/project_dynamic_topics.py:610` (called at `:1406`). It requires
**both** `labels_compatible` (`:595` — `SequenceMatcher` ratio ≥
`MERGE_LABEL_MIN = 0.80` over an `[^a-z0-9]`-normalised string, `:594`) **and**
`cosine ≥ MERGE_THRESHOLD = 0.90` (`:592`).

| pair | SeqMatcher | labels_compatible | raw cos | cosine gate | blocked by |
|---|---|---|---|---|---|
| 242 ↔ 12927 | 0.2828 | **False** | 0.9018 | **PASS** | **LABEL only** |
| 242 ↔ 510 *(Magnitude 7.4 Earthquake Strikes Colombia)* | **0.7111** | False | 0.8651 | FAIL | both |
| 242 ↔ 1787 | 0.3750 | False | 0.8939 | FAIL | both |
| 242 ↔ 523 | 0.3750 | False | 0.8931 | FAIL | both |
| 242 ↔ 517 | 0.4348 | False | 0.8624 | FAIL | both |
| 242 ↔ 12103 | 0.5195 | False | 0.8705 | FAIL | both |
| 242 ↔ 8602 | 0.4211 | False | 0.8740 | FAIL | both |

**The most damning row: "7.4-Magnitude Earthquake Kills Dozens in Colombia" vs
"Magnitude 7.4 Earthquake Strikes Colombia" scores 0.7111 — same magnitude, same
verb sense, same country — and the predicate says incompatible.** This is a live
instance of the defect the 7th gate already named (`labels_compatible` SeqMatcher
ASCII ≥0.80 blocks ~50% of same-story pairs). The 8th gate's pre-registered
replacement predicate
(`docs/superpowers/specs/2026-08-03-landing-predicate-preregistration.md`,
Unicode-norm + subject-token containment) is the fix in flight — **it is not what
production ran.**

**Second mechanism, `build_umbrella_topics.py` — it fired but excluded dt-242:**
- the deterministic path is complete-linkage at **0.95** (`:476`, `_complete_linkage`
  at `:103`); dt-242's raw cosine to *every* umbrella child maxes at **0.8939** —
  no edge clears 0.95;
- the LLM same-event path is **chunked at 120 topics** (`:288`) and its own
  docstring concedes at `:309-311` that *"Cross-chunk merges the judge can no
  longer see are the accepted cost of parseability."* With 3,088 active topics
  that is 26 chunks; reproducing `semantic_chunk_order` over today's field, the
  Colombia/Venezuela earthquake family scatters across **8 distinct chunks**
  (dt-242 in 24, dt-510 in 7, dt-517/dt-1787 in 8, dt-523 in 9, dt-528 in 0).
  dt-242 and the umbrella's anchor child were almost certainly never in one
  prompt. *(Indicative — see caveat 2.)*

**Not this class:** `detect_overmerge.py` / `app/services/overmerge.py` **split**
over-merged topics (opposite direction); the condemnation clock governs label
condemnation, not identity fusion; the story lens is explicitly and correctly not
a merge gate (`story.py:5-9`, `story_siblings.py:3-6`) — ranking-with-receipts,
writes nothing.

---

## 5. PRE-REGISTERED PROPOSAL — for Pedro's decision, nothing built

Written **before** any run, per project discipline: gate + kill rule first.

The measurement splits the problem into two classes that need **different**
rules. Do not conflate them.

### Class A — story ↔ story duplicates
**Rule A (DLI-A):** flag a pair when
`whitened_cos ≥ 0.90` **AND** shared dominant 7-day evidence country **AND**
overlapping `[first_seen, last_seen]` **AND** both `state='active'`.
Today: **29 pairs**, small enough for nightly hand review.

- **Pre-registered gate:** precision ≥ **90%** on **30 pairs drawn at RANDOM**
  from the flagged set (not hand-picked), labelled independently by two
  annotators, **κ reported**.
- **Kill rule:** precision < 90% → Rule A does not ship in any form.
  Precision ≥ 90% **but** recall < 50% on the witness set below → ships
  **detect-only** (a review queue + a rail chip), **never** as an automatic merge
  trigger.
- **Pre-registered witness set (frozen now, before the run):** dt-4081↔dt-4038
  (Chania, whitened 0.8487 — a KNOWN miss at T=0.90, included deliberately so
  recall cannot be gamed), dt-8594↔dt-8603 (Kumamoto), dt-9395↔dt-9399 (Ceuta),
  dt-12103↔dt-8602 (Colombia/Japan mislabel).
- **Honest note:** the 5/5 precision above is **6 of 29 pairs, chosen by me
  across the weight range, not randomly sampled.** It is not a precision
  estimate with a CI. The gate exists because that number cannot be trusted yet.

### Class B — story ↔ umbrella (Pedro's actual case)
Rule A **cannot** catch it: dt-12927 is excluded from every candidate universe by
`NOT is_umbrella`, and its centroid is diluted by a second earthquake plus Ebola
noise, so its whitened cosine to dt-242 is 0.6489 — far below any
precision-safe threshold. **Lowering the threshold is the wrong lever.**

**Rule B (DLI-B) — the child-consensus rule.** Do not compare a story to an
umbrella's centroid at all. Compare it to the umbrella's **children**, using the
walk output that already exists:

> If ≥ **2** of a story's measured top-k siblings are **active children of the
> same umbrella**, and that story is not itself a child of any umbrella, flag it
> as a candidate member of that umbrella.

**It would have caught this case: 3 of dt-242's 11 siblings (dt-523 #1, dt-1787
#6, dt-517 #8) are children of dt-12927.** It costs no new embedding work, no
new LLM call, and it sidesteps both the argmax-dispersion disease and the
blob-diluted-centroid problem, because it reads agreement across *several*
measured edges instead of one.

- **Pre-registered gate:** on a sweep of every active non-child story, ≥ **80%**
  of flagged (story, umbrella) candidates are judged genuinely the same event as
  that umbrella's **dominant** lane, hand-checked on **20 randomly drawn**
  candidates.
- **Kill rule:** < 80% → Rule B does not ship. ≥ 80% → it ships **detect-only**
  first (surfaced as a sibling/"possible same event" chip and a review queue).
  **Promotion to an actual umbrella-membership write requires its own separate
  gate** — this measurement does not authorise a lifecycle change, and the
  dt-12927 contamination (§2) is a live example of why an automatic fold would
  import noise.
- **Pre-condition to even measure it:** the `NOT is_umbrella` filter at
  `story.py:73-77` must be relaxed *for the measurement harness only*, not in
  serving. Also fix the false comment at `story.py:193-194`.

### Ordering recommendation
1. **Rule B first.** It is the reported case, it reuses output that already
   exists, and its gate is cheap.
2. **Rule A second**, and only as a review queue.
3. Neither before the **8th gate's landing predicate** lands — `labels_compatible`
   at SeqMatcher 0.7111 on "7.4-Magnitude Earthquake Kills Dozens in Colombia" vs
   "Magnitude 7.4 Earthquake Strikes Colombia" is the root defect, and fixing the
   predicate may dissolve part of Class A on its own.
4. **Separate chip:** the 3 byte-identical-centroid pairs.

---

## 6. Caveats that should make you distrust specific numbers

1. **"Duplicate" is qualified.** dt-12927 carries two different earthquakes plus
   4 Ebola rows. dt-242 duplicates its **Colombia lane (~42% of evidence)**, not
   the whole topic.
2. **The chunk-assignment finding is an approximation, not a replay.**
   `semantic_chunk_order` was run over *today's* 3,088-topic field, not the exact
   topic set of the 2026-08-14 09:16 umbrella build. Strong circumstantial
   support, not proof of that run.
3. **The sweep universe excludes the case itself** (umbrella). Every number in
   the threshold table is story↔story only.
4. **1,201 of 3,088 topics (38.9%) have no 7-day evidence footprint** and are
   structurally invisible to the shared-country filter. The threshold counts are
   **lower bounds**.
5. **Hand-check sample = 6 of 29, chosen not randomly.** "5 of 5" is not a
   precision estimate. This is why §5 pre-registers a random sample.
6. **Country codes are outlet-origin-contaminated** (dt-12927's `DE` is German
   outlets covering Colombia). "Shared country = ∅" is partly a tagging artifact,
   and the sweep's country filter inherits that noise both ways.
7. **Entity overlap 0.0000 is partly a coverage artifact** — dt-12927's entities
   are visibly malformed multilingual NER (`a bank worldwide`, `school to
   engineers to venezuela`). It measures NER quality as much as topical distance.
8. **Sibling payloads came from warm caches** (3.4 s / 1.3 s vs the documented
   9–14 s cold path) — `_TOPICS_CACHE` up to 120 s stale, Redis up to 300 s.
   Independent local recomputation matched the rendered cosines to 2 decimals.
9. **`agg_n_signals` is cumulative across clustering passes**, not a 168 h
   window. dt-242's 323 and dt-12927's 2,257 are not comparable to the "~54 in
   today's rail" figure. *(A parallel session is correcting this basis name in
   ThemeDetail as of the same day.)*
10. **All member evidence is what survives 7-day hot retention.** dt-242's 19
    evidence rows are a small tail of a 323-signal cumulative topic.
