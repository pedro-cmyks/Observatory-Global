# Handoff — Phase 2 Emergent Layer wired into the Brief

Date: 2026-05-30
Branch: `v3-intel-layer` (production)
Spec: `docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md`

## Where we are

The emergent topic discovery layer is now the **primary topic feed** for
the brief's Watchlist surface, with a fallback to the static
`atlas_topics` ranking when no fresh snapshot exists. The chain
end-to-end:

```
signals_v2 (24h)
  → snapshot_emergent_topics.py: clean + e5-base + HDBSCAN (leaf)
                                  + emergent precision gate (≥90%)
                                  + DeepSeek labeling
  → emergent_clusters (mig 046, RLS on)
  → /api/v2/briefing.top_atlas_topics  (mapped to existing contract)
  → Watchlist section in Briefing.tsx / BriefNewspaper.tsx
  → click row → /api/v2/theme/cluster-<id>
              → _emergent_cluster_detail (JOIN sample_signal_ids
                                          against signals_v2)
              → ThemeDetail panel renders gated evidence
```

`/api/v2/emergent` exists as a dedicated inspector endpoint (router
tests in `test_emergent_router_shape.py`, 7 passing). The brief still
sources via `top_atlas_topics` for back-compat with the existing
frontend contract; the response is mapped:
- `slug` → `cluster-<id>`
- `signal_count` ← `raw_signal_count` (HDBSCAN cluster size)
- `gated_signal_count` ← `n_signals` (kept by the gate)
- `gate_scored_count` ← `raw_signal_count` (every member was scored)
- new optional fields: `description`, `velocity`, `top_country_codes`,
  `cohesion`, `vendor_agreement`

## What shipped

### Database

- `backend/migrations/046_emergent_clusters.sql` — applied live via
  `asyncpg` to the Supabase pooler. Table created with RLS enabled, 3
  secondary indexes (`idx_emergent_snapshot`, `idx_emergent_velocity`,
  `idx_emergent_recent_window`).

### Backend

- `backend/scripts/snapshot_emergent_topics.py` — runs the full pipeline
  on the off-iCloud mlvenv and writes one row per surviving cluster.
  Computes velocity vs the most recent prior snapshot via centroid
  cosine match (≥ 0.85). Translates HDBSCAN local indices to
  `signals_v2.id` before persisting (this bit had a bug in the first
  run; the corrected snapshot is what landed live).
- `backend/app/routers/emergent.py` — `GET /api/v2/emergent?hours=N&limit=L`.
  Latest-snapshot read sorted by `velocity DESC NULLS LAST, n_signals
  DESC`. Degrades to `[]` with `warnings: ["emergent_clusters_missing"]`
  if the table is absent.
- `backend/app/routers/briefing.py` — `top_atlas_topics` now reads from
  `emergent_clusters` (latest snapshot in window) when available; falls
  back to the static `signal_topic_assignments` ranking when there is
  no recent snapshot.
- `backend/app/routers/themes.py` — added `_emergent_cluster_detail`
  helper + a `cluster-<id>` slug branch in `get_theme_details` so the
  brief Watchlist click lands on real evidence (JOIN sample_signal_ids
  against signals_v2). Same theme-detail shape as the atlas-slug
  branch so ThemeDetail renders unchanged.
- `backend/app/main_v2.py` — registered `emergent.router`.
- `backend/tests/test_emergent_router_shape.py` — 7 query-shape
  guardrails (route registered, table guard, latest-snapshot logic,
  velocity ordering, limit, no leaks of centroid/raw_sample/vendor
  internals, response contract).

### Production state after this session

- Branch `v3-intel-layer` pushed to origin (this commit + previous 2
  emergent commits).
- Backend deployed to Fly `atlas-api-pedro` via
  `scripts/deploy-fly-api.sh`.
- Frontend `frontend-v2` auto-deploys on push via Vercel (no frontend
  files changed this session — the Watchlist surface already exists
  from prior session).
- Mig 046 applied live in Supabase.
- First snapshot written manually:
  `2026-05-31T03:35:13Z` — 11,539 rows after dedupe, 21 raw clusters,
  16 kept after the gate, 16 DeepSeek labels persisted. Velocities are
  all `NULL` (first snapshot, no prior to match).
- Cron (`com.atlas.atlas-topic-classifier.plist`) is healthy and has
  been running every 30 min throughout this session — the previous
  handoff's "stopped since 2026-05-27" was stale.

## Verified end-to-end

- `pytest tests/test_emergent_router_shape.py tests/test_briefing_performance_shape.py`
  — **22/22 pass**.
- Live DB smoke (`asyncpg`):
  - `MAX(snapshot_at)` returns the fresh snapshot.
  - Briefing SQL returns 16 rows mapped to the
    `top_atlas_topics` contract (`slug`, `label`, `signal_count`,
    `gated_signal_count`, etc.).
  - `cluster-<id>` resolution joins `signals_v2` and returns real
    headlines (e.g. "Encontraron muerta a Agostina Vega…",
    "Frankie Valli cancels the remainder of the Four Seasons' farewell
    tour…").

## Known issues / caveats

- **Velocity = NULL on every cluster.** First snapshot; no prior to
  match. Next snapshot (run by cron after Phase 3, or manually) will
  produce real velocities.
- **Sample size per cluster = 8.** `sample_signal_ids` is capped at 8
  by the underlying `_cluster_stats` / `_apply_gate` ranking. Cluster
  detail panels show 8 headlines max for now. Bumping to ~24 is a
  small, safe change (a few extra bytes per row).
- **Language-density artifact** flagged in the spec verification
  section: multi-topic same-language clusters (Greek/Turkish "roundup"
  style) can pass the gate with high kept_ratio. Phase 6
  (`dynamic_topics` lifecycle) plus tighter HDBSCAN params can address
  this; not blocking.
- **No cron yet for emergent snapshots.** Phase 3 wires the launchd
  job (00/06/12/18 UTC) plus the daily 3-vendor calibration at 03:00.

## CORRECTION — wrong surface targeted this session

After Pedro reviewed the deployed app on his phone, he pointed out a
context-gap miss: this session wired the emergent feed into the
**Briefing modal Watchlist** and the **/brief newspaper page**, NOT
into the **Narrative Threads** section that is the primary visible
panel on `/app`. The screenshot he sent shows a thread list rendered
by `NarrativeThreads.tsx` (which consumes `/api/v2/threads` →
`backend/app/services/thread_intelligence.py`), not the briefing.

`thread_intelligence.py` builds threads from atlas-topic anchors using
`assemble_thread` + `confidence_band` + `_trend_label` + `_why_now` +
`build_thread_id`. The emergent clusters do not flow into this path
yet. So even though emergent_clusters is now powering the briefing's
top_atlas_topics block, the visible Narrative Threads list on the
mobile app is still computed from the static atlas pipeline.

**This is exactly the context-gap problem documented in the inventory
proposal.** The fix surfaces a NEW priority for the next session
(below).

## Next priorities (suggested order)

1. **Wire `emergent_clusters` into `/api/v2/threads`** — the actual
   visible surface. Two paths:
   - **Augment**: `fetch_threads` returns atlas threads PLUS emergent
     threads (each emergent cluster becomes a thread row with
     fields mapped to the thread contract — confidence_band derived
     from gate_threshold, trend from velocity, why_now from cluster
     description). Non-breaking.
   - **Replace**: route /api/v2/threads entirely through
     emergent_clusters, deprecate the atlas-anchored thread_intelligence
     code path. Cleaner but bigger; do this once Phase 6
     `dynamic_topics` lifecycle is also built so emergent threads have
     persistent identity + first_seen for the "Started Xh ago" string.
   - Recommended: ship Augment first, evaluate, then plan the
     Replace path.
2. **Project inventory tool + lighter CLAUDE.md** (see
   `docs/state/2026-05-30-context-gap-inventory-proposal.md`). The
   miss above is the second-this-session example of why this matters.
3. **Phase 3 — cron for emergent snapshots.** Add
   `run-emergent-snapshot.sh` to AtlasLocalWorker + launchd plist at
   4× daily cadence. Daily 3-vendor calibration job at 03:00.
3. **Phase 5 — translation layer.** `signal_translations` table +
   `/api/v2/translate` endpoint + frontend bilingual display
   (original + translation underneath).
4. **Phase 6 — `dynamic_topics` lifecycle.** Replace `atlas_topics` as
   the canonical taxonomy with a self-curating dynamic vocabulary.
5. Optional polish:
   - Bump `sample_signal_ids` cap from 8 to ~24 in the snapshot
     script so cluster detail panels show more evidence.
   - Add a frontend rendering of `velocity` (currently the field is
     in the API payload but the brief Watchlist row markup does not
     render it).

## Quick resume

- Verify cron health: `launchctl list | grep atlas`.
- Verify production API: hit `/api/v2/briefing?hours=24` and check
  that `top_atlas_topics[].source_table` is `"emergent_clusters"`.
- Run a manual snapshot ad-hoc:
  ```
  export DATABASE_URL=$(grep -E '^DATABASE_URL=' .env | sed -E 's/^DATABASE_URL=//')
  export DEEPSEEK_API_KEY=$(grep -E '^DEEPSEEK_API_KEY=' .env | sed -E 's/^DEEPSEEK_API_KEY=//')
  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
    -m backend.scripts.snapshot_emergent_topics \
    --window-hours 24 --max-signals 15000 \
    --min-cluster-size 20 --min-samples 10 --top-clusters 30
  ```
- Inspect emergent rows in SQL:
  ```sql
  SELECT label, n_signals, raw_signal_count, velocity, top_country_codes
  FROM emergent_clusters
  WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM emergent_clusters)
  ORDER BY velocity DESC NULLS LAST, n_signals DESC LIMIT 10;
  ```
