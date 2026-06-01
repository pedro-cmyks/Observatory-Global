# Observatorio Global — Docs Index

Opens this folder as an [Obsidian](https://obsidian.md/) vault. Use the
graph view (cmd-G) for the relationship map across all docs. Wikilinks
below resolve via Obsidian's fuzzy search regardless of folder.

## Start here

- [[ARCHITECTURE]] — data-flow diagram + API surfaces + cron table.
- [[PROJECT_INVENTORY]] — machine-verified endpoints / frontend ↔ API /
  DB tables / cron / recent commits. Regen via
  `python scripts/project_inventory.py`.
- [[STATUS]] — long-running operational status doc.

## Latest handoffs

- [[2026-05-30-phase-2-emergent-wiring-handoff]] — Phase 2/3 emergent
  layer shipped; correction about wrong surface; next-session top
  priority.
- [[2026-05-30-context-gap-inventory-proposal]] — diagnosis of the
  context-fragmentation problem that motivated this index + the
  inventory tool.

## Active design specs

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

- [[2026-05-27-atlas-papers-master-plan]] — 8-paper series outline.
- [[2026-05-27-methodology-paper-outline]] — Paper 1 outline.
- [[2026-05-28-precision-to-90-roadmap]] — roadmap to push Atlas
  classification precision from ~51% → 90%.

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
- Re-run `python scripts/project_inventory.py` whenever the code
  changes meaningfully; the rest of the vault is human-curated.
