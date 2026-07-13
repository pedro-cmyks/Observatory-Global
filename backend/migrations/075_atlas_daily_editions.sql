-- Compact publication artifact produced on the M1 after the sealed topic
-- snapshot. Heavy candidate/receipt/graph work never runs in the L1 request.
CREATE TABLE IF NOT EXISTS atlas_daily_editions (
    edition_date date PRIMARY KEY,
    edition_start timestamptz NOT NULL,
    edition_end timestamptz NOT NULL,
    generated_at timestamptz NOT NULL,
    contract text NOT NULL,
    status text NOT NULL CHECK (status IN ('ready', 'degraded')),
    package jsonb NOT NULL,
    graph jsonb NOT NULL,
    selection jsonb NOT NULL,
    completion jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (edition_end >= edition_start)
);

CREATE INDEX IF NOT EXISTS idx_atlas_daily_editions_end
    ON atlas_daily_editions (edition_end DESC);

COMMENT ON TABLE atlas_daily_editions IS
    'One compact, reproducible Atlas daily PublicationPackage per sealed edition; heavy compute remains on the M1.';
