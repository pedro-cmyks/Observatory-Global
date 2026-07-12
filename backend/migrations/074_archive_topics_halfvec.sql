-- 074_archive_topics_halfvec.sql
-- Weight fix before the archive backfill (2026-07-10): floor=8 clustering
-- yielded ~750 topics per big scope-week → projected tens of thousands of
-- rows; REAL[] centroids are 4B/dim (6KB/row). halfvec is 2B/dim (3KB/row)
-- — same precision class as signal_embeddings, halves the table. Table is
-- empty at swap time (validation run was cut before inserts). Still NO
-- vector index on this column — scan+cosine at thousands of rows.

ALTER TABLE archive_topics DROP COLUMN centroid_vec;
ALTER TABLE archive_topics ADD COLUMN centroid_vec halfvec(1536) NOT NULL;
