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
- Use `scripts/project_inventory.py` to refresh cron and endpoint truth before
  trusting old handoffs.
- New public schema tables should enable RLS in the same migration.

## Key files

- `backend/scripts/local_hot_cold_catchup.py`
- `backend/scripts/historical_backfill.py`
- `backend/scripts/historical_process_partition.py`
- `backend/scripts/historical_sync.py`
- `backend/scripts/snapshot_emergent_topics.py`
- `scripts/run-emergent-snapshot.sh`
- `scripts/install-emergent-snapshot-launchd.sh`
- `scripts/project_inventory.py`
- `infra/launchd/`
