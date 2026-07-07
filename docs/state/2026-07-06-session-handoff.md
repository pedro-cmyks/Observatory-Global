# 2026-07-06/07 Session Handoff — Security hardening, L3 connection layer, whitening, flagship dogfood

Branch `v3-intel-layer` (tip `5a366545`). All items below merged, deployed to
Fly + Vercel, and verified against code/prod. This doc is the durable record;
the CLAUDE.md top block is the scannable summary.

## Verification note

Every claim here was checked against the tree, not transcribed. Corrections
found during verification are called out inline (e.g. the dossier response
contract is `dossier-connections-v1`, but the empty-state payload returns
`dossier-connections-v0` — both live in `app/routers/dossier.py`).

---

## 1. Security — pre-launch audit + interim hardening

Doc: `docs/state/2026-07-06-security-audit.md`. Commit `e5eb99d5`
(`feat(security): interim per-IP rate limiting + CORS lock + pool bump + emergent gate`).

**3-sweep audit findings:**
- SQL-injection: clean (parametrized throughout).
- Secrets: never committed (env-sourced; `.env` gitignored).
- XSS: none found.
- **Real gap = the API is wide-open** (no auth, no rate limit, CORS `*`). That
  is the launch blocker the interim hardening addresses.

**Interim hardening shipped:**
- **Per-IP rate limiting** — `backend/app/rate_limit.py`. Keys on the leftmost
  `X-Forwarded-For` entry (Vercel forwards it). Documented caveat in-file:
  X-Forwarded-For is client-spoofable on a *direct* hit to the Fly box (interim,
  not the final defense).
- **CORS lock** — `main_v2.py:48-57`: locked to `ATLAS_CORS_ORIGINS`
  (comma-separated) when set; prints a warning and falls back to `*` when unset.
- **DB pool 5→10.**
- **`/api/v2/emergent` admin-gated** (`ATLAS_ADMIN_TOKEN`).
- `ATLAS_ADMIN_TOKEN` + `ATLAS_CORS_ORIGINS` set on Fly.

## 2. GTM plan

Doc: `docs/state/2026-07-06-gtm-plan.md` (commits `1972d67b`, `348a2e72`).
Design-partner-led motion; business/cold-outreach/M1-bound. Strategy doc only —
no code.

## 3. Search → country + surface polish

- **"Go to \<Country\>" primary action** — `SearchBar.tsx:447`. Searching a
  country name surfaces navigation to that country as the top action (commit
  `51b9496b`). Note: a broader search-simplify refactor is UNMERGED (3-way
  conflict in SearchBar) — see loose ends.
- **Real flag images** — `Flag.tsx` + `flag-icons ^7.5.0` (package.json:20),
  replacing emoji flags (commit `b89ca3a3`).
- **Time-travel** — `StoryTimeTravel.tsx` (commit `79b4b9f8`): widen a story's
  window + jump to a topic's activity spike.
- **Migration 071 natural-hazard categories** — `071_natural_hazard_categories.sql`
  (commit `1d9deb26`). ROOT CAUSE recorded in the migration: candidate-v2.json
  FLAGGED `earthquake-volcano-disaster` + `wildfire-storm-disaster` but never
  wrote them to `atlas_topics`; `compute_category_typing.py --deepseek` builds
  its menu from `atlas_topics WHERE is_active`, so seismic stories had NO
  earthquake bucket → DeepSeek force-fit them into "Armed conflict escalation"
  (KILL theme-hint on mig-019 pulls casualty language "morts"/"Kill 32" into
  conflict). Fix seeds both categories with disaster-specific theme hints
  (NATURAL_DISASTER_*, deliberately NOT KILL). Labels match candidate-v2 exactly
  so prior correct typings stay consistent.

## 4. L3 CONNECTION LAYER — the big build

Spec: `docs/specs/2026-07-06-connection-layer-constellation-assembly.md`
(commit `a367ef1e`).

### 4a. Dossier connections (`dossier-connections-v1`)

`backend/app/routers/dossier.py` (`POST /connections`, commit `75809970`) +
`frontend-v2/src/components/DossierConnections.tsx`. MEASURED relations between
pinned topics:
- semantic centroid cosine,
- shared-country,
- rarity-weighted shared-person.

Renders as an **investigative universe** + **Equal Earth map** + **coverage
distributions**. Contract: response payload = `dossier-connections-v1`;
empty-state payload = `dossier-connections-v0` (both strings in the router).

### 4b. Constellation assembly (facet-typed umbrellas)

- **Migration 072** — `dynamic_topics.facet TEXT` (`072_topic_facet.sql`,
  commit `a793c7e9`). Names the event-INTERNAL role of an umbrella child
  (death-toll / foreign-victims / international-aid / rescues / aftermath /
  government-response). Distinct from `category` (cross-event crisis class).
  NULL for umbrellas + un-parented standalones. Reversible
  (`UPDATE dynamic_topics SET facet=NULL`).
- **`scripts/assemble_constellation.py`** — lexical typer over child labels;
  folds ~35 near-dup fragments of one big story into typed facets. Applied to
  the Venezuela earthquake umbrella (topic 1837).
- **Facet-aware endpoint** (`dossier.py` `_facets_for`) + facet rendering in the
  connection layer (commit `f3c0d78e`).
- **Neighbors as background stars + visible edge-why** (commit `3a3c26dc`):
  constellation neighbors surface with the reason the edge exists.

## 5. WHITENING — de-compress e5 (measured)

The e5 embedding space is compressed (near-duplicate centroid cosines). Applied
**all-but-top k=1 whitening** to dossier neighbors.

- **Centroid level** (commit `3990af0d`, `measure_embedding_separation.py`):
  gap **+0.04 → +0.31**, AUC **0.80 → 0.87**. Surfaces real bridges
  ("Milei attends Fujimori") and drops generic-central noise. Replaced the
  earlier token-gate hack (`77f9d19c`).
- **Signal level** (commit `5a366545`, `measure_signal_separation.py`): whitening
  k=1 = **4.4x gap**. VERDICT: the clustering cliff is compressed-SCALE, not
  separability — whitened signals are a candidate lever for HDBSCAN recall
  (research finding, not yet wired into clustering).
- Prior fix `07a2865a`: dossier neighbors computed via Python cosine because
  `centroid_vec` is `real[]`, not pgvector.

Both harnesses are READ-ONLY, runnable on the M1 mlvenv (free compute).

## 6. Flagship dogfood — LatAm realignment + World Cup

Two expert briefs under `docs/research/flagship/`:
- `2026-07-06-latam-realignment-expert-brief.md`
- `2026-07-06-worldcup-geopolitics-expert-brief.md`

LatAm ran end-to-end through L3 (VE earthquake + Colombia/Peru elections;
pin→note→dossier). **Coverage-asymmetry finding:** a 3,342-death quake was led
by French press + Chinese/Syrian state media, with US/English press absent —
the connection layer surfaces this as a coverage-dynamics pattern, not an
entity-overlap match.

## 7. Method / lesson

- L3 = **multi-lens exploration**: surface angles, don't impose a thesis.
- Connect on **pattern / coverage-dynamics**, not entity-overlap.
- The **"report must stand alone" (Frank) test**: a dossier has to read without
  the session context that produced it.

---

## OPEN LOOSE ENDS

- **Search-simplify UNMERGED** — a 3-way conflict in `SearchBar.tsx`. The
  "Go to \<Country\>" action IS merged (`51b9496b`); the broader simplify is not.
- **Geo-mistag fix uncommitted** — lives in worktree
  `.claude/worktrees/sweet-bose-c24dd7` (at `6bf51d02`). Commit or discard.
- **Running background tasks** (state at handoff): clustering-whitening,
  map-key z-index, universe-legibility.
- **PERU constellation not yet assembled** — the assembly tool asked to also fold
  PERU into an umbrella; its near-dups currently appear as neighbors (background
  stars) rather than typed facets. Next mechanical run of
  `assemble_constellation.py`.
- Many sibling worktrees are pinned at the same tip (`5a366545`) — housekeeping,
  not work in flight.
