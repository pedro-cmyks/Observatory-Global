# Emergent Topic Discovery — Design

Date: 2026-05-29
Status: Draft for review

## Context

Atlas v2 currently classifies signals against a fixed 30-topic curated
taxonomy (`atlas_topics`). Pipeline: lexicon + GDELT theme hints match
signals into those 30 lenses; the scope gate (mig 045) filters to
high-precision-per-topic keepers.

That architecture has a structural blind spot: **signals about narratives
outside the 30 buckets are invisible to the product**. The taxonomy is a
strong human prior. Real narrative intelligence demands a layer that
**discovers topics from the data** — clusters that surface from volume,
velocity, and semantic cohesion — rather than only matching against a
pre-established list.

The fixed taxonomy is not wrong; it is **incomplete**. It belongs in a
two-track product:

- **Emergent** (this spec): discover what is heating up. Embeddings →
  clustering → consensus labeling.
- **Watchlist** (existing `atlas_topics`): things we choose to track
  always (electoral integrity, conflict escalation, etc.), independent
  of organic emergence.

Both shipped, the brief shows "What's emerging" as the lead and
"Watchlist" as a curated overlay.

## Goals

1. Surface 5–20 emergent narrative clusters per snapshot, each with a
   human-readable label, sample headlines, country distribution, and a
   velocity signal (cluster size delta vs prior snapshot).
2. No fixed taxonomy. Cluster identity is data-driven and can shift
   shape day to day.
3. Coherence is a first-class output: incoherent clusters are dropped or
   quarantined automatically via 3-vendor labeling disagreement.
4. Run on the local `mlvenv` (e5-base embeddings on MPS, $0/signal).
   LLM cost bounded to ~$27/mo through tiering (DeepSeek bulk + daily
   3-vendor calibration).

## Non-goals

- Replacing `atlas_topics`. The watchlist stays. Both layers ship side
  by side.
- Tracking long-lived narrative continuity across days (cluster
  identity reset per snapshot for v1; continuity = future work).
- Multilingual cluster merging policy beyond what e5-base already does
  natively (it embeds multilingual into shared space).
- Real-time streaming. Snapshot cadence is sufficient.

## Architecture (pipeline)

```
signals_v2 (last W hours)
   │
   ▼  dedupe near-dup (cosine ≥ 0.95, same outlet or generic)
   │
   ▼  e5-base embed (mlvenv MPS, $0)
   │
   ▼  HDBSCAN cluster (cosine distance)
   │     min_cluster_size + min_samples tuned on real data
   │
   ▼  per-cluster precision filter (same ≥90% discipline as scope gate)
   │     logistic on [signal_emb || cluster_centroid_emb || cos(signal, centroid)]
   │     trained on consensus corpus (4,911 is_evidence rows + per-topic centroids)
   │     threshold calibrated on held-out for ≥90% precision
   │     kept_set per cluster = signals with score ≥ threshold
   │
   ▼  per cluster: top-K headlines from kept_set by centroid + country/source spread
   │
   ▼  labeling (tiered)
   │     hourly cadence  → DeepSeek chat (V3) only
   │     daily 03:00     → DeepSeek + claude-sonnet-4-6 + gpt-4.1
   │                       3-vendor consensus on label semantics
   │
   ▼  consensus filter (daily calibration)
   │     3 vendor labels → embed → pairwise cosine sim
   │       avg ≥ 0.7         → high agreement, label = centroid
   │       2/3 agree         → moderate, label = the 2 that agree
   │       all disagree      → incoherent, DROP cluster
   │
   ▼  persist emergent_clusters
   │
   ▼  API /api/v2/emergent?hours=N
   │
   ▼  brief frontend section "What's Emerging"
```

## Cadence and window

- **Snapshot cadence**: every 6 hours (00 / 06 / 12 / 18 UTC). 4
  snapshots/day. Balance: fresh enough for editorial brief (read 1–3×/day),
  cheap enough for the cost ceiling.
- **Window**: 24h rolling. Matches the brief's default time horizon.
- **Velocity**: signal count delta vs snapshot 6h prior on matched
  clusters (centroid cosine ≥ 0.85). New clusters: velocity = full size.

## Data & schema

New table `emergent_clusters`:

```sql
CREATE TABLE emergent_clusters (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_at         TIMESTAMPTZ NOT NULL,
    snapshot_window_h   INT NOT NULL DEFAULT 24,
    cluster_id          INT NOT NULL,                -- HDBSCAN local id
    label               TEXT NOT NULL,               -- 3-5 word human label
    description         TEXT,                        -- 1-line summary
    raw_signal_count    INT NOT NULL,                -- HDBSCAN cluster size before precision filter
    n_signals           INT NOT NULL,                -- kept after precision filter (≥90% precision)
    gate_threshold      NUMERIC,                     -- logistic threshold used for this snapshot
    velocity            INT,                         -- delta vs prior snapshot (on n_signals)
    cohesion            NUMERIC,                     -- mean pairwise cosine in raw cluster
    top_country_codes   TEXT[] NOT NULL DEFAULT '{}',
    sample_signal_ids   BIGINT[] NOT NULL DEFAULT '{}', -- top-K from kept_set for display
    raw_sample_ids      BIGINT[] NOT NULL DEFAULT '{}', -- top-K from full cluster (audit)
    centroid_vec        REAL[],                      -- 768-dim e5-base centroid (kept_set)
    vendor_agreement    TEXT NOT NULL DEFAULT 'deepseek',
                        -- 'deepseek' | 'high' | 'moderate' | 'incoherent'
    vendor_labels       JSONB,                       -- {claude:..., gpt:..., deepseek:...}
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_emergent_snapshot ON emergent_clusters (snapshot_at DESC);
CREATE INDEX idx_emergent_velocity ON emergent_clusters (snapshot_at DESC, velocity DESC NULLS LAST);

ALTER TABLE emergent_clusters ENABLE ROW LEVEL SECURITY;
-- backend connects as postgres superuser; bypasses RLS. No anon read.
```

Migration number: next available (`046` if 045 is the last).

## Per-cluster precision filter (≥90%, same discipline as scope gate)

The scope gate (mig 045) calibrated a logistic classifier per atlas topic
to keep only signals scoring above a topic-specific threshold, targeting
≥90% precision. That work was not the destination — it was the training
ground. The same discipline applies here: each emergent cluster from
HDBSCAN is a hypothesis of a narrative, and we must filter its members
to the high-precision evidence subset before labeling or shipping.

### Why HDBSCAN alone is insufficient

HDBSCAN places signals in clusters by density in embedding space. Border
points and noise label (-1) get assigned to clusters they barely belong
to. Cluster cohesion is a useful proxy for quality, but not a precision
guarantee per signal. The gate methodology gives us a calibrated,
per-signal keep/abstain decision against a centroid concept. That is
what the broad emergent product needs.

### Training data

The consensus corpus is the foundation: **4,911 binary `is_evidence` rows**
covering `(signal_id, topic_slug, is_evidence)` triples annotated by
3-vendor consensus (claude-sonnet-4-6 + gpt-4.1 + deepseek-chat). This
labels what counts as real evidence vs context/noise within an atlas
topic.

To generalize to *any* centroid (HDBSCAN-emitted), we re-frame the
features as cluster-agnostic:

- For each topic in the corpus, compute its **evidence centroid**:
  mean of e5-base embeddings of all rows with `is_evidence = 1` for
  that topic.
- For each row, build feature vector `x = [signal_emb || centroid_emb || cos(signal, centroid)]`
  where `centroid` is the evidence centroid of that row's labeled topic.
- Label = `is_evidence` (binary).

This trains a *general* "is this signal evidence for the concept this
centroid represents" classifier — independent of which atlas topic, and
therefore applicable to any HDBSCAN centroid.

### Model + calibration

- **Model**: logistic regression (same family as the scope gate). Small,
  fast, calibratable, explainable.
- **Held-out split**: same 80/20 split convention used by `train_scope_gate.py`.
- **Calibration**: isotonic regression on out-of-fold predictions, then
  threshold search such that **precision on held-out ≥ 0.90** with
  maximum recall.
- **Persistence**: `docs/research/atlas-paper/phase-1-validation/models/YYYY-MM-DD-emergent-precision-gate-v1.json`,
  same shape as `2026-05-29-scope-gate-v1-e5base.json` (scaler_mean,
  scaler_std, lr_coef, lr_intercept, global_threshold). No per-topic
  table — this is a single global threshold (we are gating arbitrary
  centroids).

### Inference (per snapshot)

For each HDBSCAN cluster:
1. Compute centroid `c` = mean of e5-base embeddings of cluster members.
2. For each member signal `s`: feature `[emb(s) || c || cos(emb(s), c)]`,
   score via the persisted logistic.
3. `kept_set` = members where `score ≥ global_threshold`.
4. Record `raw_signal_count = |cluster|`, `n_signals = |kept_set|`,
   `gate_threshold = global_threshold`.
5. Recompute centroid from `kept_set` (the production `centroid_vec`),
   then sample top-K for labeling and display.
6. If `|kept_set| < min_kept` (e.g., 10), DROP cluster — too thin to
   reach 90% precision honestly.

This guarantees what we show in "What's Emerging" carries the same
precision floor as the atlas-topic gate.

### Verification

- Same held-out precision target ≥ 0.90.
- AUC reported alongside (we already know e5-base + logistic reaches
  AUC ~0.94 on the corpus; embedding+centroid features should be
  comparable, possibly slightly lower since we drop atlas-specific
  features).
- Post-deployment: track `n_signals / raw_signal_count` ratio per
  snapshot. Sustained < 0.20 = HDBSCAN clusters are too noisy → re-tune
  cluster params. Sustained > 0.80 = gate is too permissive on novel
  centroids → re-train with fresher data.

## 3-vendor labeling consensus

Prompt (identical across vendors):

```
You are labeling a cluster of news headlines for a narrative intelligence
brief. Given these representative headlines:

{top_k_headlines}

Return JSON only:
{
  "label": "3-5 word topic name in title case",
  "description": "one-line description of what this cluster is about",
  "confidence": 0.0-1.0
}

Do not include any other text.
```

- **DeepSeek (`deepseek-chat`)**: hourly bulk. Cheap. Used as primary
  label on every snapshot.
- **Daily calibration 03:00 UTC**: re-label the most recent snapshot's
  top-N clusters (by `n_signals`, N=30) with claude-sonnet-4-6 and
  gpt-4.1. Embed all 3 labels via e5-base, compute pairwise cosine sim.
  Set `vendor_agreement` and final `label`:
  - avg sim ≥ 0.7 → `high`, label = string whose embedding is closest to
    the 3-label centroid.
  - exactly one pair sim ≥ 0.7 → `moderate`, label from that pair.
  - else → `incoherent`, drop or quarantine (`vendor_agreement = 'incoherent'`).

Vendor agreement is **diagnostic** of cluster quality, not just label
quality: low agreement strongly correlates with semantically noisy
clusters (HDBSCAN gave us a bad grouping).

## API

```
GET /api/v2/emergent?hours=24&limit=20
```

Response:

```json
{
  "snapshot_at": "2026-05-29T18:00:00Z",
  "window_hours": 24,
  "clusters": [
    {
      "id": 1234,
      "label": "Ebola surge cross-border",
      "description": "Outbreak in eastern DRC, Uganda border closure",
      "n_signals": 412,
      "velocity": 287,
      "cohesion": 0.74,
      "vendor_agreement": "high",
      "top_country_codes": ["UG", "CD", "RW"],
      "sample_signal_ids": [98765, 98770, ...]
    },
    ...
  ]
}
```

Sorted by `velocity DESC NULLS LAST, n_signals DESC`. Default `limit=20`.

## Translation layer (multilingual brief)

The brief surfaces narratives in their native language. e5-base embeds
cross-lingually, so a Greek/Chinese/Russian cluster can be detected
without translation — but the user reading the brief may not. The UX
need: original headline preserved verbatim, translation rendered
underneath in a secondary color, on demand.

### Architecture

- **Cluster labels + descriptions**: already English. The DeepSeek
  labeling prompt is English, and DeepSeek (V3) returns English labels
  even when the source headlines are Greek/Arabic/Vietnamese (validated
  in the POC: `#6 Russia-Ukraine War Updates` for a Cyrillic cluster).
  No extra work for cluster headers.

- **Per-headline translation**: lazy, cached. New table:

```sql
CREATE TABLE signal_translations (
    signal_id    BIGINT NOT NULL REFERENCES signals_v2(id) ON DELETE CASCADE,
    target_lang  TEXT NOT NULL,             -- 'en' for v1, extensible
    translated   TEXT NOT NULL,
    model        TEXT NOT NULL,             -- 'deepseek-chat-v3', etc.
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (signal_id, target_lang)
);
ALTER TABLE signal_translations ENABLE ROW LEVEL SECURITY;
```

- **Endpoint**: `GET /api/v2/translate?signal_id=N&to=en` →
  if cache → return; else DeepSeek translate, persist, return. Skip
  translation if `source_lang = target_lang` (return original).
- **Batch endpoint**: `POST /api/v2/translate/batch {signal_ids: [...]
  , to: 'en'}` for cluster snapshot pre-warming (translate top-K of
  each cluster at snapshot write time so reads are instant).

### Frontend UX

```
┌─ Cluster: Russia-Ukraine War Updates              [high confidence] ┐
│  RFE викликала свого посла з Вірменії через зближення Єревану з ЄС │
│    Russia recalled its ambassador from Armenia over Yerevan's       │
│    rapprochement with the EU  [translation, italic, color secondary]│
└─────────────────────────────────────────────────────────────────────┘
```

- Original headline: primary color, normal weight.
- Translation: italic, secondary color, 11px. Always visible (not
  click-to-reveal) so the reader can scan in their native language
  without extra interaction.
- Hide the translation block when `source_lang === ui_lang`.

### Cost

DeepSeek V3 input ~$0.07/M / output ~$1.10/M. Avg headline 30 tokens
in, 35 out. 5,000 translations/day = $0.0002/day ≈ $0.006/mo.
Trivially cheap; translation cache + signals_v2 prune (90d) bound the
table size.

### Phasing

- Phase 5a: schema migration + lazy endpoint. Frontend renders
  translation when present, hides when missing.
- Phase 5b: batch pre-warm at snapshot time (top-K per cluster).
  Cluster detail loads with translations already cached.
- Phase 5c (later): user-selectable target language (es, pt, fr, ar).

## Cron / runner

New runner `run-emergent-snapshot.sh` (off-iCloud at AtlasLocalWorker):

- 4× daily snapshots: launchd schedule 00:00, 06:00, 12:00, 18:00 UTC.
  Runs `mlvenv/bin/python -m scripts.emergent_snapshot --window-hours 24`.
- 1× daily calibration: launchd schedule 03:00 UTC. Runs same script
  with `--calibrate-3vendor --top-n 30`.

Both write to `emergent_clusters`. Non-fatal: a snapshot failure does
not block other Atlas pipelines (atlas-topic classifier, gate scorer).

## Cost

| Run | Vendor | Calls/run | Tokens (avg) | Cost/run | Runs/day | Cost/day |
|-----|--------|-----------|--------------|----------|----------|----------|
| Snapshot | DeepSeek V3 | ~80 clusters | ~600 in / 80 out | ~$0.005 | 4 | ~$0.02 |
| Calibration | Anthropic claude-sonnet-4-6 | 30 | ~600 / 80 | ~$0.30 | 1 | ~$0.30 |
| Calibration | OpenAI gpt-4.1 | 30 | ~600 / 80 | ~$0.20 | 1 | ~$0.20 |
| **Total** | | | | | | **~$0.52/d ≈ $16/mo** |

Storage trivial (centroid_vec is 768 floats per cluster, ~6KB; 80
clusters × 4 snapshots × 30 days ≈ 60MB/mo).

Local compute: e5-base on MPS over ~20–30k dedupe headlines per snapshot
≈ 3–5 minutes. HDBSCAN at that scale ≈ 30s. Within snapshot budget.

## Self-curating taxonomy (Atlas as a living model)

The fixed `atlas_topics` taxonomy (30 hand-curated lenses) is the wrong
abstraction long-term. A narrative intelligence product whose topic
vocabulary is frozen by the engineer cannot reflect the world it claims
to describe. Topics are born, peak, mutate, and die — the model has to
do the same.

### Direction

Replace (or layer over) `atlas_topics` with `dynamic_topics`: emergent
clusters that persist across snapshots when sustained, fade when they
stop appearing, and retire automatically.

```sql
CREATE TABLE dynamic_topics (
    id             BIGSERIAL PRIMARY KEY,
    slug_auto      TEXT NOT NULL UNIQUE,    -- slugified from current label
    label          TEXT NOT NULL,            -- best label (3-vendor consensus)
    description    TEXT,
    status         TEXT NOT NULL,            -- 'emerging' | 'active' | 'fading' | 'retired'
    first_seen     TIMESTAMPTZ NOT NULL,
    last_seen      TIMESTAMPTZ NOT NULL,
    snapshot_hits  INT NOT NULL DEFAULT 1,
    centroid_vec   REAL[] NOT NULL,          -- running mean
    centroid_n     INT NOT NULL DEFAULT 1,
    vendor_agreement TEXT,                   -- from last 3-vendor calibration
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_dyn_status_lastseen ON dynamic_topics (status, last_seen DESC);
ALTER TABLE dynamic_topics ENABLE ROW LEVEL SECURITY;
```

### Lifecycle (per snapshot, after precision gate)

For each surviving emergent cluster with kept set centroid `c`:

1. **Match**: cosine-search `dynamic_topics` where `status != 'retired'`.
   Best match with `cos >= 0.85` → same topic. Below → new.
2. **Update on match**:
   - `last_seen = NOW()`
   - `snapshot_hits += 1`
   - centroid running mean: `new = (centroid * n + c) / (n + 1)`, `n += 1`
   - If 3-vendor calibration changed the label this snapshot and
     vendor_agreement is `high`, update `label` (and `slug_auto`).
3. **Insert on miss**: `status='emerging'`, `first_seen = NOW()`, hits=1.
4. **Promote `emerging → active`** when `snapshot_hits >= 3` (3 snapshots
   at 6h cadence = 18h of sustained presence).
5. **Decay sweeper** (runs at the same cadence after labeling):
   - `last_seen < NOW() - INTERVAL '48 hours'` → `status='fading'`.
   - `last_seen < NOW() - INTERVAL '7 days'` → `status='retired'`.
   - Retired rows kept for audit; excluded from match search and product
     surfaces.

### Why running-mean centroid

Lets a topic drift gracefully as the narrative mutates (e.g. "Ebola
outbreak" → "Ebola outbreak in DRC" → "Ebola outbreak cross-border").
The threshold-0.85 match catches versions that are still semantically
the same story; if drift exceeds 0.85 a new topic is born and the old
one fades — exactly the right behavior.

### Atlas topics migration

- One-time: import every active `atlas_topic` as a `dynamic_topic`
  seeded with the centroid of its is_evidence-positive corpus rows,
  `status='active'`, `first_seen = '2026-05-23'` (their real launch
  date in production), `snapshot_hits = 999` (high so they don't fade
  immediately while we observe).
- `signal_topic_assignments` keeps pointing at atlas topics for
  back-compat (gate-aware ThemeDetail still resolves them).
- `dynamic_topics` becomes the canonical product taxonomy. Atlas
  becomes either a "preset watchlist" overlay or deprecates after
  dynamic_topics covers what we care about.

### Implications for the product

- API: `/api/v2/topics?status=active&since=N` replaces today's
  `top_atlas_topics` block. Sorted by `snapshot_hits DESC, last_seen
  DESC`.
- Brief: "Topics" section is **what the world is actually about right
  now**, not the engineer's prior. The Watchlist concept survives only
  as user-pinned topics (a follow-this-specific-topic feature).
- Scope gate (mig 045) still useful for atlas_topics imported as
  seeds; the emergent-precision gate applies to every dynamic topic
  including new emergent ones.

## Phasing

**Phase 1 — POC script (this session, after frontend honest patch).**
Standalone script `backend/scripts/emergent_poc.py`. Pull last 24h
headlines from `signals_v2`, dedupe, embed e5-base, HDBSCAN cluster,
label clusters via DeepSeek, print top 20 clusters to stdout (no DB
write, no API). Iterate `min_cluster_size` (15, 20, 30) and
`min_samples` (5, 10) until cluster quality (judged by spot-reading)
reasonable. No precision filter yet — measures raw HDBSCAN quality so
we know how much work the filter has to do.

**Phase 1.5 — Train per-cluster precision gate.** New script
`backend/scripts/train_emergent_precision_gate.py`. Builds the
embedding+centroid feature set from the consensus corpus (4,911
`is_evidence` rows), fits logistic, calibrates threshold for ≥90%
precision on held-out, persists artifact to
`docs/research/atlas-paper/phase-1-validation/models/YYYY-MM-DD-emergent-precision-gate-v1.json`.
Done in parallel to Phase 1 once POC clusters confirm HDBSCAN gives us
real candidates. Hook the saved gate into the POC for a second
spot-read of `kept_set` quality.

**Phase 2 — Persist + API.** Migration 046 for `emergent_clusters`.
Script writes snapshots. New router `routers/emergent.py` exposes
`/api/v2/emergent`. Backend tests.

**Phase 3 — Cron + 3-vendor calibration.** Runner + launchd plists.
Calibration job. Initial frontend brief section "What's Emerging" above
the Watchlist on `/brief` and in `Briefing.tsx`.

**Phase 4 — Continuity.** Cluster identity across snapshots via
centroid cosine matching. Trend lines per persistent cluster. Pre-req
for Phase 6 (it formalizes the matching into the `dynamic_topics`
lifecycle).

**Phase 5 — Multilingual translation layer.** Schema +
`/api/v2/translate` endpoint + batch pre-warm at snapshot. Frontend
renders original headline + translation underneath. Phases 5a/5b/5c
detailed under "Translation layer" above.

**Phase 6 — Self-curating taxonomy (`dynamic_topics`).** Migration +
snapshot lifecycle + decay sweeper + atlas import + unified
`/api/v2/topics`. Replaces `top_atlas_topics` and `emergent_clusters`
surfaces in the brief with the living dynamic topic vocabulary. Phases
6a/6b/6c/6d detailed under "Self-curating taxonomy" above.

## Open questions

- **min_cluster_size** value will only emerge from POC iteration. Start
  at 20 (≈0.1% of 24h volume).
- **Noise bucket (HDBSCAN label -1)**: dropped in v1. Could later be
  surfaced as "uncategorized hot signals" if velocity high.
- **Dedupe threshold (0.95)**: needs validation on real noise (RSS
  reposts, syndication). May need per-outlet rules.
- **Label language**: prompt above is English; multilingual headline
  clusters may produce non-English labels from DeepSeek/Claude. Decide:
  force English labels in prompt, or accept multilingual.
- **POC headline cap**: HDBSCAN scales poorly above ~50k points. If
  24h volume > 50k after dedupe, sample (random, or stratified by
  country/source family).

## Risks

- **Cluster drift between snapshots**: high. v1 accepts it (clusters
  identity is per-snapshot).
- **HDBSCAN parameter sensitivity**: high. Mitigation = POC iteration
  before any production wiring.
- **3-vendor agreement may be artificially low** if vendors disagree
  on label style (verbose vs terse). Mitigation = strict JSON schema in
  prompt, embed-based similarity not string match.
- **DeepSeek API reliability**: unknown vs Anthropic/OpenAI. Mitigation
  = snapshot is non-fatal, retry once, fall back to no-label cluster.

## Verification

- POC: spot-read 10 random clusters per parameter setting. Reject
  params where >30% of clusters are visibly incoherent.
- Production: track `vendor_agreement` distribution over time. Target:
  >60% of top-N clusters reach `high` or `moderate`. Sub-target = signal
  HDBSCAN params need re-tuning.
