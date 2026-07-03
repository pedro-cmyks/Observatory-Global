-- #219 Kalman movement feed: extend topic_movement with the smoothed state
-- (the pilot's estimate_state output) so it becomes the SINGLE shared movement
-- field. The existing volume/baseline/zscore/multiplier cols are the anomaly
-- view; these add the Kalman level+velocity+uncertainty+surprise. One row per
-- topic per run, engine_version distinguishes ('movement-kalman-v1').
ALTER TABLE topic_movement
  ADD COLUMN IF NOT EXISTS smoothed_intensity real,
  ADD COLUMN IF NOT EXISTS velocity          real,
  ADD COLUMN IF NOT EXISTS uncertainty       real,
  ADD COLUMN IF NOT EXISTS surprise          real,
  ADD COLUMN IF NOT EXISTS trend             text,
  ADD COLUMN IF NOT EXISTS n_observations    integer;
