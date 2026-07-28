# Identity by shared measured evidence — replacing centroid-and-label with an evidence overlap gate

**STATUS: CLOSED — Stage-0 gate fired NO-GO, K3 = REFUTED on all three lanes (2026-07-29).**
Measurement: `docs/research/recall-229/2026-07-29-witness-reconvergence.md`. The binding
constraint is GRAPH DENSITY, not pairwise precision: merge_duplicates runs to a fixpoint, so the
seed point's 1.4% false-pair rate = 58,106 edges = a 96.2% connected component (K2 bar: 2%).
The separation probe shows the recall cut and the safety cut never cross at any tau.
REHABILITATED BY THE SAME RUN: today's cos>=0.90 AND label>=0.80 satisfies K2 (1.13%), admits
0/1200 false pairs, and halves witness fragmentation (Caspian 9->4, Berlin Pride 22->4) — its
catastrophic failure mode was the five-day label blackout, which is already fixed
(SNAPSHOT_UNLABELLED, 22f102f5). Kept as the record of what was designed and how it died.

**Date:** 2026-07-28 · **Status:** DESIGN, nothing built · **Branch:** `eclipse-dramatic-moment`
**Predecessors (read first):**
- `docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md` — the diagnosis (shredding + absorption, one mechanism)
- `docs/research/recall-229/2026-07-28-whitened-identity-taus.md` — whitening REFUTED by a pre-registered kill rule
- `docs/superpowers/plans/2026-07-28-identity-whitening.md` — the plan whitening was killed inside

**One-line thesis.** The identity layer needs a same-story signal that **survives translation**.
Centroid cosine does not give one in any linear space we have measured (raw overlaps, whitened
destroys cross-lingual alignment). The signal that does survive is **shared measured evidence** —
the same named entities, the same URLs, the same normalized headlines appearing in both sides —
because a proper name, a link and a wire reprint are the same string in Bucharest and in Beirut.

---

## 0. Prior art this is built on (do not re-derive)

| Fact | Source | Consequence for this design |
|---|---|---|
| Raw cosine overlaps at all three identity gates | diagnosis | the gates cannot be re-fit, they need a second axis |
| Whitening: `anchor` gap −0.5471, `merge` gap −0.1173, both STOP | whitened-taus §2 | whitening is NOT the second axis; it is not used here |
| `match` (cluster↔running centroid) is the ONE gate that PROCEEDs on raw (p5 true 0.9469 vs p95 false 0.8978) — but its TRUE set is engine-selected | whitened-taus §2, §9 | **keep `MATCH_THRESHOLD=0.88`**; do not touch it in this work |
| Naive entity overlap is HARMFUL — one ubiquitous person links everything | CLAUDE.md #234 | rarity weighting is mandatory, not optional |
| `weight = 0.30 + 0.68·norm_rarity`, `norm_rarity=(1/df−1/df_max)/(1−1/df_max)` | `app/services/constellation_walk.py:480` | reuse verbatim; it is already validated on this corpus |
| Country-dominant actor overlap beats combined Jaccard (person-swamped) | `app/services/overmerge.py:305` | reuse `country_dominant_overlap` shape for the veto |
| The DeepSeek "one story or two?" judge runs at 91–93% measured precision | CLAUDE.md 2026-07-20/21 | it is the borderline confirmer, never the primary |
| `_norm_headline` already collapses masthead reprints + HTML-entity twins | `app/services/thread_ranking.py:117` | it is the headline-lane normalizer; one definition of "one headline" |

---

## 1. Problem

Three decision points in `backend/scripts/project_dynamic_topics.py` all decide "is this the same
story?" from centroid cosine, and two of them add a **label string** as the only second axis:

| # | Site | Today's rule | Measured failure |
|---|---|---|---|
| 1 | `merge_duplicates` (L472) | `cosine ≥ 0.90` **AND** `SequenceMatcher(label) ≥ 0.80` | 2/15 of the Caspian fragment pairs clear the label gate; **0** clear it during a label blackout (`labels_compatible(None,None)` is False) — merging was fully disabled 07-23→07-27 |
| 2 | `process_snapshot` attach (L511) | `cos(running) ≥ 0.88` **AND** `cos(anchor) ≥ 0.93` | the anchor guard measures **STOP in both spaces** (raw gap −0.1154, AUC 0.6166). An unrelated CO political cluster sits 0.938 from a NZ sexual-assault anchor |
| 3 | `process_snapshot` greedy 1-to-1 (`used_t`, L521) | a topic absorbs **at most one** cluster per snapshot | 8–33 fragments of one event **cannot** land on one identity in a night, by construction |

The net effect is the diagnosis's finding: the same event shreds into 8–33 clusters that never
reconverge (GQ-05 story coverage **6.4%**), while stale identities absorb unrelated stories.

**What this design is not.** It is not a re-fit of the cosine thresholds, and it is not whitening.
It adds an orthogonal, translation-surviving axis and lets the cosine axis stay where measurement
put it.

---

## 2. Entity availability — the load-bearing check (MEASURED 2026-07-28, read-only)

The design leans on `signals_v2` entity columns. NER throughput is a known constraint (#184), so
this was measured before designing, not assumed. **Five findings; two of them change the design.**

### 2.1 Two entity lanes exist, and they are complementary

`signals_v2` carries two independent entity sources:

- `persons text[]` / `organizations text[]` — **GDELT GKG only**. Measured over 953,043 signals in
  the last 7 days: `gdelt` 84.4% carry either; **`independent` / `wire` / `state` / `social` / `api`
  are 0.0% — literally zero.** These arrays are not NER output, they are GKG passthrough.
- `nlp_persons jsonb` — a **typed, multilingual** entity list `[{name, type}]` with types
  `PERSON / ORG / LOC / GPE / NORP / FAC`. 64.2% of the 7-day corpus. It is written with
  `nlp_model_version = NULL` and `nlp_processed_at = NULL`, i.e. **by the ingest path, not by the
  M1 NER fleet** (the fleet accounts for only 6,217 rows / 7d, all `en-v1`).

Neither lane alone is sufficient. Their **union** is what this design consumes.

### 2.2 Coverage by language — the Cyrillic hole is the only real gap

`nlp_persons` non-empty rate, 7-day corpus:

| lang | n | `persons[]`/`orgs[]` | `nlp_persons` |
|---|---|---|---|
| xx (GDELT, lang unknown) | 530,120 | 78.6% | 52.7% |
| en | 347,492 | 82.2% | 80.4% |
| es | 9,432 | **0.0%** | 80.5% |
| ko | 8,040 | 0.0% | 72.8% |
| pt | 7,075 | 0.0% | 79.5% |
| **ru** | 6,725 | 0.0% | **10.0%** |
| zh | 5,281 | 0.0% | 79.2% |
| de | 5,227 | 0.0% | 67.4% |
| fa | 3,899 | 0.0% | 82.0% |
| ar | 3,502 | 0.0% | 81.2% |
| fr | 2,993 | 0.0% | 86.9% |
| **uk** | 633 | 0.0% | **4.7%** |

**ru (10.0%) and uk (4.7%) are the only languages where the entity lane effectively does not
exist.** That is a named, bounded residual — and it lands squarely on the Russia-Ukraine story
family, which is one of the biggest recurring shredding cases (`Russian Missile Strikes on Ukraine`
appears three times in the whitened-taus fragment tail). Section 3.4's lane U/H exists partly for
this.

### 2.3 The witness clusters are richly covered — entities are NOT the bottleneck

Per witness family, over every `sample_signal_ids` reference:

| family | clusters | sample refs | resolvable | **carry ≥1 entity** | with URL | distinct outlets |
|---|---|---|---|---|---|---|
| Berlin Pride (22 clusters, 07-28) | 22 | 257 | 256 (99.6%) | **236 / 256 = 92.2%** | 100% | 195 |
| Caspian / Iran-Ukraine (9 clusters, 07-28) | 9 | 136 | 136 (100%) | **132 / 136 = 97.1%** | 100% | 111 |

Whole 07-28 snapshot: **2,014 of 2,032 clusters (99.1%) carry ≥1 entity**, mean **23.6 distinct
entities per cluster**, 31,197 distinct entities, **84% at df=1**, `df_max = 383`, df p50 = 1,
p99 = 9.

**Verdict on the availability question: entity coverage is sufficient. The design proceeds on
entities as lane E.** Lanes U and H (§3.4) are not a fallback for thin coverage — they are a
fallback for the ru/uk hole and for cross-script name mismatch (§2.5).

### 2.4 🔴 FINDING THAT CHANGES THE DESIGN — evidence evaporates in ~8 days

`sample_signal_ids` resolvability against `signals_v2`, by snapshot day (measured today, 07-28):

| snapshot day | clusters | sample refs | resolvable | **% resolvable** |
|---|---|---|---|---|
| 2026-07-28 | 2,032 | 24,192 | 23,599 | **97.5%** |
| 2026-07-27 | 3,475 | 42,159 | 34,784 | 82.5% |
| 2026-07-26 | 3,593 | 43,704 | 30,516 | 69.8% |
| 2026-07-25 | 3,854 | 46,765 | 27,131 | 58.0% |
| 2026-07-24 | 2,395 | 29,086 | 13,567 | 46.6% |
| 2026-07-23 | 2,190 | 26,455 | 8,199 | 31.0% |
| 2026-07-22 | 2,517 | 30,124 | 4,943 | 16.4% |
| 2026-07-21 and older | 7,199 | 86,998 | **0** | **0.0%** |

Direct consequence on the named false-absorption witnesses:

| witness | founding anchor cluster | resolvable sample signals |
|---|---|---|
| topic 784 anchor (07-01, "Cabo Verde Captain Rape Allegations") | `ec 2036` | **0 / 10** |
| topic 52 anchor (06-03, "Trump Endorses De la Espriella") | `ec 133` | **0 / 24** |
| topic 52, 24 of its 30 member clusters | ≤ 07-22 | **0** |

**This is the single most important structural fact in this document.** An evidence gate cannot be
implemented as a live query against `signals_v2`, because:

- **same-snapshot** comparisons (fragment ↔ fragment, tonight) have 97.5% evidence available → a
  live query works **today**;
- **cross-day** comparisons (tonight's cluster ↔ an old topic's frozen anchor) have **0%** evidence
  beyond ~8 days → the anchor guard and topic↔topic merge have **nothing to compare against**.

Therefore the design **must materialise an evidence fingerprint at snapshot-write time**
(migration 092, §3.2), and the anchor/merge lanes carry an unavoidable **cold start** of one
fingerprint-retention window. Stage ordering in §6 follows from exactly this.

### 2.5 Honest limits of the entity lane

- **Entity names are stored in the source language.** Sampled live: `"ایران"` (fa),
  `"Kilimanjaro"`/`"África"` (es), `"حماس"` (fa). A Persian and a Romanian report of the same event
  share the *event*, not necessarily the *string*. Latin-script proper nouns
  (`"Edmundo González"`) do survive; Cyrillic/Arabic/CJK renderings of the same name do not match
  their Latin form. **Lane E is therefore biased toward Latin-script and toward proper nouns.**
- **`nlp_persons` is noisy.** Sampled: `{"name":"sustraer L.190","type":"PERSON"}`,
  `{"name":"Policía","type":"GPE"}`. Noise inflates df for junk strings and adds spurious low-df
  singletons. M3 must measure the noise floor before setting the rarity gate.
- **`sample_signal_ids` is capped at 24.** Measured on 07-28: only **4.1%** of clusters are
  truncated, and 24,192 / 25,122 = **96.3%** of clustered signals are inside the sample. The
  fingerprint is a near-complete, not complete, view of membership. Report this; do not hide it.
- **GQ-05 caveat.** `%espriella%` = 651 signals in 7 days but only **7** clusters touch them via
  `sample_signal_ids`. The diagnosis's "33 fragments" was measured from the offline clustering run,
  not from persisted samples. M1 must reconstruct the GQ-05 witness from the offline run, not from
  `emergent_clusters` alone, or it will measure a different object.

---

## 3. Design

### 3.1 The signal: `EvidenceOverlap`, three lanes, one number

A pure function over two **evidence fingerprints**, mirroring `overmerge.py`'s posture (pure numpy /
stdlib, deterministic, unit-tested with zero DB; the script does the I/O).

```
lane E  entities   union of persons[] ∪ organizations[] ∪ nlp_persons[].name,
                   lowercased + unaccented, rarity-weighted by snapshot-wide df
lane U  locators   exact source_url (a literal reprint) and registrable domain
lane H  headlines  _norm_headline(headline) keys — the SAME normalizer thread_ranking
                   uses for syndication, so "one headline" has one definition
```

`evidence_overlap(a, b) -> EvidenceOverlap` returns, per lane, the shared set, its size, and the
**rarest** shared item's `norm_rarity` — plus one scalar:

```
strength = max( w_E · max_norm_rarity(shared entities),
                w_U · locator_score,
                w_H · max_norm_rarity(shared headline keys) )
```

Taking the **max over lanes**, not the sum, is deliberate and inherits
`country_dominant_overlap`'s lesson: two signals that each independently prove sameness must not
dilute each other. Taking the **rarest** shared item within a lane inherits `actor_edge_weight`:
one distinctive actor carries the link; a ubiquitous one (df 383 today) cannot launder it.

`w_E / w_U / w_H` and the rarity gate are **set by M3**, not guessed here.

### 3.2 Where the fingerprint lives — migration 092

`emergent_clusters` has no entity column and `signals_v2` is 7-day hot (§2.4), so:

```
092_evidence_fingerprints.sql   (RLS + 082-style revokes, per the project rule)

cluster_evidence_fingerprints
  emergent_cluster_id  bigint PK REFERENCES emergent_clusters(id) ON DELETE CASCADE
  snapshot_at          timestamptz NOT NULL
  entities             text[]        -- normalized, deduped
  entity_dfs           int[]         -- parallel; df AS OF this snapshot (frozen)
  domains              text[]
  url_keys             text[]        -- hashed exact URLs, bounded
  headline_keys        text[]        -- _norm_headline output, bounded
  n_signals_seen       int           -- how many sample signals actually resolved
  built_at             timestamptz
  GIN on entities, headline_keys, domains

topic_evidence_fingerprints
  dynamic_topic_id     bigint  REFERENCES dynamic_topics(id) ON DELETE CASCADE
  kind                 text CHECK (kind IN ('anchor','rolling'))   -- PK (topic, kind)
  entities/domains/url_keys/headline_keys   text[]
  n_clusters           int
  updated_at           timestamptz

dynamic_topic_members
  + reason_code  text     -- why this cluster attached (never NULL going forward)
  + evidence     jsonb    -- the receipt: which shared items, which lane, which rarity

identity_absorption_ledger
  run_id, dynamic_topic_id, emergent_cluster_id, action, reason_code,
  evidence jsonb, created_at        -- the reversibility spine (§5.3)
```

**Freezing `entity_dfs` at build time is load-bearing.** df is a property of the night's field; a
fingerprint compared six weeks later must carry the rarity it had when it was written, or the
rarity gate silently drifts.

`topic_evidence_fingerprints` has exactly two rows per topic, mirroring `anchor_centroid` vs the
running centroid:

- **`anchor`** — written once at founding from the founding cluster's fingerprint. **Never updated.**
  This is the black-hole cure: topic 784's anchor is a Cape Verde ship captain; a Bolivian
  recruitment cluster shares none of its entities, its domains, or its headline keys.
- **`rolling`** — union over the last `ROLL_K` snapshots the topic was seen, bounded by size. This
  is what lets a legitimately evolving story keep attaching as its cast changes (the Ukraine-war
  case that killed the label-instability guard, `project_dynamic_topics.py:54`).

### 3.3 The three decision points

#### DP-1 — `merge_duplicates`: replace the label gate with an evidence gate

```
today:      cosine(a,b) >= 0.90   AND   SequenceMatcher(label) >= 0.80
proposed:   cosine(a,b) >= MERGE_TAU_COS   AND   evidence_overlap(a,b).strength >= MERGE_TAU_EVID
            [borderline band -> judge; judge unavailable -> DO NOT MERGE]
```

The cosine term **stays**. It is not being replaced — the evidence term replaces the *label* term.
This is not a style choice; it is forced by measurement (§4, M2 preview):

> Over the 07-28 snapshot, **8.7%** of random dissimilar-label cluster pairs share ≥1 entity.
> `merge_duplicates` runs to a fixpoint, so merging is **transitively closed** — an 8.7%-density
> edge set collapses the entire snapshot into one component almost surely. **Entity overlap alone
> is not a merge gate.** It is only safe as a conjunct with cosine.

Measured seed (07-28, Berlin Pride as the true witness, 406 dissimilar-label random pairs as false):

| rule | BP components (22 clusters) | BP pairs admitted | false pairs admitted |
|---|---|---|---|
| `cos ≥ 0.90` (today's cosine term) | 1 | 77 / 231 | 20 / 406 = **4.9%** |
| `cos ≥ 0.90 AND ent ≥ 1` | **3** ✗ | 37 / 231 | 3 / 406 = 0.7% |
| **`cos ≥ 0.86 AND ent ≥ 1`** | **1** ✓ | 73 / 231 | 11 / 406 = **2.7%** |
| `cos ≥ 0.82 AND ent ≥ 2` | 7 ✗ | 33 / 231 | 7 / 406 = 1.7% |
| entity ≥ 1, no cosine | 1 | 94 / 231 | 35 / 406 = 8.7% ✗ |

Caspian (9 clusters) reaches 1 component under every rule tested — it is the easy witness.

The `cos ≥ 0.86 AND ent ≥ 1` row is the interesting one: **it reconverges the hardest witness to one
identity while roughly halving the false-pair admission rate of today's cosine gate.** That is a
strict two-axis improvement, which is what an orthogonal signal is supposed to buy.

`0.86` and `≥1` are **seeds from one night and one family. M1/M2 set the operating point.** They are
written here so the reader can judge whether the direction is worth building, not as the answer.

Additional DP-1 rules:
- **Roundup exclusion stays** (`left.is_roundup or right.is_roundup -> skip`) — unchanged.
- **A missing fingerprint on either side falls back to today's exact behaviour** (cosine + label),
  counted in `merge.fingerprint_missing`, never to "merge freely".
- **Labels are not discarded.** `labels_compatible` becomes a *third* corroborator that can carry a
  pair through the borderline band without a judge call — it is demoted from gate to evidence.

#### DP-2 — `process_snapshot`: replace the anchor guard with an anchor-evidence guard

```
today:      cos(c, t.centroid) >= 0.88   AND   cos(c, t.anchor_centroid) >= 0.93
proposed:   cos(c, t.centroid) >= 0.88   AND   anchor_evidence_ok(c, t)

anchor_evidence_ok(c, t) :=
      evidence_overlap(c, t.fingerprint['anchor']).strength  >= ANCHOR_TAU_EVID
   OR evidence_overlap(c, t.fingerprint['rolling']).strength >= ROLL_TAU_EVID
```

`MATCH_THRESHOLD = 0.88` **stays** — it is the one gate the whitened-taus harness returned PROCEED
for on raw (p5 true 0.9469 vs p95 false 0.8978, only 0.07% of false pairs above p5 true).

`ANCHOR_THRESHOLD = 0.93` **goes**. It measures STOP in raw *and* whitened space; 67.9% of the
harness's false pairs sit above p5(true). It is not a guard, it is noise with a number on it. The
witness table makes the replacement's case directly: every topic-784 absorption (Bolivian
recruitment, CO assassination plot, four unlabelled CO clusters) clears 0.93 on cosine and shares
**nothing** with a New Zealand Cape Verde-captain anchor on any evidence lane.

Two lanes, not one, because the anchor lane alone is too strict for a story whose cast turns over
(a war, a long election). The `rolling` lane is the concession; `ROLL_K` is the knob that decides
how much drift is tolerated, and **M5 sets it**.

**Fallback discipline:** a topic with no persisted anchor fingerprint (every topic founded before
mig 092) falls back to today's `ANCHOR_THRESHOLD = 0.93` and is counted in
`attach.fingerprint_missing`. The gate improves as fingerprints accumulate; it never silently opens.

#### DP-3 — drop `used_t`, add a real absorption guard

Dropping `used_t` is **required** for reconvergence — 22 Berlin Pride fragments cannot land on one
identity under 1-to-1 matching, at any threshold. It is also the change the diagnosis explicitly
warns will make black holes worse if shipped alone. Four guards, in order:

**(a) Frozen scoring — the anti-chaining rule.** All candidate (cluster, topic) scores are computed
against the topic's centroid and fingerprints **as they stood at the start of the snapshot**.
Attaching cluster #1 must not widen what cluster #2 is allowed to clear. This is `score-then-attach`,
not `attach-then-score`, and it is the mechanism that stops a single night's absorption from
walking a topic across the field. `used_c` **stays** (one topic per cluster).

**(b) Per-snapshot absorption cap.** `MAX_ABSORB_PER_TOPIC` and `MAX_ABSORB_SHARE` (fraction of the
snapshot's clusters one topic may take). Note the cap must be **generous** — Berlin Pride legitimately
needs 22 — so it is a blast-radius limiter, not the real brake. **M2 sets both** from the observed
distribution of per-topic absorption counts, not from intuition.

**(c) Post-absorption multimodality split — the real brake.** After the night's absorption set is
chosen, run the **existing** `overmerge.split_stats` over the absorbed clusters' centroids. If the
set is itself a balanced, wide-gap fusion (`gap_ratio ≥ tau_sep`, `balance ≥ tau_bal`, and the
country-dominant actor overlap does **not** veto), the absorption is **split**: the topic keeps the
sub-cluster containing the highest-scoring cluster; the other side is founded as a **new topic**,
reason-coded. This reuses the module that already runs at 91–93% measured precision, at the moment
where it is cheapest to act.

**(d) Country-dominance veto reuse.** `country_dominant_overlap` over the absorption set's member
countries, exactly as the over-merge detector uses it, so a single-country story's halves are never
split apart by (c).

The **DeepSeek judge confirms (c)** in the borderline band only, with the same precision-first
polarity as `apply_judge_verdict`: `one_story -> keep merged`, `two_stories -> split`,
`unavailable/unparseable -> keep merged and reason-code the absence` (splitting on infrastructure
state would manufacture identities).

### 3.4 Why three lanes and not just entities

Lane E has two named holes (§2.2, §2.5): **ru 10.0% / uk 4.7% coverage**, and source-language entity
strings that do not match across scripts. Lanes U and H cover exactly those:

- **Lane U (locators)** is script-blind by construction. A wire story reprinted by a Romanian and an
  Arabic outlet often carries the same origin URL or the same agency domain. It is the strongest
  possible same-story evidence when it fires (a literal identical link is not a coincidence) and it
  is the lane with the **best data**: `source_url` and `source_name` are **100% populated** across
  the whole 7-day corpus and both witness families.
- **Lane H (normalized headlines)** catches syndication that lane U misses because each masthead
  rewrote the URL. `_norm_headline` already strips the masthead suffix and HTML-entity twins.

Lane U's honest weakness: domain-level crossover is weak evidence (two clusters both containing a
Reuters item prove nothing) — so **only exact-URL and low-df domains count**, rarity-weighted like
everything else. M3 measures whether the domain half of lane U is worth keeping at all; if it is
not, delete it rather than leave it decorative.

---

## 4. Measurements to run

Every threshold named above is a seed. Each of these produces a dated artifact under
`docs/research/recall-229/`. Read-only unless stated. Run on the M1 `mlvenv`.

| # | Measures | Script | Artifact |
|---|---|---|---|
| **M0** | Fingerprint build feasibility + coverage: per-cluster entity/domain/headline-key counts over the whole latest snapshot; empty-fingerprint rate; build wall-clock; per-language coverage inside witness clusters | `backend/scripts/measure_evidence_fingerprint.py --coverage` | `2026-07-29-evidence-fingerprint-coverage.md` |
| **M1** | **Witness reconvergence sweep (primary).** Connected components per witness family over a grid of `(MERGE_TAU_COS × lane × rarity gate)`. Families: Caspian (9), Berlin Pride (22), GQ-05 (33, reconstructed from the offline clustering run — see §2.5), plus ≥3 new families discovered by the same label-similarity rule the whitened-taus harness used, so the fit is not overfit to three exhibits | `measure_evidence_fingerprint.py --sweep` | `2026-07-29-witness-reconvergence.md` |
| **M2** | **False-side density at each M1 operating point.** Whole-snapshot merge-edge count, the largest connected component as a share of all topics, and the shared-entity rate on the same mechanical FALSE construction the whitened-taus harness used (disjoint countries + dissimilar labels). This is the run that says which M1 winners are actually safe | `measure_evidence_fingerprint.py --false-density` | `2026-07-29-evidence-false-density.md` |
| **M3** | **Rarity calibration.** df distribution per lane over ≥7 snapshots; `df_max` choice; the `nlp_persons` noise floor (what share of df=1 entities are NER garbage — hand-label 200); whether the domain half of lane U discriminates at all; fit `w_E/w_U/w_H` | `backend/scripts/calibrate_evidence_rarity.py` | `2026-07-30-evidence-rarity-calibration.md` |
| **M4** | Fingerprint-persistence sizing: the resolvability decay curve (the §2.4 table, re-run as a script), retention interaction, storage estimate, and the resulting **cold-start length** for DP-1/DP-2 | `measure_evidence_fingerprint.py --retention` | folded into M0's artifact |
| **M5** | **Anchor-evidence guard on the false witnesses + `ROLL_K` fit.** ⚠ **NOT MEASURABLE TODAY** — topic 784's and topic 52's anchor evidence is gone (0/10 and 0/24 resolvable). This measurement is **gated on ≥14 nights of accumulated fingerprints** and on a fresh set of false-absorption witnesses harvested from `detect_overmerge` demotions during that window | `backend/scripts/measure_anchor_evidence.py` | `2026-08-1x-anchor-evidence-guard.md` |
| **M6** | Judge volume + cost dry-run: how many pairs land in the borderline band per night at the M2-selected operating point; token estimate; valley-window placement | `measure_evidence_fingerprint.py --judge-dryrun` | folded into M2's artifact |
| **M7** | **Shadow A/B.** The new identity layer under `--engine-version identity-v2` writing to a shadow topic namespace for ≥7 nights; compared against production on every §5 metric | `backend/scripts/identity_ab_report.py` | `2026-08-xx-identity-v2-ab.md` |

**M1 and M2 must be run by the same script in the same pass**, so no operating point can be chosen
on recall evidence without its false-side number in the same table.

---

## 5. Pre-registered success metrics and kill rules

**Written before any code. No threshold below is tuned after seeing a downstream outcome.**

### 5.1 Success metrics (inherited from the diagnosis, unchanged)

| Metric | Baseline | Target |
|---|---|---|
| **Primary — GQ-05 story coverage** (story signals in ONE persisted topic / story signals in corpus) | **6.4%** (38/598, largest topic 13) | **≥ 50%** |
| **Fragments per event** | 33 (GQ-05), 22 (Berlin Pride), 9 (Caspian) | **≤ 3**, all three |
| **New false absorptions** (topics whose absorbed clusters span ≥3 unrelated primary countries under a court-failed label) | 784 (NZ→BO→CO), 52 (CR→MX→DO→CO) | **0 new** |
| **Purity control — `detect_overmerge` demote count** next nightly | **187** | **no spike** (see 5.2) |
| Confounder | — | the measurement snapshot must have **0% NULL-label rate**, else the run is **VOID** |

### 5.2 Kill rules

**K1 — the falsifier (inherited).** If `detect_overmerge`'s nightly demote count rises **> 1.5×
baseline (187 → 281)** in the first two nights after any stage lands, that stage is **reverted**.
`detect_overmerge` is deliberately left untouched by this work (§7) precisely so it remains a valid
control.

**K2 — transitive collapse.** At any candidate operating point, if the **largest connected component
of the merge graph over a whole snapshot exceeds 2% of that snapshot's topics**, that operating point
is rejected. (Context: an 8.7% edge density collapses the field; today's per-family components are
9 and 22 out of ~2,000 clusters, i.e. ~1%.)

**K3 — the entity-signal kill rule (new, this design's own).**

> Run M1/M2 jointly. Take the set of operating points that satisfy **K2**. If, over that set, **no
> operating point brings ≥ 2 of the 3 named witness families to ≤ 3 components**, then **lane E is
> insufficient as the primary signal.**
>
> Escalation, in order, each with the same K2 constraint:
> 1. Re-run M1 with **lane U (locators) as primary** and E/H as corroborators. Locator data is 100%
>    populated and script-blind — if the failure is cross-script name mismatch, U rescues it.
> 2. Re-run M1 with **lane H (normalized headlines) as primary**.
> 3. If **all three lanes fail K3**, the entity-overlap direction is **REFUTED**, this spec is closed
>    like the attention-coverage-divergence spec was, and the honest conclusion is recorded: *the
>    same event's fragments carry no shared surface evidence, so reconvergence cannot happen at the
>    identity layer and must be attacked at clustering time* (`min_cluster_size`, scoped passes) —
>    which is a different program with a different spec.
>
> **No fourth attempt. No threshold relaxation after seeing the result.** The whitening measurement
> earned its credibility by having exactly this shape; this one inherits it.

**K4 — cold-start honesty.** DP-2 and DP-1's cross-day half **must not be enabled** until
`topic_evidence_fingerprints` covers ≥ 80% of active topics. Until then they run in the documented
fallback (§3.3), and the fallback rate is published in the nightly ledger. Enabling a gate that has
no data to gate on is how `_INFO_DESERT_FLOOR=40` happened.

**K5 — GQ-05 primary.** If after Stage 3 the primary metric has not moved above **25%** (half the
target), stop and re-diagnose rather than tuning further.

---

## 6. Staged build order — with an explicit go/no-go between every stage

### Stage 0 — Measure (no code that writes anything)
Build `measure_evidence_fingerprint.py` + `calibrate_evidence_rarity.py`. Run **M0, M1, M2, M3, M4,
M6**. Produce the artifacts.

> **GO/NO-GO 0:** K3 must not fire. An operating point must exist that satisfies K2 **and** brings
> ≥2 of 3 witness families to ≤3 components. Its `(MERGE_TAU_COS, lane, rarity gate)` values are
> **frozen into the plan** before Stage 1 begins.
> **NO-GO ⇒ escalate per K3, or close the spec.**

### Stage 1 — Fingerprints (write-only, gates nothing)
Migration 092. `build_evidence_fingerprints.py`, wired into the nightly **immediately after the
snapshot write, before signals age out**. Backfill as far as the resolvability curve allows (≈8
days, §2.4). Nothing reads the fingerprints yet.

> **GO/NO-GO 1:** fingerprint coverage of new clusters ≥ 95%; build wall-clock inside budget (§8);
> zero change to any serving metric; `detect_overmerge` baseline unmoved (nothing is gated yet, so
> any movement means the writer has a side effect).

### Stage 2 — DP-1, same-snapshot only (the cheapest real win)
Swap the label gate for the evidence gate in `merge_duplicates`, **restricted to topics whose
clusters come from within the fingerprint window**. Same-snapshot fragment merging is where
evidence is 97.5% available (§2.4) and where the witness families live. Reason codes + ledger from
day one. Kill-switch `ATLAS_IDENTITY_EVIDENCE_MERGE=off`.

> **GO/NO-GO 2:** fragments-per-event ≤3 on ≥2 witness families **in production**; K1 not fired
> after two nights; K2 holds on the live merge graph; `merge.fingerprint_missing` published and
> falling.

### Stage 3 — DP-3, `used_t` removal with the absorption guard
Drop `used_t`; add frozen scoring (a), caps (b), the post-absorption multimodality split (c), the
country veto (d), the borderline judge. This is the change that moves the **primary metric** —
and the change most able to manufacture black holes, which is why it lands only on top of a
merge gate already proven in production.

> **GO/NO-GO 3:** **primary metric (GQ-05 story coverage) ≥ 25%** and rising; **0 new false
> absorptions** by the diagnosis's definition; K1 not fired. **K5 applies here.**

### Stage 4 — DP-2, the anchor-evidence guard
Only after **M5** is measurable (≥14 nights of fingerprints, ≥80% active-topic coverage per K4) and
a fresh false-absorption witness set has been harvested. Replace `ANCHOR_THRESHOLD` with
`anchor_evidence_ok`. Fit `ROLL_K` on M5.

> **GO/NO-GO 4:** on the fresh witness set, the anchor-evidence guard rejects the absorptions the
> 0.93 cosine guard admitted, **without** rejecting the continuations it correctly admitted
> (Russia-Ukraine class, anchor cosine 0.94–0.97). If it cannot do both, **ship neither** — keep
> 0.93 and record the negative result.

### Stage 5 — A/B and cutover
M7 shadow run ≥7 nights, then a single reversible env flip, per the project's standing cutover
pattern (`ATLAS_TOPIC_MEMBERS_ENGINE_VERSION` precedent).

---

## 7. Boundaries — what this design does NOT touch

- **HDBSCAN parameters, `min_kept`, the precision gate.** The diagnosis explicitly rejects loosening
  them ("accounts for only 5.4% of GQ-05's loss and would multiply fragments rather than unify
  them"). Untouched.
- **Whitening.** REFUTED for identity by a pre-registered kill rule. It stays exactly where it is
  (HDBSCAN input, default-off). This design does not resurrect it and does not re-litigate it.
- **`MATCH_THRESHOLD = 0.88`.** Measured PROCEED. Not re-fit.
- **`detect_overmerge` / `app/services/overmerge.py` decision logic.** It is the **falsifier** (K1).
  Its thresholds and its nightly behaviour must stay unchanged for its demote count to remain a
  valid control. This design *calls* `split_stats` / `country_dominant_overlap`; it does not modify
  them.
- **The serving layer.** `/threads`, `rank_threads`, the daily edition, the Brief, the universe
  field, eclipse. Nothing here changes what is served except through the identities themselves.
- **The label court, `relabel_court_failed`, `flag_junk_topics`, the umbrella layer
  (`build_umbrella_topics`).** Orthogonal.
- **NER throughput (#184).** This design consumes whatever entity coverage exists and publishes the
  gap (ru 10.0% / uk 4.7%); it does not try to fix the fleet.
- **`PROVIDER_EXHAUSTED` handling.** Already fixed 07-27 (non-zero exit + ledger line). This design
  **inherits** it and adds one rule: a snapshot whose fingerprints failed to build is treated the
  same way — loud, non-zero, never a silent gate bypass.

---

## 8. Cost and latency budget

The nightly `run-scoped-snapshot.sh` already runs ~6h (22:00→03:54) and straddles both DeepSeek
peak windows. This design must not extend it materially.

| Component | Budget | Basis |
|---|---|---|
| Fingerprint build (Stage 1) | **≤ 120 s** per snapshot | pure SQL over ~24k sample signals; the equivalent extraction ran interactively in seconds during this design's measurement |
| Evidence overlap in `merge_duplicates` | **≤ +10%** on the projection step | set intersection over ~24 entities/cluster; the pairwise loop is already O(n²) on cosine |
| Evidence overlap in `process_snapshot` | **≤ +10%** on the projection step | same, plus two fingerprint lookups per candidate pair |
| Storage (mig 092) | **≤ 200 MB** steady state | ~3.5k clusters/night × ~50 short strings × 30-day retention; measured in M0 |
| **DeepSeek judge — hard cap** | **150 calls per nightly run** | scale precedent: `detect_overmerge` flags 26 from 540 court-failed. At ~700 tokens/call ≈ 105k tokens/night |
| Judge placement | **UTC valley** (local 00:20–00:50 window, per the 07-27 peak/valley work) | the LLM *step* moves, not the job |

Judge exhaustion behaviour: `None` verdict → the **conservative** side of each decision
(DP-1: do not merge; DP-3: keep merged, do not split) → a `PROVIDER_EXHAUSTED` ledger line → non-zero
exit. Never a silent degrade.

---

## 9. Honesty rails

1. **No silent filtering.** Every attach, merge and split writes `dynamic_topic_members.reason_code`
   and `evidence` jsonb. Reason codes are a closed vocabulary:
   `evidence:entity/<rarest-entity>`, `evidence:url`, `evidence:headline`, `evidence:label-corroborated`,
   `judge:one_story`, `judge:two_stories`, `judge:unavailable-kept`, `split:multimodal`,
   `veto:country-dominant`, `centroid-only:no-fingerprint`, `cap:absorption-limit`.
2. **The judge's verdicts are logged with receipts** — the exact headlines and shared evidence items
   shown to it, alongside the verdict, in the absorption ledger. A verdict without its prompt inputs
   is not auditable.
3. **Reversibility.** `identity_absorption_ledger` + `--revert RUN_ID` on every write path,
   mirroring `detect_overmerge --revert m4-...`: detach the members added by that run, re-found the
   clusters that were split off, restore the prior `state`. **Never delete.** Every stage ships with
   its own env kill-switch.
4. **Absence is a state, not a zero.** `fingerprint_missing`, `entities_missing`, `judge_unavailable`
   and `signals_unresolvable` are **counted and published** in the nightly summary. A gate that
   cannot see its evidence says so; it does not pass silently, and it does not report a fabricated
   pass.
5. **The residuals stay written down**, not quietly dropped: the ru/uk entity hole (10.0% / 4.7%),
   the source-language entity-string bias, the 24-signal sample cap (4.1% of clusters truncated),
   and the DP-2 cold start.
6. **Every threshold that ships carries its measurement's artifact path in a code comment**, in the
   house style of `overmerge.py`'s constant block and `project_dynamic_topics.py:40-57`.

---

## 10. Open questions the measurements must settle (not decided here)

1. Does lane U's **domain** half discriminate at all, or is only exact-URL worth keeping? (M3)
2. What is the `nlp_persons` noise floor, and does NER garbage at df=1 poison the rarity gate? (M3)
3. Is `ROLL_K` a snapshot count or a time window, and does the rolling lane re-open the black hole
   the anchor lane closes? (M5 — **the single biggest unknown**, and unmeasurable for ~2 weeks)
4. Should the post-absorption split (DP-3c) re-found the minority side as a **new** topic or return
   its clusters to the unmatched pool for normal founding? (Stage 3 design detail; the ledger must
   support both.)
5. Does the 24-signal sample cap materially weaken fingerprints for the 4.1% of large clusters, and
   is `raw_sample_ids` a usable supplement? (M0)
