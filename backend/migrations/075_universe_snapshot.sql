-- Universe view precompute (contract universe-v0).
--
-- GET /api/v2/universe rebuilds the whole field per request: 5 heavy
-- topic_members×signals_v2 joins + numpy SVD + full-space neighbor matrix
-- over ~500 active topics = ~11s warm / >20s cold (the frontend's 20s abort
-- fires → "Universe data unavailable"). This table holds the finished payload
-- so serving is a single cheap JSONB read.
--
-- One row per `days` window (the endpoint's only param). The M1 cron keeps it
-- warm; the endpoint self-heals with a write-through recompute when the row is
-- missing or stale, so a dead cron degrades to ONE slow request per window,
-- never the empty state.
CREATE TABLE IF NOT EXISTS universe_snapshot (
    days        integer     NOT NULL,
    payload     jsonb       NOT NULL,
    node_count  integer,
    build_ms    integer,
    built_at    timestamptz NOT NULL DEFAULT NOW(),
    PRIMARY KEY (days)
);
