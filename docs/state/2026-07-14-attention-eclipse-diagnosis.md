# Attention-Eclipse / Under-the-Radar Detection — Diagnosis + Design + Probe

Date: 2026-07-14 · Branch: `v3-intel-layer` · Status: **diagnosis + design + read-only probe complete; no build yet**

> **Scenario (owner).** It is the World Cup; the final is imminent. Global attention
> concentrates on one screen and the information firehose bloats around it. Atlas
> should answer, precisely then: *"while everyone watches the final, what ELSE
> important or anomalous is slipping under the radar?"* — surface the consequential
> stories being drowned out when attention eclipses onto one dominant event. The
> owner believes Atlas cannot do this today.

## TL;DR verdict

**The owner is right. Atlas cannot do this today** — but the missing piece is a
*single additive read-only signal*, not a rebuild, and a live probe proves the
signal separates a genuinely-eclipsed consequential story from quiet noise.

Decompose the question into three needs and grade each against the code:

| Need | Status today | Evidence |
|---|---|---|
| **(c) Consequence proxy** (importance ≠ volume, per story) | ✅ **EXISTS, live** | `global_breadth_signal(langs, countries)` — [daily_edition.py:114](backend/app/services/daily_edition.py:114), wired into edition scoring at [:257](backend/app/services/daily_edition.py:257) |
| **(a) Dominant-event / attention-concentration detector** (window-level) | ❌ **ABSENT** | Nothing aggregates the candidate universe to detect one event dominating; grep for `eclipse\|attention.share\|concentration` finds only delight microcopy |
| **(b) Attention-share ratio + eclipse-gated under-radar surfacing** | ❌ **ABSENT** | No `story_volume / window_total`; the one under-radar heuristic (`quiet_fact`) is a country-level loading-screen fact, [delight_facts.py:73](backend/app/services/delight_facts.py:73) |

And worse than merely absent: **L2 thread ranking makes the eclipse actively
worse.** Volume is a *positive* score term ([thread_ranking.py:30](backend/app/services/thread_ranking.py:30))
so the dominant event ranks **up**, and `global_breadth` is also positive so a
consequential-but-thinly-covered story ranks **down** — with no term that boosts a
story *because* attention is concentrated elsewhere. The only counterweight is a
sports/entertainment lane-damp, which (i) will not fire on a non-sports dominant
event and (ii) is itself unreliable (measured: `classify_stream_lane('armed-conflict-escalation') → sports`, a false positive).

## The three surfaces (file:line evidence)

### L1 Brief (`/brief`) — cannot answer today

`BriefNewspaper.tsx` consumes the sealed daily edition built by
`daily_publication.fetch_daily_publication → daily_edition.select_daily_edition`.
That selection is a **Pareto frontier over 7 ABSOLUTE per-story state dimensions**
(movement_magnitude, surprise, measurement_confidence, evidence_quality,
coverage_breadth, global_breadth, persistence) — [daily_edition.py:260](backend/app/services/daily_edition.py:260),
enumerated at [:472](backend/app/services/daily_edition.py:472). None is
attention-share; none is normalized against a dominant event.

- The consequence proxy `global_breadth` enters as one dimension + reason code — [:257](backend/app/services/daily_edition.py:257). It is the numerator we want, but it is never divided by attention.
- Kalman `surprise` enters as an absolute off-baseline magnitude — [:247](backend/app/services/daily_edition.py:247) — with no cross-story normalization.
- The Pareto frontier **incidentally protects** a quiet-but-consequential story: high on `global_breadth`/`persistence` but low on movement, it can still sit on front 0 and be selected ([_pareto_fronts, :289](backend/app/services/daily_edition.py:289)). But that is multi-objective *diversity*, not eclipse-awareness — nothing detects the dominant event, and the lead/spine (`order_spine_by_publishability`, [:330](backend/app/services/daily_edition.py:330)) will happily seat the eclipsing event at the top.
- Fixed 12-slot layout, **no reserved under-radar slot** — [daily_publication.py:579](backend/app/services/daily_publication.py:579). Dominant and quiet stories compete for the same 12 slots on the same ranking.
- `/brief` has no eclipse/under-radar UI at all — [BriefNewspaper.tsx:494](frontend-v2/src/pages/BriefNewspaper.tsx:494).

### L2 Console (`/app`) — cannot answer today, and ranks against it

- Repo-wide grep for `under.?radar|eclipse|attention.?share|drowned|slipping` returns **zero** hits in `frontend-v2/src`. The eclipse question has no surface.
- Thread ranking: volume is a positive 0.30 term — [thread_ranking.py:30](backend/app/services/thread_ranking.py:30); `global_breadth` is a positive 0.25 term that *penalizes* under-covered stories — [:99](backend/app/services/thread_ranking.py:99); the only mitigation is a sports lane-damp — [:44](backend/app/services/thread_ranking.py:44).
- `AnomalyPanel` surfaces **loud, not quiet**: GEO ALERTS are above-baseline coverage-volume spikes (`current vs 7-day baseline_avg/stddev`) — [AnomalyPanel.tsx:179](frontend-v2/src/components/AnomalyPanel.tsx:179), [indicators.py:114](backend/app/routers/indicators.py:114). Structurally the inverse of an under-radar detector.
- A public-vs-media contrast **does** exist but only as a per-item leaf band — [PublicAttentionPanel.tsx:218](frontend-v2/src/components/PublicAttentionPanel.tsx:218) — never a ranked discovery surface.
- `UniverseView` SURGING/ORPHANS/"fastest rising" filters are all loud/novelty lenses — [UniverseView.tsx:757](frontend-v2/src/components/UniverseView.tsx:757).
- A backend `silent-risk` classifier exists ([topic_relationship.py:71](backend/app/services/topic_relationship.py:71)) and endpoint (`GET /api/v2/attention/silent-risks`, [attention_threads.py:162](backend/app/routers/attention_threads.py:162)) — but **zero frontend consumers** (only `Docs.tsx` mentions it). Dead code relative to the UI.

### L3 Workbench — *partial*: investigation works, discovery/entry does not

- Investigation is **entirely query-driven**: `ResearchPlanPanel` hangs off a typed `query` — [ResearchPlanPanel.tsx:73](frontend-v2/src/components/ResearchPlanPanel.tsx:73). The intent parser knows only geo + 3 hard-coded topic axes (climate/water/conflict_infrastructure) — [research_plan.py:41](backend/app/services/research_plan.py:41), [:140](backend/app/services/research_plan.py:140). There is **no channel to express "consequential-but-drowned-out"** as an investigable intent.
- But once you *have* a story: capture → pin auto-creates an investigation from the query and freezes a #227 evidence snapshot — [ResearchPlanPanel.tsx:125](frontend-v2/src/components/ResearchPlanPanel.tsx:125); coverage gaps are surfaced honestly — [research_anchor_discovery.py:233](backend/app/services/research_anchor_discovery.py:233); who-covers/who-is-silent is computed at dossier via voice-mix + relationship classification — [dossier.ts:137](frontend-v2/src/lib/dossier.ts:137).
- **The loop cannot start**: no surface produces "the 3 stories being eclipsed tonight" as clickables. Hand L3 a query and it investigates well; Atlas cannot tell the analyst *which* story is eclipsed.
- Caveat: "who is silent" is thin in practice — the relationship classifier collapses to `media-led` for ~all atlas topics because discussion/mood member lanes are near-empty (forum ingest thin).

## Data landscape — what is queryable, and the honest caveats

Verified against the live DB (schema introspection + bounded reads).

**Present and sufficient for a COVERAGE-eclipse (read-only, zero schema change):**
- `signals_v2` — atomic coverage: `timestamp, country_code, source_lang, source_family, source_name, source_origin_country, persons, organizations, headline`. The raw material for volume, breadth, distinct-actors.
- `topic_members(role='evidence', assigned_at)` JOIN `signals_v2` — the story→signal read path for per-story volume + breadth ([daily_publication.py:396](backend/app/services/daily_publication.py:396), [migration 057](backend/migrations/057_topic_members.sql:7)). **Live: 41,680 evidence members / 257 topics in the last 24h.**
- `global_breadth_signal` — the consequence proxy, production-wired ([daily_edition.py:114](backend/app/services/daily_edition.py:114)).
- `topic_movement` (Kalman `velocity/surprise/uncertainty`) — per-topic momentum ([migration 066](backend/migrations/066_topic_movement_kalman.sql:6)). **Live: 3,699 rows in 48h.**
- `dynamic_topics` — `category`, `crisis_relevant`, `mean_cohesion`, `is_junk`, `is_roundup` — the DeepSeek-typed lane + quality flags for gating.

**Caveats to state to the owner (each degrades a dimension, none blocks a v0):**
1. **True AUDIENCE attention is unmeasurable against stories.** `wiki_pageviews_v2` and `trends_v2` — the only "what people are actually watching" signals — are decoupled from topics (free-text `article_title`/`keyword`, no `topic_id`), top-N-ranked only (no full distribution → no share denominator), and daily/stale/rate-limited (#104). So "everyone is watching the final" is measurable **only as coverage-VOLUME concentration** (the firehose bloating around the event), a *proxy* for attention. Label it honestly; do not claim eyeballs.
2. **`country_code` is coverage-vs-subject geography (#238).** Geographic-spread measures where a story is *covered from*, not where it is *about*.
3. **`persons` is unverified (#184).** Distinct-actors as a consequence dimension is noisy (NER throughput-starved; gazetteer-typed).
4. **Breadth comes from a bounded receipt SAMPLE**, so `language_breadth`/`country_breadth` are lower-bound estimates; a stale thread with no current members scores zero.
5. **No stored per-window baseline** for "eclipse vs normal day" — compute concentration live per request.
6. `country_heat_v2`/`country_hourly_v2` are **materialized views** (not base tables — hence absent from `information_schema.tables`); the composite `atlas_heat` ([migration 017](backend/migrations/017_country_heat_v2.sql:194)) is country-level, 24h-hardcoded, not per-story.

## Adjacent prior art (reuse, do not rebuild)

- **`global_breadth_signal`** ([daily_edition.py:114](backend/app/services/daily_edition.py:114)) — the consequence-not-volume proxy. The numerator, verbatim.
- **`classify_relationship`** ([topic_relationship.py:71](backend/app/services/topic_relationship.py:71)) — the "ratio reframe" the silent-risk methodology said *would* work (`evidence_fraction < 0.05`), but built for press-vs-public, never generalized to consequence-vs-attention-share, and data-starved (discussion/mood ≈ 0 → everything `media-led`).
- **`silent-risk` scaffold** ([silent_risk.py](backend/app/services/silent_risk.py), [attention_threads.py](backend/app/routers/attention_threads.py)) — a mounted, cached, DB-orchestrating endpoint with lane classification + honest empty states. **The wrong signal** (public Wikipedia attention minus media coverage; its own docstring records the wiki instrument was measure-first *disproved* — "world cup" reads covered) and frontend-dead, but the router structure + honesty conventions transfer directly.
- **`quiet_fact`** ([delight_facts.py:73](backend/app/services/delight_facts.py:73)) — the closest "under the radar" phrasing, but heat-on-low-volume at country granularity, loading-screen-only.
- **`voice_mix` self_voice** ([voice_mix.py:71](backend/app/services/voice_mix.py:71)) — coverage asymmetry (who covers a subject), an orthogonal enrichment for an eclipsed story once found.

The silent-risk methodology doc ([docs/methodology/silent-risk-detection.md](docs/methodology/silent-risk-detection.md)) already reached the right conclusion for its own problem — *"Attention/coverage RATIO, not absolute-zero"* — but the ratio it endorsed was never generalized to **consequence vs. attention-share under an eclipse**. That is the gap this work fills.

## Live probe — proving the signal separates (read-only)

Script: [backend/scripts/probe_attention_eclipse.py](backend/scripts/probe_attention_eclipse.py) (repeatable, read-only, reuses `global_breadth_signal`). Run over the last 24h against production data.

```
WINDOW = last 24h · topics(>=3 evidence) = 249 · total coverage = 41,669
(a) ECLIPSE DETECTOR — REAL NOW: top1=4.5%  top3=12.2%  HHI=0.0165  ->  DIFFUSE (no dominant event; signal stays quiet)
    SIMULATED WC-FINAL (dominant at 45% share): top1=45.0%  HHI=0.2075  ->  ECLIPSE DETECTED
```

**Finding 1 — the detector separates cleanly and is honest by construction.**
Today attention is *diffuse* (top story = 4.5% of coverage, HHI 0.0165) → there is
no eclipse → the signal correctly stays quiet. Inject a WC-final-scale dominant
event (45% share) → top1 jumps to 45%, HHI to 0.21 → eclipse detected. A single
`top-1 share ≥ 0.20` threshold (or HHI vs a rolling baseline) is a clean gate. The
signal does **not cry wolf** on an ordinary day.

**Finding 2 — the naive consequence/attention RATIO is WRONG (measured negative result).**
The first cut ranked by `consequence / attention_share`. It exploded on tiny
denominators and surfaced local trivia — *"Bull gores runner in the face"*,
*"Kanye concert in Albania"*, *"Assassin's Creed review"* — all at attention ≈ 5,
one language, consequence ≈ 0.4. These are quiet **noise**, not eclipsed news. The
ratio penalizes genuinely consequential stories (Ukraine, Palestinian children)
for *already* having coverage. **Do not use the raw ratio.**

**Finding 3 — a CONSEQUENCE FLOOR + low-share ordering + quality gates separates genuinely.**
Gate to stories that are multi-language **and** multi-country (`L≥3 & C≥8`), drop
junk/roundup and low-cohesion clusters, classify the sports/entertainment lane via
the **DeepSeek-typed `dynamic_topics.category`** (not the buggy keyword classifier),
then order by *lowest attention share*. The under-radar set becomes genuinely
consequential-but-quiet:

```
UNDER-RADAR (consequential, quality-gated, lane=general) — lowest attention share first:
  att= 42 share=0.10% L 4/C18  EU launches $1 billion initiative … (Gaza €900m, Intel €5bn, German chip aid)
  att=120 share=0.29% L 3/C17  US Bombards Iran Over Ormuz Attack           (vel +0.46, rising)
  att=141 share=0.34% L 4/C23  Mexico Seeks ICE Death Charges
  att=142 share=0.34% L 5/C34  Denmark Rejects Trump Greenland
  att=152 share=0.36% L 7/C28  Maďarský parlament schválil zmenu ús…        (Hungary constitutional change)
  att=205 share=0.49% L11/C46  Oštra rasprava o Srbiji u EP…                (Serbia debate, EU Parliament)
  att=138 share=0.33% L 5/C28  election-legitimacy-dispute
LABELED-OUT (classified, never silently hidden):
  att=673 L5/C56  lane:sports       Trump FIFA World Cup Scandal
  att=365 L5/C55  lane:sports       Sports and Politics Mix
  att=195 L3/C17  junk              (Yazd cluster)
  att= 90 L8/C36  roundup(label)    "Naslovne strane za sredu" (front-pages container — spurious breadth)
```

These are real, consequential, multi-country events sitting at 0.1–0.5% of
coverage. During a 45%-eclipse they are exactly what is being drowned out — and
the gates correctly hold back the FIFA scandal (sports, *labeled* not dropped, per
the no-silent-filtering guardrail), a junk cluster, and a daily front-pages
roundup whose breadth is spurious.

**Finding 4 — honest residuals (the signal RANKS, it does not CERTIFY).**
Two items still slip through: *"Lauren Bennett kimdir?"* (att 20 — an incoherent
grab-bag of unrelated celebrity items whose `mean_cohesion` reads 0.92, the #204
label-precision ceiling of ~40–52%) and *"Actor Sam Neill … dies"* (a celebrity
obituary the category typing missed). The eclipse signal **surfaces candidates**;
individual certification still needs the daily-edition publishability checks
(subject-geography verified, not a grab-bag umbrella — [daily_edition.py:330](backend/app/services/daily_edition.py:330))
plus an analyst's eye. It must never be presented as ground truth.

## Design — the attention-eclipse signal

One additive, read-only signal that reuses the existing consequence machinery and
the shared story graph. **No parallel truth model, no schema change.**

**1. Eclipse detector (window-level).** Over the candidate universe (topics with
≥3 current evidence members), compute coverage-volume shares → `top1_share` +
`HHI`. Declare `eclipse=ON` when `top1_share ≥ τ` (probe suggests ~0.20) or HHI
exceeds a rolling-baseline multiple. Emit the dominant event + its share. Label:
**"coverage-volume concentration — a proxy for attention, not audience eyeballs."**
On a diffuse day the detector is OFF and the surface shows nothing.

**2. Consequence score (per story).** REUSE `global_breadth_signal(langs, countries)`
(numerator) + `topic_movement.velocity/surprise` (a rising eclipsed story beats a
stale one) + distinct distinctive-actors from `persons` (*labeled unverified*, #184).

**3. Attention share (per story).** `evidence_members(topic) / window_total` — new,
trivial, read-only.

**4. Under-radar ranking.** Among stories that clear a **consequence floor**
(multi-language AND multi-country) and **quality gates** (not junk/roundup,
cohesion floor, editorial lane by `dynamic_topics.category` — sports/entertainment
**labeled, not dropped**), rank by **lowest attention share**, gated on
`eclipse=ON`. Every row carries a reason-coded ledger, mirroring `daily_edition`.
Not a raw ratio (Finding 2).

**Surfacing per layer (reuse existing contracts):**
- **Backend (the missing primitive):** new pure module `attention_eclipse.py` (TDD)
  + read-only `GET /api/v2/attention/eclipse`, built as a **sibling of the parked
  silent-risks router** ([attention_threads.py](backend/app/routers/attention_threads.py)) — reusing its cache, lane
  classification, and honest empty states, and `daily_edition`'s ledger pattern.
- **L1 Brief:** a reserved **"MEANWHILE, OFF THE FRONT PAGE"** strip, rendered
  *only when `eclipse=ON`*, in the #172 gap-box slot — a reserved slot, so the
  eclipsing event's shadow can't bury it in the 12-slot competition.
- **L2 Console:** promote the per-item PUBLIC-vs-MEDIA band ([PublicAttentionPanel.tsx:218](frontend-v2/src/components/PublicAttentionPanel.tsx:218))
  into a ranked **"Under the Radar"** lens, with an eclipse banner ("One story holds
  N% of coverage — here's what's underneath"). Optionally fold a concentration
  factor into `rank_threads` (calibratable, gated) so consequential low-share
  stories aren't buried *during* an eclipse.
- **L3 Workbench:** each eclipse item is a clickable emitting a `query`/`thread_id`
  → reuses the pin→plan→dossier ramp ([ResearchPlanPanel.tsx:125](frontend-v2/src/components/ResearchPlanPanel.tsx:125)) unchanged; the
  dossier's voice-mix + relationship classification already answers
  "who covers it / who is silent." This closes the surface→investigate loop.

## Recommended first build slice

**Ship the backend read-only signal + `GET /api/v2/attention/eclipse` first.** It
is the one primitive all three surfaces need; it is pure and TDD-able (the eclipse
detector, consequence floor, and under-radar ranking are pure functions over
supplied rows); it requires zero schema change and reuses `global_breadth_signal`,
the `topic_members→signals_v2` join, and the silent-risks router scaffold; and the
probe already demonstrates it ships honest — the detector gates it (diffuse day →
empty), the consequence floor + quality gates are proven necessary, and every row
is reason-coded. L1's reserved strip and L3's pin ramp are thin follow-ons.

Suggested test cases (freeze the probe's findings): detector OFF on a diffuse
distribution / ON at ≥τ; naive-ratio trivia excluded by the floor; junk/roundup/
sports labeled-out; a consequential low-share story ranked above a quiet noise
story; empty/honest output when `eclipse=OFF`.

## What Atlas cannot do (state plainly)

- It cannot measure **audience** attention (eyeballs on the final). The signal is a
  **coverage-volume** eclipse proxy; wiki/trends can't be attributed to stories.
- It cannot **certify** an individual under-radar story is real news — the
  label-precision ceiling (#204) lets grab-bags and obituaries slip; the signal
  ranks candidates for an analyst, it does not adjudicate.
- Geographic spread is **coverage-from**, not **about** (#238); distinct-actors is
  **unverified** (#184). Both are honest lower-signal dimensions, not ground truth.

## Build — backend signal shipped (TDD, 2026-07-14)

The first slice is built and verified (not deployed).

- **Pure logic:** [backend/app/services/attention_eclipse.py](backend/app/services/attention_eclipse.py) — `attention_concentration` (detector), `consequence_score` (reuses `global_breadth_signal` + Kalman movement), `lane_of` (DeepSeek-category typing, fixes the `armed-conflict-escalation→sports` bug), `select_under_radar` (consequence floor + quality gates + lowest-share ordering, reason-coded ledger, no silent filtering), `assemble_eclipse` (rows→detector→gated selection).
- **Tests:** [backend/tests/test_attention_eclipse.py](backend/tests/test_attention_eclipse.py) — 19 tests, RED→GREEN. Freeze the probe findings: detector diffuse-vs-eclipse, consequence reuse + bounds, the lane-bug regression, naive-ratio trivia excluded by the floor, quality classes labeled-out (not dropped), quiet-when-no-eclipse. 73-test neighborhood regression green.
- **Endpoint:** `GET /api/v2/attention/eclipse` — [backend/app/routers/attention_eclipse.py](backend/app/routers/attention_eclipse.py), mounted [main_v2.py:178](backend/app/main_v2.py:178). Read-only, sibling of the parked silent-risks router.
- **Live end-to-end verified:** default 0.20 gate → DIFFUSE → eclipse=false → 0 surfaced (honest quiet); forced 0.04 gate → ECLIPSE → surfaces the real under-radar set (EU aid, US-Iran Ormuz, Mexico ICE, election-legitimacy), ledger complete (249/249). Residuals (grab-bag, obituary) still slip — the label-precision ceiling (#204), which the parallel event-grouping/classification work fixes.

### How eclipse relates to velocity and breadth (three readings of one shared state)

The signal does **not** invent a new truth — it is a third reading of the same
per-story state the rest of Atlas already computes:

| Axis | Question | Source | Reading |
|---|---|---|---|
| **breadth** (`global_breadth_signal`) | how globally consequential? | languages × countries | ABSOLUTE, spatial |
| **velocity / surprise** (`topic_movement`) | is it moving / off-baseline? | Kalman over coverage volume | ABSOLUTE, temporal |
| **attention share** (eclipse, NEW) | how much of the room is it taking vs everyone else? | story volume ÷ window total | **RELATIVE, field-level** |

`consequence = 0.6·breadth + 0.25·|velocity| + 0.15·surprise` (breadth is the
consequence anchor; velocity/surprise sharpen a *rising* eclipsed story above a
fading one — in the probe, "US Bombards Iran" carried velocity +0.46). **Eclipse =
high consequence ∧ low attention-share ∧ field concentrated.** Breadth and velocity
say *how important*; attention-share says *how visible*; eclipse is the gap between
them under a concentrated field.

**Why this is one thread with the classification work.** All three axes are computed
*over a story's member set*. If an event is fragmented across topics (the gap-2
problem — e.g. the live US-Iran event split across `{121, 583, 881}`), its breadth is
undercounted and its attention-share is split three ways, so it reads quieter and
*less consequential* than it is; if members are mislabeled (grab-bag, wrong lane) the
gates misfire (the "Lauren Bennett" residual). **Correct event-grouping + correct
labels upstream directly sharpen this signal** — the owner's intuition is right: the
eclipse is only as honest as the classification underneath it.
