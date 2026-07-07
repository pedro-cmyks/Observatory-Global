# Embedding-space integration — whitening for edges + coherence, cost ledger

**2026-07-07.** Integrated the WINNERS of the measured LatAm head-to-head onto
`v3-intel-layer` (base HEAD `33954739`). Cherry-picked from 5 unmerged worktree
branches — did NOT merge naively (one branch was on an older base; three winners
+ the OpenAI-space branch all shared current HEAD, so hunks applied against
identical context and were combined per-file).

## The head-to-head (why these winners)

Pins: `dynamic-topic-52` (Cepeda — conflated Colombia black-hole),
`dynamic-topic-1419` (Keiko/Peru), `dynamic-topic-792` (Milei). Ground truth:
**Keiko↔Milei is a REAL edge** (they share Fujimori's inauguration);
**Cepeda↔anything is SPURIOUS**.

| space | Keiko↔Milei | Cepeda↔* (spurious) | verdict |
|---|---|---|---|
| raw e5 | 0.957 | 0.940 / 0.922 | unusable — all 0.92-0.96 |
| **whitened k=1 (global)** | **0.655** | **0.400 / 0.364** | **WINNER for edges** (wide margin, FREE) |
| OpenAI-space | 0.775 | 0.637 / 0.567 | tighter but PAID → not adopted |

Coherence (avg member→centroid cosine), same pins:

| space | dt-52 Cepeda | dt-1419 Keiko | dt-792 Milei | gap (blob vs clean) |
|---|---|---|---|---|
| raw e5 | 0.939 | 0.950 | 0.966 | ~0.011 (too tight to gate) |
| **whitened k=1** | **0.531** | **0.657** | **0.816** | **~0.126 (~11x)** |

Whitening de-compresses the coherence gap ~11x — a **clean loose/tight split
with NO OpenAI needed**. OpenAI-space coherence was only to be adopted if
whitening stayed borderline; it did not, so the OpenAI-space branch
(`confident-payne`) was NOT integrated (files `openai_space.py`,
`measure_openai_space.py` deliberately absent).

## What shipped

### 1. Global whitening asset (from `eloquent-mirzakhani-922e80`, clean add)
- `backend/app/services/whitening.py` — `load_whitening()` (cached, thread-safe)
  + `apply_whitening()` (center by mean, project out top-k, L2-normalize).
- `backend/app/data/e5_whitening.npz` — the fitted transform: **k=1, dim=768,
  fit on 99,871 signal vectors** (`fit_at 2026-07-07T19:39Z`).
- `backend/scripts/fit_global_whitening.py`, `backend/tests/test_whitening.py`
  (7 pass), the `--signals` extension to `measure_embedding_separation.py`, and
  `docs/research/embedding-whitening/2026-07-07-global-whitening-fit.md`.

### 2. AI cost ledger (from `upbeat-swartz-6308f2`, additive + signature reconcile)
- `backend/migrations/073_ai_cost_events.sql` — **APPLIED to Supabase**
  (`ai_cost_events`, RLS on).
- `backend/app/services/ai_cost.py` (`log_ai_cost`, fire-and-forget, never blocks
  the user path), `backend/scripts/ai_cost_report.py`,
  `backend/tests/test_ai_cost.py` (10 pass).
- **Signature reconcile:** `insight_llm.generate_insight` now returns a 4-tuple
  `(text, provider, error, usage)` and accepts `surface=`/`session_id=`. All 3
  callers updated to unpack 4 values + tag their surface:
  `dossier.py` (`dossier-synthesis`), `themes.py` (`theme-insight`),
  `briefing.py` (`brief`). `translate.py`, `deep_history.py`,
  `compute_category_typing.py` instrument their own paid calls too.
- Report verified live: renders per-surface token rows + $/interaction +
  $/active-user/month projection.

### 3. Dossier EDGES → global whitening (FREE) — `dossier.py`
- Pin centroids run through `apply_whitening()` (global asset, batched once)
  before the pin↔pin gate. **Whitened cosine drives the connect decision + the
  semantic weight; raw cosine stays the display `semantic_sim`.** Edge payload
  gains `whitened_sim`; meta reports `semantic_space` + the active threshold.
- **Threshold `SEM_EDGE_WHITENED_THRESHOLD = 0.50`** — re-measured on the 3 pins
  with the global asset (0.400 < 0.50 < 0.655), not hardcoded blind.
- Reversible: `ATLAS_DOSSIER_WHITENED_EDGES=0` → raw ≥ 0.88 gate. Degrades to the
  raw gate if the asset is unavailable.
- **Live verified:** only `Keiko ↔ Milei` survives (whitened 0.655, basis
  `[semantic, shared_person]`); both Cepeda edges dropped.

### 4. Coherence guard → global whitening (FREE) — `themes._thread_coherence`
- Now computes coherence in the **whitened space** (Python, member vecs pulled +
  whitened; country stats from the same rows). Contract UNCHANGED
  (`{score, tier, distinctCountries, topCountryShare, members, warning}` +
  additive `space`) so the ThemeDetail badge is untouched — only space +
  thresholds changed.
- **Whitened tiers:** loose < 0.60, mixed 0.60–0.70 (+ no-dominant-country
  guard), tight otherwise. Calibrated on a 60-topic sample (p25 0.737; real
  stories ≥0.60; atlas aggregate blobs — trade-export 0.35, heat-health 0.49 —
  well below).
- Reversible: `ATLAS_THEME_WHITENED_COHERENCE=0` → raw-e5 tiers (0.915/0.945).
- **Live verified:** dt-52 → loose + warning; dt-1419 Keiko → tight; dt-792
  Milei → tight (Peru/Argentina single-country events pass the country guard).

## Consumers by embedding space (adopt-per-consumer discipline)

| consumer | space | note |
|---|---|---|
| dossier pin↔pin edges | **whitened-e5-k1 (global)** | this change, tau 0.50 |
| dossier neighbors | whitened (per-request k=1) | pre-existing (HEAD), local fit |
| theme coherence guard (#224) | **whitened-e5-k1 (global)** | this change, loose 0.60 |
| assignment / clustering / gate | raw e5 | unchanged — re-measure before any flip |
| semantic thread-members ANN, research lane taus | raw e5 | unchanged |

## Explicitly NOT integrated
- `suspicious-sammet-794e1d` (LLM edge-verifier) — math-first; reasoning-AI is
  reserved for the brief prose only.
- `youthful-liskov-a53412` (per-request whitened edges) — stale base + superseded
  by the global asset. Its measured tau (~0.50) reused as the starting point,
  then re-confirmed empirically.
- `confident-payne-cab845` (OpenAI-space edges + coherence) — whitening (free)
  won both, so neither path was adopted.

## Verification
- `test_whitening.py` 7 pass · `test_ai_cost.py` 10 pass · dossier/theme suites
  green (one PRE-EXISTING stale failure `test_theme_insight_shape.py` — asserts
  a string that moved to `insight_llm.py` in the 2026-07-05 B0 refactor; absent
  on HEAD too, not caused here).
- `frontend-v2`: `npm run build` green · `npx vitest run` 203 pass (no frontend
  files changed).
- Live in-process tests against prod DB: coherence tiers + dossier edges exactly
  match the head-to-head.
- Backend `main_v2` boots; all touched modules import.

Reversibility: two env flags (`ATLAS_DOSSIER_WHITENED_EDGES`,
`ATLAS_THEME_WHITENED_COHERENCE`), migration 073 reversible (`DROP TABLE
ai_cost_events`).
