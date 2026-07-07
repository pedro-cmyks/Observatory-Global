# L3 Connection Layer — Constellation Assembly (direction, 2026-07-06)

**Status:** consolidated direction (Pedro + Claude, from the 2026-07-06 flagship
investigation session). This is the agreed NEXT JUMP after today's L3 dogfooding.

## Where this came from

Today we ran the first real L3 investigation end-to-end (pin → note → dossier)
on the live LatAm current phase (Venezuela earthquake + Colombia/Peru elections).
The session produced three loads of learning, all pointing to one gap.

### The lesson about L3 (Pedro's correction, load-bearing)
L3 is **NOT** the AI (or analyst) imposing a single thesis about "the"
relationship. L3 is a **multi-lens exploration surface**: the analyst pins —
even "crazily" — and then explores different **profiles / angles / nuances** of
the pinned set to discover relationships they could not have imagined. My repeated
failure this session was concluding ("they connect weakly", "change the approach
to dynamics") instead of letting the exploration surface the connections. Fix the
posture: **surface angles, don't close the thesis.**

### What the investigation measured
- **Connection is often structural, not entity-level.** Colombia + Peru elections
  barely share entities (Colombia→Spanish politics; Peru→Peru figures), so a naive
  entity-overlap test called them "weakly connected." WRONG lens. They rhyme
  strongly at the **pattern/category level** (both "election legitimacy dispute";
  both contested right-outsider wins; both loser-cries-fraud) and at the
  **coverage-dynamics level** (how the info moved). L3 must connect on
  category/pattern + coverage-dynamics, not just shared entities.
- **The earthquake ↔ elections link is real but geopolitical, not topical.** The
  through-line is US assertiveness: US intervention → Delcy interim govt → Trump's
  oil interest ("how much oil" first, "so sad about the quake" second) → the
  disaster unfolding under a US-shaped government, alongside the US-aligned
  right-wing election wins. This connection only emerges if you explore; it's
  invisible to a surface entity check.
- **Coverage asymmetry is itself the story** (who-says-what): the 3,342-death
  quake is led by French press + Chinese/Syrian STATE media, US/English absent,
  Spanish below-gate. Who covers a disaster — and who stays silent — is geopolitical.

### The gap that defines the next jump
Atlas **over-fragments** a big story. The Venezuela earthquake is not one thread —
it's a **constellation of ~30 near-duplicate/facet threads** in `dynamic_topics`:
many identical "Venezuela Earthquake Death Toll", plus rescues, UN affected
estimates, foreign victims by nationality (Italian/Spanish/Portuguese), aid
(Dominican Rep./Uruguay/Ecuador), aftermath, epidemic risk, govt inspection plan.
The **risk-management** dimension and the **international-reaction** dimension the
analyst asks for both EXIST — but scattered across dozens of fragments, so no
single surface shows the coherent picture.

## The next jump: the Connection Layer = Constellation Assembly

Assemble the fragments into a navigable constellation the analyst can explore by
facet. Two halves:

### A. Engine side — assemble the constellation
Merge near-duplicate / same-story fragments into ONE umbrella with typed
sub-facets, so "Venezuela Earthquake" is a single story with branches:
`death-toll`, `rescues`, `foreign-victims (by nationality)`, `international-aid`,
`government-response / risk-management`, `aftermath`. Builds on:
- R2 umbrella hierarchy (`build_umbrella_topics.py`, complete-linkage @0.98).
- The SAME-STORY / EVENT-LEVEL dedup guards from robot_categories (2026-07-05):
  intra-cohesion ≥0.80 = same-story work-list; dominant-token ≥60% = event-level.
- #238/#150 subject-geography (so a Colombian election isn't led by "West Bank",
  and foreign-victim facets attach to the right umbrella).
- Facet typing = the R3 category lens applied WITHIN an umbrella.

### B. L3 side — surface + explore the assembled constellation
The dossier/workbench must let the analyst explore the assembled story's facets
and cross-pin relations, on multiple lenses (topical, pattern/category,
coverage-dynamics, geopolitical entity-chain). This is the **dossier-rich task
already running** (task_4d886df7 → `local_f58ddd92`): connection analysis across
pins + embedded Equal Earth map + scoped investigative universe/vector-field +
coverage distributions. That task delivers the L3 half; it should connect on
**category/pattern + coverage-dynamics + shared-entity**, not entity-overlap alone.

## The principle to hold
- L3 = the analyst's multi-lens exploration tool. The system ASSEMBLES the
  constellation and OFFERS lenses; it does not pre-decide the one relationship.
- Connect on structure/pattern + coverage-dynamics, not just shared entities.
- Never fabricate a connection; never suppress one either — surface the profiles
  and let the analyst find the unimagined link.

## Execution status — engine side SHIPPED (2026-07-06)

§A (engine — assemble the constellation) built + verified against live prod DB:
- **mig 072** `dynamic_topics.facet` — event-internal narrative role of an umbrella
  child (distinct from `category` = R3 crisis class).
- **`backend/scripts/assemble_constellation.py`** — per-umbrella: (1) ATTACH ORPHANS
  by centroid cosine ≥0.93 GATED on sharing a discriminating SUBJECT token (generic
  hazard words like "earthquake" excluded via `_GENERIC_EVENT`, so Lakonia/Philippines/
  Mexico quakes never merge in — e5 space is compressed p50 0.94, cosine alone floods
  628); (2) RELABEL a facet-polluted umbrella to the canonical event stem; (3) TYPE
  each child facet (lexical, multilingual) — death-toll / foreign-victims / rescues /
  international-aid / government-response / aftermath. Reversible (`facet=NULL`).
  Broad `--apply` gated behind `--all` (dry-run showed sports/crime over-attach +
  label breakage; per-umbrella review is the safe default).
- **Applied to umbrella 1837**: "Venezuela Earthquake Death Toll" (a facet label) →
  **"Venezuela Earthquakes"**; +9 stragglers attached (522 ONU afectados, 1686 death
  toll 3,342, 258 US aid, 677 Portuguese repatriation, 520 Papa solidaridad…the
  international-reaction dimension); **35 children typed into 6 facets** (death-toll 17,
  international-aid 6, foreign-victims 5, rescues 3, aftermath 3, core 1).
- **Endpoint (`app/routers/dossier.py`, contract → `dossier-connections-v1`)**: pins
  that are umbrella children COLLAPSE into ONE umbrella node exposing `facets[]`
  (assembled over the umbrella's FULL child set, each facet with topics + evidence_n +
  countries) + `collapsed_from` + `child_count`. `collapse_umbrellas=false` = legacy
  flat view. **VERIFIED**: pinning the ~30 VE-quake fragments → **1 umbrella node + 6
  facets**, unresolved=0 (was 30 noisy near-duplicates).
- **#238 (scoped)**: FIPS `WE`(West Bank)/`GZ`(Gaza)→`PS` added to `country_codes`
  (was leaking raw non-ISO "WE"); backfilled 705 stored rows. HONEST residue: id-52's
  West-Bank lead is an **upstream GDELT geocoder error** (Spanish Sánchez/PSOE stories
  mis-located to West Bank), not a conversion gap — a separate ingest-quality task.
  Facet attachment is centroid-based (geo-independent), so "facets attach to the right
  umbrella" holds regardless. Tests: `tests/test_assemble_constellation.py` (facet lens
  + stem) + `tests/test_dossier_connections.py` green.

NOT wired into the nightly cron yet (per-umbrella review recommended until the relabel/
attach guards are hardened for sports/crime umbrellas) — run `assemble_constellation.py
--umbrella <id> --apply` after an umbrella build.

## Pointers
- Today's dossier + method: the "Double Séisme Venezuela in Venezuela" investigation
  (3 pins, connection note) — dogfooded live.
- Expert briefs: `docs/research/flagship/2026-07-06-latam-realignment-expert-brief.md`,
  `docs/research/flagship/2026-07-06-worldcup-geopolitics-expert-brief.md`.
- GTM framing: `docs/state/2026-07-06-gtm-plan.md` (dossier = the wedge artifact).
- L3-side build: task_4d886df7 (running). Engine-side (constellation assembly)
  = the umbrella-merge + facet-typing piece — NOT yet spawned; the other half.
