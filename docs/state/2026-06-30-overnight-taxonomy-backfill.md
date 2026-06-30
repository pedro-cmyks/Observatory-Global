# Overnight session — #204 gold base + embedding backfill (2026-06-29 → 06-30)

**Goal (Pedro, /goal):** grow the taxonomy gold base *significantly* + run the
embedding backfill, **measured** resource use, several passes, all night.

## Result — both axes grew hard, machine never strained

| Metric | Start | End | Δ |
|---|---|---|---|
| **Gold base** (labeled signals) | 811 | **2,134** | **+1,323 (2.6×)** |
| **signal_embeddings** (corpus) | 54,691 | **239,233** | **+184,542 (4.4×)** |
| Fleiss κ (full label space) | 0.739 | **0.776** | rose with size (substantial) |
| κ in-category (crisis types) | — | **0.800** | substantial |

Load stayed **~1–3 the whole night** (the 177-spike crash from running embed on
performance cores is not repeated). Everything ran on **efficiency cores**
(`taskpolicy -b`) + MPS-fallback + load guard + cooldowns. Heavy M1 crons were
OFF the whole night (no pile-up).

## How (measured, two phases)
1. **Gold + embed runner** (18 iters, ~22 min each): per-iter 5K embed batch +
   one ensemble gold pass. Mid-run the sampling was **widened** (Pedro's call):
   random pull 150→350 from the **full recent stream** (72h→336h), so the gold now
   represents the real input distribution the gate must classify — not only
   gate-kept evidence. This is what makes the OUT_OF_SCOPE decision measurable +
   trainable.
2. **Embed-night continuation** (24 iters, embed-only): once the gold base was big
   + validated, the rest of the night went to the **taxonomy-INDEPENDENT**
   embedding backfill (the $0-gate substrate, #229). No gold passes → no codex,
   no 2-vote debt.

## Codex (the metered 3rd annotator)
ChatGPT-subscription codex exhausted its quota ~00:20 and **did not reset by
2:55am** (rolling window longer than the ~1:30am estimate). The base kept growing
2-model (DeepSeek + OpenAI) the rest of the night — valid, just 2 votes.
- **~700 records are 2-vote** (codex-missing). Quality of the 3-vote subset is
  intact (77% unanimous, κ 0.78).
- **Backfill ready:** `backend/scripts/ensemble/phase_d_codex_backfill.py`
  (quota-safe, idempotent) fills *only* those gaps when codex resets:
  ```bash
  cd backend && .venv/bin/python -m backend.scripts.ensemble.phase_d_codex_backfill
  ```
  ~50 codex calls (within a fresh window). Re-run after each reset until it
  reports 0 remaining. **Not auto-run** — your codex budget, your call when.

## Documented for the papers (Pedro's ask: "documéntalo bien")
`docs/research/taxonomy-revision/2026-06-29-taxonomy-revision-methodology.md` now
has a **manuscript-ready "Methodology for Paper 1"** section: motivation
(taxonomy-bound precision), multi-model×multi-persona ensemble, **representative
sampling** rationale, gold construction + provenance, **Fleiss κ 0.776 / 0.800**,
honest limitations (LLM-consensus not human gold; codex quota episode; embeddings
taxonomy-independent), reproducibility. Committed.

## State at handoff
- **Nothing heavy running** (embed-night done 05:47; machine idle, load <1).
- **Crons still OFF** (you paused them — they re-process with the *old* gate, which
  v2 will redo). Re-enable when ready:
  ```bash
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.atlas.embed-hot-corpus.plist
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.atlas.atlas-topic-classifier.plist
  # heavy ML crons (booted out earlier this session, separate):
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.atlas.nlp-fleet.plist
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.atlas.emergent-snapshot.plist
  ```
- Remaining un-embedded in the 336h window: **~223K** (replenished by ingest;
  nightly embed cron chips it once re-enabled).

## Next (the payoff — held for your review)
1. **Codex backfill** the ~700 2-vote gaps (command above) → uniform 3-vote base.
2. **Train/calibrate the v2 GATE** on the gold base → kills the ~60% force-fit;
   **measure the precision lift** (current 41.6% → expected ~75–80%, the
   LLM-baseline ceiling) on a held-out split. This is the Paper 1 result + the
   product win (clean, honest threads).
3. **Wire v2 into production** (gate/assignment prompts + the 2 new natural-hazard
   categories in `atlas_topics`) — on your go.
4. Your **interactive round** against Atlas with the v2 taxonomy.

---

# Morning session (2026-06-30) — codex backfill + v2 gate SHIPPED

- **Codex backfill** done → gold base uniform 3-vote (2,134, 0 gaps, κ 0.775 full /
  0.800 in-category).
- **v2 gate experiment** (`v2_gate_experiment.py`): baseline lexical gate 48.7%
  category precision / 46.4% force-fit; v2 e5 gate 61.5% / 70% in-scope @0.50,
  **80% @ thr 0.60** (threshold = product knob). Documented as the Paper 1 result.
- **v2 gate TRAINED + SHIPPED** (`train_v2_gate.py` → `backend/models/v2_gate.json`,
  numpy weights). **FLIP applied live: 567 force-fit demoted** (43.3%), tagged
  `gate_model=v2-gate-e5-lr-1`, reversible.
- **Recurring reject wired**: classifier runner Step 3 (`apply_v2_reject.py`,
  mlvenv numpy-only), flag `ATLAS_V2_GATE_ENABLED=true` in AtlasLocalWorker/.env.
  Every 30min: lexical + e5base gate + v2 force-fit cut. **NOTE: the runner
  `/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh` is un-versioned —
  the Step 3 edit lives only there + the synced model/script in AtlasLocalWorker.**
- **A/B documented in Paper 1** (verifiable + reversible via the gate_model tag).
- Crons re-enabled (classifier + embed); nlp-fleet + emergent-snapshot stay OFF.

**Reversibility:** `UPDATE signal_topic_assignments SET gate_kept=true WHERE
gate_model='v2-gate-e5-lr-1'` undoes the whole v2 reject.

**Open here (afternoon, on Pedro's go):** Plan 2 = grow more gold (rare-category +
in-scope balanced) to lift the gate's *balanced* point; optional 3am–9am
classification catch-up for the window the classifier was paused.
