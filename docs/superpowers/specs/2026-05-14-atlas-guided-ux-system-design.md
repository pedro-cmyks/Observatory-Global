# Atlas Guided UX System Design

Date: 2026-05-14  
Branch: `v3-intel-layer`  
Status: Draft for user review  

## Summary

Atlas should present itself as a **public narrative intelligence** product with an editorial voice. The product should not be framed as a GDELT wrapper. It should explain what Atlas is, what it does, and how it works within the first few seconds, then guide users into the right level of depth.

The preferred journey is:

`Landing -> Brief -> Atlas Console -> Workspace`

The console remains directly accessible for power users, but the Brief is the recommended first door for people who need a readable orientation before entering the denser analyst interface.

## Issues In Scope

Directly in scope:
- `#108` — Landing `/app` link + brief loading coherence.
- `#121` — Coverage bias correction and explanation.
- `#123` — Workspace discoverability.
- `#80` — Session graph / investigation trail from navigation.
- `#128` — Workspace bounds and distinct Trail/Pinned graph modes.

Partially in scope:
- `#111` — Signal Stream as global panel motor. This spec defines the interaction direction but does not require the full global sync engine in the first implementation.
- `#79` — AEIL-style panel consistency. This spec defines the shared panel grammar but does not migrate every panel in one pass.
- `#112` — Related topic clarity. This spec informs the help/docs language, but detailed related-topic behavior can remain a follow-up.
- `#107` — Slow-loading panels. Loading and empty-state guidance is included; SWR/cache implementation is a separate performance pass.

Out of scope for this spec:
- `#82` Temporal narrative graph expansion.
- `#124` Saved searches and persistent alerts.
- `#106` Mascot/loading identity.
- New backend endpoints, native apps, or strict statistical redesign of the normalization model.

## Product Framing

Atlas is a public narrative intelligence console with an editorial entry layer. It helps users see how topics move through open media, public attention, geography, source provenance, and investigation paths.

The brand promise:
- Atlas shows what narratives are moving.
- Atlas shows where and through whom those narratives move.
- Atlas separates raw volume from importance.
- Atlas lets a user move from a readable brief into an investigation trail.

The landing page should communicate:
- What Atlas is: public narrative intelligence.
- What Atlas does: tracks global narratives across open signals, public attention, countries, sources, and time.
- How it works: starts with a readable Brief, then opens a live console where users can inspect evidence and build a Workspace trail.

## Surface Model

### Landing

The landing page has two primary paths with clear hierarchy:

1. **Read Today's Brief** — recommended for first-time or general users.
2. **Open Atlas Console** — direct access for users who already know they want the full analyst interface.

Docs should remain visible from the landing page. It should not be hidden behind the console because the docs become part of user education.

The landing should be concise and product-forward. It should not over-explain all panels. Its job is to orient and route.

### Brief

The Brief is the easy, editorial layer.

It should support:
- Global front page by selected time range.
- Country filter/search.
- Country-specific brief when a country is selected.
- Theme/narrative cards showing the most active narratives for the selected global/country context.
- Direct navigation back to Landing.
- Direct navigation into the Atlas Console.

Theme cards should be large click targets. The primary click behavior is:

`Brief theme -> /app?theme=<theme>&country=<country-if-present>`

If the user selected a theme from a global brief, the console opens that global narrative. If the user selected a theme from a country brief, the console opens that country-scoped narrative.

### Atlas Console

The console is the analyst layer.

Default behavior:
- If the user enters `/app` directly without theme/country/query context, the center panel defaults to **Signal Stream**.
- If the user enters from Brief with theme/country context, the console preserves that context.
- If the user is first-time, the general walkthrough appears first, then the chosen narrative/country opens.
- If the user has already completed or skipped the walkthrough, no interruption occurs.

The command bar should keep direct access to:
- Landing/home.
- Brief.
- Workspace.
- General Tour.
- Settings.

### Workspace

Workspace is the memory and evidence surface.

It should include:
- **Trail**: chronological route of the user's investigation.
- **Pinned**: deliberate evidence saved by the user.
- **Notes**: analyst notes attached to the investigation.
- **Export**: shareable/portable investigation summary.
- **Canvas/graph**: relationship view for pinned evidence and later richer graph modes.

Trail and Pinned are related but not identical:
- Trail answers: "How did I get here?"
- Pinned answers: "What evidence am I keeping?"

The Workspace shell must remain inside browser bounds on laptop-sized viewports. Close and action controls must always remain reachable.

## Onboarding And Help System

Atlas needs layered help, not only tooltips.

### Level 1: Tooltips

Tooltips remain short and local. They answer a single phrase-level question, such as "What does this number mean?"

Tooltips should not carry full teaching responsibility.

### Level 2: General Tour

The existing guided tour remains the primary first-run onboarding.

Behavior:
- Stored in local cache/localStorage.
- Appears automatically only when the user has not seen or skipped it.
- Can always be reopened manually from the `TOUR` button.
- Includes the major console areas: Search, Globe, Signal Stream, Narrative Threads, Anomaly/Public Attention, Workspace, and Brief.
- If the user arrives from Brief for the first time, show the general tour first, then land them on the selected narrative/country context.
- The user can skip the tour, and the chosen Brief destination must still be respected.

### Level 3: Panel Help Drawer

Each major panel should expose a short help drawer/modal from its `?` affordance or a similar action.

This is not another coachmark sequence. It should be compact and readable.

Each panel help drawer should explain:
- What this panel is.
- What data it shows.
- What the user can do here.
- How it connects to the rest of Atlas.
- Link to deeper docs.

Panels needing help:
- Signal Stream.
- Narrative Threads.
- Theme Detail / Narrative Thread detail.
- Country Intelligence.
- Public Attention.
- Anomaly Alert.
- Source Integrity.
- Workspace.
- Brief.

### Level 4: Docs

Docs become the deep manual for Atlas.

Docs should include:
- Product overview.
- Brief guide.
- Console panel guide.
- Workspace guide.
- Coverage bias and normalization.
- Sentiment/NLP explanation.
- Public Attention: Google Trends and Wikipedia.
- Source provenance and source integrity.
- Data limitations and confidence language.

The panel help drawer should link into the relevant docs section.

## Coverage Bias And Volume Language

Atlas must distinguish volume from importance.

Raw signal volume means there is more evidence to analyze, not that a country or topic is inherently more important. Countries with larger media ecosystems will naturally produce more signals. Atlas should use that volume to improve confidence/refinement, while visual importance should be based on baseline-relative movement and context.

Product language:
- Raw volume = evidence density.
- Baseline deviation = unusual attention.
- Larger sample = better confidence, not greater real-world importance.
- Small sample = thin or limited confidence.

Implementation can keep a short disclaimer in the UI, but deeper explanation belongs in docs and panel help.

This spec does not require a full statistical redesign. It requires that the UX consistently explain the distinction and avoid copy or visuals that imply raw volume equals importance.

## Panel Consistency Principle

Every investigable panel should follow a recognizable Atlas Entity Intelligence Layout grammar:

1. Identity: what entity/topic/country/source/person is being inspected.
2. Metrics: signal count, countries, sources, sentiment, attention, or confidence.
3. Explanation: short natural-language summary.
4. Connections: related themes, countries, people, sources, public attention.
5. Evidence: recent signals, articles, sources, or attention items.
6. Actions: pin, export, open in Workspace, compare, or continue investigation.
7. Help: short panel drawer + full docs link.

Panels can differ because they answer different questions, but they should not feel like unrelated products.

## Navigation Rules

Landing:
- Can open Brief.
- Can open App.
- Can open Docs.

Brief:
- Can return directly to Landing.
- Can open App globally.
- Can open App with theme/country context.

App:
- Can return to Landing.
- Can open Brief.
- Can open/restart Tour.
- Can open panel help.
- Can open Workspace.

Workspace:
- Can switch between Trail and Pinned.
- Can promote Trail items into Pinned evidence.
- Can reopen the relevant panel/entity from Trail or Pinned items.

## Acceptance Criteria

The spec is successful when the implemented product supports:

- A first-time visitor can understand the product promise from Landing.
- A non-expert user can choose Brief as the easiest entry path.
- A power user can still open the console directly.
- Brief theme clicks preserve context into the console.
- The general tour does not interrupt returning users.
- First-time Brief-to-App users see the general tour before the selected narrative opens.
- Every major panel has access to a compact help drawer.
- Help drawers link to deeper docs.
- Docs explain panels and methodology beyond tooltip length.
- Workspace clearly distinguishes Trail from Pinned.
- Workspace remains inside viewport bounds.
- Coverage and volume language consistently avoids equating raw volume with importance.

## First Implementation Plan Boundary

The first technical plan should focus on:

1. Landing navigation/copy refinements.
2. Brief navigation back to Landing and context-preserving App links.
3. Tour gating and Brief-to-App deferred destination behavior.
4. Panel help drawer framework and content for the first set of panels.
5. Docs information architecture and initial panel/methodology pages.
6. Workspace bounds fix and Trail/Pinned visual distinction.

The first technical plan should not include:
- Full Signal Stream global motor implementation.
- Full temporal narrative graph.
- Saved searches/alerts.
- New backend normalization model.
- New data sources.

## Self-Review

Placeholder scan: no TBD/TODO placeholders remain.

Internal consistency: the journey, navigation, help layers, and Workspace model all use the same Landing -> Brief -> App -> Workspace structure.

Scope check: this is a UX/product/design spec. It intentionally defers technical file-by-file implementation to a separate plan.

Ambiguity check: the largest ambiguity is the exact implementation of panel help. This spec resolves that by choosing a short help drawer/modal rather than per-panel coachmark sequences.
