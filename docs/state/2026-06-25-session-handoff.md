# Session handoff — 2026-06-25

Branch `v3-intel-layer` (= production: Fly `atlas-api-pedro` + Vercel +
Supabase). Clean + pushed. Commits this session: `5fe589e` → `c562f3c`.

This session had two arcs: (A) **infra / NLP throughput** — the headline work,
ending in an adaptive parallel NER fleet now running on the M1; and (B)
**product + papers** — #234 relation upgrades and bringing all 8 papers current
with the product. Everything below is shipped, verified, and deployed unless it
says otherwise.

---

## TL;DR — what to check tomorrow

The one thing we're **waiting on**: the new adaptive NLP fleet draining the
208K-signal NER backlog overnight. To review:

```bash
# 1. Fleet job alive + what mode it's in (gentle while Pedro works, burst when idle)
launchctl list | grep atlas.nlp-fleet
grep "switching" /Users/pedro/AtlasLocalWorker/logs/nlp-fleet.out.log | tail   # look for "gentle -> burst"

# 2. Did burst actually run + drain? (worker children during an idle window = up to 2)
pgrep -fl enrichment.nlp_worker
```

```sql
-- 3. Backlog trend (was 208,238 un-NER'd at session end). Want this FALLING.
SELECT COUNT(*) FILTER (WHERE nlp_processed_at IS NULL) AS backlog,
       COUNT(*) FILTER (WHERE nlp_processed_at IS NOT NULL) AS done
FROM signals_v2;
-- 4. Typed-subject payoff: nlp_persons coverage rising → subjects flip unverified→verified
SELECT COUNT(*) FILTER (WHERE nlp_persons IS NOT NULL
        AND jsonb_typeof(nlp_persons)='array' AND jsonb_array_length(nlp_persons)>0
        AND timestamp > NOW() - INTERVAL '24 hours') AS persons_24h,
       COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '24 hours') AS signals_24h
FROM signals_v2;
```

**Success = backlog falling after an idle/overnight window + persons_24h rising.**
If backlog is NOT falling: check the fleet log for burst events; if it never
bursted, Pedro may not have been idle >180s on AC, or check
`logs/nlp-fleet.err.log` for worker errors.

---

## A. Infra + NLP throughput (the main work)

### Final machine layout — one purpose per box
| Machine | Runs | Notes |
|---|---|---|
| **Fly `app`** (1GB shared-1) | API + ingestion (`start.sh`) | unchanged |
| **Fly `nlp_worker`** (4GB shared-2x) | **embed service** (e5, semantic lane — must sit next to the API; M1 NAT can't serve it) + light sentiment fast-lane | NER made rare here (`NLP_WORKER_INTERVAL_SECONDS=600`) so it never starves embed → `/research/plan` steady ~0.45s |
| **M1 `com.atlas.nlp-fleet`** | the **adaptive NER fleet** (see below) | bulk NER lives here, mindful |
| **M1 crons** | atlas-topic-classifier (30m), emergent-snapshot (6h), embed-hot-corpus (17:30/23:30/05:30) | unchanged |

Why this shape: the original bug was the Fly `nlp_worker` hosting BOTH the embed
service and the heavy NER in one Python process → per-cycle model load starved
the embed thread → semantic search timed out. Fix = NER off the Fly box onto the
M1; embed stays on Fly next to the API.

### The adaptive NLP fleet (#184) — the headline deliverable
Goal (Pedro): drive NER true-output toward 100% (output == input) + drain the
backlog, but NEVER freeze his machine while he works.

- **Backlog measured:** 208,238 signals un-NER'd (95%); 11,232 done (5%);
  ingest ~6.4k/hr; ~7 days of retention.
- **Sharding** (`backend/enrichment/nlp_pipeline.py`, `_priority_select_sql`):
  `NLP_WORKER_SHARD_COUNT` / `NLP_WORKER_SHARD_INDEX` → each worker restricted to
  `id % N = K`. Verified even + disjoint (N=4 → 52043/52080/52000/52115 = the
  backlog). Chosen over `FOR UPDATE SKIP LOCKED` because the NER batch is slow —
  SKIP LOCKED would hold a transaction open minutes × N; modulo sharding needs no
  locks and no held transactions.
- **Adaptive supervisor** (`scripts/nlp_fleet_supervisor.py`): probes HID idle
  (`ioreg HIDIdleTime`) + AC power (`pmset`) every 30s.
  - **GENTLE** (active / on battery): 1 mindful worker (`taskpolicy -b` →
    efficiency cores, `SHARD_COUNT=1`, covers everything). Identical to the prior
    single worker.
  - **BURST** (idle > 180s on AC): N sharded workers at normal priority →
    performance cores → ~8-10k/hr > ingest → drains the backlog. Falls back to
    gentle within 30s of Pedro touching the machine.
- **launchd** `com.atlas.nlp-fleet` (repo: `infra/launchd/com.atlas.nlp-fleet.plist`):
  deliberately NO `ProcessType=Background` — that QoS clamp would propagate to the
  worker children and pin the burst workers to the efficiency cores, defeating the
  burst. Each worker sets its own QoS instead.
- **8GB constraint:** the M1 is **8GB** (verified, not 16) and also runs heavy ML
  crons → `BURST_WORKERS=2` (each worker peaks ~1.5GB of models; 2 perf workers
  already clear ingest). Bump via `ATLAS_NLP_BURST_WORKERS` only if free RAM
  proves comfortable.
- **Retired:** the old single-worker `com.atlas.nlp-worker` job (booted out +
  its installed plist removed so it can't reload on login and double-run). The
  repo still has `infra/launchd/com.atlas.nlp-worker.plist` + the old runner
  `scripts/run-nlp-worker-local.sh` for reference — superseded by the fleet.

### Honest throughput model (set expectations)
- **Active hours:** gentle ~3k/hr < 6.4k/hr ingest → backlog grows slightly. This
  is the deliberate trade-off (mindful: never freeze the machine).
- **Idle hours:** burst ~8-10k/hr > ingest → drains + makes up the deficit.
- So **output == input is reachable as a DAILY AVERAGE** given enough idle time,
  NOT instantaneously while Pedro works. The 208K backlog clears over **~days of
  idle bursting**, then steady-state keeps up.
- Faster levers if wanted later: `burst=3` (RAM permitting) or a dedicated
  always-on box (not the 8GB M1).

### Verified at session end
Gentle worker completed a cycle ("NER[en-v1]: 300 signals"); burst env validated
(2 disjoint shards); supervisor in gentle; only the fleet job present (no
double-run). **NOT yet observed live:** an actual burst→drain cycle — that needs
a real idle window (tomorrow's review).

### Operational note (IMPORTANT for any future worker change)
The fleet runs from `/Users/pedro/AtlasLocalWorker` (macOS TCC blocks launchd
from the Desktop/iCloud repo path). The code is **versioned in this repo** but
**executed from there**. On ANY change to `enrichment/` or the fleet scripts,
re-sync:
```bash
cp backend/enrichment/*.py /Users/pedro/AtlasLocalWorker/backend/enrichment/
cp scripts/nlp_fleet_supervisor.py /Users/pedro/AtlasLocalWorker/nlp_fleet_supervisor.py
cp scripts/run-nlp-fleet-local.sh /Users/pedro/AtlasLocalWorker/run-nlp-fleet-local.sh
launchctl kickstart -k gui/$(id -u)/com.atlas.nlp-fleet
```
Credentials (`DATABASE_URL`) live in `/Users/pedro/AtlasLocalWorker/.env` (600).

### Multilingual NER — investigated, NOT enabled (don't retry blindly)
Tried to flip multilingual on the M1 to verify non-English subjects. Two
blockers: (1) `xx_ent_wiki_sm` extracts Latin-script fine (es/fr/pt) but returns
NOTHING for Persian/Arabic/CJK — the actual diversity gap; the Problema-A
gazetteer already types those honestly. (2) the xlm sentiment tokenizer is broken
in the M1 `mlvenv` (transformers 5.8 / Py3.14 routes SentencePiece → tiktoken),
no skip-sentiment flag → would crash the worker. Real non-Latin NER needs a
proper multilingual token-classification model + a working transformers env — a
scoped task, not a config flip. Until then non-English subjects stay
gazetteer-typed (`unverified`, honest).

---

## B. Product + papers

### #234 relation upgrades (shipped, browser-verified, on Vercel)
- **Rarity-weighted entity-overlap thread siblings** (`NarrativeThreads.tsx`):
  opening a thread surfaces siblings sharing a top-2 country OR a shared
  DISTINCTIVE entity. Naive entity-overlap was HARMFUL — one common GDELT entity
  ("donald trump", DF 14/30) linked every unrelated thread; fixed by counting
  only entities with document-freq ≤ min(3, 25% of the list). Live-verified:
  spurious matches gone, genuine cross-geography siblings surface.
- **Sibling reason chips:** a surfaced sibling shows WHY it relates
  ("↔ Russia" / "↔ <distinctive entity>") instead of a silent dim — satisfies the
  no-silent-filtering / reason-codes guardrail. Verified: open "Ukraine War
  Updates" → 2 siblings chipped "↔ Russia", 17 dimmed, 0 console errors.
- #234 is now complete for country/person/thread focus across all main surfaces.
  Remaining (NOT done, design discussion needed): **thread-as-full-focus-lens**
  (today thread-open clears focus by design); public-attention focus panels
  (already mostly item-scoped).

### #229 coverage — DIAGNOSED, not fixed (data-layer task)
Funnel measured: 174K signals/24h → 71K persisted corpus → ~23 clusters/snapshot
→ ~50 served threads ≈ **0.2% coverage**. Bottleneck is **clustering RECALL, not
the promotion gate** (verified: 0 candidates qualify-but-stuck; 150/181
candidates single-snapshot; 114 < 30 signals; fast-tracking high-volume
candidates would promote 0 topics). Real lever = `min_cluster_size` granularity +
scoped regional passes (global HDBSCAN drowns regional stories — e.g. the Peru
recount, 92 signals, never clustered). Needs an offline-tested clustering change
on the M1 cron — a dedicated data-layer session.

### Papers — all 8 now current with the product
Pedro's instruction: cross-references must be WRITTEN INTO the paper methodology
(grow the paper), not just mentioned. Master plan:
`docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`.
- **P7** (viz/workflow): focus-propagation relation model + the rarity-weighted
  finding (DF-launder → distinctive-only, same volume≠importance principle as P3)
  + a relation-quality ablation to collect. *(this session, by main thread)*
- **P8** (open-set discovery): the #229 recall-ceiling measurement as product
  evidence. *(this session, by main thread)*
- **P1–P6**: product evidence added by a spawned agent (`8c62cef`), each verified
  against code (e.g. `SIGNAL_MIN_SIMILARITY=0.84`, the 0.45/0.35/0.20 thread
  ranking weights, `voice_mix` self_voice/voice_entropy, `thread_matches_person`,
  `atlas_heat`, `twitter-xlm-roberta`). All six are real crosses.

---

## Open / next (in rough priority)
1. **Tomorrow:** review the fleet drain (TL;DR section). Decide if burst=2 is
   enough or bump to 3 / consider a dedicated box.
2. **#229 clustering recall** — the real coverage lever; dedicated data-layer
   session (offline quality testing on the M1 cron).
3. **Multilingual NER** — proper token-classification model + working transformers
   env, so non-English subjects flip verified (#162).
4. **#234 thread-as-focus-lens** — design discussion first (changes the
   thread-open focus model).
5. Parked/standing: `burst=3` if RAM allows; the Fly `nlp_worker` could shed its
   rare NER entirely once a clean `NLP_WORKER_NER_ENABLED=false` deploy lands
   (the flag is committed; the process-group deploy kept failing to apply staged
   secrets — `interval=600` achieves the same reliably for now).

## Quick reference
- Deploy Fly API: `./scripts/deploy-fly-api.sh` · Fly worker: `./scripts/deploy-fly-nlp-worker.sh`
- Prod embed smoke: `curl -s -X POST https://atlas-api-pedro.fly.dev/api/v2/research/plan -H 'Content-Type: application/json' -d '{"query":"Iran water","hours":168}'`
- Fleet logs: `/Users/pedro/AtlasLocalWorker/logs/nlp-fleet.{out,err}.log`
- Frontend tests: `cd frontend-v2 && npm run build && npx vitest run` (74 passing)
