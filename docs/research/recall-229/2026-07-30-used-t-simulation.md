# Dropping `used_t` from `process_snapshot` — offline simulation

**Generated:** 2026-07-28 · read-only (`SET default_transaction_read_only = on`), no prod write, no commit
**Harness:** `backend/scripts/simulate_used_t_removal.py`
**Artifacts:** `2026-07-30-used-t-simulation.json` (primary, 12 nights) ·
`…-labelled.json` (labelled nights only) · `…-singlenight.json` (07-28 only, fidelity check)
**Question:** the diagnosis's fix 2 — *"drop `used_t` in `process_snapshot` so one topic can
absorb many clusters per snapshot"* (`2026-07-28-identity-layer-raw-cosine.md`), everything
else byte-identical (`MATCH_THRESHOLD` 0.88, `ANCHOR_THRESHOLD` 0.93, `merge_duplicates`
untouched and not run).

---

## VERDICT: **NO-GO**

**Guard 2 (false absorptions) fired**, and it fired by three orders of magnitude over its
pre-registered kill rule of `>0`: **2,247** within-night multi-absorptions carry the topic-784
signature, **1,513 of them on fully-labelled nights** (so the label blackout does not explain
them). Baseline is **0** by construction.

**And the recall bar was never approached.** Not one of the three core witness families reached
≤3 topics *because of* the change:

| core family | clusters | topics — baseline | topics — variant | target |
|---|---|---|---|---|
| `GQ-12 caspian [window]` | 16 | 10 | **8** | ≤3 |
| `berlin pride [window]` | 54 | 34 | **22** | ≤3 |
| `GQ-05 [window]` | 7 | 3 | **3** | ≤3 |

`GQ-05` sits at 3 in **both** arms — it was already there; the variant changed nothing about it.
So the honest count against the pre-registered bar ("≤3 on ≥2 of 3 core families") is
**0 of 3 improved to target**, not 1.

The change is not a small loss either. It is a large, badly-aimed one: over the same 12 nights
the variant ends with **4,067 topics instead of 6,529 (−37.7%)** and **1,177 active instead of
2,662 (−55.8%)**. It deletes more than half the serving population and buys a 35% fragmentation
reduction on one family.

---

## 1 · Data availability — and why the label rail lands elsewhere

Labelled snapshots (0% NULL `emergent_clusters.label`) available at run time:

| snapshot | clusters | NULL labels |
|---|---|---|
| 2026-07-17 14:51 | 1966 | 0 |
| 2026-07-19 16:34 | 537 | 0 |
| 2026-07-19 19:04 | 539 | 0 |
| 2026-07-20 07:35 | 3754 | 0 |
| 2026-07-21 07:42 | 2369 | 0 |
| 2026-07-22 07:38 | 2517 | 0 |
| **2026-07-28 03:28** | **2032** | **0** |
| *07-23 … 07-27* | *2190 / 2395 / 3854 / 3593 / 3475* | *100% — VOID* |

**Only ONE labelled snapshot exists after the blackout (07-28); no 07-29 snapshot has run yet.**
Six labelled nights precede it, separated from it by the five VOID nights.

The T-A2 rail says the blackout nights are not valid *measurement* nights. That is correct for
merging — `labels_compatible(None, None)` is False, so `merge_duplicates` is disabled there. It
does **not** apply to this question: **`process_snapshot`'s matcher never reads a label.** The
gates are `cos(cluster, topic.centroid) ≥ 0.88` and `cos(cluster, topic.anchor_centroid) ≥ 0.93`
and nothing else. Replaying the blackout nights is therefore faithful, and *skipping* them would
be the distortion — they are exactly the nights on which the Berlin-Pride and Caspian identities
were founded.

So both were run, and they agree:

| run | replayed | core families baseline → variant |
|---|---|---|
| `--mode all` (primary) | 12 nights | caspian 10→8 · berlin pride 34→22 · GQ-05 3→3 |
| `--mode labelled` | 7 nights | caspian 9→**9** · berlin pride 24→21 · GQ-05 1→1 |
| `--mode all`, 07-28 only | 1 night | caspian 9→8 · berlin pride 23→21 |

On labelled nights alone the Caspian family does not consolidate **at all**. Both runs return
NO-GO on the same kill (labelled-only: 1,514 flagged).

---

## 2 · A structural fact the harness makes visible

Within one snapshot, `pairs` is built against the topics that exist when the night *starts*;
unmatched clusters found new topics only **after** the match loop
(`project_dynamic_topics.py:507-537`). So **a brand-new event whose N fragments all arrive in the
same snapshot founds N topics in both arms** — `used_t` is not the binding constraint there, it
is arithmetically incapable of being one. Dropping `used_t` can only consolidate clusters onto a
topic that already existed when the night began.

This is why the family analysis had to be run **window-scoped**, not snapshot-scoped. The
snapshot-scoped families (the object the witness-reconvergence artifact scored) were extended
across the replay window by **shared `sample_signal_ids`** — one hop, label-free, so it reaches
the blackout nights that label similarity cannot:

| family | 07-22 | 07-23 | 07-24 | 07-25 | 07-26 | 07-27 | 07-28 | total |
|---|---|---|---|---|---|---|---|---|
| `berlin pride` | 2 | — | 2 | 2 | 7 | 18 | 23 | **54** |
| `GQ-12 caspian` | — | — | — | — | 1 | 6 | 9 | **16** |

---

## 3 · Metric 1 — witness reconvergence (PRIMARY)

Primary run, 12 nights. `topics` = distinct topics holding ≥1 of the family's clusters at the end
of the replay.

| family | clusters | topics BASE | topics VAR | largest topic BASE | largest topic VAR | variant's largest holder |
|---|---|---|---|---|---|---|
| `GQ-12 caspian` (07-28) | 9 | 9 | 7 | 1 | 3 | Iran Warns Ukraine Over Vessel Attack |
| `berlin pride` (07-28) | 23 | 23 | 19 | 1 | 3 | **Venezuela Earthquake Tragedy** |
| `fresh:us-strikes-on-iran` | 9 | 9 | 8 | 1 | 2 | Jordan Intercepts Iranian Missiles |
| `fresh:paris-knife-attack` | 9 | 9 | 9 | 1 | 1 | **Venezuela Earthquake Tragedy** |
| `fresh:russian-missile-strikes-on-kyiv` | 9 | 9 | 9 | 1 | 1 | Ukrainian Drone Attacks on Russia |
| `fresh:wildfires-in-france-and-spain` | 8 | 8 | 8 | 1 | 1 | Severe Storms in France |
| `GQ-12 caspian [window]` | 16 | 10 | 8 | 3 | 4 | Iran Warns Ukraine Over Vessel Attack |
| `berlin pride [window]` | 54 | 34 | 22 | 3 | 7 | **Venezuela Earthquake Tragedy** |
| `fresh:us-strikes-on-iran [window]` | 46 | 12 | 8 | 6 | 11 | US Airstrikes on Iran |
| `fresh:paris-knife-attack [window]` | 11 | 11 | 10 | 1 | 2 | **Andy Burnham UK PM** |
| `fresh:russian-missile-strikes-on-kyiv [window]` | 38 | 13 | **14** | 5 | 5 | Ukrainian Drone Attacks on Russia |
| `fresh:wildfires-in-france-and-spain [window]` | 29 | 13 | 13 | 5 | 5 | Europe Heatwave Crisis |
| `GQ-05 [window]` | 7 | 3 | 3 | 5 | 5 | **Senator Calisto Fraud Case** |

Best case is Berlin Pride: 34 → 22 topics, a 35% reduction, still 7× the target. One family gets
**worse** (Kyiv 13 → 14). And the topic that ends up holding the most Berlin-Pride clusters is
called *Venezuela Earthquake Tragedy*.

---

## 4 · Why it does not consolidate — the decisive negative finding

The harness records, for every witness cluster, its full score row against every topic at match
time. For each family it then asks about the **topic that ends up holding the most of that
family's clusters** — the natural consolidation target — what the geometry said for every *other*
family cluster:

| family (variant) | clusters | distinct holders | admissible to target | blocked by anchor | **target not even in the cluster's top-12 topics** |
|---|---|---|---|---|---|
| `berlin pride [window]` | 54 | 22 | 9 | 2 | **43** |
| `GQ-12 caspian [window]` | 16 | 8 | 3 | 0 | **13** |
| `fresh:us-strikes-on-iran [window]` | 46 | 8 | 11 | 5 | **30** |
| `fresh:russian-missile-strikes-on-kyiv [window]` | 38 | 14 | 5 | 2 | **31** |
| `fresh:wildfires-in-france-and-spain [window]` | 29 | 13 | 5 | 0 | **24** |
| `GQ-05 [window]` | 7 | 3 | 5 | 1 | 1 |

**43 of 54 Berlin-Pride fragments do not have the consolidation target among their twelve
nearest topics at all.** The fragments of one event do not share an argmax. Each one
independently picks a different stale identity — *Polish Healthcare Crisis*, *Venezuela
Earthquake Rescue*, *Bangkok Bar Fire* (all three are prod's real 07-28 assignments, reproduced
by the baseline replay).

That is the finding the honesty rail anticipated, in a sharper form than "the fragments do not
clear 0.88 against each other's topics". They *do* clear it — against the wrong topics.
`used_t` was never the binding constraint. **The binding constraint is that raw e5 cosine does
not put a family's fragments near the same topic.** Removing the one-topic-per-night cap lets a
topic take many clusters; it does nothing to make an event's clusters *choose the same topic*.

The baseline arm makes the same point from the other side: its GQ-05 consolidation target is
`Cabo Verde Captain Rape Allegations` — **topic 784 itself**, the diagnosis's own exhibit,
absorbing Colombian Espriella clusters. The replay reproduces the pathology without any change.

---

## 5 · Metric 2 — false absorptions (the kill)

Signature, pre-registered: a topic absorbing ≥2 clusters in one night whose absorbed clusters
span **≥3 distinct primary countries**, or whose labels are flatly incompatible
(SequenceMatcher < 0.40 **and** no shared distinctive token — a token outside the top-decile df
of that night's cluster-label vocabulary). Baseline cannot produce these: `used_t` caps it at one
cluster per topic per night, so **baseline = 0** by construction.

| | baseline | variant |
|---|---|---|
| multi-absorption topic-nights | **0** | **4,467** |
| flagged 784-class | **0** | **2,247** |
| …of which on fully-labelled nights | — | **1,513** |
| signature: country span only | — | 778 |
| signature: label clash only | — | 983 |
| signature: both | — | 486 |
| umbrella topics among the flagged | — | 68 |

Per night (variant): 07-17 257 · 07-19 107 · 07-20 396 · 07-21 262 · 07-22 269 · 07-23 52 ·
07-24 136 · 07-25 191 · 07-26 185 · 07-27 170 · 07-28 222. The blackout nights score *lower*
only because the label-clash half is undecidable there (a NULL label is never counted as a
clash) — the country-span half still fires.

Worst offenders:

```
2026-07-26  'Valencia Building Collapse'        absorbed 41 clusters, 12 countries
                                                BR CY EG FR GR IN IT MD PL SY …
2026-07-25  'UK Bans Energy Drinks for Minors'  absorbed 40 clusters, 17 countries
                                                AE AU CA CU CY DJ DK ES FR GB GR IL …
2026-07-25  'Valencia Building Collapse'        absorbed 38 clusters, 10 countries
2026-07-27  'Turkey News Roundup'               absorbed 18 clusters, 17 countries
```

Label-clash examples (labelled nights, so the labels are readable):

```
'Mette-Marit Lungentransplantation Entlassung' + 'Neonazi Liebich Auslieferung'   sim 0.222
'Senate Democrats Block Defense Bill Over Iran War' + 'US House Withholds Nigeria Aid'  sim 0.329
'Jornal Anhanguera Video Editions' + 'Acre News Broadcasts'                        sim 0.192
```

Context (computed identically in both arms, so it is a fair comparison rather than a
construction): the *lifetime* 784 signature — a topic whose window clusters span ≥3 primary
countries — is **775 topics in baseline** and **415 in variant**. The variant's number is lower
only because it has 38% fewer topics; per topic it is worse, and it now concentrates the
cross-country fusion into single nights, which is what the kill rule measures.

**Kill rule `>0` ⇒ NO-GO. Fired.**

---

## 6 · Metric 3 — over-merge pressure (passes the letter, fails the spirit — measured)

`overmerge.partition` + `overmerge.decide` run over each arm's simulated member sets (members =
the embedded sample signals of the clusters a topic holds inside the window; actors = subject
country + NER persons, via `country_dominant_overlap`).

| | baseline | variant | ratio |
|---|---|---|---|
| topics evaluated (≥12 embedded members) | 2,518 | 1,211 | |
| demote-eligible (demote + borderline) | 253 | 49 | **0.194** |
| demote-eligible rate | 10.1% | 4.1% | 0.40 |

**Ratio 0.194 ≪ 1.5, so the pre-registered guard 3 does not fire. It should not be read as
reassurance, and here is the measurement that says why.** Bucketing by how many clusters each
topic actually fused:

| clusters fused | baseline topics / gap_ratio median / eligible rate | variant topics / gap_ratio median / eligible rate |
|---|---|---|
| 1 | 35 · 1.247 · 0.0% | 28 · 1.207 · 0.0% |
| 2–4 | 576 · 1.287 · 4.2% | 285 · 1.295 · 1.8% |
| 5–9 | 1,557 · 1.300 · 11.6% | 341 · 1.324 · 5.0% |
| **10+** | 350 · **1.044** · 13.7% | **557** · **0.818** · **4.9%** |

The variant pushes 557 topics into the 10+ bucket (baseline 350), and in that bucket the median
`gap_ratio` **falls to 0.818** — below `TAU_SEP_LOW = 1.3`, i.e. an automatic `KEEP` labelled
*"unimodal (no wide gap)"*. This is exactly the blindness the detector's own doc records
(`2026-07-20-overmerge-detector.md`: a fusion of 3+ stories has no clean bimodal split, so
2-means finds no two poles). A 41-cluster / 12-country blob is not bimodal — it is a smear.
**The variant's demote-eligible count is lower because the detector stops seeing the blobs, not
because there are fewer of them.** Guard 3 is therefore reported as *not fired, and not
informative at this operating point*.

---

## 7 · Metric 4 — absorption density (variant)

12,256 absorbing topic-nights; distribution of clusters absorbed per topic per night:

| stat | value |
|---|---|
| mean | 2.23 |
| p95 | **7** |
| p99 | **17** |
| max | **41** |
| topic-nights over the 10-cluster red flag | **320** |

Histogram tail: 1 → 7,789 · 2 → 1,947 · 3 → 832 · 5 → 325 · 10 → 52 · 20 → 12 · 30 → 2 ·
**41 → 1**. Hand-inspected red flags are in §5 — *Valencia Building Collapse* (41 clusters,
12 countries) and *UK Bans Energy Drinks for Minors* (40 clusters, 17 countries) are not stories,
they are drains.

---

## 8 · Metric 5 — anchor-guard effectiveness

Over the 12-night primary run, counting every (cluster, topic) pair evaluated:

| | baseline | variant |
|---|---|---|
| pairs admitted (both gates) | 809,415 | 485,750 |
| **cleared MATCH 0.88, blocked by ANCHOR 0.93** | **17,808,412** | **10,727,995** |
| cleared ANCHOR, blocked by MATCH | 317 | 1,141 |

**The anchor guard rejects 95.7% of everything the 0.88 match admits** (17.81M of 18.62M). The
reverse case is negligible (317 pairs, 0.002%), i.e. `ANCHOR ≥ 0.93` is very nearly a strict
sub-condition of `MATCH ≥ 0.88` on this substrate — the running centroid drifts toward, not away
from, whatever the anchor already accepts.

So: the anchor guard is doing essentially *all* of the braking, and it is still not enough. It
admits 809k pairs, of which the greedy pass consumes ~27k, and §5 shows that what it admits
includes Berlin-Pride-onto-Venezuela-Earthquake at cos 0.93–0.98. **The anchor guard cannot serve
as the absorption brake once `used_t` is gone** — that is the direct answer to the side-metric's
question. Also measured: **0 pairs** land within 1e-12 of either gate, so the harness's dgemm-vs-
ddot numerics cannot have flipped a decision.

---

## 9 · Harness fidelity, and its limits

The baseline arm is production. Validated against prod's real `dynamic_topic_members`:

| replay | prod rows compared | agreement |
|---|---|---|
| **07-28 only, hydrated from real prod state** | 1,988 | **93.8%** (123 disagreements, 26 involving the umbrella layer) |
| 12 nights from 07-17 | 1,988 | 57.2% |

The single-night number is the fidelity claim: same-night, same state, 93.8% identical
assignment, and the arm reproduces prod's aggregate exactly — **1,937 attached / 95 founded**
versus prod's 1,893 attached-to-pre-existing + 95 founded + 44 clusters carrying no membership
row at all (1,893 + 44 = 1,937). The 12-night number is honest accumulated drift and is *not* a
defect of the comparison: baseline and variant are diffed against each other inside one run, from
one identical hydration.

Limits, stated:

- **Umbrella topics participate in matching**, because `hydrate_topics` loads all of
  `dynamic_topics` with no `is_umbrella` filter — that is production behaviour, replicated, and
  identical in both arms. 68 of the 2,247 flagged groups are umbrellas.
- **`merge_duplicates` is not run** (production runs it only under `--rebuild`). The label gate
  it applies is unchanged by this question and, per the witness-reconvergence artifact, it is
  currently the only density controller that satisfies K2.
- **`flag_content_roundups` is skipped** — it affects lifecycle votes, never matching, and is
  identical in both arms.
- **Over-merge members are built from cluster `sample_signal_ids`**, not `topic_members` (which
  this simulation does not write). Embeddings survive only ~7 days, so §6's evaluation is
  effectively carried by the recent nights; both arms share that coverage.
- **GQ-05 is an in-snapshot proxy** (7 clusters found by signal-id overlap), not the diagnosis's
  21/33 offline HDBSCAN fragments — those live outside `emergent_clusters` and cannot be nodes of
  a projection replay. The 07-28 snapshot contains **zero** Espriella-touching clusters.
- **One post-blackout labelled night exists.** The multi-night claim rests on 12 replayed nights
  of which 7 are labelled; a second post-blackout labelled night would strengthen §3 but cannot
  plausibly reverse §4 or §5, whose margins are 43-of-54 and 2,247-vs-0.

---

## 10 · Surprises

1. **`used_t` is not what fragments the field — the raw-cosine argmax is.** §4. This retires the
   diagnosis's fix 2 as an independent lever: it is not "safe only after whitening", it is
   *ineffective* with or without `used_t`, because the fragments are not competing for the same
   topic in the first place.
2. **`used_t` is already violated in production, 633 times.** Non-umbrella topic-nights holding
   >1 cluster: 07-27 77 · 07-26 95 · 07-25 84 · 07-22 27 · 07-21 43 · 07-20 33 … but **0 on
   07-28**. The projection cannot produce these, so another writer does — `robot_apply_outputs.py`
   (`UPDATE dynamic_topic_members SET dynamic_topic_id=…`) is the likely source. Worth confirming
   separately; it means the "one cluster per topic per night" invariant is a property of the
   projection, not of the table.
3. **44 of the 07-28 snapshot's 2,032 clusters carry no membership row at all** — including
   `Iran Accuses Ukraine of Caspian Attack` (70 signals, the largest Caspian fragment) and
   `Spanyol Juara Piala Dunia 2026` (106 signals). They are not orphaned by `used_t`: the baseline
   replay attaches all 44. Their `identity_key`s are absent from `dynamic_topics`, so they were
   dropped between matching and persistence. Their `cluster_id`s are in the 200k+ range (a scoped
   country lane), consistent with those clusters being written *after* the projection ran, leaving
   them queued for a next projection pass that has not happened. Flagged, not diagnosed.
4. **The anchor guard is nearly a strict sub-condition of the match gate** (317 counter-examples
   in 18.6M pairs). The two gates are not independent controls; tuning 0.88 without 0.93 moves
   almost nothing.
5. **The over-merge detector gets *quieter* as blobs get bigger** (§6, gap_ratio median 1.044 →
   0.818 in the 10+ bucket). Any future change that increases fusion must not use
   `detect_overmerge`'s demote count as its purity control without this correction.

---

## 11 · What would have to be true for a GO

Not a threshold change — none was made here, and none would help. §4 says the fragments do not
share an argmax, so any relaxation of `used_t`, `MATCH`, or `ANCHOR` redistributes clusters among
*wrong* topics faster. The ordering in the diagnosis was right and this run sharpens it:

- **Fix 1 first, and on its own merits.** Run the identity layer in whitened space and re-fit
  the three thresholds there. §4's number to beat is concrete and now measurable: *of a family's
  N fragments, how many have the family's own topic in their top-12?* Today it is 11/54 for
  Berlin Pride. Whitening's job is to move that number, and if it does not, `used_t` is moot.
- **Only then re-run this simulation**, unchanged, as the second gate — the harness is
  parameterised on nothing but the gates it imports, so pointing it at a whitened identity layer
  is a one-line change.
- **Do not use `detect_overmerge`'s demote count as the purity control** for that re-run (§6).
  The country-span signature in §5 is the one that stayed honest as blobs grew.
