# Spec — Atlas Engine R2: umbrella hierarchy (centroid-of-centroids) (#229)

Date: 2026-07-01 · Author: Claude (Opus 4.8) · Status: **DRAFT for Pedro review**
Companion: `2026-06-30-atlas-engine-recall-scoped-clustering.md` (R0/R1/R3),
Paper 8 (`2026-06-30-paper-8-result-skeleton.md`, Interventions 3/4), Paper 4
(`2026-05-24-living-narrative-threads.md`, decision 3 = hierarchical threads).

## 0. Where we are (R1 shipped, 2026-07-01)
R1 (scoped per-country clustering) is live: **731 tight topics, 126 countries,
cohesion 0.968, no blob**; serving bootstrap-promoted **68 → 392 active**, purity
held. R1 raised *recall*. It leaves two *legibility* debts that R2 pays — both
measured, not hypothetical, in the R1 output:

1. **Cross-country duplication.** A global story forms one scoped cluster PER
   country. Observed live in the served set:
   - "France Heatwave Deaths" (44) as its own topic, plus per-country heat topics.
   - "Venezuela Earthquake Disaster" AND "ONU Estima Afectados Terremotos
     Venezuela" — same event, two languages.
   - "Morocco vs Netherlands World Cup 2026" tagged under MX; World-Cup topics
     recur across many countries.
   Correct for a country-scoped view ("the story in THIS country's press"),
   N-fold noise in the GLOBAL list.
2. **Fragmentation.** A single evolving story appears as many flat topics (Paper 4
   finding: US–Iran ≈ 7 flat threads; Russia–Ukraine as UA + RU + … scoped
   clusters). No parent to say "these are one story."

## 1. The lever — cluster the centroids (embedding-of-embeddings)
Pedro's framing (2026-06-30), validated: R1 topics each carry a `centroid_vec`
(mean of member embeddings). R2 runs a SECOND clustering pass over **the ~731
centroids** (not the 200K signals) → **parent umbrella topics**, with the scoped
per-country/regional topics as **children**.

- **Cheap by construction.** ~731 vectors, not 200K → seconds, not the ~50min R1
  pass. This is what lets the umbrella layer be near-real-time (§4).
- **No black-hole.** It is a small second pass over already-clean centroids, NOT a
  bigger global HDBSCAN over raw signals — the exact failure mode (#224) is
  structurally avoided: children are fixed, the umbrella only groups them.
- **Collapses duplication.** France-Heatwave-DE + FR + GB centroids are near →
  one umbrella "France heatwave", children preserved for per-country serving.
- **Gives the hierarchy.** Big story = umbrella (parent) + child sub-threads, each
  with its own narrative + movement (Paper 4 decision 3, finally implemented).

## 2. Mechanics

### 2.1 Schema (decision E-R2-a)
Two options:
- **(a) `parent_id` self-ref on `dynamic_topics`** (+ `is_umbrella bool`). Umbrellas
  are rows in the same table; children point up. Minimal migration; serving filters
  `parent_id IS NULL` for the top level. **Default** — on-thesis (one topic model),
  reuses lifecycle/serving, and an umbrella IS a topic (it has a centroid = mean of
  child centroids, a label, members = union of children).
- (b) Separate `topic_umbrellas` table. Cleaner separation but duplicates
  lifecycle/serving plumbing and splits the model. *Alt.*

### 2.2 The umbrella pass (`build_umbrella_topics.py`, new)
1. Load active + candidate `dynamic_topics` with `centroid_vec` (the children pool).
2. Cluster centroids. Candidate methods (decision E-R2-b): **agglomerative /
   single-link at a cosine-distance cut**, or a light HDBSCAN over centroids.
   Agglomerative with an explicit threshold is more predictable for ~700 points and
   gives a tunable "how close is one story" knob. Threshold measured like R1's
   (a cliff sweep), NOT guessed.
3. A cluster of ≥2 children → an umbrella (centroid = mean of child centroids;
   label = DeepSeek over the children's labels/members, or the highest-volume
   child's label as fallback). A singleton child → **its own umbrella of one**
   (honest: no fabricated grouping; it just has no siblings).
4. Write umbrellas as `dynamic_topics` rows (`is_umbrella=true`), set children's
   `parent_id`. Idempotent + reversible (a re-run re-parents; `parent_id=NULL`
   reverts to flat).

### 2.3 Cross-country collapse — the honest rule
An umbrella groups children that are the SAME story across countries/languages
(France heatwave DE/FR/GB). It must NOT merge merely-similar-topic children
(all "election" topics into one) — that is the taxonomy axis (#204), a DIFFERENT
lever. The centroid-distance cut is the guard: same-event centroids are far tighter
than same-theme ones (measure the two distributions in R2.1 and cut between them,
same discipline as R1's gate).

## 3. Serving (decision E-R2-c)
- **Global `/threads`** = umbrellas (top level, `parent_id IS NULL`), ranked by the
  union movement/volume of their children. Collapses the France-Heatwave-×N noise.
- **Drill into an umbrella** = its children (per-country/regional sub-threads) — the
  existing thread-detail contract, one level down.
- **Country `/threads?country_code=CC`** = the child topics whose members are in CC
  (the country view stays child-level — a country wants ITS version, not the global
  umbrella). NOTE: this also addresses the current gap where the country path serves
  atlas-generic labels; R2 lets it serve the scoped children.
- Honesty invariant: an umbrella-of-one serves exactly as a normal topic today (no
  visible change when a story is genuinely single-country).

## 4. Cadence — the 3-speed model (ties Paper 4 decision 5)
R2 is the cheap layer that makes serving feel live without streaming clustering:
- **Formation** (R1 HDBSCAN): nightly, heavy, discovers NEW children.
- **Assignment** (nearest-centroid ≥0.88, `build_unified_topics`): every 30min with
  ingest — children GROW, velocity moves (the ticker).
- **Umbrella** (this spec): cheap centroid re-cluster → **hourly or on-read**,
  re-scoped per requested window (an umbrella is only over the children alive in
  that window). Movement numbers = Kalman #219.

## 5. Phases
- **R2.1 — measure.** Centroid self-similarity over the R1 731: distribution of
  cross-country same-event distance vs same-theme distance; pick the cut. Count the
  duplication rate (how many children collapse). Read-only, light.
  **RESULT (2026-07-01, first pass):** over the 731-topic snapshot, **261,555
  cross-country centroid pairs**; similarity sweep **≥0.97: 984 pairs · ≥0.95:
  3,823 · ≥0.92: 15,431 · ≥0.90: 39,572 · max 0.999**. So cross-country
  duplication is real and substantial — max 0.999 = the same event in two
  countries (the observed "Venezuela Earthquake" ×2-language, France-heatwave-×N
  cases). The cut lives ~0.95–0.97 (tight same-event) before the tail toward 0.90
  starts admitting same-THEME creep — R2.2 sets it by the two-distribution gap +
  a union-find pass converts pairs→umbrella components (the distinct-collapse
  count; the naive DISTINCT-over-cross-join is too slow live, union-find offline).
  `centroid_vec` is `real[]` — cast `::vector` for the pgvector cosine operator.
- **R2.2 — build.** `build_umbrella_topics.py` + schema migration (parent_id/
  is_umbrella). Write umbrellas, parent the children. Reversible.
  **RESULT (2026-07-01):** migration 058 applied; `build_umbrella_topics.py`
  written + validated on the 392-active set. Two findings:
  (1) **single-link union-find CHAINS** — at 0.95/0.97 it transitively merged
  World-Cup matches + heatwaves + unrelated topics into garbage megagroups
  ("Egypt vs Iran World Cup" ← 25 incl. Iraq Anti-Corruption). Fixed with greedy
  **COMPLETE-linkage** (a group forms only if ALL cross-pairs ≥ threshold) — the
  same-EVENT vs same-THEME guard, in the algorithm not just the threshold.
  (2) **threshold 0.98, not the spec's 0.95** — some topic centroids are diffuse
  (short-headline e5 means for generic/roundup topics sit near many things), so
  the same-event cut is TIGHTER than expected; 0.98 complete-linkage is clean
  (Venezuela Earthquake ×2, France Heatwave ×2, Egypt World Cup ×4, Xpeng ×3),
  0.96 still leaked ("Football Transfer News" ← Sudan Conflict). **26 umbrellas
  over 55 children, 337 singletons → 363 top-level** (from 392). Umbrella members
  = union of children's (so the umbrella aggregates counts/countries/evidence via
  the existing serving query). Reversible: `parent_id=NULL` + delete umbrella rows.
- **R2.3 — serve.** Serving reads top-level umbrellas globally, children on drill +
  country. A/B vs the flat R1 serving (does the global list get more legible without
  losing any story — every child still reachable).
  **CODE READY, DEPLOY-BLOCKED (2026-07-01):** `_DYNAMIC_TOPICS_SQL` gained
  `AND dt.parent_id IS NULL` (global list = top-level; the flat query is unchanged
  for country/drill since umbrellas carry union members + detail is by id). The
  filter is INERT without umbrellas (all topics have parent_id NULL → all show), so
  it is safe to deploy anytime. Backend deploy needs Pedro's Fly auth
  (`flyctl auth login`; no token in env). **Sequence:** (1) Pedro deploys the
  serving code; (2) run `python -m backend.scripts.build_umbrella_topics
  --threshold 0.98`; (3) verify prod `/threads` shows umbrellas + no dup children.
  Until (1), the umbrellas are rolled back (prod serves the clean 392-flat) so the
  undeployed old code can't show umbrella+child duplication.
- **R2.4 — cadence.** Wire the umbrella pass into the 30min/hourly path (cheap) so
  the hierarchy stays live between nightly R1 formations.

## 6. Decisions needed (Pedro)
- **E-R2-a schema:** parent_id self-ref (default) vs separate table.
- **E-R2-b umbrella clustering:** agglomerative@threshold (default, tunable) vs
  HDBSCAN-over-centroids.
- **E-R2-c serving semantics:** global=umbrellas / drill=children / country=children
  (default) — confirm the country view goes child-level.
- **E-R2-d label source:** DeepSeek over children (cost per umbrella) vs
  highest-volume-child label (free). Default: highest-volume-child now, DeepSeek
  later if labels read poorly.

## 7. Honesty invariants (carry from R1)
- No fabricated groupings: a story with no cross-country sibling stays a topic of
  one, served unchanged.
- No taxonomy collapse: umbrellas group same-EVENT children, not same-THEME (that is
  #204). The distance cut enforces it, measured.
- Never delete: umbrella-ing re-parents rows; it never drops a child. Reversible to
  flat via `parent_id=NULL`.
- The evolution graph (Paper 7, engine-truth reframe) renders an umbrella as its
  children entering/leaving across time buckets — the umbrella IS the "bigger
  thread" Pedro described.

## 8. Ties to the papers
- **Paper 8 Intervention 4** (already stubbed): R2 is coverage→legibility; the
  before/after = global-list duplication rate + fragmentation count, pre/post
  umbrella, every child still reachable (no recall lost to legibility).
- **Paper 4 decision 3**: this IS hierarchical threads (parent + child sub-threads),
  the spec'd-never-built model, now built on the R1 substrate.
- **Paper 7**: the umbrella hierarchy is what the engine-truth evolution graph draws.
