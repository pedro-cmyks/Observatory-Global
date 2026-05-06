# Phase 5 Workspace Board Manual QA

Date: 2026-05-05  
Scope: Issue #58 interactive workspace board

## What Changed

- Workspace opens as an interactive relationship board instead of a static drawer.
- Pinned items render as graph nodes.
- Existing endpoints enrich pinned themes, countries, people, and sources into relationship links.
- The right notes panel preserves the previous notes and markdown export workflow.
- Source profiles now expose a pin action so sources can enter the workspace.

## Manual QA Checklist

- Pin a country from `CountryBrief`; confirm a country node appears in the board.
- Pin a theme from `ThemeDetail`; confirm related countries, sources, persons, and themes connect to it.
- Pin a source from `SourceProfile`; confirm source-related theme and country nodes appear.
- Type into the graph filter; confirm visible nodes and links update together.
- Toggle node type filters and relationship filters; confirm the graph narrows without losing pinned notes.
- Edit notes in the pinned list; reload `/app`; confirm notes persist from `atlas-workspace`.
- Export workspace; confirm markdown still includes every pinned item and note.

## Known Validation Constraint

This note documents the manual QA path. A visual screenshot should be captured from a running browser once the local API is available with live data.
