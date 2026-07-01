# Spec — Atlas Engine R3: the unification (one model, 3 levels, all five brains)

Date: 2026-07-01 · Branch: `v3-intel-layer` · Status: **DRAFT for Pedro review**
Author: Claude (Opus 4.8).

**This is a CONVERGENCE spec, not a new invention.** It ties together work that
was built piecemeal across the last ~15 specs and finishes the pieces left
un-flipped. Read alongside — and it supersedes the "next steps" of — these, which
it was written against (not in a vacuum):

- `2026-06-29-atlas-unified-engine.md` — the approved engine (F0–F4). **R3 = F4 +
  F3.3, reframed.** Its `topic_members` typed model + A/B discipline are the spine.
- `2026-06-30-atlas-engine-attention-anomaly-roles.md` — the 5-brains (attention +
  anomaly→movement). Its explicit gate was "recall FIRST" — **recall is now DONE**
  (R1/R2), so its held phases UNBLOCK here.
- `2026-06-30-atlas-engine-recall-scoped-clustering.md` (R0/R1) + `2026-07-01-
  atlas-engine-r2-umbrella-hierarchy.md` (R2) — the topic FORMER R3 sits on.
- `2026-06-29-atlas-engine-gdelt-decoupling-syndication.md` — GDELT-as-feature +
  the `KILL` polysemy + syndication; the ablation gate R3 must respect.
- `2026-05-24-living-narrative-threads.md` (Paper 4) — decisions 3 (hierarchy) +
  5 (any-window). R3 delivers decision 3 as the EVENT level.
- Papers: `2026-06-03-paper-1-result-skeleton.md` (the A/B IS its experiment; the
  40–52% taxonomy ceiling = #204), `2026-06-30-paper-8-result-skeleton.md`
  (recall/coverage), `2026-05-27-atlas-papers-master-plan.md`.

---

## 0. Why this spec exists (Pedro, 2026-07-01)

Pedro, looking at prod, asked the question we keep returning to: *"why are there
still TWO — atlas and dynamic? there should be ONE."* He is right. Verified on
prod today:

```
atlas_topics (lexical, 30, WITH parent_domain)   → badge "CLIMATE DISASTER" etc.
dynamic_topics active (embedding, 418, NO domain) → badge "narrative thread"
fetch_threads:  rank_threads(dynamic + atlas_extra)   ← serves BOTH, merged by score only
topic_members:  v1-compat 29968 · unified-v2 8643     ← the unified engine EXISTS, is not served
dynamic_topics has NO parent_domain column            ← so scoped topics can never be typed
```

Three things where there should be one. The deeper diagnosis (the insight that
organizes R3): **it is not just two pipelines — it is two LEVELS OF ABSTRACTION
served as peers.** An atlas topic ("Constitutional crisis", 2.0k signals, the
whole world) is a broad CATEGORY; a dynamic topic ("Venezuela Earthquake Death
Toll") is a specific STORY; the R2 umbrella ("France Heatwave" across countries)
is the EVENT in between. Flattening category + event + story into one ranked list
is why it reads wrong. The whole split-brain arc has been closing this one seam
from different ends; R3 finishes it with an explicit hierarchy.

---

## 1. The end-state — ONE model, three levels

One population of narrative STORIES (embedding-discovered, the R1/unified-v2
engine). Category and Event are not separate populations — they are an **attribute**
and a **grouping** ON the stories:

| level | what it is | today | R3 target |
|---|---|---|---|
| **CATEGORY** | crisis-taxonomy class (climate disaster, political legitimacy) + the OUT_OF_SCOPE reject class | a separate population of 30 `atlas_topics` | an **attribute** on every story (`category`, from #204 candidate-v2); also a filter view. NOT peer threads |
| **EVENT** | same-event group across countries/languages (France Heatwave DE/FR/GB) | R2 umbrella over `dynamic_topics` (built 2026-07-01) | the EVENT grouping over the ONE unified population (fold R2 in) |
| **STORY** | the specific narrative (Venezuela Earthquake Death Toll) | `dynamic_topics` (R1) ‖ served beside atlas | the ONE served population; every story typed with a category + optionally under an event |

Every served row is a STORY carrying `{category, event_parent, country, roles}`.
"atlas vs dynamic" disappears: atlas becomes the CATEGORY attribute + a category
filter; the badge stops being "climate disaster vs narrative thread" and becomes
"every thread has a category."

---

## 2. Inventory — what is ALREADY built (R3 must NOT rebuild)

The reason R3 is convergence, not invention. Built + verified:

- **Typed membership** — `topic_members` (mig 057), roles evidence/discussion/mood,
  `engine_version` v1-compat + unified-v2 (unified-engine F0).
- **Unified construction v2** — `build_unified_topics.py` (F3.1): every embedded
  signal → nearest active centroid ≥0.88 + HDBSCAN-leaf new-topic formation;
  recurring on the M1 embed cron. **A/B WINS** (F3.2: coherence 0.930>0.908,
  black-hole 12.1%<19.0%, topics≥3 103>66; Paper 1's experiment).
- **Recall (R1)** — scoped per-country clustering; 68→418 served, cohesion 0.968.
  *(This is what CLEARS the attention-anomaly spec's "recall first" gate.)*
- **Event level (R2)** — `build_umbrella_topics.py`, complete-linkage @0.98; 26
  umbrellas; global dedup + country-view children LIVE on Fly.
- **Taxonomy candidate-v2 (#204)** — ensemble-κ gold, **κ 0.739**, the OUT_OF_SCOPE
  reject class + per-category excludes. BUILT + validated, **NOT wired** to
  production assignment/gate (the missing link R3.1 needs).
- **The read-flag** — `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` (F0.3, default OFF,
  parity PASS). The switch R3 flips.
- **Forum ingest (F1)** Bluesky+Lemmy, **F2** social-seed guard.

So R3 wires + flips + folds; it builds only the genuinely-missing roles.

---

## 3. What R3 must do (the gaps, in dependency order)

### R3.1 — TYPE every story with a category (kills the badge asymmetry) — the precision lever
The `parent_domain` badge asymmetry (atlas typed, dynamic untyped) is the visible
face of the split. Fix: **classify every story-topic into the #204 candidate-v2
taxonomy** (33-way + OUT_OF_SCOPE), storing `category` + `category_confidence` on
the topic. Two honest sub-decisions:
- Method: embed the topic's centroid/label + members, classify against the
  candidate-v2 category prototypes (semantic), OR the ensemble prompt on the
  topic label. Start semantic (cheap, local); reserve LLM for low-confidence.
- **This is also the #204 wiring** (the missing production link): the OUT_OF_SCOPE
  reject + per-category excludes go into the classifier, not just the gold set.
- Paper 1 payoff: this is the "does typing every topic move the 40–52% topical
  precision" experiment — the taxonomy lever F3.2b identified as dominant.
- Honesty: a topic that is OUT_OF_SCOPE is **labeled uncategorized, not force-fit**
  (the reject class is the whole point — no fake "Heat-health" for an Amazon-buy).

### R3.2 — COLLAPSE atlas_topics from a population to an attribute + F4 cutover
- Serving stops emitting `atlas_topics` as peer threads. `fetch_threads` serves
  ONE population (the unified stories); `category` (R3.1) carries what the atlas
  badge used to. Atlas survives as: (a) the category vocabulary, (b) a category
  FILTER view ("show all political-legitimacy stories") — NOT rows in the story list.
- This IS unified-engine **F4** (flip `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` →
  serve unified-v2), reframed: the cutover is not just "serve v2 members," it is
  "serve ONE typed population." Gated on the §7 gate.

### R3.3 — FOLD the R2 umbrella into the unified population (event level)
R2 built umbrellas over `dynamic_topics`; F4 serves `topic_members`/unified-v2.
These must reconcile or the umbrella breaks at cutover. R3.3 makes the umbrella a
grouping over the ONE served population (centroid-of-centroids over the unified
topics, same complete-linkage @0.98). The EVENT level then sits natively on the
unified model, not on a soon-to-be-legacy table. (Also: give the umbrella a
`category` from its children — the umbrella inherits the dominant child category.)

### R3.4 — the ANOMALY/MOVEMENT brains (now UNBLOCKED by recall) — answers "how do the events relate?"
The attention-anomaly spec HELD these on recall; recall is done. Two distinct
pieces (verified 2026-07-01: `events_v2`=1,023,222 GDELT CAMEO rows,
`acled_conflicts_v2`=0, `topic_members` has ZERO `movement` rows):
- **R3.4a — `anomaly→movement` (topic property, cheap, ships first).** Per-topic
  volume-vs-baseline z-score → `topic_movement` (attention-anomaly G2). Pure-SQL on
  the classifier cron. Makes each thread carry its OWN movement (retires the
  fake-"critical" lead). No schema change, no #232 blocker.
- **R3.4b — event-`movement` role (#232, the Sudan question).** Bind the conflict
  events (`events_v2` CAMEO — the Darfur "military force" rows the analyst SEES in
  the anomaly panel) to the topic they belong to. Events are **co-occurrence-
  bindable, NOT embeddable** (verified — no text to embed), so binding = country +
  time-window + entity overlap, NOT centroid cosine. Needs the **member-ref schema**
  (attention-anomaly G0: `member_kind`/`member_ref`, nullable `signal_id`). This is
  the direct answer to Pedro's Sudan finding: today the Darfur events and "Sudan
  Conflict Escalation" are two panels that never reconcile; R3.4b makes the event a
  typed `movement` member of the thread.

### R3.5 — the ATTENTION brain (trends first, wiki held) — the 5th brain
Bind Google Trends (`trends_v2`, 24,902 rows/24h — real volume) to topics
semantically (embed keyword → cosine vs centroid), typed `attention`,
`verified=false`. Wiki (`wiki_pageviews_v2`, 1,700/7d, thin) stays HELD on #104.
Reuses the member-ref schema from R3.4b (one DDL, two roles). Recall being done is
exactly what makes this worth it (the topic surface is 418, not 68).

### R3.6 — unify the id namespace + serving one shape
The unified spec kept dual ids (`atlas-slug` / `dynamic-topic-N`) "to unify at F3."
R3 finishes it: one id space for the served population; `/threads`, `/theme/{id}`,
`/topic/{id}/relationship`, country-view all project from the one model by role +
level. The `relationship` 5-types (#168) finally differentiate on real
attention/discussion/movement data (not all `media-led`).

---

## 4. Hard constraints R3 MUST respect (extracted from the specs + papers)

1. **GDELT-theme removal is ablation-gated (Paper 1).** Themes stay an OPTIONAL
   confidence feature; removing them entirely needs `gdelt_hint_ablation.py` to
   prove no recall loss — else Paper 1's 41.6% number stops being reproducible.
   R3.1 uses themes as a feature, never as the category source of truth.
2. **Honesty invariants (verbatim).** evidence never mixes discussion/mood/
   movement/attention; `gated_signal_count` evidence-only; `verified=false` on
   social + attention + movement; OUT_OF_SCOPE is labeled, never force-fit; no
   silent blanks (coverage note instead).
3. **Black-hole #224.** The anchor-guard + `leaf` selection preserved; the A/B
   gate blocks any cutover that worsens black-hole/noise.
4. **F4 gold gate (F3.2b).** The cutover's precision gate must use a **FIXED
   precise gold label set** (the candidate-v2 goldset, κ 0.739), NOT production
   labels — the production-label judge is confounded by label drift.
5. **Compute discipline.** Heavy steps (re-classify, embed trends, umbrella-on-
   unified) run OFF-PEAK on the M1 embed schedule; the M1 crashed at load 177 from
   stacked compute. Daytime-safe: schema, pure-SQL movement.
6. **Hot-PK migration (member-ref).** The `topic_members` PK change is the riskiest
   DDL — reversible, off-peak, after backing up the v1-compat parity check.
7. **Recall/taxonomy are the coverage/precision levers, not roles.** Roles enrich;
   they do not fix coverage (recall, done) or topical precision (taxonomy, R3.1).
   Don't mistake role-work for the precision result (attention-anomaly self-eval).

---

## 5. Reconciliation — the tensions R3 resolves (so nothing regresses)

- **umbrella (R2) vs unified-v2:** R2 sits on `dynamic_topics`; F4 serves
  unified-v2. → R3.3 folds the umbrella onto the unified population BEFORE/with F4,
  so the EVENT level survives the cutover.
- **three artifacts → one:** atlas_topics (category attribute + filter),
  dynamic_topics/unified-v2 (the one story population), topic_members (the
  membership of that population). After R3, "atlas_topics as served threads" is gone.
- **recall sequencing (attention-anomaly spec):** its "recall first" gate is
  CLEARED (R1/R2). Recorded so the held G-phases proceed.
- **taxonomy is the precision lever, not the engine (F3.2b):** R3.2 (engine
  cutover) buys cleaner topics; R3.1 (category typing + #204 wiring) is what moves
  user-facing precision. R3 does BOTH, in that order, and measures them separately.
- **id namespace:** resolved at R3.6 (the unified-spec's deferred F3 decision).

---

## 6. Phases (executable; heavy = off-peak)

- **R3.0 — schema (daytime-safe).** `topic_members` role CHECK += `attention`;
  `member_kind`/`member_ref` + nullable `signal_id` (unlocks R3.4b + R3.5);
  `topic_movement` table; `category`/`category_confidence` on the topic model.
  Reversible. (= attention-anomaly G0 + a category column.)
- **R3.1 — category typing + #204 wiring (off-peak).** Classify every story into
  candidate-v2 (+ reject); wire OUT_OF_SCOPE/excludes into assignment. Measure the
  topical-precision lift on the κ-0.739 held-out split (the Paper 1 number).
- **R3.4a — anomaly→movement (daytime-safe, pure-SQL).** `topic_movement` on the
  classifier cron. Ships early — it is cheap and answers the "critical lead" honesty.
- **R3.3 — umbrella-on-unified (off-peak).** Re-home `build_umbrella_topics` on the
  unified population; umbrella inherits child category.
- **R3.2 / F4 — cutover to one population (off-peak, gated).** Flip serving to
  unified-v2 + collapse atlas to attribute/filter. ONLY on the §7 gate.
- **R3.4b — event-movement (#232, off-peak).** Co-occurrence bind `events_v2` →
  `movement` members via the member-ref schema. (The Sudan answer.)
- **R3.5 — attention (trends), off-peak.** Embed+bind `trends_v2`; wiki held.
- **R3.6 — id unify + serving one shape + relationship types differentiate.**

Ordering rationale: schema first (unblocks everything); the two CHEAP wins
(category typing precision + anomaly-movement honesty) before the risky cutover;
the cutover only after the umbrella is folded so nothing regresses; the event/
attention roles last (they enrich the already-unified surface).

---

## 7. A/B + acceptance (the cutover gate — same discipline as F3/F4)

Extend `engine_ab_report.py`. Cutover (R3.2/F4) flips ONLY when, on the fixed gold set:
- unified-v2 ≥ v1 on coherence, evidence-purity, recall; no worse on black-hole/noise (F3 gate, already PASS);
- **+ R3.1 category typing raises topical precision above the ~40–52% baseline on the κ-0.739 held-out split** (the new gate — the taxonomy lever, measured);
- serving parity holds where it must (the F0.3 parity harness) EXCEPT the intended change (one population, category attribute);
- honesty invariants hold (no OUT_OF_SCOPE force-fit; verified=false roles never in `gated_signal_count`).

Each role (movement, attention) is independently flag-gated + A/B-measured
(`ATLAS_ENGINE_TOPIC_MOVEMENT`, `ATLAS_ENGINE_ATTENTION`), isolated `engine_version`.

---

## 8. Paper impact (the backing — written, not just referenced)

- **Paper 1** — R3.2/F4 delivers the measured SUCCESSOR to the 41.6% number on the
  served unified engine; R3.1 is the "does typing move the 40–52% taxonomy ceiling"
  result (the dominant lever F3.2b named). The unification is reported as a
  5-pipeline reconciliation (3 done + attention/movement measured).
- **Paper 4** — the 3-level hierarchy (category→event→story) IS decision 3
  (hierarchical threads) delivered; typed membership + the differentiated 5
  relationship types.
- **Paper 8** — recall (R1/R2) + the movement/attention roles extend open-set
  discovery to multi-modal (events + attention as modalities); coverage curve served.
- **Paper 3** — anomaly→movement + attention-as-lens (not ranking) = the
  volume≠importance principle, transferred.
- **Paper 7** — press + forum + events + attention in ONE topic view = the analyst
  surface; the category attribute makes the badge honest.

---

## 9. Decisions (need Pedro) + my defaults

- **E-R3-a — category typing method.** *Default:* semantic (centroid vs candidate-v2
  category prototypes) with LLM only for low-confidence; cheap, local, off-peak.
- **E-R3-b — atlas after collapse.** *Default:* keep atlas as the category
  vocabulary + a category FILTER view; remove it from the served story list. *Alt:*
  keep a few genuinely-broad atlas "domain" rows as pinned category headers.
- **E-R3-c — cutover boldness.** *Default:* flip serving to unified-v2 ONLY after
  R3.1 (typing) + R3.3 (umbrella folded) + the §7 gold gate — not before. The three
  cheap/safe pieces (typing, movement, umbrella-fold) land first; the flip is last.
- **E-R3-d — member-ref schema (the hot PK).** *Default:* extend `topic_members`
  (member_kind/member_ref, nullable signal_id) — one DDL serves both event-movement
  (#232) and attention; on-thesis "one typed table." Reversible, off-peak.
- **E-R3-e — scope of R3 vs a follow-up.** *Default:* R3 = R3.0–R3.4 (schema,
  typing, cutover, anomaly-movement, event-movement); R3.5 attention + R3.6 id-unify
  can be a fast follow if R3 gets large. Confirm.

## 10. Deferred (explicitly NOT R3)
- Causal cross-vocabulary linking (unified-engine §14 — still out).
- Wiki attention (thin, #104).
- The hourly/on-read umbrella + the assignment-30min "ticker" (the 3-speed cadence
  upgrade; R3 keeps the nightly cadence).
- Frontend: rendering the category→event→story hierarchy visibly (umbrella
  expand/collapse, category chips) — a UI track once R3's data model lands.
