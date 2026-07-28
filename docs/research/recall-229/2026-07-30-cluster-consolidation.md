# Consolidating same-event fragments at the CLUSTER level, before projection

**Generated:** 2026-07-28 · read-only (`SET default_transaction_read_only = on`), no prod write, no commit
**Harness:** `backend/scripts/measure_cluster_consolidation.py`
**Artifacts:** `2026-07-30-cluster-consolidation.json` (primary, 12-night replay + over-merge +
the four graph variants) · `…-singlenight.json` (07-28 only, the 93.8%-fidelity downstream arm)

**Question:** `2026-07-30-used-t-simulation.md` refuted the `used_t` fix and left one sharp
number behind — *43 of 54 Berlin-Pride fragments do not have the consolidation target among
their twelve nearest topics.* The fragments of one event do not share an argmax, so nothing at
the **matching** layer can make them choose the same topic. This tests the move that sidesteps
argmax dispersion entirely: **unify the fragments with each other first, inside the snapshot,
using the only rule `2026-07-29-witness-reconvergence.md` found to be K2-safe** —

```
cos(centroid_a, centroid_b) >= 0.90   AND   labels_compatible(label_a, label_b)
```

— connected components become ONE super-cluster, which then makes ONE pick against the topic
pool. 22 fragments each picking a different stale topic becomes 4 picks, or 1.

Everything under test is imported, never re-implemented: `MERGE_THRESHOLD`, `MERGE_LABEL_MIN`,
`labels_compatible`, `is_roundup_label` from `project_dynamic_topics`; `process_snapshot_sim`
(with `allow_multi=False`, i.e. production's `used_t` **INTACT**), `hydrate_as_of`, the family
discovery and the guard constants from `simulate_used_t_removal`; `different_story` /
`countries_disjoint` / `countries_share` from `measure_evidence_fingerprint`.

Four graph variants are scored per snapshot on one shared candidate-pair set: the **primary**
rule above; a **unicode-label** variant for comparability with the 07-29 artifact; a
**roundups-excluded** variant; and **cos-only** (metric 6). A fifth, **+ shared country**, was
added *after* the primary run's kill fired and is reported in §11.1 as a lead, never as a
result of this run.

---

## VERDICT: **NO-GO**

Both pre-registered kills fired, and a third finding — not a threshold, and not anticipated by
the task — is the one that actually decides it.

| kill | rule | result |
|---|---|---|
| **K2** | largest consolidated component > 2% of that snapshot's clusters | **fired** on 3 of 15 labelled snapshots (3.28% / 2.46% / 3.15%) |
| **784-class** | a component spanning ≥3 primary countries AND carrying an incompatible label pair, count > 0 | **fired**, 1 component (07-17: Ukraine + Iran + Yemen fused, 12 clusters, 243 signals, 7 countries) |

**And the finding that matters more than either.** The consolidation works — spectacularly, on
its own axis. Berlin Pride goes from 23 topics to **3**; the Paris knife attack from 9 topics to
**1**; story coverage rises from 0.109 to 0.931 and from 0.174 to **1.000**. But the single
topic the event concentrates onto is, in **4 of 6** witness families, the **wrong identity**:

```
Paris Knife Attack        x9 clusters, 149 signals  ->  100.0% onto "Monaco Explosion Targets Ukrainian…"
Russian Missile Strikes on Kyiv  x9, 163 signals    ->   75.5% onto "Drone Attacks on Moscow"
Iran/Ukraine Caspian ship attack x9, 183 signals    ->   77.0% onto "Iran Attacks UAE Tankers"
Wildfires in France and Spain    x8, 178 signals    ->  100.0% onto "Fontainebleau Forest Fires"
```

Kyiv-being-struck lands on Moscow-being-struck: the same war, the opposite direction. In the
RAW arm those same fragments are also mis-attached — but each wrong topic holds **one** cluster
(11–48% of the family's signals). **Consolidation does not create the mis-attachment. It makes
it total.** Recall improves by 2–9×; the identity does not improve at all, and one wrong topic
now owns the entire event.

That is the used_t artifact's §4 restated at a new layer: the argmax is wrong, and giving it a
better-formed question does not make its answer right.

---

## 1 · Data availability — say the number

`emergent_clusters` holds **131 snapshots**. Fifteen are fully labelled (0% NULL `label`, ≥100
clusters). **Exactly ONE is from 2026-07-28 onward** — `2026-07-28T03:28:39` (2032 clusters).
No 07-29 or 07-30 snapshot has run.

Restricting the graph metrics to "07-28 onward" would therefore be a one-night claim, which is
the exact weakness the used_t artifact flagged in itself. So metrics 1/2/3/5/6 are computed on
**all 15 labelled snapshots** (2026-07-01 → 2026-07-28) and reported per night; 07-28 is the
headline snapshot because it is the only post-blackout one and the one the witness artifact
scored. The five blackout nights (07-23 → 07-27, 100% NULL) cannot carry this rule at all — see
§8.

## 2 · Harness fidelity

Four independent reproductions, none of them assumed:

| check | expected | measured |
|---|---|---|
| fast-path label conjunct ≡ `labels_compatible` | exact | **0 / 20,000** disagreements |
| sampled FALSE pairs satisfy the imported construction | exact | **0 / 1,200** violations |
| witness artifact's shipping-rule row on 07-28 (380 edges, largest 23 = 1.1%, 0/1200 false) | reproduce | **380 edges, 23, 1.13%, 0/1200** (unicode-label variant) |
| witness artifact's cos-only 0.90 row (88,103 edges, largest 1997 = 98.3%) | reproduce | **88,103 edges, 1997, 98.28%** |
| RAW arm vs prod `dynamic_topic_members`, single-night | ≈93.8% | **93.81%** (1865/1988; 95.06% excluding umbrella rows) |
| RAW arm vs the used_t artifact's baseline arm, 12 nights | identical | topics 6529 = 6529 · active 2662 = 2662 · agreement 57.19% = 57.2% · `berlin pride [window]` 34 = 34 · `caspian [window]` 10 = 10 |

The primary rule uses production's `labels_compatible` **verbatim**, which normalizes with
`[^a-z0-9]+`; the witness artifact used a Unicode-aware normalizer. On 07-28 the two differ by
**one edge in 380** (379 vs 380). Measured cost of the ASCII normalizer: 25 of 2032 labels
(1.23%) normalize to the empty string and can never merge with anything — a silent per-script
disablement, reported rather than assumed.

A singleton component reproduces its cluster exactly (same centroid, label and `cluster_id`,
hence the same `identity_key` a founding would produce), so every divergence between the two
downstream arms comes from a real merge.

## 3 · Metric 1 — fragments per event after cluster consolidation (PRIMARY)

Snapshot 2026-07-28, connected components of the consolidation graph.

| family | kind | clusters | components | target |
|---|---|---|---|---|
| `GQ-12 caspian` | **core** | 9 | **4** | ≤3 |
| `berlin pride` | **core** | 23 | **3** ✓ | ≤3 |
| `GQ-05` | **core** | — | **not scorable** | — |
| `fresh:us-strikes-on-iran` | fresh † | 9 | 2 | |
| `fresh:paris-knife-attack` | fresh † | 9 | 1 | |
| `fresh:russian-missile-strikes-on-kyiv` | fresh † | 9 | 4 | |
| `fresh:wildfires-in-france-and-spain` | fresh † | 8 | 1 | |

**Result: 1 of 2 scorable core families at ≤3. The bar (≥2 of 3) is unmet.**

`GQ-05` cannot be scored: the 07-28 snapshot contains **zero** espriella-touching clusters
(the same limitation the used_t artifact recorded). Requiring 2 of the 2 that exist is the
strict reading; 1 of 2 fails either way.

† **Fresh families are not independent witnesses of this rule and their numbers must not be
read as evidence for it.** The discovery rule (`simulate_used_t_removal.fresh_families`) is
*label similarity ≥ 0.80 plus a shared country* — essentially the label conjunct of the rule
under test. For a fresh family, metric 1 only asks whether cos ≥ 0.90 *also* holds. The core
families are `label ILIKE` patterns (`iran` AND `ukrain`; `berlin` AND `pride`), discovered
independently of label similarity, which is why the bar is stated over them.

The full 07-28 component-size histogram: `1 → 1650 · 2 → 94 · 3 → 18 · 4 → 3 · 5 → 7 · 6 → 3 ·
7 → 1 · 9 → 2 · 10 → 1 · 17 → 1 · 23 → 1`. 382 of 2032 clusters (18.8%) enter a multi-cluster
component; 131 components form. Hand-read, the large ones are exactly the right objects:

```
23  Berlin Pride Van/Vehicle/Car/Terror Attack, CSD Berlin …        DE      286 signals
17  Wildfires in France and Spain (x16) + Wildfire Evacuations …    ES      414
10  Russian Strikes on Odesa Ports / Kyiv Region / Ukrainian Ports  RU,UA   171
 9  Lottery Results / Draw / Live / Today …                         GB,IT,ES,FR,BR
 9  Paris Knife Attack (x9)                                         FR      149
 7  US Strikes / Airstrikes / Military Strikes on Iran              IR       91
```

## 4 · Metric 2 — K2 on the cluster graph (**KILL FIRED**)

| snapshot | clusters | edges | largest | share | K2 |
|---|---|---|---|---|---|
| 2026-07-01 | 731 | 314 | 24 | **3.28%** | ✗ |
| 2026-07-03 | 186 | 8 | 2 | 1.07% | ✓ |
| 2026-07-04 | 285 | 34 | 7 | **2.46%** | ✗ |
| 2026-07-05 | 224 | 9 | 3 | 1.34% | ✓ |
| 2026-07-06 | 594 | 97 | 9 | 1.52% | ✓ |
| 2026-07-09 | 728 | 131 | 12 | 1.65% | ✓ |
| 2026-07-12 | 773 | 130 | 9 | 1.16% | ✓ |
| 2026-07-13 | 788 | 130 | 13 | 1.65% | ✓ |
| 2026-07-17 | 1966 | 432 | 18 | 0.92% | ✓ |
| 2026-07-19 16:34 | 537 | 42 | 6 | 1.12% | ✓ |
| 2026-07-19 19:04 | 539 | 117 | 17 | **3.15%** | ✗ |
| 2026-07-20 | 3754 | 1010 | 31 | 0.83% | ✓ |
| 2026-07-21 | 2369 | 519 | 32 | 1.35% | ✓ |
| 2026-07-22 | 2517 | 630 | 19 | 0.76% | ✓ |
| **2026-07-28** | 2032 | 379 | 23 | **1.13%** | ✓ |

**The kill fired on 3 of 15 nights. It is honoured, and no threshold was moved after seeing
it.** But the three offending components were hand-inspected and none of them is a fusion:

```
2026-07-01  24 clusters  "World Cup 2026 Updates / Coverage / Group J / Knockout Stage / …"   20 countries
2026-07-04   7 clusters  "Monaco Bombing Suspect" x7                                           4 countries
2026-07-19  17 clusters  "US Strikes on Iran" / "US Airstrikes on Iran" / "US Strikes Iran…"   1 country (IR)
```

All three are ONE real event correctly reassembled. They exceed 2% only because those snapshots
hold 285–731 clusters, where 2% is 6–15 clusters. On every snapshot at current production scale
(≥1,900 clusters) the share is **0.76%–1.35%**, comfortably inside the bar, and the *absolute*
largest components on the failing nights (24 / 7 / 17) are smaller than on the passing ones
(31 / 32). **K2-as-a-share is size-sensitive, and the 2% bar was calibrated on a 2032-cluster
night.** That observation does not rescue the run — the rule was pre-registered — but it says
which of the two kills is the real defect, and it is not this one.

Excluding roundup/listing-labelled clusters (as `merge_duplicates` does for topics) does not
help: the three offending components are not roundups, and the largest component moves on only
2 of 15 nights.

## 5 · Metric 3 — the false side, same pass

The mechanical FALSE construction (disjoint non-empty country sets AND dissimilar same-script
labels), 1,200 pairs sampled per snapshot from the imported predicates:

| | admitted by the rule | admitted by cos ≥ 0.90 alone |
|---|---|---|
| all 15 labelled snapshots | **0 / 1,200 on every night** | 29 – 210 per night |
| 2026-07-28 | **0 / 1,200** | 35 / 1,200 (2.9%) |

On 07-28 the false pairs reach cos **0.9487** (p99 0.9186) — 35 of them clear the cosine gate
outright. The label conjunct rejects all 35. **The precision of this rule is entirely the label
conjunct's doing**, which is the same thing §8 says from the other side.

**Cross-family components: 0.** No two witness families ever land in one component, on any
labelled night.

## 6 · Metric 4 — downstream, through `process_snapshot` with `used_t` INTACT

Two arms, one identical hydration, production's matcher unchanged: **raw clusters** vs
**consolidated super-clusters** (centroid = n_signals-weighted mean, label = modal/longest,
`cluster_id` = min).

### 6a · Single night — the high-fidelity configuration (raw arm 93.81% vs prod)

| family | clusters | signals | RAW topics | RAW coverage | **CON topics** | **CON coverage** | landed on |
|---|---|---|---|---|---|---|---|
| `GQ-12 caspian` | 9 | 183 | 9 | 0.383 | **4** | 0.770 | Iran Attacks UAE Tankers ✗ |
| `berlin pride` | 23 | 276 | 23 | 0.109 | **3** | **0.931** | Berlin Pride Vehicle Attack ✓ |
| `fresh:us-strikes-on-iran` | 9 | 111 | 9 | 0.180 | **2** | 0.820 | US Strikes on Iran ✓ |
| `fresh:paris-knife-attack` | 9 | 149 | 9 | 0.174 | **1** | **1.000** | Monaco Explosion Targets Ukrainian… ✗ |
| `fresh:russian-missile-strikes-on-kyiv` | 9 | 163 | 9 | 0.239 | **4** | 0.755 | Drone Attacks on Moscow ✗ |
| `fresh:wildfires-in-france-and-spain` | 8 | 178 | 8 | 0.483 | **1** | **1.000** | Fontainebleau Forest Fires ✗ |

Topics-per-event falls on **all six**; story coverage rises on **all six**. Serving is barely
touched: 6659 → 6642 topics, active 1361 → 1319 (−3.1%). For contrast, dropping `used_t` cut
active topics by **55.8%**.

The `landed on` column is the control the metric list did not ask for and the run could not
honestly omit. **Coverage measures CONCENTRATION, not correctness.** Four of six families
concentrate onto a topic that is a different event. `identity_ok` (production's own
`labels_compatible` between the holder's label and the family's modal cluster label) is a
strict proxy — it scores "US Strikes on Iran" ✓ but would have scored a correct rename as
False — so the ✓/✗ above is hand-assigned, and the proxy is reported alongside it in the JSON
(`metric4_identity_landing_consolidated`). The proxy agrees with the hand read on direction:
single-night it is **4/12 → 4/12** (flat), and over the 12-night window it **falls, 4/13 →
2/13**. On no configuration does consolidation improve identity.

### 6b · Twelve nights — and why it looks so much worse

| family | clusters | RAW topics | CON topics | RAW cov | CON cov |
|---|---|---|---|---|---|
| `GQ-12 caspian [window]` | 16 | 10 | **9** | 0.259 | 0.456 |
| `berlin pride [window]` | 54 | 34 | **26** | 0.094 | 0.454 |
| `fresh:us-strikes-on-iran [window]` | 46 | 12 | **13** ↑ | 0.198 | 0.151 ↓ |
| `fresh:paris-knife-attack [window]` | 11 | 11 | **3** | 0.144 | 0.828 |
| `fresh:russian-missile-strikes-on-kyiv [window]` | 38 | 13 | **13** | 0.178 | 0.313 |
| `fresh:wildfires-in-france-and-spain [window]` | 29 | 13 | **15** ↑ | 0.330 | 0.382 |
| `GQ-05 [window]` | 4 | 3 | **3** | 0.571 | 0.571 |

**Core window bar: 1 of 3 at ≤3, 0 improved to target. Unmet.**

The reason is measured, not inferred. Consolidation is a **within-snapshot** operation, and
five of the twelve replayed nights are the label blackout, where it is a strict no-op:

| night | labelled | clusters | super-clusters | merged away | edges |
|---|---|---|---|---|---|
| 07-17 | yes | 1966 | 1738 | 228 | 432 |
| 07-19 ×2 | yes | 537 / 539 | 507 / 459 | 30 / 80 | 42 / 117 |
| 07-20 | yes | 3754 | 3166 | 588 | 1010 |
| 07-21 | yes | 2369 | 2026 | 343 | 519 |
| 07-22 | yes | 2517 | 2154 | 363 | 630 |
| **07-23 … 07-27** | **no** | 2190 / 2395 / 3854 / 3593 / 3475 | **identical** | **0** | **0** |
| 07-28 | yes | 2032 | 1781 | 251 | 379 |

Berlin Pride's 54 window clusters are distributed 07-22 (2) · 07-24 (2) · 07-25 (2) · 07-26 (7)
· 07-27 (18) · 07-28 (23). **Twenty-nine of them fall on blackout nights** and cannot merge.
The consolidated arm ends at 26 topics — i.e. the residual is essentially the blackout
fragments. Caspian: 7 of 16 clusters on blackout nights, 9 topics remain. **The window numbers
are measuring the blackout, not the rule.**

The two families that got *worse* (`us-strikes-on-iran` 12→13, `wildfires` 13→15) are
accumulated arm divergence, not a mechanism: on the blackout nights both arms are fed identical
cluster lists yet the consolidated arm founds **+394** topics more across the five nights
(1,669 vs 1,275), because its topic population diverged on the labelled nights that preceded
them.

**One hypothesis formed and killed here.** The obvious explanation for the weak cross-night
result was that a super-cluster's averaged centroid becomes a *looser* founding anchor, so
tomorrow's fragments fail `ANCHOR_THRESHOLD` against it. Measured directly
(`super_cluster_geometry`): mean cos(super, member) = **0.9806** vs mean pairwise cos(member,
member) = **0.9382**; min-to-super 0.973 vs min-pairwise 0.931; the average is tighter in
**100.0%** of components on every night. Averaging **tightens** the anchor. The hypothesis is
refuted; the cross-night residual is the blackout plus argmax dispersion.

## 7 · Metric 5 — over-merge, with the honest control (**KILL FIRED**)

The used_t artifact §6 measured `detect_overmerge` going blind as fusions grow (gap_ratio
median 1.044 → 0.818 at 10+ clusters), so the pre-registered control is the **country-span
signature**: a component spanning ≥3 primary countries **AND** carrying an internally
incompatible label pair (SequenceMatcher < 0.40 with no shared distinctive token).

Across 15 labelled nights: **1 flagged component.**

```
2026-07-17   12 clusters   243 signals   CO IR RU SK UA YE YM

  Russia-Ukraine Conflict Escalation · Russia-Ukraine War Escalation
  Russia-Ukraine Conflict Updates    · Ukraine War Escalation
  US-Iran Conflict Escalation  x3    · US-Iran Military Escalation x3
  Yemen Conflict Escalation    x2
```

Traced to the pair that bridged it, not asserted:

```
Russia-Ukraine Conflict Escalation  <->  US-Iran Conflict Escalation    label_sim 0.852  cos 0.9096
US-Iran Conflict Escalation         <->  Yemen Conflict Escalation      label_sim 0.808  cos 0.9054
```

**Three wars in one super-cluster, joined by a direct edge — not a long chain.** The mechanism
is Atlas's own labeller: DeepSeek emits a **template**, `"<X> Conflict Escalation"`, and
SequenceMatcher over `russia ukraine conflict escalation` vs `us iran conflict escalation`
scores the *template*, not the story — 0.852, well clear of the 0.80 gate. Raw e5 puts two
war-escalation centroids at 0.91, well clear of 0.90. Both gates are satisfied by construction
whenever the labeller reuses a frame. This is the same failure class the 2026-07-21 country-lane
work hand-labelled as "Ukraine + Iran = two wars".

The permissive OR form of the signature (country-span **or** clash) fires **114** times across
the 15 nights — 111 span-only, 2 clash-only, 1 both — but almost all of those are span-only and
legitimate: World Cup 2026 across 20 countries, `Lottery Results` across GB/IT/ES/FR/BR. Only
the AND form isolates a real fusion, and it isolates exactly one.

`overmerge.decide()` alongside, on 07-28 (embedding coverage 97.6%):

| arm | evaluated | demote-eligible | rate | gap_ratio median |
|---|---|---|---|---|
| consolidated components (≥2 clusters) | 130 | 18 | 13.9% | 1.800 |
| singleton control | 561 | 0 | 0.0% | 1.162 |
| — components of 2–4 | 114 | 18 | 15.8% | 1.931 |
| — components of 5–9 | 13 | 0 | 0.0% | 1.174 |
| — components of 10+ | 3 | 0 | 0.0% | **0.818** |

Two honest reads. The detector **is** sighted at this operating point (most components are
2–4 clusters) and it flags 18 — though its top examples are arguable rather than clear-cut
(`Brent Oil Price Rises` + `Brent Oil Price Surpasses $100` demoted at gap 3.11; `The Odyssey
Box Office` + `The Odyssey India Box Office` demoted). And the singleton control is
**confounded by member count**: 1,089 of 1,650 singletons were skipped as too thin to evaluate,
while merged components clear `min_members` by construction, so part of the 13.9% vs 0.0% gap
is size, not fusion. Meanwhile the 10+ bucket reproduces the blindness signature exactly
(gap_ratio 0.818, below `TAU_SEP_LOW`) on 3 components — the used_t lesson holds and
`detect_overmerge`'s count must not be used as the purity control here either.

## 8 · Metric 6 — the blackout dependency (report only, not adopted)

`labels_compatible(None, None)` is False, so on a NULL-label night the rule builds **zero
edges** and consolidation silently disappears. That was accepted going in
(`SNAPSHOT_UNLABELLED` already alerts) — but §6b shows the cost is not cosmetic: it is most of
the multi-night result.

So: what would relaxing the label conjunct cost? Cosine alone at the same τ = 0.90:

| snapshot | largest component share, cos-only |
|---|---|
| 2026-07-01 … 2026-07-22 | 93.11% – 97.89% |
| **2026-07-28** | **98.28%** (1997 of 2032 clusters) |

The whole snapshot becomes one blob on **every one of the 15 nights**, and false-pair admission
goes from 0/1200 to 29–210/1200. **The label conjunct is not a refinement of this rule, it is
the entire density controller.** There is no version of this that survives a blackout. Reported;
not adopted.

## 9 · Orphans

The known 07-28 defect is confirmed: **44 clusters carry no `dynamic_topic_members` row**
(671 signals), including `Iran Accuses Ukraine of Caspian Attack` (70 signals, the largest
Caspian fragment) and `Spanyol Juara Piala Dunia 2026` (106).

They are **included** in the cluster-level analysis, because they exist in `emergent_clusters`
and that is what the consolidation pass would read. Their placement was checked, not assumed:
the orphaned Caspian fragment lands **inside** the 6-cluster Caspian component, and two of the
23 Berlin-Pride clusters are orphans that land inside the 21-cluster Berlin component. So the
defect does not distort metric 1/2/3/5/6 at all.

For metric 4 the effect is bounded and symmetric: both replay arms attach all 44 (the used_t
artifact verified the baseline arm reproduces prod's aggregate exactly — 1937 attached + 95
founded = 1893 + 95 + 44), so the *diff between arms* is unaffected. What the orphans do affect
is the comparison against **prod**: they carry no member row, so they sit outside the 1,988-row
comparison set entirely (1,988 + 44 = 2,032). The 93.81% agreement is measured on the clusters
prod did persist and says nothing about the orphans either way.

## 10 · Honest limits

- **One post-blackout labelled snapshot.** Metrics 1/3/5 are strongest on 07-28 and are
  reported per night across 14 earlier ones; the multi-night claim rests on those, and the
  earlier nights are 4–13× smaller, which is exactly what §4 shows biting K2.
- **`merge_duplicates` does not currently run in production.** `project_dynamic_topics.run()`
  calls it only under `--rebuild`, and neither cron passes it
  (`scripts/run-scoped-snapshot.sh:238` says so explicitly; `scripts/run-emergent-snapshot.sh`
  omits it). The witness artifact calls this "today's shipping rule" — it is production code
  and it is the merge rule, but it fires only on rebuild. Wiring it into every nightly
  projection **activates** the §7 fusion mode rather than inheriting it.
- **Fresh families are circular with the rule** (§3) and are excluded from every bar.
- **`GQ-05` is not scorable in-snapshot** (zero espriella clusters on 07-28) and its window
  proxy has shrunk to 4 clusters as the corpus ages out — it was 7 in the used_t run. It is
  3 topics in both arms, unchanged.
- **`identity_ok` is a strict lexical proxy**, not a semantic judgement; the ✓/✗ in §6a is
  hand-assigned and the proxy is published beside it.
- **`overmerge` members are built from cluster `sample_signal_ids`**, not `topic_members`
  (this simulation writes nothing), and its singleton control is member-count confounded (§7).
- **The clash scan inside a component is capped at 40 members.** Under the primary rule the
  largest component measured is 32, so the cap never binds; it exists so the cos-only
  diagnostic terminates. Capping can only under-count clashes, never invent one.
- **12-night replay drift is 57.2%** against prod and is *not* a defect of the comparison —
  both arms diff against each other from one identical hydration — but §6a (93.81%) is the
  configuration whose absolute labels can be trusted, and §6b's `landed on` labels differ from
  it for that reason.

## 11 · What would have to be true for a GO

The recall side of this idea is real and should not be thrown away: within a labelled snapshot
it takes 23 Berlin-Pride fragments to 3 topics at 93.1% coverage, 9 Paris fragments to 1 at
100%, and it costs the serving population 3.1% instead of `used_t`'s 55.8%. Three things stand
between that and a GO.

### 11.1 · The two kills are closable — and the obvious fix is the wrong one

The `784`-class fusion is a **labeller-template** artifact (§7), so the instinctive remedy is to
require, on top of `labels_compatible`, at least one **shared distinctive subject token** — a
token outside the top decile of that night's cluster-label df. That predicate already exists in
this harness (it is half of the 784-class signature), so it was measured before being
recommended. **It is refuted:**

| night | `conflict` | `escalation` | `berlin` | `pride` | `paris` | `knife` |
|---|---|---|---|---|---|---|
| 07-17 (1966 labels, top-decile = 196 tokens) | df 21 ✗ | df 18 ✗ | df 0 ✓ | df 0 ✓ | df 5 ✓ | df 0 ✓ |
| 07-28 (2032 labels, top-decile = 203 tokens) | df 19 ✗ | df 11 ✗ | **df 29 ✗** | **df 24 ✗** | **df 12 ✗** | **df 11 ✗** |

(✗ = inside the top decile, i.e. not "distinctive".) On 07-17 the cut works. On 07-28 it kills
Berlin Pride too — because **a big same-event family makes its own subject tokens frequent by
construction**. `berlin` has df 29 precisely *because* 23 clusters are about Berlin Pride.
Measured: `shared-distinctive("Berlin Pride Van Attack", "Berlin Pride Attack Victim")` = False
on 07-28. A df-based distinctiveness cut is anti-correlated with exactly the families it must
preserve — the same shape as the witness artifact's separation probe, one layer down.

**What does work, measured on the same 15 nights:** add `countries_share` (imported verbatim —
the same D3 conjunct the fresh-family discovery rule uses) to the conjunct.

| | primary rule | **+ shared country** |
|---|---|---|
| 784-class components, 15 nights | **1** | **0** |
| K2 passes | 12 / 15 | **14 / 15** |
| 07-01 World Cup blob | 24 (3.28% ✗) | 14 (1.92% ✓) |
| 07-17 largest | 18 (0.92%) | 9 (0.46%) |
| 07-21 largest | 32 (1.35%) | 15 (0.63%) |
| false-pair admission | 0/1200 every night | 0/1200 every night |
| `berlin pride` components | 3 | **3** |
| `fresh:us-strikes-on-iran` | 2 | **2** |
| `fresh:paris-knife-attack` | 1 | **1** |
| `fresh:russian-missile-strikes-on-kyiv` | 4 | **4** |
| `fresh:wildfires-in-france-and-spain` | 1 | **1** |
| `GQ-12 caspian` | 4 | **5** ↑ |

The Ukraine↔Iran bridge dies because RU and IR are disjoint primary countries, and five of six
witness families are untouched. **Both pre-registered kills would be closed** — only the
07-19 19:04 K2 failure survives, and §4 shows that one is 17 correctly-merged
`US Strikes on Iran` clusters on a 539-cluster night.

Two honesty conditions on that result. It was constructed **after** seeing the failure, so it is
a lead for its own pre-registered run, **not a GO** — and this run's downstream arm was not
re-executed with it. And its cost is already visible and structural: `GQ-12 caspian` goes 4 → 5,
because a genuinely **bilateral** story (Iran accusing Ukraine over a Caspian vessel) has
fragments whose country lists do not overlap. A shared-country conjunct can never merge those.

### 11.2 · Consolidation must not be scored by coverage alone

Coverage 1.000 onto "Monaco Explosion Targets Ukrainian…" is a black hole, not a fix (§6a). Any
future run needs the identity-landing column as a first-class metric and needs it to *improve*,
not merely to concentrate. Today it does not: 4/12 → 4/12 single-night, 4/13 → 2/13 over the
window.

### 11.3 · The blackout is not a side condition

Five of twelve nights contribute zero consolidation and carry 29 of Berlin Pride's 54 fragments
(§6b, §8). A second LLM provider key — already the standing NEEDS PEDRO item — is a
precondition for this measurement to mean anything over a window rather than a night.

### 11.4 · And the ordering from the used_t artifact still holds above all three

**Fix 1 first.** §6a is the clearest statement yet of why. Consolidation gives the field a
well-formed question — one super-cluster per event instead of nine — and raw e5 still answers
*Moscow* when asked about *Kyiv*. Even a perfectly clean super-cluster picks the wrong topic
two times in three. Whitening's job is to move that, and if it does not, neither `used_t` nor
cluster consolidation is the lever.

## 12 · Surprises

1. **Consolidation works and that is the problem.** Every previous attempt in this program
   failed at recall. This one succeeds at recall (23 → 3 topics, coverage 0.109 → 0.931) and
   fails at *identity*, which no pre-registered metric would have caught. Coverage and
   correctness had to be separated before the run could be read at all.
2. **The 784-class fusion is a labeller artifact, not a geometry artifact.** A direct
   Ukraine↔Iran edge at label_sim 0.852 — the template `"<X> Conflict Escalation"` scores as
   similarity. The label gate that makes this rule safe is also what makes it fuse wars.
3. **All three K2 failures are correct consolidations** (World Cup ×24, Monaco Bombing ×7, US
   Strikes on Iran ×17) on snapshots 4–13× smaller than today's. K2-as-a-share is size-
   sensitive; the kill fired on the metric's units, not on a fusion.
4. **Averaging tightens the anchor, in 100% of components** (0.981 vs 0.938). The obvious
   explanation for the weak cross-night result was wrong and had to be discarded.
5. **`merge_duplicates` has never run in the nightly path.** The rule the witness artifact
   named "today's shipping rule" is gated behind `--rebuild`, which neither cron passes
   (`scripts/run-scoped-snapshot.sh:238`). Inserting a consolidation pass into the incremental
   projection would be the first time this rule has ever fired nightly.
6. **The obvious fix for the fusion is self-defeating, and a fix nobody proposed works.**
   A df-based "distinctive token" cut kills Berlin Pride along with the three-war fusion,
   because a large family inflates its own tokens' df (§11.1). Requiring a **shared country**
   — the cheapest predicate available, already imported — takes the 784-class count to 0 and
   K2 to 14/15 while leaving five of six witness families untouched. Both remedies had to be
   measured; only the counter-intuitive one survives.
