# Atlas Productization Design — Manual, Dossier, Reading Mode

## Decision

Do not rename Brief to Atlas Daily yet.

Use this separation:

- **Brief**: the live interactive orientation page. It answers "What is happening now and where should I look?"
- **Atlas Daily**: a future generated/shareable publication output. It can be created from Brief snapshots, saved watches, or curated investigations.
- **Workspace Dossier**: the evidence layer inside App/Workspace. It answers "What did I collect and what supports this finding?"
- **Reading Mode / Investigation Newspaper**: a polished narrative view generated from a Workspace Dossier. It answers "How do I read and share this investigation?"

This keeps the current product understandable: Brief remains an entry point; Reading Mode becomes an output of investigation, not a competing destination.

## Option A — Workspace Dossier

Entry point:

- Primary: inside Workspace, after the user has pinned nodes or built an investigation trail.
- Secondary later: from App context bar when an active investigation has enough evidence.

Behavior:

- Collect raw signals, sources, themes, countries, people, temporal snapshots, Public Attention items, and user notes linked to pinned nodes.
- Show source evidence first, then graph structure.
- Export as Markdown/HTML/PDF later, but first build an in-product preview.

Why it matters:

- Journalists and analysts need the underlying articles/evidence, not only the graph.
- This directly extends #133 and becomes the data foundation for #141.

## Option B — Atlas Daily

Relationship with Brief:

- Brief is live and interactive.
- Atlas Daily is generated, archived, and readable.

Possible first version:

- "Generate Daily Edition" from the current Brief filter.
- Sections: global lead, country watchlist, top narrative shifts, public attention, source integrity note, evidence links.
- This should wait until Brief speed and methodology are reliable (#136/#137).

Why not rename Brief now:

- The user already understands Brief as a live product screen.
- Renaming before fixing loading, analysis gaps, and context persistence would hide the real problem.

## Option C — Visual Manual With Live Cases

Format:

- Use real product screenshots or controlled simulated product states.
- Annotate screenshots with persona-specific visual language:
  - Journalist: source/evidence highlights, quote brackets, dossier pins.
  - Investor/risk analyst: trend lines, risk circles, country comparisons.
  - Editor/product user: route arrows, decision checkpoints, reading order.
  - Intelligence analyst: relationship lines, confidence markers, temporal sequence.

Core flows:

1. Landing -> Use Case -> Brief -> App.
2. Brief country filter -> theme -> country-scoped ThemeDetail.
3. Search in Spanish -> concept/theme/country routing.
4. Public Attention -> scoped investigation pivot.
5. Pin evidence -> Workspace Dossier -> Reading Mode.
6. Saved Watch -> repeated monitoring -> Atlas Daily edition.

Implementation note:

- The manual should be product content, not a static README only. Landing cards should link into it (#135), and App/Brief should have contextual docs affordances.

## First build order

1. Fix trust blockers: loading, unavailable analysis, context loss, Trends/Public Attention.
2. Build visual manual using the current best flows, with screenshots captured after trust blockers are fixed.
3. Build Workspace Dossier export/preview.
4. Build Reading Mode as the first "newspaper" output.
5. Add Atlas Daily once Brief can reliably generate a credible edition.
