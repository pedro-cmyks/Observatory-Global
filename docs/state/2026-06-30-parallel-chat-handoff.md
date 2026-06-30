# Handoff for the parallel chat (paste this)

Working on **Atlas / Observatorio Global**, branch `v3-intel-layer`. Read
`CLAUDE.md` first (product wedge + guardrails). For the live map of
endpoints/DB/cron, run `python scripts/project_inventory.py`.

## ⛔ RESERVED — do NOT touch (another session owns this, in flight)
The **backend taxonomy + classifier + gate engine** track. Specifically leave alone:
- `docs/research/taxonomy-revision/` (the gold base `goldset.json`, methodology) — #204.
- The v2 reject gate: `backend/models/v2_gate.json`, `backend/scripts/ensemble/*`
  (`apply_v2_reject.py`, `train_v2_gate.py`, `v2_gate_experiment.py`), and the
  classifier runner Step 3 (`/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh`).
- `atlas_topics`, `signal_topic_assignments` gating, the scope gate
  (`apply_scope_gate.py` / `score_assignments_gate.py`), the unified-engine specs
  (`docs/specs/2026-06-29-atlas-*.md`).
- The M1 crons + `AtlasLocalWorker/` tree. **Don't run heavy local compute**
  (embed/clustering) — that session is doing a gold-growth pass this afternoon and
  the machine has crashed before from stacked compute.

## Current state (1 line)
v2 reject gate just shipped: cut ~43% force-fit from served threads (reversible via
`gate_model='v2-gate-e5-lr-1'`). Engine arc F0–F3 done; #204 taxonomy v2 live.

## ✅ Open tracks you CAN take (frontend / product surfaces — no backend-engine overlap)
Pick per the spec; all independent of the reserved track:
- **L2 deep-review remainder** — `docs/specs/2026-06-26-l2-deep-review.md`: A3 scope
  strips, A4 first-click walkthrough, C3 per-thread public attention. (frontend-v2)
- **#234 focus propagation remainder** — thread-as-full-focus-lens, public-attention
  focus panels. (frontend-v2, client-only)
- **Mobile visualization #236** — phone-native surfaces (L0 Landing / L1 Brief
  polish are near-term; L2 console is bigger). (frontend-v2)
- **Consumer MVP Phase 2 leftovers** — share-card (Task 6) + final Lighthouse/PWA
  (Task 8) from `docs/state/2026-06-25-consumer-mvp-pwa-session.md`.

## Guardrails (from CLAUDE.md — non-negotiable)
- Product wedge = the **narrative analyst** (honest situational awareness). No new
  surface until telemetry shows a value moment.
- User-facing topic model = **Narrative Threads** (never raw GDELT themes/curated
  concept maps). `dynamic_topics` is the backing record, not a separate concept.
- **No silent filtering** — ranking/gating needs reason codes + inspectable trays.
- **Verify before assuming** a panel/data is broken (measure-first).
- frontend-v2: **vanilla CSS** (Tailwind only in `Landing.tsx`); `data-tip` not
  `title=`; `getThemeLabel()` for theme names; run `npm run build` (not just tsc)
  before pushing.

If unsure whether something overlaps the reserved track, ask before editing
backend `classify/gate/topic/taxonomy` code or anything under `AtlasLocalWorker/`.
