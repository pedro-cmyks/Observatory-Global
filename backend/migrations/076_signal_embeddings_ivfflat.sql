-- 076_signal_embeddings_ivfflat.sql
--
-- #241 measured ANN cutover for the shared 1 GB Supabase database.
-- HNSW builds spilled even at m=4 (after 214,302 / 326,762 tuples). IVFFlat
-- with rows/1000 = 327 lists built in ~105 seconds. A deterministic 20-query
-- benchmark reached recall@10=1.00 at ivfflat.probes=20 (mean 131 ms, max
-- 203 ms). The application sets that measured probe floor per ANN query.
--
-- Idempotent on production: the live index was built during incident recovery;
-- reapplying this migration must not drop and rebuild an equivalent index.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname = 'idx_signal_embeddings_vec'
          AND indexdef ILIKE '%USING ivfflat%'
    ) THEN
        RAISE NOTICE 'idx_signal_embeddings_vec is already IVFFlat; no-op';
        RETURN;
    END IF;

    DROP INDEX IF EXISTS idx_signal_embeddings_vec;
    EXECUTE $ddl$
        CREATE INDEX idx_signal_embeddings_vec
        ON signal_embeddings USING ivfflat (vec halfvec_cosine_ops)
        WITH (lists = 327)
    $ddl$;
END
$$;

ANALYZE signal_embeddings;
