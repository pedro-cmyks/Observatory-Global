# Spec — Atlas Engine: GDELT decoupling + syndication-aware ranking

Date: 2026-06-29 · Branch: `v3-intel-layer` · Status: **REVIEW** — investigation
complete; build items gated on §7 answers. Author: Claude (Opus 4.8). Origin:
Pedro's 2026-06-29 engine review ("attack the Atlas engine directly").

Changelog:
- 2026-06-29 a: initial draft (pillars 1/3, paper crossref via subagent).
- 2026-06-29 b: §4B/§4C added (embedding input + bodies) after Pedro's "embedding
  only gets the title" concern.
- 2026-06-29 c: §4B.3/§4B.4 RESULTS run on prod (ablation + clustering sweep) —
  TWO cheap recall hypotheses disproved (mapped in §8). Papers updated (master
  plan P1/P4/P8). Status → REVIEW.

> **This spec is deliberately narrow.** It covers ONLY the two engine changes
> that are (a) high-value and (b) NOT already specced. Everything else from the
> 2026-06-29 conversation is already covered elsewhere — see §1. Do not rebuild
> what exists.

---

## 0. The idea in one sentence

Atlas classifies with a **split brain** (a GDELT-theme lexicon classifier ‖ a
headline-only embedding clusterer) that never reconcile, and ranks threads in a
way that **rewards syndicated copy over real diverse coverage**. This spec
(1) decouples GDELT from the user-facing classifier — gated on a recall
ablation, not by fiat — and (2) adds a syndication-aware ranking term so a
travel ad reprinted across 25 outlets stops outranking a Gaza airstrike.

---

## 1. What is ALREADY covered — do not rebuild

Verified against existing specs/papers (paper crossref agent, 2026-06-29):

| Already covered | Where | Status |
|---|---|---|
| Truncated-surface connection (item → thread, honest gap) | `docs/specs/2026-06-26-truncated-narrative-thread.md` | rev2, partly shipped. Today's SignalDetail "Where this fits" = its **T1.4**. |
| Focus anti-pattern ("fly to UK, talk about UK") | same spec, **T3.3 / P-FOCUS** | specced, not built |
| Label propagation = embedding → **Atlas-topic centroid** (NOT GDELT themes) | `assign_discussion_topics.py`, truncated spec **T2.1** | shipped, threshold 0.90 |
| Threads as first-class unit; unified dynamic+atlas ranking | `docs/specs/2026-05-24-living-narrative-threads.md` (§2026-06-24) | shipped |
| GDELT-themes-are-hints-not-proof guardrail | living-threads spec §Guardrails | canon |

**Correction logged:** the 2026-06-29 idea to "propagate GDELT themes to
non-GDELT rows" is **rejected** — it re-couples GDELT. The shipped Atlas-topic
centroid propagation is the correct mechanism; if non-thread rows need a coarse
bucket, propagate the nearest **Atlas topic**, never a GDELT theme.

---

## 2. Engine diagnosis (verified in code, 2026-06-29)

### 2.1 Split-brain: two parallel classifiers that never meet

1. **Lexicon classifier** → `atlas_topics`, `model_version='theme-hint-lex-v2'`.
   Input = `signals_v2.themes` (GDELT GKG codes) ∩ `atlas_topic.gdelt_theme_hints`
   (set-membership; qualifies with ≥3 theme hits **OR** a `lexicon_terms`
   substring hit on the headline). GDELT is a **hard matching signal here, not a
   soft hint.**
2. **Embedding classifier** → `dynamic_topics`. Input =
   `passage: {headline}` **— headline text ONLY** (`snapshot_emergent_topics.py:330`,
   `embed_hot_corpus.py:108`). e5-base → HDBSCAN → DeepSeek labels survivors.
   **GDELT never touches this path.**

The two layers do not reconcile at classification time. This is the same
split-brain the L2 review named at the alert↔evidence level — it is also true
one level down, at the classifier level.

### 2.2 The `KILL` polysemy — root cause of nonsensical threads

From the seed (`migrations/019_atlas_topic_intelligence.sql:149,169`):

```
'armed-conflict-escalation'  gdelt_theme_hints = ['ARMEDCONFLICT','MILITARY','KILL']
'gender-violence-rights'     gdelt_theme_hints = ['HUMAN_RIGHTS','KILL','PROTEST']
```

GDELT's `KILL` GKG theme fires on **any** "kill/killed/killing" token, including
idioms ("killing it", "killer deal", "dressed to kill"). A travel/sports/
entertainment article → tagged `KILL` → matches a conflict topic via theme-hint.
**This is the mechanism behind the nonsensical conflict threads.** It is direct
evidence that GDELT theme codes are too lexically naive to be hard classifier
hints.

### 2.3 Headline-only embeddings invert priorities

Because the cluster input is the headline alone:
- **Syndicated identical copy** (e.g. one travel article × 25 outlets) → identical
  vectors → a perfect, tight cluster → high coherence → ranks #1.
- **Real diverse coverage** (a Gaza airstrike across languages/outlets/angles) →
  dispersed headlines → a weak cluster → may not promote at all → no thread.

Live proof (prod, 2026-06-29): `dynamic-topic-262` "Las Vegas Travel Guide", 135
signals, ranked **#0** at 24h — all the SAME headline ("Las Vegas: beyond glitz,
discover the desert city's depths") reprinted across ~25 Australian Community
Media regional papers (`.com.au`). Meanwhile a Gaza-airstrike signal with 92–95%
semantic neighbours has **no living thread**.

---

## 3. Pillar 1 — GDELT decoupling (GATED)

**Goal end-state:** GDELT is a raw headline-ingest firehose ONLY. It no longer
(a) appears as user-facing taxonomy, nor (b) acts as a classifier matching
signal.

### 3.1 Two parts, very different risk

- **1a — UI chip removal (LOW risk, ship now):** the "GDELT Taxonomy" chips.
  Already demoted + collapsed in SignalDetail today. No paper claim attached
  (pure legibility). Continue removing/collapsing across surfaces. **No gate.**
- **1b — drop `gdelt_theme_hints` from the classifier (HIGH risk, GATED):**
  this mutates `theme-hint-lex-v2` — the exact system Paper 1's only quantitative
  result (41.6% precision) measured.

### 3.2 The gate (BLOCKING — do not skip)

Before removing `gdelt_theme_hints` in production, run the ablation Paper 1 §7
already lists as "not started":

1. **Recall delta:** on the existing stratified benchmark, how many TRUE
   assignments came *only* via the theme-hint path (no lexicon, no semantic) and
   would vanish?
2. **Semantic recovery:** does the embedding/semantic-assignment path recover
   them? Measure precision/recall of the semantic replacement on the same set.
3. **Decision rule:** remove theme-hints in prod ONLY IF semantic recall ≥
   theme-hint recall on the benchmark (no net true-assignment loss), OR the lost
   assignments are measurably noise (the `KILL`-class false matches).

Artifacts: a `scripts/gdelt_hint_ablation.py` (read-only, repeatable) + a report
under `docs/research/`. Until it passes, theme-hints stay; the work is the
*measurement*, not the deletion.

### 3.3 Note on the real lever

L2 review §3.3 + master-plan P4 split-brain note both point at **gate recall on
non-English** as the deeper reason the classifier fails, not GDELT per se.
Removing GDELT does not fix recall; it removes a *noisy* recall source. The
semantic path must carry the load, and it is throughput-starved (#184). So 1b is
downstream of semantic-classification health, not a standalone win.

---

## 4. Pillar 3 — syndication-aware ranking

### 4.0 MEASURED RESULT (2026-06-29) — `headline_diversity` DISPROVEN; PIVOT

Measure-first (audit `scripts/syndication_audit.py` + raw-corpus SQL via Supabase,
24h) **disproved the `headline_diversity` lever below.** Findings:

- The served evidence sample is already **headline-deduped**, so diversity
  measured on the API reads ~1.0 for everything — the API is the wrong instrument
  (must measure raw `signals_v2`, not the served sample).
- On RAW data, of 506 high-reprint headline groups (≥8 reprints): **482 (95%) are
  clean independent wire** (~1 post per distinct domain) — and they are BOTH real
  news AND filler: "Iran attacks Bahrain" (116 reprints / 115 domains) is
  structurally **identical** to "sausage rolls healthier" (92/92). **Diversity /
  domain-count cannot tell importance from filler.** Worse, the owner-network case
  (Las Vegas × 25 `.com.au` fronts, one owner) posts once per domain → looks
  identical to legit wire. A `headline_diversity` ranking penalty would
  **false-demote real wire news** (the §4.3 risk, realized).

**Pivot (replaces the metric below):**
- **(a) single-domain boilerplate demote** — high reprints from ONE domain
  ("China Daily website connecting China" ×104 / 1 domain). 21 groups / 421
  signals in 24h (4%). Clean and safe: one outlet spamming a template ≠ a story.
- **(b) editorial lane on thread ranking (the real Vegas fix)** — "Las Vegas
  Travel Guide" / "World Cup Live Streams" rank high because they are
  lifestyle/sport/entertainment (low news value), NOT because they are
  syndicated. Apply the existing #177 stream-lane classifier
  (analyst|sports|entertainment|general) to thread eligibility/ranking. This is
  the lever that actually separates the Vegas pathology from "Iran attacks".

The original `headline_diversity` design is kept below STRUCK-THROUGH for the
record. ~~Build it.~~ → disproved; build (a)+(b) instead.

### 4.1–4.4 (DISPROVED — kept for the record)

**The genuinely new contribution.** No existing measurement infrastructure.

### 4.1 Metric

```
headline_diversity = distinct_normalized_headlines / total_signals      (0..1]
```

- Vegas cluster: ≈ 1/135 ≈ 0.007 → syndication.
- Real diverse story: ≈ 0.8 → genuine.

**Normalization (must be defined — exact-match is insufficient):** lowercase +
strip punctuation/whitespace + collapse, THEN near-dup via MinHash/shingle or
trigram Jaccard so "...Travel Guide" and "...Travel Guide 2026" collapse. Exact
match alone will miss templated variants.

### 4.2 Publisher-family collapse (dependency that does NOT exist yet)

25 `.com.au` subdomains = one owner (Australian Community Media). There is **no
source→family map anywhere** in the repo (P2 lists "aggregator-share per thread"
as uncollected). Build `source_family_map` (owner/network → member domains),
seeded from the obvious syndication networks, and a `distinct_publisher_families`
count per cluster. This is shared P2/P4 infrastructure.

### 4.3 How it enters ranking — INPUT, never a GATE

Current: `0.45·log-volume + 0.35·movement + 0.20·coherence` (no diversity term).

- Add `headline_diversity` (and/or `distinct_publisher_families`) as a **damping
  input** on the volume/coherence terms, NOT as a filter.
- **Critical validity guard:** syndicated ≠ unimportant. One legitimate AP wire
  on a real Gaza airstrike IS syndicated. The metric must *down-weight*, never
  *exclude*. A genuinely important wire story still surfaces via movement +
  cross-family spread; only single-family identical copy collapses.
- Surface it honestly: a thread card says "25 outlets · 1 syndicated copy" vs
  "25 outlets · independent coverage". Same N, opposite reading — never hide it.

### 4.4 Validation (paper claim → needs evidence)

- New tooling: `scripts/syndication_audit.py` (read-only, repeatable) + baseline
  artifact, mirroring `voice_mix_audit.py`. Measures the diversity distribution
  over live threads and flags the false-demote rate.
- Becomes a **Paper 4 ablation**: 4-term ranking (with diversity) vs the 3-term
  v1, scored against analyst-judged top-k. Needs the judged labels (don't exist
  yet) — flag as evidence-to-collect, do not claim validity prematurely.

---

## 4B. Embedding input quality (NEW — measured before any re-embed)

Diagnosis recap (verified prod, 168h, 356,531 signals): the embedding input is
`passage: {headline}` only. Field population: **snippet 9.5%** (90.5% have no
body at all), **NER persons 30.6%**, GDELT themes 79.2%, headline avg **132
chars** (a full sentence, not a fragment).

### 4B.1 How embedding "classification" actually works

e5 is **NOT a trained classifier** — it predicts nothing. It maps text → a 768-d
vector where similar MEANING → nearby vectors. Pipeline: embed headline → HDBSCAN
groups vectors by **density** → a surviving cluster = a thread (DeepSeek labels
it) → new signals join the nearest centroid. **Categories EMERGE from
similarity.** Whatever text you embed defines what "similar" means: title-only →
similar = similar wording (why identical syndication clusters perfectly); add
actors → similar = wording + shared actors.

### 4B.2 Which fields help — NOT all of them

e5 embeds WORDS, not numbers/codes; a structured field must be textualized first.

| field | help? | why |
|---|---|---|
| **NER entities** (person/org/place) | **YES** | actors are topical + discriminative. `passage: {headline} \| {entities}`. Coverage 30.6% (partial). |
| **sentiment** | **NO** | non-topical. Two unrelated negative stories must not cluster. Pollutes. |
| **country** | **RISKY** | over-clusters by geography (all Iran together regardless of topic = the "fly to country" anti-pattern at cluster level). Usually already in the headline. |
| **GDELT themes** | **NO** | re-couples GDELT (Pillar 1) + injects KILL-noise. |

Only **NER entities** are worth testing.

### 4B.3 Gate: measure on a SAMPLE before any full re-embed 🔒

A full re-embed (~200K) + re-cluster is a large M1 job, invalidates stored
vectors, and forces all three embed paths (snapshot / hot-corpus / on-demand) to
change together. Do NOT run it blind.

1. Stratified sample (~5–10K, including known syndication + known diverse
   stories like the Gaza cluster).
2. Embed 3 ways: title-only / title+entities / title+entities+country.
3. Cluster each; compare: does enrichment pull diverse real coverage together
   (Gaza recall ↑) WITHOUT degrading the 70% with no NER, and WITHOUT
   over-clustering by geography?
4. Full re-embed ONLY if the sample shows a measured cluster-quality win.

Artifacts: `scripts/embedding_input_ablation.py` + report. Runs on M1 — **free
compute, no API tokens**. Note: enrichment does NOT touch Vegas (identical title
clusters identically either way) — that is §4 diversity. Enrichment is a RECALL
lever for diverse coverage only.

### 4B.4 Clustering-recall sweep (where the ablation actually pointed) — RESULT

Smoke ablation (1039 deduped rows, prod, 2026-06-29) finding:

| variant | gaza_recall | gaza_noise | geo_purity |
|---|---|---|---|
| A title | 0.067 | 0.72 | 0.592 |
| B title+entities | 0.074 | 0.69 | 0.583 |
| C +country | 0.087 | **0.642** ⚠ over-clusters | 0.642 |

**Verdict: the full re-embed is NOT worth it.** Enrichment buys ~1pp recall;
country over-clusters by geography (predicted, confirmed). The DOMINANT problem
is that **~70% of diverse Gaza coverage falls to HDBSCAN noise** — the bottleneck
is clustering RECALL (#229), one level below the embedding input. Entities (B)
stay as a marginal nice-to-have for a *future* re-embed, not a priority.

So the cheap lever WAS a **clustering-param sweep** over a FIXED title-only
embedding (`scripts/cluster_recall_sweep.py`, embed once / cluster many).

**RESULT (smoke, 1074 rows, prod, 2026-06-29) — NEGATIVE, with a purity guard:**

| config | clusters | gaza_recall | gaza_noise | gaza_purity | modal_size |
|---|---|---|---|---|---|
| `leaf mcs5 ms3` (production) | 25 | 0.044 | 0.66 | **1.0** | 20 |
| `eom mcs8 ms1` | 4 | 0.967 | 0.03 | **0.49** | **896** |
| `eom mcs5 ms1` | 35 | 0.053 | 0.50 | 1.0 | 24 |

The eom configs' high recall is a **#224 mega-blob artifact**: the "Gaza cluster"
holds 896 of 1074 rows at 49% purity — it swallowed 84% of the sample, half of it
unrelated. Production `leaf` is NOT a bug: purity 1.0, the fragmentation is the
*price* of avoiding blobs (a correct precision/recall choice). There is **no grid
config with high recall AND high purity** — a cliff between fragmented-pure
(leaf) and merged-impure (eom), no middle.

**Two hypotheses now disproved with data:** (1) embedding enrichment → ~1pp
(§4B.3); (2) clustering-param tuning → blob or shatter, nothing between. The
"cheap lever" does not exist. #229 was right: a recall CEILING, not a quick fix.
Caveat: the smoke sample is Gaza-heavy (~42%, probe-injected) — a representative
8000-row run should confirm, but the cliff structure is unlikely to change.

**The real recall lever = scoped regional/topical clustering passes (#229 lever
2):** pre-filter to a coherent subset (conflict signals, or a country/region),
cluster WITHIN it where the density structure is clean, so a diverse story forms
one pure dense cluster without a global blob. Data-layer work, not a param flip.
Next experiment belongs in the #229 track, not this spec.

## 4C. Article-body fetching in ingest (exploration)

The deepest lever: 90.5% of signals have NO body — for them the headline IS all
the text Atlas owns. Real body text would help clustering far more than
restructuring a 132-char title.

- **Cost:** fetching bodies at 356K/168h = rate limits, ToS/legal exposure,
  latency, storage.
- **Trades against #184 (the true bottleneck Pedro named):** body fetch + NER +
  embed share the M1; more text per signal = slower NER. This makes the
  true-output problem worse, not better.
- **Selective fetch:** fetch bodies ONLY for PROMOTED/served signals (the few
  that become threads), not the firehose. Bounds cost, helps where it matters.
- **Status: exploration.** Needs a feasibility probe — 100 URLs across source
  families, measure fetch-success rate + body quality + legal posture — before
  any commitment. Likely outcome: selective, not firehose-wide.

## 5. Paper crossref & must-verify (from the 2026-06-29 review agent)

| Pillar | Paper(s) | Relation | Gate |
|---|---|---|---|
| 1a chips | P7 legibility | UX, no paper claim | none |
| 1b theme-hints | **P1** (primary), P8 | mutates P1's measured system | **§3.2 ablation BLOCKING** |
| 3 syndication | **P4** (primary), P2 | new ranking term + family map | §4.4 audit + false-demote rate |
| (2/4/5 already canon) | P4/P7/P8 | shipped/specced | fold "done" status in |

**Paper edits needed** (do as the work lands, not before): P1 §6.4 gains a
theme-hint-deprecation subsection + the theme-only/lex-only/semantic ablation;
P4 ranking-ablation gains the `headline_diversity` term; P2 gains the
publisher-family map as consumed-by-P4 infrastructure. Reframe any P8
propagation text to **Atlas-topic centroid, not GDELT themes**.

**Unmodeled cross-pillar chain (write one sentence into P1 §6.7 / P8):**
removing theme-hints → lower recall → fewer threads (#229, 0.2% of signal mass)
→ the truncated-surface "honest gap" fires MORE often. The pieces are known; the
chain is unmeasured.

---

## 6. Work order (hard gates marked 🔒)

1. **1a — finish GDELT-chip removal/collapse across surfaces.** Low risk,
   continues today's SignalDetail work. No gate.
2. **3a — build `source_family_map` + `headline_diversity` computation** (offline,
   read-only `syndication_audit.py` first; measure before touching ranking).
3. **3b — add diversity as a ranking INPUT** (not gate) + honest thread-card
   label. Verify against prod: Vegas drops, real diverse threads hold.
4. 🔒 **1b — GDELT theme-hint ablation** (`gdelt_hint_ablation.py` + report).
   Only AFTER it passes §3.2's decision rule, remove theme-hints in prod.
5. Fold paper edits (§5) as each lands.

Pillars 2/4/5 (truncated surfaces, focus anti-pattern, propagation) continue on
their own spec (`2026-06-26-truncated-narrative-thread.md`) — not duplicated here.

---

## 7. Open questions for Pedro

### RESOLVED (Pedro agreed to recommendations, 2026-06-29)

1. Diversity weight → **conservative damping**, tune up (false-demote risk).
2. Coarse bucket → **defer**; the honest "not connected yet" gap stays until #184.
3. 1b appetite → **theme-hints STAY** until the ablation proves semantic parity.
4. Enriched-embedding sample ablation → done → **disproved** (~1pp); not building.
5. Re-embed scheduling → **moot** (re-embed not happening; hypothesis disproved).
6. Article bodies → **park** (worsens #184); revisit selective-fetch later.

Net: the only build that proceeds is **§4 syndication ranking** (audit first),
plus §3.1a chips and the 🔒§3.2 ablation. Originals kept below for rationale.



1. **Diversity weight:** start conservative (small damping) and tune, or aim to
   actively demote single-family copy hard? (Recommend conservative — false-demote
   risk.)
2. **Coarse bucket:** do non-thread rows need an Atlas-topic propagation *now*, or
   is the honest "not connected yet" gap (shipped today) enough until semantic
   throughput (#184) improves? (Recommend: gap is honest, defer the coarse bucket.)
3. **1b appetite:** are you OK that GDELT theme-hints STAY until the ablation
   proves semantic parity? (This is the disciplined path; the alternative breaks
   Paper 1's reproducibility.)
4. **Enriched embedding (§4B):** approve the SAMPLE ablation (entities only)
   before any full re-embed? (Recommend yes — cheap, M1, no tokens; proves the
   win before the big run.)
5. **Re-embed scheduling vs #184:** a full re-embed competes with NER on the M1.
   Run in idle windows (accept slower NER drain), or defer until the NER backlog
   clears? (Recommend: idle-window, only after §4B.3 proves the win.)
6. **Article bodies (§4C):** want the feasibility probe (100 URLs), or park it
   as a known deep lever until throughput is solved? (Recommend: park — it
   worsens #184; revisit selective-fetch later.)

---

## 8. Investigated alleys (negative results — MAPPED, do not re-investigate)

These were investigated on prod data this session. They are not dead ends — they
are *mapped* terrain. Re-open only with the new lever noted.

| Alley | What we tried | Result | Don't redo unless |
|---|---|---|---|
| **Enrich embedding input** | e5 over `headline + entities (+country)` vs title-only, on a prod sample (§4B.3) | Entities +~1pp recall (marginal); country OVER-clusters by geography (geo_purity ↑). Not worth a full re-embed. | a cheaper recall lever is already exhausted AND a re-embed is happening anyway — fold entities in then. |
| **Tune HDBSCAN params** | grid `min_cluster_size × min_samples × selection` over a fixed title-only embedding (§4B.4) | A CLIFF: `leaf` = purity 1.0 but shatters (Gaza recall 0.04, ~70% noise); `eom`/big mcs = recall 0.97 but a **mega-blob** (896/1074 rows, 0.49 purity = #224 black-hole). No high-recall + high-purity config. | running the representative 8000-row confirm; OR after regional-pass pre-filtering changes the density structure. |
| **GDELT theme codes as classifier hints** | read the seed | `KILL` is polysemous, wired into conflict + gender topics → false threads (§2.2). Confirmed root cause, not a fix attempt. | n/a — feeds the Pillar-1 ablation. |
| **`headline_diversity` ranking penalty** | audit + raw-corpus SQL, 24h (§4.0) | DISPROVEN: 95% of high-reprint is clean independent wire; real news ("Iran attacks", 116/115) is structurally identical to filler ("sausage rolls", 92/92); owner-network fronts (Vegas `.com.au` ×25) look like legit wire. Would false-demote real news. | never as specced — diversity ≠ importance. Replaced by single-domain-boilerplate demote + editorial lane. |

**The lever that survives:** scoped regional/topical clustering passes (#229
lever 2) — cluster within a coherent pre-filtered subset where the density
structure is clean. Belongs in the #229 data-layer track, not this spec.

**The independently-shippable win that survives:** §4 syndication-aware ranking
(`headline_diversity` + publisher-family) — lives in the serving/ranking COUNT
layer, untouched by the recall ceiling. Fixes the visible "Las Vegas #1" symptom.

---

## 9. Implementation TODO

Shipped this session:
- [x] SignalDetail "Where this fits" — render `connected_threads` (member /
  semantic / keyword basis badges) + honest empty state; collapse GDELT taxonomy
  into `<details>`. (`SignalDetailPanel.tsx` + `.css`; = truncated-spec T1.4.)
- [x] `scripts/embedding_input_ablation.py` — §4B.3 ablation harness (run on M1).
- [x] `scripts/cluster_recall_sweep.py` — §4B.4 param sweep + purity guard.
- [x] Paper edits: master plan P1 (KILL motivation) / P4 (headline_diversity) /
  P8 (negative recall result).

Investigated → negative (mapped §8), not building:
- [x] ~~Embedding-input enrichment~~ → ~1pp, not worth re-embed.
- [x] ~~HDBSCAN param tuning for recall~~ → blob/shatter cliff.

Investigated → negative (added 2026-06-29):
- [x] ~~§4 `headline_diversity` ranking penalty~~ → DISPROVEN by measure-first
  (`scripts/syndication_audit.py` + raw SQL, §4.0): diversity ≠ importance,
  false-demotes real wire news. Artifacts `docs/research/syndication/`.

Shipped (the §4 PIVOT):
- [x] **§4(b) editorial lane on thread ranking** (the real Vegas fix): added a
  `lifestyle` lane to `classify_stream_lane` (`stream_relevance.py`) + a
  multiplicative `lane_rank_multiplier` damp in `rank_threads` (`thread_ranking.py`,
  label-based; sports 0.5 / entertainment+lifestyle 0.45; real-news labels →
  general → 1.0). Damp, not gate — threads still appear. Tests +5 (22 pass).
  **Verified on LIVE prod data (re-ranked locally, no deploy): Las Vegas #0→#7,
  World Cup #5→#10; John Bolton / Trump-Iran / Venezuela Earthquake / Ukraine now
  lead, undamped.** Needs a Fly deploy to go live. Limitation: label-only (threads
  don't carry member themes here); keyword sets can grow.

Pending (the §4 PIVOT — measured replacements):
- [ ] **§4(a) single-domain boilerplate demote** (clean, small): high reprints
  from ONE domain → template junk, demote. ~4% of high-reprint groups.
- [ ] §3.1a finish GDELT-chip removal/collapse across remaining surfaces.
- [ ] 🔒 §3.2 `scripts/gdelt_hint_ablation.py` (recall delta) → only then remove
  theme-hints in prod.
- [ ] §4B.3 representative 8000-row confirm run (optional; off Pedro's work hours).
- [ ] (deferred) §4C article-body feasibility probe; entity-enriched re-embed.

Out of scope here (other specs): truncated surfaces / focus anti-pattern /
Atlas-topic propagation → `2026-06-26-truncated-narrative-thread.md`; regional
clustering passes → #229.

---

## 10. Spec ↔ code sync (verification pass)

- **Aligned:** `connected_threads` contract (backend `signals.py:583` →
  `SignalDetailPanel.tsx`); both ablation scripts exist, syntax-checked, smoke-run
  on prod via the M1 `mlvenv` (reuse `emergent_poc._build_embedder/_cluster`).
- **Drift:** none introduced.
- **Gaps (spec promises, not built):** all §9 "Pending" items — by design, gated
  on §7. The biggest is §4 (syndication ranking) — the recommended next build.
