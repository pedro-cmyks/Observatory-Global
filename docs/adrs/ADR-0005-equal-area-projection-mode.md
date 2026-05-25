# ADR-0005: Equal-Area Projection Mode For Atlas

## Status

**Proposed**

## Date

2026-05-25

## Context

Atlas uses the world map as an analytical surface, not as decoration. Projection
choice therefore changes the product's epistemic framing: what appears central,
large, peripheral, or small affects how users interpret global movement.

Pedro flagged the Equal Earth projection as a product-relevant direction because
it preserves relative land-area proportions better than Mercator. The linked
Equal Earth project describes it as an equal-area pseudocylindrical projection
for world maps, created as a visually readable alternative to Gall-Peters while
preserving correct area relationships between tropical/developing regions and
the northern/developed regions. Its wall-map data sources are public-domain
or public references, including Natural Earth vector data, Natural Earth shaded
relief, CIA/GEOnet place-name references, and Wikipedia for mountain elevations.

Sources:

- https://equal-earth.com/equal-earth-projection.html
- https://equal-earth.com/data-sources.html

## Relationship To ADR-0004

ADR-0004 accepted Mercator for production because the prior globe/deck.gl
integration caused layer drift and floating artifacts. That decision was
technical, not philosophical: the priority was keeping heat, flow, marker, and
hit-test layers correctly aligned.

This ADR does not reverse ADR-0004 immediately. It records a future product
direction: Atlas should evaluate an equal-area projection mode once the map
stack can preserve layer alignment and interaction quality.

## Decision

Treat Equal Earth / equal-area projection support as a dedicated product
architecture issue, not as ad hoc visual polish.

Tracking issue: https://github.com/pedro-cmyks/Observatory-Global/issues/212

## Product Principle

Atlas should make geographic framing honest. If the product defaults to a
projection that distorts area, that is a product decision and should be explicit.
An equal-area mode is aligned with Atlas's goal of showing global narrative
movement without silently amplifying Europe/northern-latitude scale.

## Non-Goals For The Current Data Phase

- Do not interrupt Path C taxonomy work.
- Do not replace the production map until all analytical layers are verified.
- Do not ship a projection toggle that breaks country focus, flows, heat, or
  hit-testing.

## Future Acceptance Criteria

1. Prototype Equal Earth or another equal-area projection in the current
   MapLibre/deck.gl stack, or document why the current stack cannot support it.
2. Verify country fill/heat, flow arcs, markers, selection, hover, zoom/pan, and
   responsive layout.
3. Compare the analytical readability of Mercator, globe, and equal-area modes.
4. Ship only if layer alignment is demonstrably correct.

## Consequences

Positive:

- Makes Atlas's worldview more explicit and less Mercator-biased.
- Gives the product a stronger identity around proportional global attention.
- Creates a clean place to evaluate projection work without derailing data
  quality backlog.

Negative:

- Equal-area projection may not be supported directly by the current interactive
  map stack.
- Flow and heat layers may need custom projection handling.
- Adds another visual verification burden before release.
