# Witness reconvergence (M1) and false-side density (M2) — one table

**Generated:** 2026-07-28T14:26:15.544499+00:00 · read-only · harness `backend/scripts/measure_evidence_fingerprint.py --sweep --false-density --judge-dryrun`  
**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` §3.1/§4/§5.2 · **Plan:** `docs/superpowers/plans/2026-07-28-entity-overlap-identity.md` (T-A1/T-A3)  
**Snapshot:** `2026-07-28T03:28:39.196920+00:00` · 2032 clusters · 2063496 pairs · 987864 at cos ≥ 0.84

## GO/NO-GO 0: **NO-GO**

Pre-registered, frozen before the run (spec §5.2, plan T-A3): an operating point must satisfy **K2** (largest connected component of the whole-snapshot merge graph ≤ **2%** of that snapshot's topics) **AND** bring **≥2 of the 3 core witness families** to **≤3 components**.

- points satisfying K2: **44 / 140**
- points satisfying K2 **and** the witness criterion: **0**

**No operating point exists.** K3's escalation ladder (§5.2) was run in the same pass — lane U and lane H appear as their own lane sets below — and every rung fails on the same K2 constraint:

| K3 rung | operating points satisfying K2 | best core families at ≤3 components among them | rung |
|---|---|---|---|
| 1 — lane E (entities) primary | 8 | 0 of 3 | **FAIL** |
| 2 — lane U (locators) primary | 6 | 0 of 3 | **FAIL** |
| 3 — lane H (headlines) primary | 20 | 0 of 3 | **FAIL** |

**K3 resolution: REFUTED — all three lanes fail K3.** Per the spec's own words: *"If all three lanes fail K3, the entity-overlap direction is REFUTED, this spec is closed like the attention-coverage-divergence spec was, and the honest conclusion is recorded: the same event's fragments carry no shared surface evidence [that is safe to merge on], so reconvergence cannot happen at the identity layer and must be attacked at clustering time."* **No fourth attempt, and no threshold was relaxed after seeing the result.**

One arithmetic corollary, so the obvious next idea is foreclosed rather than left hanging: a rule of the form `cos AND (label OR evidence)` — evidence as a *rescue* for the label blackout rather than a replacement — **cannot** satisfy K2 either. Connected components are monotone under edge addition, so the union's largest component is at least the evidence half's, and the evidence half exceeds 2% at every cut that moves a witness. This follows from the table; it needs no extra run.

## The mechanism the table is measuring

`merge_duplicates` runs **to a fixpoint**, so merging is transitively closed: an edge set is not a set of decisions, it is a graph, and what matters is **density**, not per-pair precision. Raw e5 is anisotropic — on this snapshot the cosine-only edge densities are:

| cos ≥ | merge edges | largest component | share of snapshot | false-pair admit rate |
|---|---|---|---|---|
| 0.84 | 987864 | 2032 | **100.0%** | 46.0% |
| 0.86 | 516236 | 2031 | **100.0%** | 22.9% |
| 0.88 | 224555 | 2027 | **99.8%** | 8.5% |
| 0.9 | 88103 | 1997 | **98.3%** | 2.8% |

Today's shipping rule (`cos>=0.9 AND label>=0.8`) for contrast: **380** edges, largest component **23** (1.1%), 0/1200 false pairs admitted. Its family components: `GQ-12 caspian` 4, `berlin pride` 4, `fresh:paris-knife-attack` 1, `fresh:russian-missile-strikes-on-kyiv` 4, `fresh:wildfires-in-france-and-spain` 1, `fresh:wildfires-in-france-and-spain#2` 1.

## The spec's seed candidate, tested

The spec's pre-measurement proposed **`cos ≥ 0.86 AND ent ≥ 1`** on the strength of Berlin Pride reaching 1 component while admitting 2.7% of 406 random dissimilar-label pairs. On the full grid that row reads:

- Berlin Pride **2** components, GQ-12 Caspian **1** — the recall claim essentially reproduces.
- false-pair admission **1.4%** — the precision claim also reproduces (same order as the spec's 2.7%).
- **largest connected component 1955 / 2032 clusters = 96.2% of the snapshot.** K2's bar is 2%. It misses by **48×**.

**The seed candidate is killed, and it is killed by the number M2 exists to produce.** Its supporting measurement scored 406 sampled pairs; it never built the graph. A 1.4% false-pair rate sounds small and is fatal here: over 2.06M pairs it is tens of thousands of edges, and `merge_duplicates` runs to a fixpoint. Percolation, not precision, is the binding constraint — which is exactly why the spec required M1 and M2 in one table.

### What today's shipping rule does on the same graph

`cos>=0.9 AND label>=0.8` — the rule this design set out to replace — satisfies K2 (**1.13%**, inside the 2% bar), admits **0/1200** false pairs, and leaves the two in-snapshot core families at **4** and **4** components. **No evidence-gate operating point in this grid matches that combination.** The label gate is a far better density controller than any evidence lane measured here; its documented failure was the five-day blackout (`emergent_clusters.label` 100% NULL 07-23→07-27, so `labels_compatible(None, None)` disabled merging entirely), not its discrimination on a labelled night. That distinction was not visible before this run, and it changes what DP-1's problem actually is.

## Witness families

| family | kind | clusters | signals | countries | example labels |
|---|---|---|---|---|---|
| `GQ-12 caspian` | core | 9 | 183 | IR,UA | Iran Accuses Ukraine of Caspian At · Iran Condemns Ukraine Ship Attack · Iran Threatens Ukraine Over Ship A |
| `berlin pride` | core | 22 | 265 | DE | Berlin Pride Van Attack · Berlin Pride Attack Victim · Berlin Pride Attack |
| `GQ-05` | core (rebuilt) | 21 | 651 | CO |  |
| `fresh:paris-knife-attack` | fresh | 9 | 149 | FR | Paris Knife Attack · Paris Knife Attack · Paris Knife Attack |
| `fresh:russian-missile-strikes-on-kyiv` | fresh | 9 | 163 | UA | Russian Missile Strikes on Kyiv · Russian Missile Strike on Kyiv Reg · Russian Strikes on Ukrainian Ports |
| `fresh:wildfires-in-france-and-spain` | fresh | 8 | 178 | FR | Wildfires in France and Spain · Wildfires in France and Spain · Wildfires in France and Spain |
| `fresh:wildfires-in-france-and-spain#2` | fresh | 7 | 218 | ES | Wildfires in France and Spain · Wildfires in France and Spain · Wildfires in France and Spain |

**GQ-05 reconstruction** (spec §2.5): `%espriella%` = 651 signals in the hot window, 645 embedded; offline HDBSCAN at the scoped snapshot's own parameters (mcs=5, ms=2, leaf, PRE-gate) → **21 fragments** (436 signals to noise). Pairwise centroid cosine inside the family: 0.8816 / 0.9306 / 0.9768 (min/p50/max); 99.5% of its internal pairs share at least one entity.

## M1 + M2 — the single table

Every row is one operating point. **Left half = recall** (connected components per witness family; the target is ≤3). **Right half = the false side** at the SAME point. `prereg` marks the pre-registered grid; `supp` rows widen only the rarity axis, because two pre-registered rarity gates are vacuous against the measured shared-item df distribution (see the coverage artifact). No kill threshold is moved.

| tau | lanes | rarity gate | grid | `GQ-12 caspian` | `berlin pride` | `GQ-05` | `fresh:paris-knife-attack` | `fresh:russian-missile-strikes-on-kyiv` | `fresh:wildfires-in-france-and-spain` | `fresh:wildfires-in-france-and-spain#2` | merge edges | largest comp | **share (K2)** | K2 | false admit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.84 | E | `any-shared` | prereg | 1 | 2 | 1 | 2 | 1 | 1 | 1 | 92539 | 1963 | **96.6%** | ✗ | 32/1200 (2.7%) |
| 0.84 | E | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | E | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | E | `df<=2` | supp | 7 | 14 | 1 | 7 | 7 | 8 | 6 | 1837 | 1258 | **61.9%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E | `df<=3` | supp | 6 | 10 | 1 | 6 | 6 | 8 | 5 | 3479 | 1638 | **80.6%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E | `df<=5` | supp | 5 | 7 | 1 | 5 | 5 | 7 | 3 | 6414 | 1804 | **88.8%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E | `df<=median(shared)` | supp | 1 | 2 | 1 | 2 | 1 | 2 | 1 | 48241 | 1954 | **96.2%** | ✗ | 10/1200 (0.8%) |
| 0.84 | E|U | `any-shared` | prereg | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 168342 | 2031 | **100.0%** | ✗ | 55/1200 (4.6%) |
| 0.84 | E|U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 481 | 74 | **3.6%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E|U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | E|U | `df<=2` | supp | 7 | 14 | 1 | 7 | 7 | 8 | 6 | 2246 | 1482 | **72.9%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E|U | `df<=3` | supp | 6 | 10 | 1 | 6 | 6 | 8 | 5 | 4613 | 1766 | **86.9%** | ✗ | 1/1200 (0.1%) |
| 0.84 | E|U | `df<=5` | supp | 5 | 7 | 1 | 5 | 5 | 7 | 3 | 9434 | 1899 | **93.5%** | ✗ | 2/1200 (0.2%) |
| 0.84 | E|U | `df<=median(shared)` | supp | 1 | 2 | 1 | 2 | 1 | 2 | 1 | 85386 | 2015 | **99.2%** | ✗ | 20/1200 (1.7%) |
| 0.84 | E|U|H | `any-shared` | prereg | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 169952 | 2031 | **100.0%** | ✗ | 56/1200 (4.7%) |
| 0.84 | E|U|H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 481 | 74 | **3.6%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E|U|H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | E|U|H | `df<=2` | supp | 6 | 14 | 1 | 7 | 7 | 8 | 6 | 2316 | 1524 | **75.0%** | ✗ | 0/1200 (0.0%) |
| 0.84 | E|U|H | `df<=3` | supp | 6 | 10 | 1 | 6 | 6 | 7 | 5 | 4752 | 1818 | **89.5%** | ✗ | 1/1200 (0.1%) |
| 0.84 | E|U|H | `df<=5` | supp | 5 | 7 | 1 | 5 | 5 | 5 | 3 | 9662 | 1934 | **95.2%** | ✗ | 2/1200 (0.2%) |
| 0.84 | E|U|H | `df<=median(shared)` | supp | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 86432 | 2017 | **99.3%** | ✗ | 20/1200 (1.7%) |
| 0.84 | U | `any-shared` | prereg | 4 | 15 | 1 | 6 | 6 | 6 | 4 | 99592 | 2003 | **98.6%** | ✗ | 26/1200 (2.2%) |
| 0.84 | U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 481 | 74 | **3.6%** | ✗ | 0/1200 (0.0%) |
| 0.84 | U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | U | `df<=2` | supp | 9 | 22 | 15 | 9 | 9 | 8 | 7 | 482 | 74 | **3.6%** | ✗ | 0/1200 (0.0%) |
| 0.84 | U | `df<=3` | supp | 9 | 22 | 5 | 9 | 9 | 8 | 7 | 1331 | 685 | **33.7%** | ✗ | 1/1200 (0.1%) |
| 0.84 | U | `df<=5` | supp | 9 | 22 | 2 | 8 | 9 | 8 | 7 | 3604 | 1220 | **60.0%** | ✗ | 2/1200 (0.2%) |
| 0.84 | U | `df<=median(shared)` | supp | 6 | 15 | 1 | 7 | 7 | 6 | 7 | 49803 | 1938 | **95.4%** | ✗ | 12/1200 (1.0%) |
| 0.84 | H | `any-shared` | prereg | 7 | 18 | 21 | 7 | 8 | 6 | 7 | 2819 | 360 | **17.7%** | ✗ | 1/1200 (0.1%) |
| 0.84 | H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.84 | H | `df<=2` | supp | 7 | 22 | 21 | 9 | 9 | 8 | 7 | 99 | 6 | **0.3%** | ✓ | 0/1200 (0.0%) |
| 0.84 | H | `df<=3` | supp | 7 | 20 | 21 | 9 | 9 | 7 | 7 | 186 | 14 | **0.7%** | ✓ | 0/1200 (0.0%) |
| 0.84 | H | `df<=5` | supp | 7 | 18 | 21 | 9 | 9 | 6 | 7 | 301 | 35 | **1.7%** | ✓ | 0/1200 (0.0%) |
| 0.84 | H | `df<=median(shared)` | supp | 7 | 18 | 21 | 7 | 8 | 6 | 7 | 1707 | 317 | **15.6%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E | `any-shared` | prereg | 1 | 2 | 1 | 2 | 2 | 1 | 1 | 58106 | 1955 | **96.2%** | ✗ | 17/1200 (1.4%) |
| 0.86 | E | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | E | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | E | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1636 | 1109 | **54.6%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E | `df<=3` | supp | 6 | 12 | 1 | 6 | 7 | 8 | 5 | 3057 | 1564 | **77.0%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E | `df<=5` | supp | 5 | 8 | 1 | 5 | 6 | 7 | 3 | 5580 | 1768 | **87.0%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E | `df<=median(shared)` | supp | 1 | 2 | 1 | 2 | 2 | 2 | 1 | 35361 | 1945 | **95.7%** | ✗ | 6/1200 (0.5%) |
| 0.86 | E|U | `any-shared` | prereg | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 122617 | 2029 | **99.9%** | ✗ | 38/1200 (3.2%) |
| 0.86 | E|U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 409 | 49 | **2.4%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E|U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | E|U | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1986 | 1333 | **65.6%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E|U | `df<=3` | supp | 6 | 12 | 1 | 6 | 7 | 8 | 5 | 4018 | 1708 | **84.1%** | ✗ | 1/1200 (0.1%) |
| 0.86 | E|U | `df<=5` | supp | 5 | 8 | 1 | 5 | 6 | 7 | 3 | 8158 | 1875 | **92.3%** | ✗ | 2/1200 (0.2%) |
| 0.86 | E|U | `df<=median(shared)` | supp | 1 | 2 | 1 | 2 | 2 | 2 | 1 | 68505 | 2013 | **99.1%** | ✗ | 16/1200 (1.3%) |
| 0.86 | E|U|H | `any-shared` | prereg | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 123766 | 2029 | **99.9%** | ✗ | 38/1200 (3.2%) |
| 0.86 | E|U|H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 409 | 49 | **2.4%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E|U|H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | E|U|H | `df<=2` | supp | 6 | 15 | 1 | 7 | 8 | 8 | 6 | 2048 | 1415 | **69.6%** | ✗ | 0/1200 (0.0%) |
| 0.86 | E|U|H | `df<=3` | supp | 6 | 12 | 1 | 6 | 7 | 7 | 5 | 4141 | 1762 | **86.7%** | ✗ | 1/1200 (0.1%) |
| 0.86 | E|U|H | `df<=5` | supp | 5 | 8 | 1 | 5 | 6 | 5 | 3 | 8351 | 1908 | **93.9%** | ✗ | 2/1200 (0.2%) |
| 0.86 | E|U|H | `df<=median(shared)` | supp | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 69264 | 2015 | **99.2%** | ✗ | 16/1200 (1.3%) |
| 0.86 | U | `any-shared` | prereg | 4 | 15 | 1 | 6 | 6 | 6 | 4 | 84655 | 1990 | **97.9%** | ✗ | 23/1200 (1.9%) |
| 0.86 | U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 409 | 49 | **2.4%** | ✗ | 0/1200 (0.0%) |
| 0.86 | U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | U | `df<=2` | supp | 9 | 22 | 15 | 9 | 9 | 8 | 7 | 410 | 49 | **2.4%** | ✗ | 0/1200 (0.0%) |
| 0.86 | U | `df<=3` | supp | 9 | 22 | 5 | 9 | 9 | 8 | 7 | 1132 | 256 | **12.6%** | ✗ | 1/1200 (0.1%) |
| 0.86 | U | `df<=5` | supp | 9 | 22 | 2 | 8 | 9 | 8 | 7 | 3091 | 1133 | **55.8%** | ✗ | 2/1200 (0.2%) |
| 0.86 | U | `df<=median(shared)` | supp | 6 | 15 | 1 | 7 | 7 | 6 | 7 | 44124 | 1923 | **94.6%** | ✗ | 11/1200 (0.9%) |
| 0.86 | H | `any-shared` | prereg | 7 | 18 | 21 | 7 | 8 | 6 | 7 | 2299 | 357 | **17.6%** | ✗ | 0/1200 (0.0%) |
| 0.86 | H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.86 | H | `df<=2` | supp | 7 | 22 | 21 | 9 | 9 | 8 | 7 | 91 | 6 | **0.3%** | ✓ | 0/1200 (0.0%) |
| 0.86 | H | `df<=3` | supp | 7 | 20 | 21 | 9 | 9 | 7 | 7 | 170 | 14 | **0.7%** | ✓ | 0/1200 (0.0%) |
| 0.86 | H | `df<=5` | supp | 7 | 18 | 21 | 9 | 9 | 6 | 7 | 266 | 34 | **1.7%** | ✓ | 0/1200 (0.0%) |
| 0.86 | H | `df<=median(shared)` | supp | 7 | 18 | 21 | 7 | 8 | 6 | 7 | 1417 | 314 | **15.4%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E | `any-shared` | prereg | 1 | 3 | 1 | 2 | 4 | 1 | 1 | 33991 | 1926 | **94.8%** | ✗ | 8/1200 (0.7%) |
| 0.88 | E | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | E | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | E | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1390 | 881 | **43.4%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E | `df<=3` | supp | 6 | 13 | 1 | 6 | 7 | 8 | 5 | 2524 | 1413 | **69.5%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E | `df<=5` | supp | 5 | 9 | 1 | 5 | 6 | 7 | 3 | 4475 | 1637 | **80.6%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E | `df<=median(shared)` | supp | 1 | 3 | 1 | 2 | 4 | 2 | 1 | 23315 | 1912 | **94.1%** | ✗ | 3/1200 (0.2%) |
| 0.88 | E|U | `any-shared` | prereg | 1 | 3 | 1 | 1 | 4 | 1 | 1 | 85099 | 2012 | **99.0%** | ✗ | 26/1200 (2.2%) |
| 0.88 | E|U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 318 | 47 | **2.3%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E|U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | E|U | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1660 | 1126 | **55.4%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E|U | `df<=3` | supp | 6 | 13 | 1 | 6 | 7 | 8 | 5 | 3274 | 1593 | **78.4%** | ✗ | 1/1200 (0.1%) |
| 0.88 | E|U | `df<=5` | supp | 5 | 9 | 1 | 5 | 6 | 7 | 3 | 6457 | 1789 | **88.0%** | ✗ | 2/1200 (0.2%) |
| 0.88 | E|U | `df<=median(shared)` | supp | 1 | 3 | 1 | 2 | 4 | 2 | 1 | 50964 | 1992 | **98.0%** | ✗ | 13/1200 (1.1%) |
| 0.88 | E|U|H | `any-shared` | prereg | 1 | 3 | 1 | 1 | 4 | 1 | 1 | 85741 | 2012 | **99.0%** | ✗ | 26/1200 (2.2%) |
| 0.88 | E|U|H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 318 | 47 | **2.3%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E|U|H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | E|U|H | `df<=2` | supp | 6 | 15 | 1 | 7 | 8 | 8 | 6 | 1707 | 1150 | **56.6%** | ✗ | 0/1200 (0.0%) |
| 0.88 | E|U|H | `df<=3` | supp | 6 | 13 | 1 | 6 | 7 | 7 | 5 | 3367 | 1636 | **80.5%** | ✗ | 1/1200 (0.1%) |
| 0.88 | E|U|H | `df<=5` | supp | 5 | 9 | 1 | 5 | 6 | 5 | 3 | 6594 | 1822 | **89.7%** | ✗ | 2/1200 (0.2%) |
| 0.88 | E|U|H | `df<=median(shared)` | supp | 1 | 3 | 1 | 1 | 4 | 1 | 1 | 51425 | 1994 | **98.1%** | ✗ | 13/1200 (1.1%) |
| 0.88 | U | `any-shared` | prereg | 5 | 15 | 1 | 6 | 6 | 7 | 4 | 66869 | 1957 | **96.3%** | ✗ | 20/1200 (1.7%) |
| 0.88 | U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 318 | 47 | **2.3%** | ✗ | 0/1200 (0.0%) |
| 0.88 | U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | U | `df<=2` | supp | 9 | 22 | 15 | 9 | 9 | 8 | 7 | 319 | 47 | **2.3%** | ✗ | 0/1200 (0.0%) |
| 0.88 | U | `df<=3` | supp | 9 | 22 | 5 | 9 | 9 | 8 | 7 | 889 | 141 | **6.9%** | ✗ | 1/1200 (0.1%) |
| 0.88 | U | `df<=5` | supp | 9 | 22 | 2 | 8 | 9 | 8 | 7 | 2402 | 665 | **32.7%** | ✗ | 2/1200 (0.2%) |
| 0.88 | U | `df<=median(shared)` | supp | 7 | 15 | 1 | 7 | 7 | 7 | 7 | 36534 | 1858 | **91.4%** | ✗ | 11/1200 (0.9%) |
| 0.88 | H | `any-shared` | prereg | 7 | 18 | 21 | 7 | 9 | 6 | 7 | 1696 | 326 | **16.0%** | ✗ | 0/1200 (0.0%) |
| 0.88 | H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.88 | H | `df<=2` | supp | 7 | 22 | 21 | 9 | 9 | 8 | 7 | 75 | 4 | **0.2%** | ✓ | 0/1200 (0.0%) |
| 0.88 | H | `df<=3` | supp | 7 | 20 | 21 | 9 | 9 | 7 | 7 | 138 | 10 | **0.5%** | ✓ | 0/1200 (0.0%) |
| 0.88 | H | `df<=5` | supp | 7 | 18 | 21 | 9 | 9 | 6 | 7 | 206 | 20 | **1.0%** | ✓ | 0/1200 (0.0%) |
| 0.88 | H | `df<=median(shared)` | supp | 7 | 18 | 21 | 7 | 9 | 6 | 7 | 1102 | 278 | **13.7%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E | `any-shared` | prereg | 1 | 3 | 1 | 2 | 4 | 3 | 1 | 18665 | 1822 | **89.7%** | ✗ | 5/1200 (0.4%) |
| 0.9 | E | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1099 | 470 | **23.1%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E | `df<=3` | supp | 6 | 13 | 1 | 6 | 8 | 8 | 5 | 1919 | 892 | **43.9%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E | `df<=5` | supp | 5 | 9 | 1 | 5 | 7 | 7 | 4 | 3252 | 1378 | **67.8%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E | `df<=median(shared)` | supp | 1 | 3 | 1 | 2 | 4 | 3 | 1 | 13787 | 1799 | **88.5%** | ✗ | 2/1200 (0.2%) |
| 0.9 | E|U | `any-shared` | prereg | 1 | 3 | 1 | 2 | 4 | 2 | 1 | 54559 | 1951 | **96.0%** | ✗ | 19/1200 (1.6%) |
| 0.9 | E|U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 213 | 25 | **1.2%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E|U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E|U | `df<=2` | supp | 7 | 15 | 1 | 7 | 8 | 8 | 6 | 1273 | 627 | **30.9%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U | `df<=3` | supp | 6 | 13 | 1 | 6 | 8 | 8 | 5 | 2407 | 1241 | **61.1%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U | `df<=5` | supp | 5 | 9 | 1 | 5 | 7 | 7 | 4 | 4561 | 1592 | **78.3%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U | `df<=median(shared)` | supp | 1 | 3 | 1 | 2 | 4 | 2 | 1 | 33940 | 1920 | **94.5%** | ✗ | 9/1200 (0.8%) |
| 0.9 | E|U|H | `any-shared` | prereg | 1 | 3 | 1 | 1 | 4 | 1 | 1 | 54843 | 1951 | **96.0%** | ✗ | 19/1200 (1.6%) |
| 0.9 | E|U|H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 213 | 25 | **1.2%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E|U|H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | E|U|H | `df<=2` | supp | 6 | 15 | 1 | 7 | 8 | 8 | 6 | 1311 | 640 | **31.5%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U|H | `df<=3` | supp | 6 | 13 | 1 | 6 | 8 | 7 | 5 | 2477 | 1275 | **62.7%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U|H | `df<=5` | supp | 5 | 9 | 1 | 5 | 7 | 5 | 4 | 4665 | 1625 | **80.0%** | ✗ | 0/1200 (0.0%) |
| 0.9 | E|U|H | `df<=median(shared)` | supp | 1 | 3 | 1 | 1 | 4 | 1 | 1 | 34192 | 1922 | **94.6%** | ✗ | 9/1200 (0.8%) |
| 0.9 | U | `any-shared` | prereg | 5 | 15 | 1 | 7 | 6 | 7 | 4 | 47040 | 1821 | **89.6%** | ✗ | 15/1200 (1.2%) |
| 0.9 | U | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 213 | 25 | **1.2%** | ✓ | 0/1200 (0.0%) |
| 0.9 | U | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | U | `df<=2` | supp | 9 | 22 | 16 | 9 | 9 | 8 | 7 | 214 | 25 | **1.2%** | ✓ | 0/1200 (0.0%) |
| 0.9 | U | `df<=3` | supp | 9 | 22 | 5 | 9 | 9 | 8 | 7 | 599 | 113 | **5.6%** | ✗ | 0/1200 (0.0%) |
| 0.9 | U | `df<=5` | supp | 9 | 22 | 2 | 8 | 9 | 8 | 7 | 1638 | 388 | **19.1%** | ✗ | 0/1200 (0.0%) |
| 0.9 | U | `df<=median(shared)` | supp | 7 | 15 | 1 | 7 | 7 | 7 | 7 | 26605 | 1703 | **83.8%** | ✗ | 8/1200 (0.7%) |
| 0.9 | H | `any-shared` | prereg | 7 | 18 | 21 | 7 | 9 | 6 | 7 | 1213 | 298 | **14.7%** | ✗ | 0/1200 (0.0%) |
| 0.9 | H | `df<=median` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | H | `norm_rarity>=0.5` | prereg | 9 | 22 | 21 | 9 | 9 | 8 | 7 | 0 | 1 | **0.1%** | ✓ | 0/1200 (0.0%) |
| 0.9 | H | `df<=2` | supp | 7 | 22 | 21 | 9 | 9 | 8 | 7 | 66 | 4 | **0.2%** | ✓ | 0/1200 (0.0%) |
| 0.9 | H | `df<=3` | supp | 7 | 20 | 21 | 9 | 9 | 7 | 7 | 113 | 8 | **0.4%** | ✓ | 0/1200 (0.0%) |
| 0.9 | H | `df<=5` | supp | 7 | 18 | 21 | 9 | 9 | 6 | 7 | 171 | 17 | **0.8%** | ✓ | 0/1200 (0.0%) |
| 0.9 | H | `df<=median(shared)` | supp | 7 | 18 | 21 | 7 | 9 | 6 | 7 | 848 | 249 | **12.2%** | ✗ | 0/1200 (0.0%) |

**FALSE construction** (1200 pairs): disjoint non-empty country sets AND dissimilar same-script labels — the same mechanical rule the whitened-taus harness used, so the two measurements share one definition of "different story". On that set: **5.0%** share ≥1 entity, 0.0% share an exact URL, 2.8% share a domain, 0.1% share a normalized headline.

Shared-item df medians actually observed (the honest denominator for `df≤median`): `{'shared:E': 91, 'vocab:E': 1, 'shared:U': 2, 'vocab:U': 1, 'shared:D': 41, 'vocab:D': 2, 'shared:H': 15, 'vocab:H': 1}`. Lane `df_max`: `{'E': 383, 'D': 168, 'U': 2, 'H': 23}`.

## The separation probe — do the two curves ever cross?

The grid samples a handful of rarity cuts, so a NO-GO on it could in principle be an artifact of which cuts were sampled. This walks the cut continuously (`df ≤ 1,2,3,4,5,6,8,10,14,20,30,45,70,100,150,250,400, any`) and reports two numbers per (tau, lane set): the **loosest** cut that still satisfies K2, and the **tightest** cut that brings both in-snapshot core families (`GQ-12 caspian`, `berlin pride`) to ≤3 components. If the tightest recall cut is looser than the loosest safe cut, **no operating point can exist between them** — arithmetically, not by taste.

| tau | lanes | loosest cut satisfying K2 | tightest cut reaching the witness bar | overlap? |
|---|---|---|---|---|
| 0.84 | E | df≤1 | df≤30 | no |
| 0.84 | E|U | df≤1 | df≤30 | no |
| 0.84 | E|U|H | df≤1 | df≤30 | no |
| 0.84 | U | df≤1 | never | no |
| 0.84 | H | df≤5 | never | no |
| 0.86 | E | df≤1 | df≤30 | no |
| 0.86 | E|U | df≤1 | df≤30 | no |
| 0.86 | E|U|H | df≤1 | df≤30 | no |
| 0.86 | U | df≤1 | never | no |
| 0.86 | H | df≤5 | never | no |
| 0.88 | E | df≤1 | df≤30 | no |
| 0.88 | E|U | df≤1 | df≤30 | no |
| 0.88 | E|U|H | df≤1 | df≤30 | no |
| 0.88 | U | df≤1 | never | no |
| 0.88 | H | df≤6 | never | no |
| 0.9 | E | df≤1 | df≤30 | no |
| 0.9 | E|U | df≤1 | df≤30 | no |
| 0.9 | E|U|H | df≤1 | df≤30 | no |
| 0.9 | U | df≤2 | never | no |
| 0.9 | H | df≤6 | never | no |

`GQ-05` is excluded from this probe: its fragments are an offline rebuild outside `emergent_clusters`, so they cannot be nodes of the snapshot merge graph whose density K2 measures. Requiring both remaining core families is the strict reading of "≥2 of 3".

## M6 — judge volume and cost at the candidate points

Borderline band = pairs a **strict** rarity gate rejects but the **permissive** (`any-shared`) gate at the same tau/lane admits. That is the population a "one story or two?" judge would adjudicate; the band's size is the judge's nightly workload.

Model `deepseek-chat` at `{'in': 0.27, 'out': 1.1}` USD/Mtok, 700 in + 60 out per call, spec §8 hard cap **150 calls/night** (≈ $0.0382/night at the cap).

| tau | lanes | strict gate | admitted (strict) | admitted (loose) | **borderline band** | × hard cap | USD/night if all judged |
|---|---|---|---|---|---|---|---|
| 0.84 | E | `df<=2` | 1837 | 92539 | **90702** | 604.7× | $23.13 |
| 0.84 | E | `df<=median(shared)` | 48241 | 92539 | **44298** | 295.3× | $11.3 |
| 0.84 | E|U | `df<=2` | 2246 | 168342 | **166096** | 1107.3× | $42.35 |
| 0.84 | E|U | `df<=median(shared)` | 85386 | 168342 | **82956** | 553.0× | $21.15 |
| 0.84 | E|U|H | `df<=2` | 2316 | 169952 | **167636** | 1117.6× | $42.75 |
| 0.84 | E|U|H | `df<=median(shared)` | 86432 | 169952 | **83520** | 556.8× | $21.3 |
| 0.84 | U | `df<=2` | 482 | 99592 | **99110** | 660.7× | $25.27 |
| 0.84 | U | `df<=median(shared)` | 49803 | 99592 | **49789** | 331.9× | $12.7 |
| 0.84 | H | `df<=2` | 99 | 2819 | **2720** | 18.1× | $0.69 |
| 0.84 | H | `df<=median(shared)` | 1707 | 2819 | **1112** | 7.4× | $0.28 |
| 0.86 | E | `df<=2` | 1636 | 58106 | **56470** | 376.5× | $14.4 |
| 0.86 | E | `df<=median(shared)` | 35361 | 58106 | **22745** | 151.6× | $5.8 |
| 0.86 | E|U | `df<=2` | 1986 | 122617 | **120631** | 804.2× | $30.76 |
| 0.86 | E|U | `df<=median(shared)` | 68505 | 122617 | **54112** | 360.7× | $13.8 |
| 0.86 | E|U|H | `df<=2` | 2048 | 123766 | **121718** | 811.5× | $31.04 |
| 0.86 | E|U|H | `df<=median(shared)` | 69264 | 123766 | **54502** | 363.3× | $13.9 |
| 0.86 | U | `df<=2` | 410 | 84655 | **84245** | 561.6× | $21.48 |
| 0.86 | U | `df<=median(shared)` | 44124 | 84655 | **40531** | 270.2× | $10.34 |
| 0.86 | H | `df<=2` | 91 | 2299 | **2208** | 14.7× | $0.56 |
| 0.86 | H | `df<=median(shared)` | 1417 | 2299 | **882** | 5.9× | $0.22 |
| 0.88 | E | `df<=2` | 1390 | 33991 | **32601** | 217.3× | $8.31 |
| 0.88 | E | `df<=median(shared)` | 23315 | 33991 | **10676** | 71.2× | $2.72 |
| 0.88 | E|U | `df<=2` | 1660 | 85099 | **83439** | 556.3× | $21.28 |
| 0.88 | E|U | `df<=median(shared)` | 50964 | 85099 | **34135** | 227.6× | $8.7 |
| 0.88 | E|U|H | `df<=2` | 1707 | 85741 | **84034** | 560.2× | $21.43 |
| 0.88 | E|U|H | `df<=median(shared)` | 51425 | 85741 | **34316** | 228.8× | $8.75 |
| 0.88 | U | `df<=2` | 319 | 66869 | **66550** | 443.7× | $16.97 |
| 0.88 | U | `df<=median(shared)` | 36534 | 66869 | **30335** | 202.2× | $7.74 |
| 0.88 | H | `df<=2` | 75 | 1696 | **1621** | 10.8× | $0.41 |
| 0.88 | H | `df<=median(shared)` | 1102 | 1696 | **594** | 4.0× | $0.15 |
| 0.9 | E | `df<=2` | 1099 | 18665 | **17566** | 117.1× | $4.48 |
| 0.9 | E | `df<=median(shared)` | 13787 | 18665 | **4878** | 32.5× | $1.24 |
| 0.9 | E|U | `df<=2` | 1273 | 54559 | **53286** | 355.2× | $13.59 |
| 0.9 | E|U | `df<=median(shared)` | 33940 | 54559 | **20619** | 137.5× | $5.26 |
| 0.9 | E|U|H | `df<=2` | 1311 | 54843 | **53532** | 356.9× | $13.65 |
| 0.9 | E|U|H | `df<=median(shared)` | 34192 | 54843 | **20651** | 137.7× | $5.27 |
| 0.9 | U | `df<=2` | 214 | 47040 | **46826** | 312.2× | $11.94 |
| 0.9 | U | `df<=median(shared)` | 26605 | 47040 | **20435** | 136.2× | $5.21 |
| 0.9 | H | `df<=2` | 66 | 1213 | **1147** | 7.6× | $0.29 |
| 0.9 | H | `df<=median(shared)` | 848 | 1213 | **365** | 2.4× | $0.09 |

DeepSeek peak pricing is 2x in UTC 01-04 and 06-10; the nightly `scoped-snapshot` runs 22:00->03:54 local and straddles both, so a judge step must be placed in the local 00:20-00:50 valley explicitly — moving the JOB does not move the STEP (CLAUDE.md 2026-07-27).

## Honest limits

- **The node set is clusters, not topics.** K2 is stated over "that snapshot's topics"; at DP-1's same-snapshot restriction every unmatched cluster founds its own topic before `merge_duplicates` runs (`project_dynamic_topics.process_snapshot`), so one cluster ≈ one candidate identity and the share is computed over the snapshot's clusters. Stated rather than assumed.
- **Roundups are not excluded.** `merge_duplicates` skips roundup topics, but `emergent_clusters` does not persist the roundup flag, so the false-side density here is an **upper bound** on the shipping graph. The direction of the error is stated; it cannot manufacture a passing operating point.
- **The FALSE construction can misfile** a genuinely shared story told with disjoint vocabulary in disjoint countries. That error raises the measured false-admit rate, i.e. it is conservative against a GO.
- **The GQ-05 family is scored on its own df**, computed over its own fragments rather than the snapshot (its fragments are an offline rebuild and are not snapshot members). A small df universe makes rarity gates *easier* to clear there, so GQ-05's component counts are optimistic relative to the families scored in-snapshot.
- **One snapshot, one night.** Every number here is 07-28. M3 (T-A2) is the measurement that spans ≥7 snapshots; until it lands, `df_max` and the df medians should be read as a single night's field, not as constants.
