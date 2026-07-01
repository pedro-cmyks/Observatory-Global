# Spec — Atlas Engine R3: the unification (spine + lenses + relations, all five brains)

Date: 2026-07-01 · Branch: `v3-intel-layer` · Status: **CLOSED + VALIDATED** (v3).
Arc: v1 → 4-agent deep read of ~20 specs + 9 papers → v2 (~30 corrections, ledger
§11) → Pedro's "why fixed 32?" → v3 anchored-emergent categories + all decisions
resolved (§9) → CLOSED: claims verified vs prod + the riskiest new idea proven with
a live PoC (§12); build started (R3.0 schema + R3.7 retirement shipped, R3.1 typing
validated + running). Author: Claude (Opus 4.8).

**This is a CONVERGENCE spec, not a new invention.** It ties together work built
piecemeal across the last ~20 specs + 9 papers and finishes the un-flipped pieces.
Read alongside — it supersedes the "next steps" of — the specs cited inline; the
canonical objects come from `2026-05-25-atlas-narrative-intelligence-framework.md`,
the engine from `2026-06-29-atlas-unified-engine.md` (F0–F4), the thread model +
Pedro's 6 decisions from `2026-05-24-living-narrative-threads.md`, the surface
charter from `2026-06-26-l2-deep-review.md §"unified-engine connection"`, the
roles from `2026-06-30-atlas-engine-attention-anomaly-roles.md`, recall/umbrella
from `2026-06-30-recall-scoped-clustering.md` + `2026-07-01-r2-umbrella-hierarchy.md`,
research contract from `2026-06-09-research-thread-builder-workbench.md`, and the
paper constraints from `2026-06-03-paper-1-result-skeleton.md` + `2026-05-27-
atlas-papers-master-plan.md`.

---

## 0. Why (Pedro, 2026-07-01)

Pedro, on prod: *"why are there still TWO — atlas and dynamic? there should be
ONE."* Verified today:
```
atlas_topics (lexical, 30, WITH parent_domain)   → badge "CLIMATE DISASTER" etc.
dynamic_topics active (embedding, 418, NO domain) → badge "narrative thread"
fetch_threads: rank_threads(dynamic + atlas_extra)   ← serves BOTH, merged by score
topic_members: v1-compat 29968 · unified-v2 8643     ← unified engine EXISTS, unserved
dynamic_topics has NO parent_domain column           ← scoped topics can't be typed
```
It is not two pipelines — it is two LEVELS OF ABSTRACTION served as peers. atlas =
broad CATEGORY, dynamic = specific STORY, umbrella (R2) = the EVENT between. R3
finishes the split-brain arc with an explicit model.

---

## 1. The end-state — a SPINE, orthogonal LENSES, and a deferred RELATION layer

**Correction from the deep review (§11 F1):** the earlier "3 levels" draft was a
SUBSET of the canon object model (`narrative-framework §Core Objects`:
signal/evidence_item/domain_anchor/parent_thread/child_thread/entity_thread/
geo_lens/source_lane/relation/quality_envelope). R3 is that canon, made one
population. Three parts:

### 1a. The compositional SPINE (what a served row IS)
ONE population of STORIES (embedding-discovered, unified-v2 engine). Two grouping
axes ABOVE a story — **they are orthogonal, both real, both needed** (§11 F-C4.1,
the biggest v1 miss):

| level | axis | example | today | R3 |
|---|---|---|---|---|
| **CATEGORY** | ANCHORED-EMERGENT super-cluster (crisis-32 = seed anchors + emergent extensions; open, grows — §3.1) | emergent "Middle East conflict" · crisis-lens "armed conflict" | 30 FIXED `atlas_topics` peer rows | an **attribute** `category`(emergent)+`crisis_class`(seed-32 lens or `non_crisis`)+`category_confidence`; also a filter view. NOT peer rows |
| **EVENT — geographic** | same-event across countries/languages | France Heatwave → {DE,FR,GB} | R2 umbrella (complete-linkage @0.98) | `event_parent` (fold R2 onto the unified population) |
| **EVENT — narrative** | sub-narratives of ONE big story (decision 3) | US–Iran → {base strikes, satellite imagery, water infra, protests} | UNBUILT (US–Iran serves as ~7 flat threads) | `narrative_parent`/`subthread` — the ACTUAL Paper-4 decision 3, **NOT delivered by the umbrella** |
| **STORY** | the specific narrative | "Venezuela Earthquake Death Toll" | `dynamic_topics` | the ONE served population; typed w/ category, optionally under an event |

A story serves standalone (no event_parent, category or OUT_OF_SCOPE) as a
FIRST-CLASS row — the country view's most valuable rows (emerging local-only
stories, R1's win) are exactly the ones with no cross-country event (§11 F-B4.8).

### 1b. Orthogonal LENSES (re-scope the SAME population, already built)
entity / geo / source are NOT levels — they are LENSES over the one population
(`narrative-framework §Product Surface Contract`; `atlas-focus-model`). Already
shipped: focus propagation #234 (`lib/focusRelation.ts` `computeFocusRelation` →
`{kind,value,dominantCountry,relationCountries,relationActive}`, honest-by-
construction), voice mix (source lens: subject≠origin≠language, §11 F-A3.15),
source integrity. **R3 must expose the story so these lenses re-scope it — it
does not invent new lenses.** CRITICAL: a story's `country` is the SUBJECT country;
the SPEAKER (`source_origin_country`) + AUDIENCE (`source_lang`) + `is_state_media`
are the voice lens and must never collapse into one "country" attribute
(voice-relation §1; §11 F-A3.15).

### 1c. The typed RELATION layer (deferred, named — not silently absent)
`narrative-framework §Thread Relations` + `workbench §E` define typed relations
(`supports / contradicts / same_actor_as / same_place_as / frame_contrast_with /
causal_claim / temporal_precedes / regional_spillover / infrastructure_dependency`)
and the `related_threads` contract (co-occurrence/entity/geo siblings — already
shipped as rarity-weighted sibling chips, §11 F-C5.1). R3 does NOT build the typed
relation graph (that is a later spec), but MUST (a) keep serving `related_threads`,
(b) consolidate the THREE existing related-computations (contract `related_threads`
‖ sibling chips ‖ `tm2` co-occ in `THREADS_SQL_TOPIC_MEMBERS`) into one, (c) state
that CATEGORY/EVENT/relationship-type are LENSES on the thread, never peer objects
(`workbench §Terminology`, §11 F-C4.5).

---

## 2. Inventory — ALREADY built (R3 must NOT rebuild)

- **Typed membership** `topic_members` (mig 057), roles evidence/discussion/mood,
  `engine_version` v1-compat + unified-v2 (unified-engine F0).
- **Unified construction v2** `build_unified_topics.py` (F3.1), recurring on the M1
  embed cron; **A/B WINS** (F3.2: coherence 0.930>0.908, black-hole 12.1%<19.0%,
  topics≥3 103>66 = Paper 1's experiment).
- **Recall (R1)** scoped per-country; 68→**418** (392 active served); clears the
  attention-anomaly spec's "recall first" gate.
- **Event-geographic (R2)** `build_umbrella_topics.py`, complete-linkage @0.98
  (single-link CHAINS — must stay complete-linkage; 0.98 not 0.95, both measured);
  26 umbrellas; global dedup + country children LIVE.
- **Taxonomy candidate-v2 (#204)** — **32 categories + an OUT_OF_SCOPE reject
  POLICY** (NOT 33; §11 F-D), κ 0.739 (reject-driven on a non-crisis sample; the
  crisis-only in-category κ is UNMEASURED). **R3.1 repositions these 32 as SEED
  ANCHORS + an editorial lens, NOT the typing target** (anchored-emergent, §3.1). **CORRECTION:** the LIVE prod thing is
  `apply_v2_reject.py` — a **BINARY keep/reject DEMOTER** within existing lexical
  assignments; it does **NOT** assign categories. So **category TYPING is genuinely
  unbuilt**; R3.1 is a new operation on the same e5 substrate, NOT the reject gate
  (§11 F-D-I4-4).
- **The read-flag** `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` (F0.3, default OFF,
  LIST parity PASS). NOTE (§11 F-A4.2): this flag governs the ATLAS-evidence read
  path ONLY; the dynamic/living population serves via `_DYNAMIC_TOPICS_SQL`. F4 must
  converge BOTH paths — the flag alone does not unify serving.
- **Forum ingest (F1)** Bluesky+Lemmy, **F2** social-seed guard.
- **Serving contract already shipped** (must survive cutover): `rank_threads`
  (0.45·log-vol+0.35·movement+0.20·coherence, **no source bias**) + editorial-lane
  damp (lifestyle/sport/entertainment) + `headline_diversity`/single-domain demote;
  the `living-narrative-threads-v0` field set; #214 count semantics; `/signal/{id}/
  context` + `connections-v0`; person→thread `?person=` (atlas-slug matching);
  `research plan` `investigative_score` inputs.

---

## 3. What R3 must do (dependency order)

### R3.1 — CATEGORIZE every story: ANCHORED-EMERGENT, not forced into a fixed 32 (Pedro, 2026-07-01)
**Corrected premise (Pedro's challenge, §11 F-Pedro32).** v1 said "type every story
into 32 fixed categories + reject." Wrong: a fixed, small, CLOSED crisis taxonomy
contradicts the whole open-set/emergent engine (R1/R2 discover emergent topics) AND
*is* the 40–52% precision ceiling — forcing an open world into 32 buckets. The
category level must be as EMERGENT as the story + event levels. Resolution =
**anchored-emergent categories:**
- **The crisis-32 (#204 candidate-v2) are SEED ANCHORS, not the target set** —
  curated, κ-validated, high editorial value. A story near a seed centroid takes that
  crisis class (the comparable, editorial label). The seeds are the category-level
  anchor-guard (same role the #224 anchor centroid plays at the story level).
- **Emergent super-clusters EXTEND the set** — coarse clustering of the story/event
  centroids (one more level of embedding-of-embeddings: story→event→CATEGORY) forms
  NEW categories for what no seed fits. The number GROWS with the world; **32 is the
  crisis FLOOR, not a ceiling.** Anchored (not pure-emergent) so the coarsest level
  doesn't mega-blob into "news."
- **Non-crisis coherent stories** take their emergent category, labeled honestly —
  NEVER force-fit to a crisis class NOR deleted. The **reject/OUT_OF_SCOPE becomes a
  crisis-RELEVANCE flag** (`crisis_class = non_crisis`), an editorial-lens value,
  never suppression (§11 F-C4.6, funnel principle). Folds decision 4 (RE-LABEL
  generic-but-coherent clusters, not gate them).
- So the crisis-32 is **repositioned from "the typing target" to a SEED + an editorial
  LENS** (like entity/geo/source in §1b) over an emergent category level. One move
  resolves Pedro's "why 32/fixed/few," the precision ceiling, and the non-crisis-home
  problem — and keeps the taxonomy's editorial value + Paper-1's measurable crisis
  subset.
- **Store** `category` (emergent id + label) + `crisis_class` (a seed-32 class or
  `non_crisis`) + `category_confidence`. A multi-frame event carries a category
  DISTRIBUTION (§3.3), not one.
- **Wire it into `backend/app/` assignment** (today OUT_OF_SCOPE + excludes live only
  in offline `ensemble/`) — DISTINCT from the shipped reject GATE (`apply_v2_reject.py`,
  a binary demoter, NOT typing; §11 F-D-I4-4).
- **Run on the 30-min classifier cron, NOT nightly** — nightly typing leaves fresh
  stories uncategorized for a day → the badge asymmetry reappears as a TEMPORAL one
  (§11 F-C4.2). R3.4a proves pure-cron work is daytime-safe.
- **Method (E-R3-a, RESOLVED + VALIDATED 2026-07-01, §12):** **DeepSeek is the PRIMARY
  typer.** Validation proved the cheap centroid-vs-seed-prototype COSINE FAILS (sims
  collapse into a 0.78–0.85 band, argmax spurious — "Las Vegas Travel Guide"→Earthquake,
  "Canada Bosnia Draw"→Currency-stress), while DeepSeek types sensibly (crisis→right
  seed, non-crisis sport/travel/legal→honest reject). DeepSeek is cheap + already
  integrated (Pedro's call). **Path B local encoder is the future $0 DISTILLATION** —
  train it on DeepSeek's topic→category labels (the Paper-1 distillation loop) to
  replace the API once it clears the 85–90% gate. Cosine is demoted to a cheap
  candidate-narrowing / emergent-clustering signal, NOT the typer. Shipped:
  `backend/scripts/compute_category_typing.py`.
- **Living-set cadence (Path C):** the anchored-emergent set is re-curated every 4–8
  weeks (promote stable emergent categories to seeds; split/merge/retire) — the
  taxonomy is a LIVING set, the honest answer to "why fixed."
- **Measure:** crisis-anchored precision on a **crisis-only held-out κ split** (with
  Wilson/bootstrap CIs + anchoring control) toward the **90%** north-star; the
  EMERGENT categories are open-set, evaluated on coverage + coherence (Paper 8), not
  fixed-taxonomy precision.

### R3.2 — COLLAPSE atlas to an attribute + F4 cutover (the SERVING SEAM — most of the risk)
Serving stops emitting `atlas_topics` as peer threads; ONE population; `category`
carries the badge; atlas survives as the category vocabulary + a filter view. This
is unified-engine F4. **The cutover MUST carry the shipped serving contract forward
(§11 F-B4.1/4.4/4.5/4.6, C4.3) — any of these dropped = a verified regression:**
- **Ranking:** reuse `rank_threads` + editorial-lane damp + `headline_diversity`
  over the new population, else "Las Vegas Travel Guide"/syndication regress to #1.
  Weights were calibrated on the merged dynamic+atlas pop R3.2 dissolves →
  RECALIBRATE or prove ranking-ORDER parity (not just membership).
- **Both read paths converge:** the F0.3 flag (atlas-evidence) AND `_DYNAMIC_TOPICS_SQL`
  (dynamic/umbrella) must serve from the one model; flipping the flag alone leaves
  dynamic on the old path.
- **Count semantics #214 parity-locked:** `signal_count`(raw) / `gated_signal_count`
  / `gate_scored_count` / `discussion_count` + the UNVERIFIED scored-but-zero tray;
  the umbrella inherits `gated_signal_count`.
- **id-unify survivors:** `/signal/{id}/context` + `connections-v0` (basis
  member/semantic/entity/co-occurrence/keyword), the `slug--cc` parse, person→thread
  `?person=` (atlas-slug `_PERSON_TOPIC_SLUGS_SQL` → must re-point to unified ids),
  focus propagation queries, the two map engines' thread fly-to, the pin-event log
  `plan_id/anchor_id` join, and `merged`-state ALIASES — all need an **id-migration/
  alias map** (§11 F-B4.1/4.6, C1.1/2.11).

### R3.3 — FOLD the R2 umbrella (geographic event) onto the unified population + STABLE id
Re-home `build_umbrella_topics` on the unified population (same complete-linkage
@0.98 — the same-EVENT-not-same-THEME cut; keep it distinct from R3.1's taxonomy
prototypes so the two NEVER cross-contaminate, §11 F-A3.6). **Adopt the stable
umbrella identity NOW** (`umbrella:<min_child_id>` upsert), not deferred — nightly
rebuild churns ids and breaks drill/pins/relationship (§11 F-A4.4). An event carries
a category **DISTRIBUTION**, not a single dominant-child category (a real event is
multi-frame: Iran water = climate+political+conflict+humanitarian; §11 F-C4.7).
Populate the reserved `subthreads` contract field. The narrative-subthread axis
(1a EVENT-narrative) is a SEPARATE, still-unbuilt relation — R3.3 delivers only the
geographic axis; do not claim decision 3 complete.

### R3.4 — the ANOMALY / MOVEMENT brains (unblocked by recall). Disambiguate 3 "movements" (§11 F-A4.8):
(i) the movement-DRIVER taxonomy (9 typed reasons a thread moves — `narrative-
framework`), NOT built, deferred; (ii) `topic_movement` = the volume-vs-baseline
z-score PROPERTY; (iii) the `movement` ROLE = events bound as members.
- **R3.4a — `topic_movement` property (cheap, ships first).** Per-topic volume vs
  168h baseline → z-score, on the 30-min cron. Retires the fake-"critical" lead (the
  L2 CI case; feeds the ALREADY-SHIPPED B1 serving consumer, don't reinvent). **Provider
  precedence must be declared:** it emits the `changed_10h`/`trend`/`velocity_10h`
  shape the thread contract + `investigative_score.movement_signal` read, and it
  either SUPERSEDES or FEEDS the Kalman #219 feed — pick one (§11 F-C4.8).
- **R3.4b — event-`movement` role (#232, the Sudan answer).** Bind `events_v2` (1.02M
  GDELT CAMEO — the Darfur rows in the anomaly panel; `acled_conflicts_v2`=0, dead)
  to the topic by **country+time+entity co-occurrence** (events are NOT embeddable) —
  REUSE `computeFocusRelation`'s relation algebra (§11 F-C5.2), don't invent binding.
  Needs the member-ref schema (R3.0). The event stays independently addressable
  (ConflictEventPanel), never dissolving into the country (P-FOCUS, §11 F-B3.9).

### R3.5 — the ATTENTION brain (trends first, wiki held) + the gap-box consumer
Bind `trends_v2` (24,902/24h) semantically → typed `attention`, `verified=false`
(wiki 1,700/7d HELD on #104). Off-peak pre-embed on the M1 cron (the surface spec
pre-specifies this, §11 F-B2.4). **Wire the INVERSE too:** trends attention with NO
bound topic = `uncoupled-attention`/silent-risk (#168/#172) → feeds the reserved
GAP BOX ("what Atlas can't see"), the honesty-thesis surface R3 v1 left with no
consumer (§11 F-B4.7).

### R3.6 — serve ONE shape + the roles differentiate + lanes R3 v1 omitted
`/threads`, `/theme/{id}`, `/topic/{id}/relationship`, `/signal/{id}/context`,
`connections`, country-view all project from the one model by role + level. The 5
relationship types (#168) differentiate ONLY after F1 forum volume + R3.4/R3.5
populate discussion/mood/movement/attention (data-gated, not just the flip; measure
"what fraction leave media-led", §11 F-D-M5-7). **Add the two omitted serving lanes:**
`forum_sentiment` press-vs-public split (P-STREAM — `mood` members exist; just a
serve-time split by `source_family`, §11 F-B4.3) and the research evidence-role
projection (below).

### R3.7 — dynamic-topic RETIREMENT / lifecycle (B1) — a unified population still ROTS without it
**R3 v1 omitted this entirely (§11 F-A1.9).** Pure-SQL `snapshots_since_seen`/
`last_seen` → active→dormant→retired, so "active" = alive NOW not "ever seen" (54/68
old topics were >3d stale yet active). This is Pedro's retention/resurrection model
(retire from SERVING, keep the row for resurrection) + Paper 8's dynamism sub-claim.
The one population needs lifecycle aging or it accumulates like the old one.

### R3.8 — carry the research evidence-role layer (a SEPARATE attribute on members)
R3's 5 roles (evidence/discussion/mood/movement/attention) are a PROVENANCE
taxonomy; research needs a RHETORICAL one (`primary_event/direct_evidence/
background_context/actor_statement/analysis/reaction/weak_support/contradiction/
osint_verification/noise`), and **`contradiction` is load-bearing for claim
verification** (the Iran "rain theft" forcing case; §11 F-C4.4/2.3). R3 does NOT
build the classifier (Paper 1 Phase 4) but MUST shape `topic_members` so a second
`evidence_role` attribute lands WITHOUT another migration (add the nullable column in
R3.0). R3 must not claim the analyst surface complete while contradiction/credibility
are unbuilt (§11 F-C4.9).

---

## 4. Hard constraints (extracted from the specs + papers)

1. **GDELT-theme removal is ablation-gated (Paper 1's 41.6%).** Themes = optional
   feature; removal needs `gdelt_hint_ablation.py` — **which DOES NOT EXIST yet**
   (§11 F-D-I4-5). This is a BUILD DEPENDENCY, not a checkbox: any theme-hint change
   without the ablation breaks Paper-1 reproducibility. The `KILL` polysemy (armed-
   conflict AND gender-violence) is the concrete defect it must measure.
2. **Honesty invariants (verbatim).** evidence never mixes discussion/mood/movement/
   attention; `gated_signal_count` evidence-only; `verified=false` on social+
   attention+movement; OUT_OF_SCOPE labeled never force-fit AND stays retrievable;
   NO silent filtering — every category/event/role assignment carries a visible
   basis + reason code; no silent blanks (coverage note).
3. **Black-hole #224.** anchor-guard + `leaf` preserved; A/B blocks worsening. No
   global HDBSCAN gives recall+purity (the cliff). Umbrella stays complete-linkage.
4. **F4 gold gate uses a FIXED precise gold set (κ 0.739), NOT production labels**
   (F3.2b — the production-label judge is confounded by label drift). Plus a
   crisis-only in-category split (unmeasured today) for the R3.1 precision claim.
5. **Compute discipline.** Heavy passes off-peak on the M1 embed schedule (crashed at
   load 177). Daytime-safe: schema, pure-SQL movement, 30-min-cron category typing.
6. **Member-ref hot-PK migration** reversible, off-peak, after backing up the v1-compat
   parity check. One DDL serves event-movement + attention + the `evidence_role` column.
7. **INFRA — `statement_timeout`.** Large `vec::text` centroid re-fetches hit the DB
   `statement_timeout` (the SAME failure that froze the embed cron — §11 F-A3.13). Any
   R3 pass re-fetching centroids/vectors at scale (R3.1 typing, R3.3 umbrella, R3.5
   trends) must raise server-side timeout or batch. Concrete, not theoretical.
8. **Preserve the shipped contract fields** (§11 F-C1.7/2.1): `velocity_10h`,
   `sentiment_swing_10h` (ONE product sentiment — nlp, never a competing GDELT tone;
   §11 F-C4.10), `trend`, `anchor_topics` (internal atlas slugs), `subthreads`,
   `related_threads`, `quality{lex_pct,...}` bands, the `investigative_score` inputs,
   `retrieval_lane`/`match_basis` (member_centroid/topic_description/signal_headline).
9. **Recall + taxonomy are the coverage/precision levers; roles ENRICH.** Don't mistake
   role-work for the precision result.
10. **Scope discipline (anti-goal).** R3 = reconciliation of existing capability, no
    new user surface until telemetry (master-consolidation §4). Frontend hierarchy
    rendering stays deferred (§10) — data model first.

---

## 5. Reconciliation of tensions (so nothing regresses)
- **EVENT is two axes** (geographic umbrella ‖ narrative subthread) — R3.3 does the
  first; the second is named-unbuilt. Do not claim decision 3 done.
- **umbrella (R2, on dynamic_topics) vs unified-v2** → R3.3 folds it + stable id BEFORE F4.
- **three artifacts → one** (atlas=attribute+filter, unified-v2=population, topic_members=membership).
- **serving seam** — the whole shipped contract (ranking/counts/context/person) carries forward (R3.2).
- **freshness** — construction stays nightly (3-speed cadence deferred, §10) BUT category (R3.1) + movement (R3.4a) run on the 30-min cron, so the badge/movement are fresh even if FORMATION is nightly (resolves the decision-5 temporal-asymmetry, §11 F-C4.2).
- **taxonomy is the precision lever, not the engine** (F3.2b): R3.1 moves precision; R3.2 buys cleaner topics; measured separately.
- **three related-computations → one** (contract/siblings/tm2, §11 F-C5.1).
- **three movement providers** — declare `topic_movement` precedence vs changed_10h vs Kalman (§11 F-C4.8).

---

## 6. Phases (heavy = off-peak)
- **R3.0 — schema (daytime-safe).** role CHECK += `attention`; `member_kind`/
  `member_ref` (nullable `signal_id`); `topic_movement`; `category`/`category_confidence`
  + nullable `evidence_role` on the topic/member model; `parent_id`/`is_umbrella`
  already exist (R2). Reversible.
- **R3.1 — category typing + #204 wiring (30-min cron).** The precision lever.
- **R3.4a — anomaly→movement (30-min cron, pure-SQL).** Ships early; cheap; fresh.
- **R3.7 — B1 retirement (pure-SQL).** Cheap; keeps the population honest.
- **R3.3 — umbrella-on-unified + stable id + category-distribution (off-peak).**
- **R3.2 / F4 — cutover to one population (off-peak, gated).** Only after R3.1 +
  R3.3 + the §7 gate + the serving-seam carry-forward verified.
- **R3.4b — event-movement (#232, off-peak).** The Sudan answer.
- **R3.5 — attention (trends) + gap-box (off-peak).**
- **R3.6 / R3.8 — one shape, lanes differentiate, forum_sentiment + evidence-role projection.**

Ordering: schema unblocks all; the cheap fresh wins (typing precision, movement,
retirement) before the risky cutover; cutover only after the umbrella is folded +
the seam carries; roles enrich the already-unified surface last.

---

## 7. A/B + acceptance (the cutover gate — extended)
Extend `engine_ab_report.py`. F4/R3.2 flips ONLY when, on the fixed gold set:
- unified-v2 ≥ v1 on coherence, evidence-purity, recall; no worse on black-hole/noise (F3, PASS);
- **R3.1 category typing raises topical precision on the CRISIS-ONLY held-out split** (with Wilson/bootstrap CI + anchoring control), toward the 90% target;
- **cross-source-binding** metric held (does a topic hold press+forum about one event — the unification payoff, §11 F-A4.10);
- **ranking-ORDER parity** (not just membership) or an explicit recalibration of `rank_threads`;
- **count-semantics #214 fields parity-locked**;
- **≥1 EXTERNAL baseline** (BERTopic / flat-embedding / TDT) — Paper 1 AND Paper 8's validation plan REQUIRE it; the internal v1-vs-v2 A/B alone does not satisfy the bar (§11 F-D-M5-10);
- **dynamism curve** (births/deaths/day, median active-age, promotion latency) served + measured (Paper 8 sub-claim, §11 F-D-M5-5);
- honesty invariants hold (no OUT_OF_SCOPE force-fit or suppression; verified=false roles never in `gated_signal_count`).
Each role (movement/attention/typing) independently flag-gated + isolated `engine_version`.

---

## 8. Paper impact + the PAPER-COHERENCE TRACK (PR3 — a work-route, not a note)
R3 delivers paper results (P1 successor-to-41.6% + the taxonomy-precision experiment;
P4 hierarchy + typed membership; P8 recall + multimodal + dynamism; P3 volume≠importance
via movement/attention-as-lens; P7 one topic view). **But the deep read found the paper
canon INCOHERENT + stale, and R3.2 supersedes its benchmark frame (§11 F-D-I4-*).**
Pedro's instruction (2026-07-01): don't patch papers ad-hoc — **build a ROUTE to
document the staleness + work it off.** The route:

- **PR3.0 — the STALENESS LEDGER (the documentation mechanism).** A living doc
  `docs/research/atlas-paper/2026-07-01-paper-staleness-ledger.md`: one row per stale
  claim = `{paper · §/line · claim-as-written · current engine reality · why stale ·
  fix (edit/experiment) · owner · status}`. Seeded from §11 F-D. Every future engine
  change that invalidates a paper number appends a row (the discipline the master-plan
  cross-ref index already broke by lagging to 2026-06-26). This makes "the papers are
  disorganized" a tracked, closeable list instead of a vibe.
- **PR3.1 — declare ONE canonical benchmark regime.** FOUR un-reconciled Atlas
  numbers live in "active" docs: 41.6% (N660 / 3-vendor consensus) · 50.79% (N189 /
  6-model balanced) · 59.02% (N61 reviewed) · learned-gate 90%@64%. Pick the canonical
  regime (recommend the 3-vendor N660 as P1's headline, the others as annotator-panel/
  N variants footnoted), and resolve the 78.6% vs 95.08% LLM split (different gold
  sets = the exact confound P1 warns of). R3.2's "successor to 41.6%" is ambiguous
  until this lands.
- **PR3.2 — re-frame Paper-1's sampling UNIVERSE.** The 30-atlas_topic × 4-bucket
  benchmark measured the CATEGORY layer of a FIXED taxonomy — which R3.1 turns
  anchored-emergent and R3.2 collapses to an attribute. Re-scope P1's benchmark as
  measuring the crisis-anchor precision, and add the open-set category coverage/
  coherence metric (Paper 8) for the emergent extensions.
- **PR3.3 — past-tense the fixed negatives + refresh the index.** P6/master-plan/P8
  assert the frozen lifecycle + "68/30 active topics" in the present; they are fixed
  (former revived; 418/392 served). Rewrite to before/after; append the F0–F4 / R0–R3 /
  candidate-v2 / R3 rows to the master-plan cross-ref index (stale since 2026-06-26).
- **PR3.4 — schedule the required-but-UNBUILT experiments R3 depends on** (each a
  ledger row with an owner): `gdelt_hint_ablation.py` (M5-1, also §4.1 build-dep),
  crisis-only κ split (M5-2), temporal hold-out week (M5-3), ≥1 external baseline —
  BERTopic/flat-embedding/TDT (M5-10, P1+P8 REQUIRE it; the internal A/B doesn't
  satisfy the bar), per-component heat ablation + Kendall-tau (M5-6), Wilson/bootstrap
  CIs + anchoring control (M5-8), dynamism curve (M5-5).

PR3 runs in PARALLEL with the R3 build (it is doc + offline experiment work, no
serving risk), and PR3.1–PR3.2 gate R3.2's headline paper claim.

---

## 9. Decisions — RESOLVED (Pedro, 2026-07-01)
- **E-R3-h — category structure [NEW, Pedro's challenge].** **ANCHORED-EMERGENT**, not
  a fixed 32. Crisis-32 = seed anchors + editorial lens; emergent super-clusters extend
  the set (open, grows via Path C). §3.1. This is the biggest change from v1.
- **E-R3-a — typing method [VALIDATED §12].** **DeepSeek is the PRIMARY typer**
  (cosine seed-prototype FAILS — proven); Path B local encoder = the future $0
  distillation of DeepSeek's labels. Cosine demoted to candidate-narrowing only.
- **E-R3-b — atlas after collapse.** Category vocabulary + filter view + the crisis
  seed-anchor set; removed from the served story list; `anchor_topics` kept internal.
- **E-R3-c — cutover boldness.** Flip ONLY after R3.1 + R3.3 + serving-seam carry-
  forward + the §7 gold gate. Cheap/safe first (typing, movement, retirement, umbrella-
  fold); flip last.
- **E-R3-d — member-ref hot PK.** Extend `topic_members` (member_kind/member_ref +
  nullable `evidence_role`) — one DDL for event-movement + attention + the rhetorical
  role layer.
- **E-R3-e — narrative-subthread axis.** The semantic sub-thread decomposition
  (decision 3's real content, distinct from the geographic umbrella) is a NAMED
  IMMEDIATE FAST-FOLLOW after R3.3, NOT claimed delivered by the umbrella (v1's error).
  Confirm order at build time.
- **E-R3-f — movement provider precedence.** `topic_movement` (z-score) is the
  authoritative velocity provider; it emits the `changed_10h`/`trend`/`velocity_10h`
  shape; Kalman #219 stays a candidate v2 that FEEDS it if promoted, never a competing
  serving provider.
- **E-R3-g — R3 scope (confirmed).** CORE = R3.0/1/3/4a/7/2 (schema, anchored-emergent
  typing, umbrella-fold, movement, retirement, cutover). IMMEDIATE FOLLOW = R3.4b/5/6/8
  + the narrative-subthread axis (E-R3-e). PARALLEL = the PR3 paper-coherence track (§8).

## 10. Deferred (explicitly NOT R3)
Causal cross-vocab linking (unified §14); wiki attention (#104); the hourly/on-read
umbrella + 30-min assignment "ticker" 3-speed cadence UPGRADE (R3 keeps nightly
FORMATION, but note R3.1/R3.4a already deliver 30-min freshness for category+movement);
the typed RELATION graph (1c); the rhetorical evidence-role CLASSIFIER (Paper 1 Phase
4 — R3 only shapes the schema for it); frontend hierarchy rendering (umbrella
expand/collapse, category chips) — data model first.

---

## 11. Deep-review reconciliation ledger (4-agent read of ~20 specs + 9 papers, 2026-07-01)
Every material finding + how this v2 resolves it. F-A = engine agent, F-B = surface
agent, F-C = thread/research agent, F-D = paper agent.

**Framing (biggest):**
- **F-Pedro32** (Pedro, 2026-07-01) "why 32 fixed categories? why so few?" — a fixed
  closed crisis taxonomy contradicts the open-set engine + IS the 40–52% ceiling →
  §3.1 rewritten to ANCHORED-EMERGENT (crisis-32 = seed anchors + emergent extensions,
  the set grows; crisis-taxonomy repositioned to seed + editorial lens). The single
  biggest v2→v3 change.
- **F-C4.1** EVENT conflated geographic (umbrella) vs narrative (decision-3 subthread) → §1a splits them; decision 3 NOT claimed done.
- **F-A4.1** 3 levels ⊂ canon object model → §1 = spine + lenses (1b) + relation layer (1c).
- **F-A3.15 / voice** subject≠origin≠language → §1b keeps subject-country + voice lens separate.

**Category typing (R3.1):**
- **F-D** 32 + reject POLICY, not 33; the LIVE gate is binary reject, not typing → §2 + §3.1 corrected.
- **F-C4.2** nightly typing = temporal badge asymmetry → §3.1 runs on 30-min cron.
- **F-C4.6 / F-C3-dec4** OUT_OF_SCOPE mis-serves coherent non-crisis + decision-4 re-label → §3.1 OUT_OF_SCOPE ≠ suppressed + fold re-label.
- **F-A1.12** Path B encoder ignored → §3.1 / E-R3-a evaluate it.
- **F-D-M5-2 / bucket2-3** crisis-only κ + 90% target → §3.1 + §7.

**Serving seam (R3.2 — the dominant risk cluster):**
- **F-B4.5 / F-C4.3** rank_threads + editorial-lane + headline_diversity + weight recalibration → §3.2 + §7 ranking-order parity.
- **F-A4.2 / F-B** F0.3 flag ≠ dynamic unfreeze → §3.2 both read paths converge.
- **F-B4.4** #214 count semantics parity-lock → §3.2 + §7.
- **F-B4.1/4.6** `/signal/{id}/context`+connections + person atlas-slug matching + id/alias map → §3.2.
- **F-B4.10** two map engines consume thread ids → §3.2 id survivors.

**Umbrella / event (R3.3):**
- **F-A4.4** ephemeral umbrella id → §3.3 stable id NOW.
- **F-C4.7** single inherited category wrong → §3.3 category DISTRIBUTION.
- **F-A3.6** same-EVENT-vs-same-THEME cross-contamination invariant → §3.3.

**Movement / roles:**
- **F-A4.8 / F-C4.8** three "movement" meanings + provider precedence → §3.4 + E-R3-f.
- **F-C5.2** reuse computeFocusRelation for binding → §3.4b.
- **F-C4.10** single product sentiment → §4.8.
- **F-B4.3** forum_sentiment lens unserved → §3.6.
- **F-B4.7** gap-box off uncoupled-attention → §3.5.
- **F-C4.4/4.9** research 11 evidence-roles + `contradiction` unserved → §3.8 (schema-ready, classifier deferred).

**Omitted entirely:**
- **F-A1.9** B1 retirement → §3.7.
- **F-A3.13** statement_timeout blocker → §4.7.
- **F-B4.8** local-only standalone story first-class → §1a.
- **F-C5.1** three related-computations → §1c consolidate.
- **F-A1.3** new-topic labeling under-specced → folded into R3.1 re-label + F3.1 step 5.

**Paper coherence (F-D — a prerequisite):**
- **F-D-I4-1** four un-reconciled precision numbers → §8.1.
- **F-D-I4-2** 30-topic benchmark universe superseded → §8.2.
- **F-D-I4-3** frozen-lifecycle asserted present-tense but fixed → §8.3.
- **F-D-I4-5/M5-1** gdelt_hint_ablation.py unbuilt → §4.1 build dependency.
- **F-D-I4-6** master-plan cross-ref index stale → §8.3.
- **F-D-M5-10** external baseline required (P1+P8) → §7.
- **F-D-M5-5** dynamism curve → §7.
- **F-D-M5-8** CIs + anchoring → §3.1 + §7.

**Verified accurate in v1 (no change):** the unified-engine spine (F0–F4, roles,
A/B discipline, honesty invariants, compute discipline), the member-ref schema, the
recall-done premise, the R2 complete-linkage@0.98 findings, the attention/movement
role split. The spine was right; the review fixed the SEAMS, the second EVENT axis,
the freshness/typing cadence, the omitted lifecycle, and the paper incoherence.

---

## 12. Validation (2026-07-01 — the claims + the riskiest new idea, verified)
This spec is CLOSED + VALIDATED: the load-bearing factual claims were checked against
prod DB + code, and the single riskiest NEW idea (anchored-emergent typing + its
method) was proven with a live PoC before committing to it at scale.

**Facts verified against prod (not asserted):**
- Two populations: `atlas_topics`=30 (typed) ‖ `dynamic_topics` active served (typed
  by R3.7 sweep 392→**348**); `dynamic_topics` has NO `parent_domain` — confirmed.
- candidate-v2 = **32 categories + a reject POLICY** (not 33) — confirmed in the JSON
  (`n_categories: 32`). The live `apply_v2_reject.py` is a binary DEMOTER, not typing.
- `events_v2`=1,023,222 (CAMEO, no text → co-occurrence-bindable, not embeddable);
  `acled_conflicts_v2`=0 (dead); `topic_members` has ZERO `movement` rows — confirmed.
- `gdelt_hint_ablation.py` does not exist (the 41.6% reproducibility gate is unbuilt).

**Built + verified this session (the build has started, not just specced):**
- **R3.0 schema** — migration 059 applied: `topic_members` member_kind/member_ref/
  evidence_role + 'attention' role; `topic_movement`; `dynamic_topics` category/
  crisis_class/category_confidence. Relationship endpoint (live consumer) unaffected.
- **R3.7 retirement** — the bootstrap over-promotion (44 stale 28–36-day topics like
  "Frankie Valli Tour Cancellation" wrongly re-activated) swept to `deprecated`;
  serving 392→348, prod `/threads` confirmed the dead topics gone (reversible, 48 ids
  saved). Pedro's retention model live: retire from serving, keep the row.
- **R3.1 typing** — `compute_category_typing.py`, validated then run:
  - **Cosine seed-prototype FAILS** — 24/30 "anchored" but the argmax is spurious
    (sims collapse into 0.78–0.85; "Las Vegas Travel Guide"→Earthquake, "Canada Bosnia
    Draw"→Currency-stress). This is the F3.2b taxonomy-is-hard finding, reproduced.
  - **DeepSeek types correctly** — 14/14 sensible (Ukraine→Armed-Conflict, Hitzewelle→
    Heat-health, Cepeda→Election-Legitimacy; Las Vegas Travel / World-Cup / class-action
    → honest non_crisis reject). This VALIDATES the anchored-emergent design AND fixes
    E-R3-a to DeepSeek-primary (Path B = future $0 distillation of its labels).
  - Full write DONE: **348/348 typed — 182 crisis (seed-anchored) + 166 non_crisis
    (honest reject, not suppressed)**; top classes Armed-Conflict 57, Earthquake 17,
    Gang-control 17, Constitutional-crisis 14. Every story now carries a category, like
    atlas carried `parent_domain` — the badge asymmetry fixed AT THE DATA LEVEL
    (serving the badge = R3.6). The emergent super-category label for the 166 non_crisis
    is the off-peak clustering follow.

**What remains is engineering with resolved decisions** (no open design questions):
R3.4a movement (gated on membership fullness pre-F4), R3.3 umbrella-fold + stable id,
R3.2/F4 cutover (the serving-seam carry-forward + gold gate), R3.4b/5/6/8 roles, the
narrative-subthread axis, and the PR3 paper-coherence track (§8 ledger). Each is
scoped, constrained (§4), and decided (§9). The design is settled; the risky ideas
are proven.
