# Data Operations MOC

This map tracks storage, ingestion, local processing, crons, historical sync,
and production runtime constraints.

## Start here

- [[ARCHITECTURE]] — current data-flow diagram, cron table, and read surfaces.
- [[PROJECT_INVENTORY]] — generated endpoint/API/table/cron inventory.
- [[2026-05-21-data-operating-roadmap]] — execution order for hot/cold,
  processed history, long-window routing, and data quality.
- [[2026-05-30-context-gap-inventory-proposal]] — why the inventory layer
  exists.

## Hot/cold and historical processing

- [[2026-05-21-processed-historical-sync-design]]
- [[2026-05-21-processed-historical-routing-design]]
- [[2026-05-20-atlas-hot-cold-data-operating-model-design]]
- [[2026-05-30-phase-2-emergent-wiring-handoff]]

## Funnel and serving maturity (2026-06-10)

- [[2026-06-10-funnel-maturity-and-positioning]] — measured 24h funnel:
  194,674 raw → 153,538 deduped → 14,343 topic-assigned → 6,785 NLP'd →
  442 latest-snapshot cluster members. Separates deliberate precision
  filtering from capacity ceilings.
- #220 funnel observability ledger (stage counts + drop causes, measurement
  only); #221 serving maturity contract (sealed-hour floor for aggregates,
  provisional badge for live stream — instead of a blanket T-1h delay, which
  cannot fix the 3.5% NLP coverage); #222 stratified snapshot sampling
  (replaces the latest-15K cap that over-represents anglophone volume).
- Governing rule (spec Pipeline Funnel Principle): gates decide what Atlas
  volunteers, not what it can find when asked — Phase 1.5 semantic lane
  retrieves the full deduped corpus with quality labels.

## Operational guardrails

- Raw historical archive remains local but physically lives on the external disk
  at `/Volumes/Ext/Atlas/Archive`; `/Users/pedro/AtlasArchive` is a compatibility
  symlink.
- Processed historical artifacts default to `/Volumes/Ext/Atlas/Processed`.
- The hot/cold runner must fail loudly when `/Volumes/Ext` is not mounted rather
  than falling back to the internal disk.
- Runnable cron/ML workers live under `/Users/pedro/AtlasLocalWorker`, not the
  Desktop checkout.
- Cron credentials live in `/Users/pedro/AtlasLocalWorker/.env`; launchd
  runners must not read the Desktop repo `.env` unless explicitly debugging.
- `com.atlas.emergent-snapshot` also runs the shadow `dynamic_topics` lifecycle
  after each successful snapshot. This step must stay local-only: e5 + student
  inference run in `mlvenv`, `emergent_clusters.role_noise_rate` is cached once
  per cluster, and no paid API calls are introduced by the lifecycle.
- `dynamic_topics` merge/dedup is rebuild-only. Do not put centroid-only dedup
  in the incremental cron; dense centroids can chain-collapse unrelated topics
  and roundups.
- Current hot/cold note (2026-06-02): `com.atlas.local-hot-cold-catchup` is
  loaded but last exited `1` after an asyncpg connection reset during
  `archive_export`; `/Volumes/Ext` is mounted. Retry/backoff is patched and
  synced to `/Users/pedro/AtlasLocalWorker/backend/scripts/`; worker dry-run
  passed. Verify the next scheduled overnight run before treating the cron as
  green.
- Use `scripts/project_inventory.py` to refresh cron and endpoint truth before
  trusting old handoffs.
- New public schema tables should enable RLS in the same migration.

## Key files

- `backend/scripts/local_hot_cold_catchup.py`
- `backend/scripts/historical_backfill.py`
- `backend/scripts/historical_process_partition.py`
- `backend/scripts/historical_sync.py`
- `backend/scripts/snapshot_emergent_topics.py`
- `backend/scripts/project_dynamic_topics.py`
- `scripts/run-emergent-snapshot.sh`
- `scripts/install-emergent-snapshot-launchd.sh`
- `scripts/project_inventory.py`
- `infra/launchd/`
