# Sibling-finder v2 — pre-registered measurement

**Date:** 2026-07-29 · **Branch:** `eclipse-dramatic-moment` · **Read-only** (`SET default_transaction_read_only = on` on every connection; zero writes, `backend/app/` untouched)
**Harness:** `backend/scripts/measure_sibling_finder_v2.py` (not committed) · **Machine summary:** `2026-07-29-sibling-finder-v2-measurement.json`
**Pre-registration:** `docs/superpowers/specs/2026-07-29-sibling-finder-v2-preregistration.md` — gates G1/G2/G3/K1 frozen there, untouched here
**Trigger:** `docs/research/gold/2026-07-29-story-lens-navloss-check.md` (the Story Lens T11 NO-GO)

---

> ## ⛔ VERDICT: **K1 fires — NO-GO. The identity layer heals first.**
>
> | gate | result |
> |---|---|
> | **G1** recall on witnesses | **FAIL** — 2 of 3 eligible gate families reach ≥3 true fragments in a top-8. **Post-hoc ceiling: 0 of 163 operating points, v1 included, reaches 3 of 3.** |
> | **G2** false-neighbor rate | **FAIL, by 15×** — **30 of 50** hand-judged rows are an unrelated story presented as kin (27 unrelated + 3 unsure). Gate allows ≤2. |
> | **G3** blob honesty | **flagger OVER-FIRES** — 6 of 11 (54.5%) G1 true-positive siblings carry `is_blob`. Reported, not tuned. Field-wide base rate is **61.25%** (626 of 1022 active topics). |
>
> **The union bought nothing.** All 50 G2 rows were already reachable by lane C alone; lanes E and G introduced **zero** new rows into any random anchor's top-5. v2's top-5 overlaps v1's by **4.3 of 5** on average. On the gate families v2 ties v1 on two and is **worse** on the third.
>
> **And the pre-registration's stated baseline is wrong.** "v1 places 0" was measured from `dynamic-topic-466`, which this run proves is **not a Berlin Pride topic at all**. Anchored on a real fragment, **v1 already places 6 of 6** true Berlin Pride fragments in its top-8.

---

## 0. Every operational choice, frozen before the gates were scored

The pre-registration froze the gates and left lane parameters and scoring form open. Each choice below was made and written down before any gate family or G2 row was scored.

| # | choice | value | why (measured, not assumed) |
|---|---|---|---|
| C1 | Universe | `story.py::_TOPICS_SQL` verbatim — `state='active' AND NOT is_umbrella AND centroid_vec IS NOT NULL` | the sibling finder's own serving contract. **1,022 topics.** |
| C2 | Member scoping | `story.py::_COUNTRIES_SQL` verbatim — `role='evidence'`, `engine_version='v1-compat'`, `quarantined IS NOT TRUE`, 7-day window | the 2026-07-27 `SNAPSHOT_UNLABELLED` class was exactly this scoping done differently in two places. **17,805 rows / 1,014 topics.** |
| C3 | Whitening | the ONE global `app/data/e5_whitening.npz` (k=1, fit_n 99,871) | spec §2.2 — never a per-request refit. |
| C4 | Walk params | `WalkParams()` LOCKED defaults, **not** `from_env()` | env drift must not move a gate. k=6, rel_floor 0.35, hop_cap 3, dedup_tau 0.85. |
| C5 | Lane E vocabulary | GDELT `persons[]` ∪ `nlp_persons[].name`; **`organizations[]` excluded** | measured 80.7% garbage at df=1 (`2026-07-30-evidence-rarity-calibration.md`). |
| C6 | Lane E junk filter | `dossier._is_clean_actor` (gazetteer + geo-token guard), reused not re-derived | drops `reuters`, `marea neagra`. Vocabulary 12,570 → **8,663**. |
| C7 | Lane E rarity gate | df ≤ `_distinctive_df_max(1022)` = **3**, swept 2/3/5 **and a relaxed 10** | df here = document-frequency with the ACTIVE TOPIC as document. By construction a *shared* entity has df ≥ 2, so df=1 garbage cannot create an edge. |
| C8 | Lane E score | `constellation_walk.actor_edge_weight` verbatim (`0.30 + 0.68·norm_rarity`, over the rarest shared actor), `df_max`=136 observed | the #234 LOCKED formula, reused. |
| C9 | Lane G membership | anchor's **primary** country ∈ candidate's country footprint (top-3 with a 10% share floor) | a superset of "same primary country", chosen for recall. Recorded as the looser reading. |
| C10 | Lane G time axis | **daily evidence histogram**, not `first_seen`/`last_seen` | **measured:** 1,007 of 1,022 active topics share the SAME `last_seen` (tonight's snapshot), and a long-lived anchor's `first_seen` predates its own fresh fragments by weeks. `first_seen`/`last_seen` cannot express "these were active together"; the histogram can. |
| C11 | Lane G score | country Jaccard × day-histogram overlap, both ∈ [0,1]; peak-day gap ≤ 2 days (the "±48h") | bounded and commensurate; floors swept at 0.00 / 0.15. |
| C12 | Union forms | `max`, `sum`, **`rrf`** (reciprocal rank fusion, k₀=60) all swept | **the lanes are not on a common scale.** A df=2 shared actor maxes at 0.637 — *below* the 0.853 cosine of the gate's marquee false neighbor — so a naive `max` can never let lane E outrank a false cosine neighbor. RRF is the scale-free answer and is swept alongside the naive forms rather than assumed. |
| C13 | Lane C fold | swept both — dedup ON (as shipped) and OFF | on a shredded field the 0.85 display fold suppresses exactly the fragments the lens exists to show; measured rather than argued. |
| C14 | Grid completeness | two **pure-lane-C** reference ops included | so the selection rule *could* have chosen "just remove the fold" if that were the whole win. It did not; but the rule had to be able to. |

**Grid: 163 operating points** (162 + the v1 baseline).

### 0a. Two recorded corrections

**(i) The pre-written selection constraint was unsatisfiable and was discarded.** The harness shipped with `mech_false_rate ≤ 0.04` as an operating-point filter. The v1 baseline *itself* measures **0.62** on that proxy, so the number was never a threshold on that scale — it was the G2 gate's units applied to a different instrument. Discarded and replaced, **before scoring**, with a purely relative lexicographic rule:

> (1) max DEV families passing → (2) max DEV true-in-top-8 total → (3) min mechanical-false rate → (4) simplest op (fewest active lanes, then `max` < `sum` < `rrf`, then dedup **as shipped** before the changed behaviour).

The mechanical proxy (`different_story`: same script, label-sim < 0.35, zero shared distinctive tokens — the whitened-taus construction v1 rule, verbatim) is kept only as a **relative** comparator. **No frozen gate moved.**

**(ii) A reproducibility defect was found and fixed mid-run.** Lane E is nearly all ties (every df=2 shared actor scores exactly 0.637). The per-lane rank ordering that RRF consumes fell back to dict insertion order, which for lane E derives from set iteration over interned strings and is therefore `PYTHONHASHSEED`-dependent. Caught by an unreproducible `mech_false_rate` (0.6367 vs 0.6400 for the same op). Fixed with an explicit key tie-break; **verified identical across two hash seeds** before any gate was scored.

---

## 1. Stage 1 — witness families (hand-verified)

Reconstructed per `2026-07-28-entity-overlap-identity-design.md` §2.5, lifted from `emergent_clusters` onto `dynamic_topics` because **the sibling finder's universe is the active topic field, not one night's cluster snapshot.**

Every membership claim below was checked by reading the member's **own evidence headlines**. Labels were not trusted — and the reason is §4.1.

| family | harvested | **verified** | G1-eligible (≥4) | role |
|---|---|---|---|---|
| `berlin-pride` | 8 | **7** | ✅ | GATE (core) |
| `caspian` | 2 | **2** | ❌ structural | GATE (core) |
| `fresh:ukrainian-drone-strikes-on-russia` | 11 | 7 | ✅ | DEV |
| `fresh:trump-threatens-iran` | 5 | 5 | ✅ | **GATE** |
| `fresh:fontainebleau-forest-fire` | 5 | 4 | ✅ | DEV |
| `fresh:trump-imposes-50-tariffs-on-canada` | 4 | 4 | ✅ | **GATE** |
| `fresh:us-iran-conflict-escalation` | 4 | 4 | ✅ | DEV |
| `fresh:russian-strikes-on-ukrainian-ports` | 6 | 3 | ❌ | — |
| `fresh:france-heatwave-death-toll` | 5 | **1** | ❌ | — |
| `fresh:russian-ballistic-missile-attack-on-ky` | 4 | **0** | ❌ | — |

**Split rule, frozen before the sweep:** core families are GATE-only by pre-registration. G1-eligible *fresh* families sorted by `(-verified_size, name)`; **even** indices → DEV (operating-point selection), **odd** → GATE. The gate families and the hand-judged G2 sample were never inputs to selection.

### 1.1 🔴 The flagship anchor is not a Berlin Pride topic

`dynamic-topic-466` *"Berlin Pride Attack: Suspect Profile and Manhunt"* — 287 signals, the topic `/threads` serves and the lens auto-enters on — is a **Greek-language crime fusion**. Its own evidence, in order:

```
Ακρόπολη: Ποινική δίωξη … στον 60χρονο που τραυμάτισε τουρίστες      (Acropolis knife attack on tourists)
Συνελήφθη 28χρονος Αιγύπτιος για τη δολοφονία του Σταύρου Γεωργίου   (murder of lawyer Stavros Georgiou)
Συνελήφθη κακοποιός με χειροβομβίδα – στόχος το σπίτι εισαγγελέα     (grenade plot against a prosecutor)
Καιρός: Νέο έκτακτο δελτίο από την ΕΜΥ – Επιμένει ο καύσωνας         (Greek heat bulletin)
Βερολίνο: … η φωτογραφία του υπόπτου για τη φονική επίθεση στο Pride (Berlin Pride, Greek coverage)
```

It absorbed Greek-language Berlin Pride coverage alongside ≥4 unrelated Greek stories. **Excluded from the family**, with that evidence, before scoring.

This single fact re-reads the entire T11 gate artifact:

- Its top sibling *"Austrian Arrested for Fraud" (0.853)* and its neighbours *"Greek News Roundup: Crime, Sports, Lottery"*, *"Italian Goldsmith Kills Robbers"* are **not errors** — they are dt-466's honest semantic neighbours. Its centroid is a Greek-crime centroid.
- `◈ STORY → EG` on a Berlin attack is likewise correct arithmetic: dt-466's **primary country is Egypt** (its footprint is DE/EG/GR).
- `18/18 is_blob` reads very differently against a **61.25% field-wide base rate** — and dt-466 is itself flagged, correctly.

Measured from dt-466 across every lane:

| lane | reached | true family members reached | in top-8 |
|---|---|---|---|
| C (walk) | 9 | 1 | 1 (rank 2) |
| E (df≤3) | 4 | 2 | 2 — *but tied at 0.637 with 2 false rows* |
| E (df≤10) | 4 | 2 | 2 |
| G | 2 | **0** | 0 — primary country EG sends it to Lebanese/Iranian topics |

**Union reach from dt-466 = 2 distinct true fragments of 7. G1 needs 3. From the anchor the product actually serves, G1 is structurally unreachable — by any scoring rule.**

### 1.2 The Berlin Pride family, and a label split the harvest rule cannot bridge

The `berlin AND pride` pattern finds 5. Three more carry the **German** name for the same parade — **CSD** (Christopher Street Day) — plus one vocabulary-free variant. All verified against their own receipts:

| topic | label | evidence (verbatim) |
|---|---|---|
| `dt-7356` | CSD Berlin Vehicle Attack | *"CSD in Berlin: Auto fährt in Menschenmenge – ein Toter, mehrere Verletzte"* (faz.net) |
| `dt-7715` | CSD Berlin Attack Suspect | *"Anschlag auf CSD Berlin: Das ist der Tatverdächtige – Polizei fahndet nach Abdul B."* (wz-net.de) |
| `dt-7714` | Berlin Car Attack on Crowd | *"В Берлине автомобиль въехал в толпу во время ЛГБТ-парада"* (pressorg24.com) |
| `dt-7712` | Berlin Pride Attack Suspect Killed | *"Suspect in deadly Berlin Pride attack killed in confrontation with police"* (nbcwashington.com) |
| `dt-7647` | Berlin Pride Terror Attack | *"Germany says fatal Berlin Pride attack believed to be Islamic extremist terror"* (cbc.ca) |
| `dt-7717` | Berlin Pride Car Attack | *"One dead, 15 injured after car driven into crowd at Berlin's Gay Pride parade"* (stuff.co.nz) |
| `dt-7716` | Berlin Pride Attack Suspect | *"Ένας 21χρονος ισλαμιστής αναζητείται ως ύποπτος για την επίθεση στο φεστιβάλ Pride"* (politis.com.cy) |

The one extension to §2.5 (an **OR over AND-patterns**) exists for this: a single AND-pattern files one event as two, which is the failure under test. An OR *within* a pattern remains forbidden.

### 1.3 The Caspian witness has aged out — recorded before scoring

Only **2** members survive in the active story field (`dt-7728`, `dt-7736`, both verified). Checked and recorded: the other Caspian-adjacent identities are **retired** (`dt-2810`, `dt-6427`), an **umbrella** (`dt-8070`, excluded from the field by design), or a different event (`dt-2802` *Iran Attacks UAE Tankers*). G1 needs an anchor plus ≥3 others; at size 2 it is **structurally unreachable, not failed**. The pre-registration's substitution clause applies: the fresh-family count rises to compensate — **two** fresh gate families instead of the required one.

---

## 2. Stage 2 — lanes, sweep, and the frozen operating point

### 2.1 Lane E is structurally weak — the load-bearing negative

True same-event pairs across all G1-eligible families that share **any** entity, by rarity gate:

| gate | true pairs reached | of | share |
|---|---|---|---|
| df ≤ 2 | 8 | 140 | 5.7% |
| **df ≤ 3** (the `_distinctive_df_max` discipline) | **12** | 140 | **8.6%** |
| df ≤ 5 | 14 | 140 | 10.0% |
| df ≤ 10 | 30 | 140 | 21.4% |
| df ≤ 20 | 30 | 140 | 21.4% |
| **no gate at all** | **50** | 140 | **35.7%** |

**Even with rarity abandoned entirely, 64% of true same-event pairs share no entity.** This is not a threshold problem. Contributing structure, all measured here: 942 of 1,022 topics carry ≥1 entity but only 763 carry a *shared* one; entity strings are stored in the source language (§2.5's own caveat), so a Greek and a German report of the Berlin attack share the event, not the string.

The pre-registration's premise — that rare-shared-entity is the lane that rescues cos-only — **is refuted at the reachability stage, before any ranking question arises.**

### 2.2 The sweep

DEV-only statistics (3 DEV families; 60-anchor mechanical false probe, seed 20260729):

| | DEV families passing | DEV true total | mech-false rate |
|---|---|---|---|
| **v1 baseline** | 1 / 3 | 5 | **0.620** |
| pure lane C, fold off | 1 / 3 | 5 | 0.620 |
| **best union (chosen)** | 1 / 3 | **6** | 0.640 |
| union range across 161 ops | 0–1 / 3 | 4–6 | **0.637 – 0.723** |

**Every operating point that activates lane E or lane G makes the mechanical false side worse than v1.** The best union buys +1 true fragment on DEV and pays 2 percentage points of false rate for it.

**Frozen operating point** (lexicographic rule, DEV inputs only):

```
form=rrf  w_C=1.0  w_E=1.5  w_G=0.5  rrf_k=60
lane E df_gate=2   lane G peak-gap ≤2d, min-score 0.15   lane C dedup=ON (as shipped)
```

---

## 3. Stage 3 — the gates

### G1 — recall on witnesses: **FAIL**

| gate family | verified size | eligible | **v2 true in top-8** | **v1 true in top-8** | passes |
|---|---|---|---|---|---|
| `berlin-pride` | 7 | ✅ | **6** (anchor `dt-7712`) | **6** | ✅ |
| `caspian` | 2 | ❌ structural | 1 | 1 | n/a |
| `fresh:trump-threatens-iran` | 5 | ✅ | **1** | **2** | ❌ *(v2 worse than v1)* |
| `fresh:trump-imposes-50-tariffs-on-canada` | 4 | ✅ | **3** | **3** | ✅ |

**2 of 3 eligible gate families. G1 requires all of them.**

v2's best Berlin Pride neighborhood, from `dt-7712` — 6 of 7 true, with the two false rows in between:

```
#1 TRUE dt-7647  s=.0486  C=.57 E=.64 G=.82  Berlin Pride Terror Attack
#2 TRUE dt-7715  s=.0232  C=.47 E=.00 G=1.00 CSD Berlin Attack Suspect
#3      dt-719   s=.0229  C=.54 E=.00 G=.45  Austrian Arrested for Fraud     ← false
#4      dt-5017  s=.0228  C=.53 E=.00 G=.59  Bahnmitarbeiter Attacke Sturz   ← false
#5 TRUE dt-7717  s=.0228  C=.50 E=.00 G=.62  Berlin Pride Car Attack
#6 TRUE dt-7356  s=.0225  C=.36 E=.00 G=.65  CSD Berlin Vehicle Attack
#7 TRUE dt-7716  s=.0224  C=.31 E=.00 G=1.00 Berlin Pride Attack Suspect
#8 TRUE dt-7714  s=.0222  C=.35 E=.00 G=.62  Berlin Car Attack on Crowd
```

v1's per-anchor recall on the same family — **the baseline the pre-registration recorded as 0**:

| anchor | dt-7712 | dt-7356 | dt-7717 | dt-7647 | dt-7714 | dt-7716 | dt-7715 |
|---|---|---|---|---|---|---|---|
| v1 true in top-8 | **6** | 5 | 5 | 4 | 4 | 3 | 2 |

### G1 ceiling — the post-hoc check K1 requires

G1 was scored at one frozen operating point. K1 asks whether **any** point could satisfy it, so the whole grid was re-run against the eligible gate families **post hoc** (clearly not the pre-registered scoring):

- **0 of 163 operating points reach 3 of 3.**
- Best = **2 of 3**, achieved by **v1 itself** (true-sum 11) and by pure lane C.
- No union point beats v1's true-sum.

### G2 — false-neighbor rate: **FAIL by 15×**

10 random active anchors (seed 20260729), top-5 each = 50 rows. Each row judged by reading **both topics' evidence headlines** — labels were not used, for the reason in §4.1. Unsure counts against.

| verdict | rows |
|---|---|
| related (same event or same running story) | **20** |
| unrelated story presented as kin | **27** |
| unsure | **3** |
| **counted against the gate** | **30 / 50** — gate allows **2** |

| anchor | label | related @5 | note |
|---|---|---|---|
| `dt-2851` | Trump Resumes Iran War | **5** | all five are the same running US-Iran war story (Arabic) |
| `dt-5885` | US Military Casualties in Iran Conflict | **5** | same, in Russian |
| `dt-5013` | Domestic Violence in Pontevedra | 4 | generously judged: #1–#4 are *other* Spanish femicides — same running story class |
| `dt-4285` | Bruxelles Oxy Tower Fire | 2 | anchor evidence is **Rome** fires; 2 Italian wildfire rows judged story-adjacent |
| `dt-3413` | Harry and Charles Reconciliation | 1 | anchor is itself a fusion (Prince George's birthday + Croatia oddities) |
| `dt-3987` | Trump Accuses China Election Interference | 1 | anchor evidence is **trade/tariffs**; #1–#4 are Vietnamese-language **war** topics |
| `dt-6975` | Morant Hitler Comparison Controversy | 1 | #2–#5 are other Spanish political stories |
| `dt-7696` | Ураган в Ростове-на-Дону | 1 | #2–#5 are drone attacks, one of them same city |
| `dt-3188` | Wildfire in Psakoudia, Halkidiki | **0** | label says wildfire, **evidence is a Chania workshop explosion** → 3 rows unsure |
| `dt-7700` | Lantratova Helps SVO Participants | **0** | siblings are an unrelated Russian human-interest/crime grab-bag |

### G2 attribution — the union added nothing

| | rows |
|---|---|
| top-5 rows already reachable by lane C | **50 / 50** |
| rows introduced by lane E or lane G | **0** |
| false rate among C-reachable rows | **0.60** |
| v2 top-5 ∩ v1 top-5, per anchor | 4, 5, 4, 5, 4, 3, 5, 5, 5, 3 → **mean 4.3 / 5** |

On *family* anchors lanes E/G do reach ranks 7–8 (e.g. `dt-2854` *Trump Threatens Iran Strikes*, a TRUE sibling, enters at rank 8 on lane G alone with `C=0.00`). They never reach a random anchor's top-5. **The 60% false rate is inherited whole from the cosine walk.**

### G3 — blob honesty: the flagger **over-fires**, and still carries signal

| measurement | value |
|---|---|
| G1 true-positive siblings flagged `is_blob` | **6 / 11 = 54.5%** → **over-fires** (> 50%) |
| field-wide base rate | **626 / 1022 = 61.25%** |
| G2 rows flagged | 36 / 50 = 72% |
| — among the 20 **related** rows | 12 / 20 = **60%** |
| — among the 30 **false** rows | 24 / 30 = **80%** |

Reported, **not tuned**. Two readings, both true: at a 61% base rate a `⚠ grab-bag` chip on a majority of rows is close to uninformative, and the T11 artifact's `18/18` is much less surprising than it read. Yet the flag is *not* noise — 80% on false rows vs 60% on true is a real 20-point separation. It is a **poorly-calibrated** signal, not a broken one.

### K1

> *"If no operating point satisfies G1 AND G2, the finder is NOT shippable on this field — the identity layer must heal first. Record and stop."*

No operating point satisfies G1 alone (0 of 163). **K1 fires. NO-GO.**

---

## 4. The three most surprising findings

### 4.1 Labels and evidence have come apart, and it is not rare

The measurement kept tripping over topics whose label describes a different story than their own receipts:

| topic | label | what its evidence actually is |
|---|---|---|
| `dt-466` | Berlin Pride Attack: Suspect Profile and Manhunt | Greek crime fusion (Acropolis, Georgiou murder, grenade plot, weather) |
| `dt-3188` | Wildfire in Psakoudia, Halkidiki | a **Chania boat-workshop explosion** |
| `dt-1226` | Crimea-Congo Hemorrhagic Fever Death | a Spanish **femicide** investigation in Benahavís |
| `dt-3747` | Russian Ballistic Missile Attack on Kyiv | Romanian **celebrity/holiday-invoice** stories |
| `dt-2944` | Russian Strikes on Ukrainian Ports | **Ukrainian** drone attacks on Russian facilities — the opposite direction |
| `dt-3764` | Russian Ballistic Attacks on Kyiv | Ukrainian drone strikes **on Russia** |
| `dt-405`, `dt-363`, `dt-400`, `dt-1228` | *…Heatwave Death Toll / Deaths* | European **wildfire** evacuations |

Whole harvested "families" dissolved on inspection: `fresh:russian-ballistic-missile-attack-on-ky` went **4 → 0** verified; `fresh:france-heatwave-death-toll` **5 → 1**. **The label-similarity harvest recovered families that were largely label artifacts** — which is why every membership in this artifact carries its receipts. It also means any future gate written against labels rather than evidence will measure the wrong object.

### 4.2 The finder was never the failure — the anchor was

`v1` places **6 of 6** true Berlin Pride fragments in the top-8 of `dt-7712`, and ≥3 from five of the family's seven anchors. The T11 artifact's *"v1 places 0"* is an artifact of anchoring on `dt-466`, whose neighborhood is honestly Greek crime. The lens's marquee failure is not candidate generation and not scoring: **the front page serves a fused identity as "the story", and the neighborhood of a fused identity is a fused neighborhood.** Every lane inherits that. This is why K1's own remedy — heal identity first — is the right one, and it is now measured rather than asserted.

### 4.3 The cosine walk groups by **language** as readily as by story

`dt-3987` *"Trump Accuses China Election Interference"* — whose evidence is Vietnamese-language **trade and tariff** coverage — returns four Vietnamese-language **war** topics (US airstrikes on Iran, Russian missiles on Kyiv, an ex-defence-minister story, Kremlin trivia) before the one genuinely related tariff topic. The shared property is the language of the reporting, not the event. `dt-7700` (Russian human-interest casework → a Russian crime/health grab-bag) and `dt-3188` (Greek explosion → Greek local incidents) are the same shape. The whitening removes one dominant direction; **a language direction evidently survives it**, and on this field it is strong enough to fill a top-5.

---

## 5. Honest limits

- **Sample size.** G1 rests on **3** eligible gate families — the active field yielded only 8 label-similarity families of size ≥4 in total, and hand-verification cut 4 of them below the threshold. G2 is 50 rows. Both are the pre-registered sizes; neither is large.
- **The Caspian witness could not be scored.** Recorded as structural (size 2), not as a failure, before scoring.
- **Family adjacency.** `fresh:trump-threatens-iran` (GATE) and `fresh:us-iran-conflict-escalation` (DEV) are adjacent stories; tuning on the DEV one could in principle leak to the GATE one. The leak would have *helped* v2, and v2 still lost that family to v1 (1 vs 2).
- **G2 was hand-judged for v2 only.** v1's 50 rows were not independently judged; the v1↔v2 comparison rests on the mechanical proxy (0.620 vs 0.640) plus the 4.3/5 list overlap. Given that overlap, v1's hand-judged rate is very unlikely to be materially better — but it is not measured here.
- **"Related" was judged generously** where an anchor's own story is a running one (Spanish femicides, the US-Iran war). A stricter same-event reading pushes the G2 false count above 30, never below.
- **`different_story` is a proxy**, and it under-counts: it fires only same-script, and needs zero shared distinctive tokens. It was used for selection only, never as a gate.
- **One day.** The whole run is the 2026-07-28/29 field. The T11 artifact independently recorded that this shredding is stable across days, but this measurement did not re-establish that.
- **Lane G's country signal inherits #238.** Dominant-coverage country ≠ subject country (`dt-466` → EG on a Berlin story). Lane G is therefore measuring where a story is *covered*, not where it *happens* — a known, inherited gap, not one introduced here.

---

## 6. What follows

**Do not change `story_siblings.py` or `story.py`.** The union is not shippable — it does not clear its own recall gate at any of 163 operating points, it degrades the false side everywhere it activates, and on the ten anchors an analyst would actually meet it returns a list 86% identical to v1's.

What the evidence points at instead, in order:

1. **Identity, as K1 says.** `dt-466` is one fused identity standing between the analyst and seven coherent fragments of the same event. Consolidation is upstream of every lane measured here.
2. **A cheap, honest interim for the lens:** the T11 defect **L1** (the neighborhood cannot render) is worth fixing on its own terms — but rendering v1's neighborhood unchanged would put a **60%-false** list on screen. If anything ships before identity heals, it should be the *anchor-quality* signal, not more neighbors: a fused anchor should say so.
3. **Two calibrations fall out for free:** `is_blob` needs re-fitting (61% base rate, 80/60 separation — real signal, wrong threshold), and the **label court** has a measurable label↔evidence divergence problem (§4.1) that no downstream ranker can repair.

*Read-only · 1,022 active story topics · 17,805 evidence rows · 163 operating points · 3 eligible gate families · 50 hand-judged rows · **K1: NO-GO***
