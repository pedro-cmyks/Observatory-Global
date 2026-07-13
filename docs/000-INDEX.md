# Observatorio Global — Docs Index

Opens this folder as an [Obsidian](https://obsidian.md/) vault. Use the
graph view (cmd-G) for the relationship map across all docs. Wikilinks
below resolve via Obsidian's fuzzy search regardless of folder.

## Start here

- [[ARCHITECTURE]] — data-flow diagram + API surfaces + cron table.
- [[PROJECT_INVENTORY]] — machine-verified endpoints / frontend ↔ API /
  DB tables / cron / recent commits. Regen via
  `python3 scripts/project_inventory.py`.
- [[STATUS]] — long-running operational status doc.
- [[Data Operations]] — storage, crons, historical sync, and runtime guardrails.
- [[Narrative Intelligence]] — Living Narrative Threads, emergent clusters, and
  product/model canon. Guardrail: `dynamic_topics` is the implementation
  backing for many user-facing threads, not a separate product category.
- [[Validation and Paper Track]] — benchmark, annotator, precision-gate, and
  paper evidence map.
- [[Frontend Product Surfaces]] — which UI panels consume which contracts.

## Latest handoffs

- [[2026-07-12-spec-history-crosswalk]] — reconciliation of the approved
  Investigation Graph with Workbench, Threads, movement, dossier,
  corroboration, events, voice, history and validation canon; records what is
  genuinely new, what must be reused and which older rank/cap decisions are
  superseded.
- [[2026-07-13-l0-l3-reliability-matrix]] — current product/ops truth from L0
  through L3, including the complete-universe Daily Investigation measurement,
  precomputed serving artifact, editorial gaps and embedding-index incident.
- [[2026-07-12-investigation-graph-slice-3-daily-publication]] — executable plan
  for typed graph edges, shared PublicationPackage, math-first L1 selector,
  Workbench adapter and joint editorial gate.

- [[2026-07-12-subject-geography-math-first-design]] and
  [[2026-07-12-subject-geography-math-first]] — complete-universe, read-only
  subject geography Stage 1 for #238, with deterministic scoring, abstention,
  proxy ledgers, invariants, and ablations. Live artifacts:
  `docs/research/subject-geography/`.
- [[2026-05-30-phase-2-emergent-wiring-handoff]] — Phase 2/3 emergent
  layer shipped; correction about wrong surface; next-session top
  priority.
- [[2026-05-30-context-gap-inventory-proposal]] — diagnosis of the
  context-fragmentation problem that motivated this index + the
  inventory tool.

## Active design specs

- [[2026-06-09-research-thread-builder-workbench]] — detailed target for
  natural research search + Workbench investigation: search returns Atlas
  anchors/options ranked by investigative usefulness, the user opens and pins
  useful items, and Workbench preserves the route for who-says-what, frame
  comparison, coverage gaps, transparent downranking, Reddit/public-discussion
  lanes, saved investigation sidebar/history, list/detail reconciliation, and
  optional report/export using the Iran climate/water + US bases/satellite
  compound case. **This is the working guide for current effort.** Phases
  0.5/1a/1b shipped 2026-06-09/10; amendments tracked in its Changelog.
- [[2026-06-10-research-workflow-spec-review]] — critical review of that spec
  after Phases 0.5/1a/1b shipped: divergences from shipped reality,
  paper-line alignment gaps (source credibility = Paper 2 → #217,
  evidence-role benchmark binding, Workbench pin-log as the future
  relevance-judgment dataset → #218), data-line gaps (evidence-window
  contract), and the amendment plan (applied in place).
- [[2026-06-12-atlas-markets-layer-l4]] — Atlas L4 markets layer (Pedro's
  personal trading-research app, future private repo): literature judgment
  (LLM trading agents, GDELT→markets evidence, leakage red flags), phased
  evidence-gated plan (M0 event study #226 → backtest harness → LLM analyst
  ensemble → paper trading → only then real capital), standing guardrails
  (no employer IP, Measurement Provenance, off-hours compute).
- [[2026-06-10-funnel-maturity-and-positioning]] — measured 24h funnel
  (194,674 raw → 442 served cluster members), serving-maturity tiers instead
  of a blanket T-1h delay (#221), funnel observability ledger (#220),
  stratified snapshot sampling (#222), Pipeline Funnel Principle ("gates
  decide what Atlas volunteers, not what it can find when asked"),
  Measurement Provenance Principle (paper numbers are method-dependent
  estimates), and the "Why Atlas vs Google" positioning answer.
- [[2026-06-04-mvp-thread-volume-and-issue-sprint-design]] — MVP sprint design:
  use GDELT themes as weak, bias-measured support signals to recover Narrative
  Thread volume, then re-triage and close stale GitHub issues.
- [[2026-06-04-thread-intelligence-packet-design]] — unify ThreadFocusPanel with
  ThemeDetail's rich data (country edges, source lanes, timeline, graph,
  attention) via one server-side packet built from the thread's signal set.
- [[2026-06-04-signal-snippet-enrichment-design]] — persist discarded source
  body text into `signals_v2.snippet`, expose it as evidence data, and render it
  in the clicked single-signal detail panel. Foundation for Atlas as a reading
  experience.
- [[2026-06-04-narrative-note-synthesis-design]] — first read-only,
  deterministic narrative note for opened threads, using thread metrics plus
  evidence headlines/snippets before any LLM generation.
- [[2026-06-03-workbench-waitlist-gate-design]] — interactive early-access
  waitlist gate for the public MVP Workbench launch (`/api/v2/waitlist`,
  real-data counter, Supabase-backed).
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — teacher-student
  evidence-role layer for classifying signals inside narrative clusters.
- [[2026-06-01-narrative-cluster-evidence-roles]] — implementation plan for
  the evidence-role pilot, teacher packet, consensus labels, student report,
  and Obsidian documentation path.
- [[2026-06-02-emergent-topic-identity-resolver-design]] — Phase 6 identity
  resolver and `dynamic_topics` lifecycle design.
- [[2026-05-29-emergent-topic-discovery-design]] — emergent layer
  (HDBSCAN + ≥90%-precision gate + DeepSeek labels), per-cluster
  precision filter, translation layer, self-curating
  `dynamic_topics` lifecycle.
- [[2026-05-25-atlas-narrative-intelligence-framework]] — Atlas as
  model + visualizer: signals → evidence → parent/child/entity
  Narrative Threads.
- [[2026-05-24-living-narrative-threads]] — living thread contract
  consumed by `/api/v2/threads` and `NarrativeThreads.tsx`.

## Research

- [[2026-06-03-research-model-product-roadmap]] — current route connecting
  Paper 1, model correction, dynamic-topic verification, and Atlas's
  information-disorder purpose.
- [[2026-06-03-paper-1-result-skeleton]] — draft-ready Paper 1 result skeleton
  with RQ1 numbers, improvement levers, limitations, and figure checklist.
- [[2026-05-27-atlas-papers-master-plan]] — 8-paper series outline.
- [[2026-05-27-methodology-paper-outline]] — Paper 1 outline.
- [[2026-05-28-precision-to-90-roadmap]] — roadmap to push Atlas
  classification precision from ~51% → 90%.
- [[2026-06-02-dynamic-topics-shadow-result]] — Phase 6 shadow lifecycle,
  student noise-rate gate, incremental cron, and guarded merge/dedup result.
- [[2026-06-03-dynamic-topics-product-smoke]] — deployed backend + browser
  smoke for `/brief`, Watchlist, Narrative Threads, and ThreadFocusPanel.
- [[2026-06-03-frontend-surface-data-map]] — route/panel/data-contract map for
  visible, hidden, partial, and dynamic-topic-fed frontend surfaces.
- [[2026-06-02-local-ollama-deprecation]] — negative local Ollama validation
  result; do not use M1-local Ollama as Atlas judge, teacher, or gold source.

## Roadmaps

- [[2026-05-25-production-cycle-and-backlog]]
- [[2026-05-21-data-operating-roadmap]]
- [[2026-05-24-open-issues-thread-triage]]

## Archive

- [[CLAUDE-history-2026-05]] — chronological session blocks
  2026-05-21 → 2026-05-29, preserved verbatim from CLAUDE.md.
- [[ARCHITECTURE-v1-2025]] — previous v1-era data-flow doc.

## How this vault works

- Wikilinks (`[[name]]`) resolve via fuzzy match across the whole
  vault. Folder layout does not matter.
- The folder is also a git-tracked markdown tree; everything lives in
  the same Observatory Global repository. The Obsidian `.obsidian/`
  config directory is gitignored.
- Re-run `python3 scripts/project_inventory.py` whenever the code
  changes meaningfully; the rest of the vault is human-curated.
