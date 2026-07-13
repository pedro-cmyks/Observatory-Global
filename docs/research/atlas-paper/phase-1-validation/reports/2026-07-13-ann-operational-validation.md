# ANN operational validation note

**Date:** 2026-07-13  
**Role in paper track:** reproducibility and system-feasibility evidence only.
This does not validate narrative quality, subject geography, or usefulness.

Atlas's hot semantic corpus moved from HNSW to IVFFlat after controlled trials
showed HNSW could not be constructed or maintained without spilling, blocking
writes, or starving serving on the shared 1 GB database. The full operational
record is `docs/state/2026-07-13-ann-index-recovery.md`.

For the current 327-list index, 20 deterministic dispersed queries were compared
with exact cosine neighbors. At probes 20, recall@10 was 1.000 for every sampled
query, mean ANN latency was 130.97 ms, and maximum was 203.08 ms. A transaction
that inserted 256 real missing IDs and rolled back took 172.429 ms. These values
support the claim that the current retrieval mechanism can preserve sampled
neighbor recall while restoring useful write throughput.

Paper-use guardrails:

- report the corpus size (326,762 at build), vector type (`halfvec(768)`), list
  count (327), query sample construction, `k=10`, probe count, and hardware/DB
  envelope together;
- call the result a sampled operational validation, not universal ANN accuracy;
- rerun exact-vs-ANN measurement after material corpus/list changes;
- do not use ANN recall as a proxy for topic precision or editorial usefulness;
- keep the shared serving/batch database as a limitation even though the index
  mechanism is recovered.

