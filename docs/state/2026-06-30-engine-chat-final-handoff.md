# Engine chat — FINAL HANDOFF (2026-06-30) — for track consolidation

Answers the 5-point request in `docs/state/2026-06-30-track-consolidation.md` §"What
I need FROM the engine chat". After absorbing this, the frontend/L2 chat is the
**single living track** and owns the engine. Everything below is committed + pushed
to `origin/v3-intel-layer` (working tree clean, 0 ahead). Checkpoint = **v2 reject
gate shipped** (a cleaner stopping point than waiting on the gold-growth pass, which
is now just an enhancement — see §2).

---

## 1. F3 / F4 status — what serves prod

**Two orthogonal things; don't conflate them:**

- **Topic CONSTRUCTION/SERVING (F3/F4): prod still serves v1.** The read-path flag
  `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` is **OFF** → `/threads` serves the
  original lexical-atlas + dynamic path, NOT `topic_members`. `unified-v2`
  (`build_unified_topics.py`) is **built + A/B-measured but NOT served**. A/B
  verdict (`engine_ab_report.py`): unified-v2 wins structurally (coherence
  0.930>0.908, purity 100%>98.1%, black-hole 12.1%<19.0%). **F4 cutover NOT
  flipped** — gated on new-topic labeling + gold confirmation + parametrizing the
  read path. `engine_version` serving prod = **v1 (original)**.
- **GATING (what counts as evidence): v2 reject is LIVE.** Independent of F3/F4.
  The lexical gate (`theme-hint-lex-v2`) + e5base scope gate now have a **third
  stage** that demotes force-fit (see §2). This changed WHICH signals are
  `gate_kept`, not how topics are constructed.

So: construction = v1 served (v2 built, not flipped); gating = v2 reject live.

## 2. #204 taxonomy gold + the v2 gate (this is the big shipment)

- **Gold base: 2,134 labeled, uniform 3-vote** (DeepSeek+OpenAI+Codex), **Fleiss
  κ 0.775 full / 0.800 in-category** (substantial). `docs/research/taxonomy-revision/goldset.json`.
  Method + result = manuscript-ready in `…/2026-06-29-taxonomy-revision-methodology.md`.
- **v2 gate measured** (`v2_gate_experiment.py`): baseline lexical gate **48.7%**
  category precision / **46.4% force-fit**; v2 e5 gate **61.5% / 70% in-scope @0.50**,
  **80% @ thr 0.60** (threshold = product knob).
- **v2 reject SHIPPED LIVE:** `backend/models/v2_gate.json` (numpy logistic over e5,
  $0 inference). Flipped: **567 force-fit assignments demoted** (43.3%), tagged
  `gate_model='v2-gate-e5-lr-1'`, **reversible**:
  `UPDATE signal_topic_assignments SET gate_kept=true WHERE gate_model='v2-gate-e5-lr-1'`.
- **A/B documented** in the methodology doc (verifiable via the gate_model tag).
- **Gold-growth pass (Plan 2) = NOT run yet.** It's the enhancement that would lift
  the gate's *balanced* point (61.5%→toward 80% without raising the threshold), by
  adding rare-category + in-scope-balanced gold. Run it **off-peak with cron
  coordination** (see §4 — crons are ON now, so the last-night "crons off + embed
  on efficiency cores" recipe must be re-applied to avoid stacking). Runner pattern:
  `/tmp/atlas_overnight.sh` (gold+embed) — re-create or adapt; gentle/measured.

## 3. `topic_members` schema + the ETL/cron chain

- **Migration 057** applied. Roles: **evidence / discussion / mood / movement**.
  Populated today: **evidence** (v1-compat ETL, parity-exact) + **discussion**
  (forum attach). **mood** = `nlp_sentiment` (F1, sparse). **movement** = blocked:
  events live in `events_v2` (GDELT CAMEO, not embeddable) / `acled_conflicts_v2`
  (0 rows) → needs an event-ref schema extension (#232), not a quick add.
- **Dual `engine_version`:** `v1-compat` (ETL projection, serves when the F0.3 flag
  flips) + `unified-v2` (build, isolated). 
- **ETL/cron chain (recurring on the M1 embed cron, 3×/day):**
  `embed_hot_corpus → assign_discussion_topics (attach) → etl_topic_members (v1) →
  build_unified_topics (v2)`. All post-embedding, pure-SQL/numpy. The
  `assign_discussion_topics` `$3::real` ambiguity bug is FIXED.

## 4. M1 cron + AtlasLocalWorker tree (so you schedule off-peak safely)

| cron | cadence | does | state |
|---|---|---|---|
| `com.atlas.atlas-topic-classifier` | 30 min | lexical assign + e5base gate + **v2 reject (Step 3)** | **ON** |
| `com.atlas.embed-hot-corpus` | 17:30/23:30/05:30 | embed→attach→ETL→build-v2 | **ON** |
| `com.atlas.emergent-snapshot` | (was 6h) | HDBSCAN snapshot | **OFF** (booted out 06-29) |
| `com.atlas.nlp-fleet` | adaptive | NER backfill | **OFF** (booted out 06-29) |

- **Heavy-compute rule (crash lesson):** never stack local embed/clustering during
  Pedro's work hours; the M1 crashed at load 177 from stacked compute. The embed
  cron fires 17:30/23:30/05:30 — schedule any extra heavy pass AROUND those, on
  efficiency cores (`taskpolicy -b`) + MPS-fallback + a load guard.
- **AtlasLocalWorker tree** (`/Users/pedro/AtlasLocalWorker/`, TCC-allowed, runs the
  crons): has `mlvenv` (numpy/torch/transformers/asyncpg) used for the gate + v2
  reject; `backend/.venv` has NO sklearn (use mlvenv for ML). `.env` has
  `ATLAS_V2_GATE_ENABLED=true` + `ATLAS_V2_GATE_JSON=…/models/v2_gate.json`.

## 5. Mid-flight / un-versioned (IMPORTANT)

- **Working tree clean, pushed (0 ahead).** No uncommitted *repo* edits.
- **⚠ The classifier runner Step 3 is UN-VERSIONED.**
  `/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh` (not in git) was
  edited to add the v2 reject; the synced `apply_v2_reject.py` + `v2_gate.json`
  live only in the AtlasLocalWorker tree. **On any engine-code change, re-sync
  `backend/scripts/ensemble/apply_v2_reject.py` + `backend/models/v2_gate.json` →
  AtlasLocalWorker, and the runner edit is not recoverable from git.** Consider
  versioning a copy of the runner in `scripts/`.
- **Pending (not started):** (a) gold-growth pass (§2); (b) 2 new natural-hazard
  categories (earthquake-volcano, wildfire-storm) into `atlas_topics` — only needed
  when the v2 taxonomy drives ASSIGNMENT prompts, deferred; (c) optional 3am–9am
  classification catch-up (the classifier was paused overnight; 30-min window only
  re-classifies forward, so that 6h window is un-classified — run
  `backfill_lexicon_topics --window-hours 7` once if you want it filled).

---

## Post-consolidation (from the consolidation doc, for continuity)
Fold the L2 §"unified-engine connection" into `2026-06-29-atlas-unified-engine.md`
as the 2 new roles (**attention** = wiki/trends→nearest centroid, verified=false;
**anomaly→movement** = per-topic volume-vs-baseline). A/B-gated. Sequence off-peak
after the gold pass. Engine guardrails unchanged: evidence never mixes
discussion/mood/movement; `gated_signal_count` is evidence-only; GDELT themes stay
an optional feature until the P1 ablation; no silent filtering.
