# Phase 5 Comparative Engine Architecture Review

Date: 2026-05-05  
Issue: #61  
Status: reviewed, not implemented in the Workspace MVP

## Current State

Atlas already has three comparison primitives:

- `CompareBar.tsx` calls `/api/v2/compare` for period-over-period deltas.
- `ThemeCompare.tsx` renders two `ThemeDetail` panes side by side.
- `PersonCompare.tsx` renders two `EntityPanel` panes side by side.

These are useful interim overlays, but they are not yet the dense 50/50 Comparative Intelligence Engine from the Stitch mockup. They reuse full-size detail panels, so they carry extra controls and spacing that do not fit a true split-screen analysis surface.

## Target Shape

The future implementation should introduce `CompareDashboard.tsx` as a dedicated overlay shell with:

- Two symmetrical comparison panes.
- Shared top controls for entity type, time window, and baseline.
- Pane-level sections for Narrative Drift, Top Sources, Active Themes, and country/person/source context.
- A narrow reusable pane API so theme, country, person, and temporal comparisons use the same layout contract.

The existing `ThemeCompare` and `PersonCompare` components can stay as compatibility wrappers until the new dashboard covers their entry points.

## Data Plan

Use existing endpoints first:

- `/api/v2/compare` for signal and sentiment deltas.
- `/api/v2/theme/{theme}` for theme pane content.
- `/api/v2/country/{code}` for country pane content.
- `/api/v2/focus` for person pane content.
- `/api/v2/source/{domain}/profile` for source pane content.

No backend endpoint is required for the initial Comparative Engine UI. If repeated frontend joins become slow or inconsistent, add a later `/api/v2/compare/entities` endpoint that returns both panes in one response.

## Implementation Boundary

Do not implement this in the Workspace MVP PR. The first Phase 5 code path should remain focused on Issue #58: interactive workspace graph, filters, notes, export, and source pinning.
