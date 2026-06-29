# Spec — Atlas Unified Engine (one engine, typed membership, measured cutover)

Date: 2026-06-29 · Branch: `v3-intel-layer` · Status: **APPROVED** (design +
spec approved by Pedro 2026-06-29; §17 decisions resolved). Author: Claude
(Opus 4.8). Companion to
`docs/specs/2026-06-29-atlas-engine-gdelt-decoupling-syndication.md` (the engine
diagnosis this builds on) and `docs/specs/2026-06-24-community-signal-layer-design.md`
(#237).

> **The idea in one sentence.** Atlas builds narrative topics through 2–3
> independent pipelines that produce different outputs and never reconcile (the
> "split-brain"). Replace that with ONE engine: any signal — press, forum,
> event — enters, is assigned to a topic over a universal substrate (the
> embedding), and is written to ONE typed-membership table; the separation of
> press/forum/evidence/discussion happens at the SERVING layer (by role), not by
> having separate construction pipelines. **Unify the construction, separate at
> serving.** Cutover is hybrid: serving unifies now, construction is rewritten
> behind a flag and A/B-measured, and the switch flips only when the numbers
> prove parity or improvement.

---

## 1. Problem (verified, 2026-06-29)

1. **Split-brain construction.** Three paths that never meet (traced in code):
   - `atlas_topics` via `theme-hint-lex-v2` — GDELT theme-hints ∩ themes OR
     headline lexicon.
   - `dynamic_topics` via emergent HDBSCAN over `passage: {headline}` embeddings.
   - `assign_discussion_topics` — social rows attached to atlas centroids
     (`semantic-discussion-v1`, `gate_kept=false`).
   They write different rows, rank differently, and a forum signal and a press
   signal about the SAME real event cannot land in the same topic.
2. **GDELT asymmetry.** Only GDELT rows carry `themes`, so only they get the
   theme-hint classification aid. RSS/forum signals are second-class in
   classification. An uneven feature that "doesn't favour the one that has it" —
   it penalises everyone else.
3. **Forum is bolted on, not integrated.** Reddit is a discussion-attach
   afterthought; it cannot contribute to a topic's formation or sit in one topic
   beside the press coverage of the same situation.
4. **Different outputs per path.** `/threads`, the discussion lane, and the
   (parked) silent-risk surface are three shapes from three pipelines, instead of
   one model the serving layer projects different views from.

---

## 2. The unifying structure — `topic_members` (typed membership)

ONE assignment table every path writes to; serving reads it filtered by role.

```sql
CREATE TABLE topic_members (
  signal_id      BIGINT  NOT NULL REFERENCES signals_v2(id),
  topic_id       TEXT    NOT NULL,            -- atlas slug or 'dynamic-topic-<n>'
  role           TEXT    NOT NULL CHECK (role IN
                   ('evidence','discussion','mood','movement')),
  source_family  TEXT,                        -- press|social|ngo|gov|event
  basis          TEXT    NOT NULL CHECK (basis IN
                   ('semantic','lexical','theme','co_occurrence')),
  confidence     REAL,
  gate_kept      BOOLEAN,                     -- evidence only: cleared the gate
  engine_version TEXT    NOT NULL,            -- 'v1-compat' | 'unified-v2'
  assigned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (signal_id, topic_id, role, engine_version)
);
CREATE INDEX idx_topic_members_topic ON topic_members (topic_id, role, engine_version);
CREATE INDEX idx_topic_members_signal ON topic_members (signal_id);
```

**Roles (the separation that happens at serving, not construction):**
- `evidence` — press/institutional, gate-scored; the verified spine of a thread.
- `discussion` — forum/social; public conversation; `verified=false`, never
  evidence (preserves the existing honesty invariant).
- `mood` — forum sentiment/concern signal (the "what the public feels/fears"
  lane; see §9.3). A discussion member can ALSO carry mood.
- `movement` — event/movement signals (vessels, aircraft, ACLED conflict,
  anomalies) bound to a topic by co-occurrence (closes #232).

**`engine_version`** is what makes the hybrid A/B possible: `v1-compat` rows are
an ETL projection of today's assignments; `unified-v2` rows are the new engine's
output. Serving reads whichever the flag selects; the A/B compares the two over
the same window.

---

## 3. Universal substrate + GDELT-as-feature (kills the asymmetry)

- **Embedding is the substrate.** Every signal has one (`passage: {headline}`,
  e5). Assignment = cosine similarity to a topic centroid. This is the only
  feature ALL sources share, so it is the spine of the unified engine.
- **GDELT themes + lexicon = optional confidence-boost FEATURES, not a path.** A
  signal that also matches a topic's `gdelt_theme_hints` or `lexicon_terms` gets
  a confidence bump (`basis='theme'/'lexical'` recorded), but a non-GDELT signal
  is never disadvantaged — it assigns on the universal embedding feature alone.
  The asymmetry disappears because the engine no longer DEPENDS on a
  source-specific feature.
- **GDELT-theme removal stays gated** on the P1 ablation
  (`gdelt_hint_ablation.py`, the companion spec §3.2): we demote themes to a weak
  optional feature now; whether to drop them entirely is decided by measured
  recall delta, not fiat (protects Paper 1's reproducibility). The `KILL`
  polysemy finding motivates the demotion.

---

## 4. Data flow

```
IN     signals_v2 (GDELT · RSS · forum/social · events) + e5 embedding + nlp_*
ENGINE assign to topic:
         - semantic: centroid similarity (universal)
         - + theme/lexical confidence boost (optional, GDELT rows)
         - role from source_family + gate (press→evidence, social→discussion/mood,
           event→movement)
       → write topic_members (role, basis, confidence, gate_kept, engine_version)
OUT    /threads          → role='evidence' spine, ranked (editorial-lane damp etc.)
       /theme/{id}       → + discussion lane (role='discussion') + mood (role='mood')
       /topic/{id}/relationship → the 5 #168 types from role-count ratios
       attention/silent-risks   → re-homed on the discussion/evidence ratio (#172)
```

---

## 5. Hybrid strategy (the approved cutover)

| stage | construction | serving | risk |
|---|---|---|---|
| **now (v1)** | atlas ‖ dynamic ‖ discussion-attach | reads the 3 paths | — |
| **F0** | unchanged | reads `topic_members` (`v1-compat` ETL of the 3 paths) | low — output-shape change only |
| **F3** | + `unified-v2` behind flag `ATLAS_UNIFIED_ENGINE` | flag selects v1-compat or unified-v2 | isolated by flag |
| **F4** | unified-v2 only | unified-v2 | flip only when A/B proves v2 ≥ v1 |

The construction is NEVER swapped blind. Serving unifies first (safe), then the
new engine runs in parallel under a flag and is measured before it serves anyone.

---

## 6. Construction v2 — the unified pass (F3)

One cron pass (extends `snapshot_emergent_topics` / persisted clustering):
1. Pull the embedded corpus (press + forum + event signals), stratified (#229).
2. **Cluster / assign**: a signal joins the nearest existing topic centroid above
   threshold; unassigned dense regions form new dynamic topics (HDBSCAN, `leaf`
   selection + #224 anchor-guard preserved). GDELT theme/lexicon match adds a
   confidence boost where present.
3. **Role assignment** from `source_family` + gate score:
   press/ngo/gov → `evidence` (with `gate_kept`); social → `discussion` (+`mood`
   if it carries sentiment/concern); event → `movement`.
4. Write `topic_members(engine_version='unified-v2', basis=…)`.
5. DeepSeek labels new topics (unchanged).

Honesty invariants carried from v1: discussion/mood/movement are NEVER counted as
evidence; `gated_signal_count` stays evidence-only; `verified=false` on social.

---

## 7. Forum-ingest layer (F1) — diversify beyond Reddit

From the 2026-06-29 forum-research agent. Land all as `source_family='social'`,
`source_origin_country` from the instance/channel (mirrors the RSS WAVE-N model),
typed `discussion`/`mood` at serving.

| priority | source | access | country tag |
|---|---|---|---|
| 1 | **Bluesky (Jetstream)** | WS `jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post`, lib `atproto` | lang only (NER geo) |
| 2 | **Lemmy** | `GET /api/v3/post/list?sort=New` per instance | **instance = country/lang** |
| 3 | **Mastodon** | `GET /api/v1/trends/links` + public timeline per instance | **instance = country** |
| 4 | **Telegram** | MTProto (Telethon, free api_id) or RSSHub | **channel = country** |
| 5 | Hacker News | `hn.algolia.com/api/v1/search_by_date?tags=story` | weak |

Plus Discourse (`/latest.json`, national forums) and phpBB/vBulletin RSS
(ForoCoches/Nairaland/4PDA-class) as the WAVE-N "one verified forum per country"
program. Verify-before-build: Stack Exchange limits + CC-BY-SA attribution;
Jetstream field schema; per-instance public-timeline availability; 4chan rehosting
ToS = excluded.

**F1 starts with Bluesky + Lemmy** (highest volume + cleanest country tag,
lowest integration cost), each a small ingest worker writing to `signals_v2`.

---

## 8. `source_family` guard on clustering (F2) — protect the engine before scaling

Today social is a negligible 24/44,209 of the embedded corpus, so it does not
pollute clusters. As F1 scales forum volume, daily-life chatter ("where can I buy
a cardigan") would enter cluster SEEDING. F2 adds a guard: social signals may
ATTACH to existing topics (discussion role) but do NOT SEED new clusters — only
press/institutional signals seed. This keeps the topic spine press-anchored while
forums enrich it. (A measured exception can be revisited for high-signal forum
events.)

---

## 9. Serving (unified) — one model, many views

### 9.1 Thread list / detail
`/threads` reads `role='evidence'` (ranked by the existing
volume+movement+coherence + editorial-lane damp). `/theme/{id}` adds the
`discussion` and `mood` lanes as separate, labelled sections. Counts served
separately: `evidence_count` / `discussion_count` / `mood_count` / `movement_count`.

### 9.2 The 5 relationship types (#168) — computed, not a new pipeline
Per topic, from role-count ratios:
- **media-led**: evidence ≫ discussion
- **public-led**: discussion high, evidence low
- **social-led**: discussion dominates, little/no press
- **silent-risk**: discussion/mood present, evidence ≈ 0 (the #172 ratio reframe —
  a relative imbalance, not the disproved absolute-zero metric)
- **uncoupled-attention**: attention with no topic binding (the honest gap)

New endpoint `GET /api/v2/topic/{id}/relationship`.

### 9.3 Mood / public-concern lane (the "carala cotidiana" value)
Daily-life forum chatter IS signal of public concern (cost of living, safety,
services) — the public agenda vs the media agenda. The `mood` role aggregates
forum sentiment + concern per country/topic into a public-mood lane, served
SEPARATELY from evidence (never fused into the thread's verified spine). This is
the honest home for the chatter Pedro flagged — a second lens, not thread
evidence.

---

## 10. Phases + acceptance

- **F0 — typed model + unified serving (no construction change).** Migration for
  `topic_members`; `v1-compat` ETL normalising current assignments
  (`theme-hint-lex-v2`→evidence, `semantic-discussion-v1`→discussion); `/threads`
  + `/theme` read `topic_members`. *Accept:* prod `/threads` order + counts match
  the current path (parity), discussion lane unchanged. Closes the serving half
  of #168/#172.
  - **Constraint discovered (2026-06-29, F0.2):** atlas topics have FULL
    per-signal membership (`signal_topic_assignments`); dynamic topics have only
    `emergent_clusters.sample_signal_ids` (a capped ~24 sample, via
    `dynamic_topic_members`→`emergent_clusters`). So `v1-compat` projects atlas
    fully + dynamic by its SAMPLE; full per-signal dynamic membership is a
    BENEFIT delivered by `unified-v2` (F3). F0 `/threads` parity is on the LIST
    (aggregate counts), not full dynamic membership.
- **F1 — forum ingest (Bluesky + Lemmy).** Two ingest workers → `signals_v2`
  social with `source_origin_country`. *Accept:* live posts land country-tagged,
  embedded, attached as discussion members. Advances #237/#235.
- **F2 — `source_family` clustering guard.** *Accept:* social no longer seeds
  clusters (verified on a scaled-forum window); #224 black-hole rate unchanged.
- **F3 — unified construction v2 behind flag + A/B harness.** *Accept:* v2 writes
  `topic_members(unified-v2)`; `scripts/engine_ab_report.py` produces the v1-vs-v2
  comparison (§11).
- **F4 — measured cutover.** Flip `ATLAS_UNIFIED_ENGINE` when v2 ≥ v1 on the §11
  gate. Closes #242/#232 (movement members feed serving).

---

## 11. A/B measurement (the cutover gate AND the paper experiment)

`scripts/engine_ab_report.py` (read-only, repeatable), v1-compat vs unified-v2 over
the same window:
- **coherence** — mean intra-topic member similarity (↑ better)
- **recall** — gold-topic recall on the stratified benchmark (↑)
- **black-hole rate** (#224) — max single-cluster share + purity (no mega-blob)
- **evidence purity** — fraction of gated evidence members truly on-topic (sample)
- **cross-source binding** — does a topic correctly hold press + forum about the
  same event (the unification payoff; sampled)
- **noise** — junk/roundup rate

**Cutover rule:** unified-v2 ≥ v1 on coherence, recall, evidence-purity AND no
worse on black-hole/noise. This comparison IS Paper 1's split-brain-vs-unified
experiment.

---

## 12. Issue closure plan (the objective — close, not just document)

| action | issues | mechanism |
|---|---|---|
| **CLOSE** | **#242** | engine review subsumed by this spec |
| | **#168** | typed membership + the 5 relationship types (§9.2) delivered |
| | **#172** | re-homed on the discussion/evidence ratio (§9.2 silent-risk) — the parked scaffold becomes the relationship view |
| | **#237** | Community Signal Layer core = forum-ingest (§7) + typed discussion/mood serving |
| | **#232** | universal input → `movement` role binds events to topics (§6/§9.1) |
| **ADVANCE** | #229 | unified clustering uses stratified recall; A/B measures it |
| | #224 | anchor-guard preserved + measured in the A/B |
| | #235 | forum-per-country extends the domestic-voice program to forums |
| | #220 | the engine's stage counts are the funnel ledger's data |
| | #217 | credibility tiers attach to the `evidence` lane |
| | #238 | subject-geography is adjacent (separate geo work) |
| | #184/#162 | NLP throughput flips subjects verified; engine clusters without it |
| | #204 | taxonomy revision feeds topic labels |

Each CLOSE issue gets a closing comment referencing the delivering phase + commit.

---

## 13. Paper-track impact (methodological backing + landing docs)

The engine is methodologically central; it must keep the paper series coherent
(the backing that gives Atlas seriousness + the landing's docs). Per-phase, the
spec generates the evidence:

| paper | what changes / evidence generated | phase |
|---|---|---|
| **P1** (classification) | split-brain→unified is a NEW method; the **A/B (§11) is the experiment**; GDELT-theme-as-feature = the theme ablation P1 lists "not started"; a measured successor to the 41.6% number on the unified engine | F3–F4 |
| **P4** (thread aggregation) | typed membership + the 5 relationship types = new contributions; syndication/editorial-lane already folded | F0, F3 |
| **P5** (sentiment fusion) | the `mood` role = press-vs-public sentiment divergence, a distinct signal | F1, F3 |
| **P7** (viz/workflow) | press-vs-public in ONE topic view = new analyst surface; truncated/focus already there | F0 |
| **P8** (open-set discovery) | universal input (forum + events as modalities) extends open-set to multi-modal; #232 movement-as-signal | F1, F3 |
| **P2** (source quality) | typed membership + `source_family` + credibility (#217) feed source scoring | F1+ |

Master plan + per-paper specs updated as each phase lands (mirrors the
2026-06-29 syndication-spec paper edits). **The hybrid measured cutover REINFORCES
the papers — it is the comparative evidence they need.**

---

## 14. Deferred (NOT in this spec)

- **Causal cross-vocabulary linking** (forum "expensive food" ↔ news "Strait of
  Hormuz economic hardship"). Atlas does not do causal reasoning today. The
  unified engine links by semantic similarity + country+time co-occurrence; the
  causal leap needs an LLM reasoning step — a future spec, explicitly out of
  scope here (Pedro confirmed 2026-06-29).

---

## 15. Risks + guardrails

- **Black-hole (#224):** v2 must preserve the anchor-guard + `leaf` selection;
  the A/B gate blocks cutover if black-hole rate worsens.
- **Honesty invariants:** evidence never mixes discussion/mood/movement;
  `gated_signal_count` evidence-only; `verified=false` on social — carried
  verbatim into `topic_members`.
- **Paper-1 reproducibility:** GDELT themes demoted to a feature now, removed only
  after the ablation; the 41.6% number stays reproducible until its measured
  successor exists.
- **Forum noise at scale:** F2 guard (social attaches, doesn't seed) lands BEFORE
  F1 scales volume.
- **Flag isolation:** unified-v2 writes a distinct `engine_version`; a v2 defect
  cannot corrupt v1 serving.

---

## 16. Implementation TODO

- [x] **F0.1** migration `topic_members` (+indexes) — `057_topic_members.sql`, applied to prod
- [x] **F0.2** `v1-compat` ETL: project `signal_topic_assignments` → `topic_members` — `scripts/etl_topic_members.py`; atlas-evidence parity EXACT (6734=6734); dynamic projected by sample (per §10 constraint). Discussion path correct (0 rows = cron freshness, not a defect).
- [x] **F0.3** `/threads` reads `topic_members` (role='evidence') behind read-flag
  `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` (default OFF) — `THREADS_SQL_TOPIC_MEMBERS`
  mirrors `THREADS_SQL` exactly (basis↔lex/theme, gate_kept/confidence carried).
  A/B gate `scripts/engine_serving_parity.py`: **CRITICAL PARITY ALL PASS**
  (set/order/signal_count/gated/source/country/entities exact, global+US+CO+topic).
  Two documented cosmetic near-parity deltas, non-blocking: related-chip top-5
  reshuffle (current = all-time co-occurrence, unified = window-scoped, MORE
  correct) + avg_confidence ±1e-3 (REAL vs double). **ETL fix shipped:** carry
  source `assigned_at` (was insert-time → would serve aged-out rows; re-seeded
  6734=6734 windowed). Flip is Pedro's (1 env var) after eyeballing the chip
  change. `/theme/{id}` read-swap deferred to F3 (the detail gate path is
  separate; the LIST parity is the F0 acceptance).
- [x] **F0.4** `GET /api/v2/topic/{id}/relationship` (5 types) — `app/services/topic_relationship.py`
  `classify_relationship` (pure, 14 tests) + role-count query over `topic_members`;
  route accepts raw topic_id or `slug--cc` thread_id. DEPLOYED + SMOKED (prod:
  armed-conflict → media-led 1412 evidence). HONEST current state: all atlas
  topics = `media-led` (discussion/mood lanes are 0 — `semantic-discussion-v1`
  has 0 source rows; public-led/social-led/silent-risk fire when F1 forum
  ingest populates discussion+mood). Closes the serving half of #168; re-homes
  #172 silent-risk on the ratio.
- [x] **F1.1** Bluesky Jetstream ingest worker → `signals_v2` social — `app/services/ingest_bluesky.py`
  (Jetstream JSON-over-WS firehose, NO `atproto` lib / no creds; bounded ~25s
  drain, substantive top-level posts only, country via NER geocode + `source_lang`
  from BCP-47 `langs` reduced to 2-letter; wired into `ingest_loop` every 4th
  cycle; 12 tests). LIVE-verified: 185 social signals in one drain, **13
  languages** (en/pt/ja/ko/…). Bug found+fixed: BCP-47 `pt-BR`/`zh-Hans` overflow
  CHAR(2) `source_lang` → reduce to base 2-letter. Geo on social is weak by
  design (lang+NER); the discussion attach is semantic (embeddings), so geo noise
  doesn't affect membership.
- [x] **F1.2** Lemmy ingest worker (instance=country) → `signals_v2` social — `app/services/ingest_lemmy.py`
  (9 live instances, `type_=Local`, `source_origin_country`=instance home; wired
  into `ingest_loop` every 4th cycle; 7 tests). LIVE-verified: 125 social signals
  inserted, country-tagged (feddit.dk Danish DK/DK; lemmy.ca covering US news →
  country=US origin=CA, the voice≠subject split). **Chain bug FOUND+FIXED:**
  `assign_discussion_topics.py` INSERT `$3` was untyped (used as both `confidence`
  real and a jsonb anyelement) → `AmbiguousParameterError` on every real run = the
  latent crash behind 0 `semantic-discussion-v1` rows. Cast `$3::real`; attach now
  works (2 high-conf discussion members at ≥0.90 → `topic_members` → prod
  `/topic/{id}/relationship` reads real `discussion_count`). REMAINING F1 wiring:
  cron `assign_discussion_topics` (attach is not yet recurring) + social embedding
  cadence (eligible but proportionally slow at 0.5% of corpus); then the
  public/social-led/silent-risk types differentiate at volume.
- [x] **F2.1** `source_family` guard in clustering (social attaches, never seeds) —
  `snapshot_emergent_topics.py` `_social_seed_pred()` excludes `source_family='social'`
  from BOTH seeding pulls (`_pull_signals` + `_PERSISTED_SELECT` stratified path);
  social still embeds + kNN-attaches as discussion. Env knob
  `ATLAS_CLUSTER_ALLOW_SOCIAL_SEED` for the measured high-signal-event exception.
  Verified on prod: 24 social excluded, 44,171 press kept for seed — lands BEFORE
  the F1.1/F1.2 volume embeds (spec §8 "guard before F1 scales"). Synced to the M1
  emergent-snapshot cron tree.
- [ ] **F3.1** unified-v2 construction pass (embed-all → assign → typed write) behind `ATLAS_UNIFIED_ENGINE`
- [ ] **F3.2** `scripts/engine_ab_report.py` (v1 vs v2 metrics, §11)
- [ ] **F3.3** `movement` role: bind events (ACLED/anomalies) to topics — closes #232
- [ ] **F4.1** cutover when A/B gate passes; close #242
- [ ] **per-phase** paper-track edits (§13) + issue-closing comments (§12)

---

## 17. Decisions (resolved — Pedro, 2026-06-29)

1. **`topic_id` namespace** → keep dual `atlas-slug` / `dynamic-topic-N` ids in
   F0 (no early migration); unify the id space at F3.
2. **`mood` extraction** → reuse `nlp_sentiment` per forum signal in F1; a
   dedicated concern-classifier is deferred.
3. **F1 source order** → Bluesky + Lemmy first (highest volume + cleanest country
   tag + lowest integration cost); Telegram/Mastodon/Discourse follow as WAVE-N.
