# Spec — Time axis: the universal activity timeline & versioned relationships

**Date:** 2026-07-21 · **Status:** DRAFT (design-converged; DEFERRED — build after
chains v1). **Dependency UPDATE (2026-07-21 validation):** the §2 compound-focus
prerequisite (thread-open composes instead of clearing) is **already MET** — shipped by
the flywheel track on `v3-intel-layer` (`focusReducer` + composing `onThreadSelect`). The
genuinely-new build is the edge-snapshot store + versioned edges + the diff/replay chart;
compound focus can be assumed. · **Wedge:** narrative analyst · **Discipline:** math-first,
LLM only on sanctioned surfaces, vanilla-CSS dashboard.

**Siblings:** `2026-07-21-multi-hop-transitive-chains.md` (the walked constellation —
needs the versioned-relationship substrate designed here; this doc was extracted from
its §2.8) · `docs/state/2026-07-21-analyst-journey-map.md` (§2 compound focus + the
"truncated connection" finding).

---

## 0. Intent

Time is a **first-class axis** in Atlas, alongside country / entity — not a filter, not
a markets feature (markets *uses* time; it does not own it). Pedro's framing, verbatim:

- *"Yesterday this story said X, today it says Y, over these months it has been telling
  it this way."* — a thread's **content/framing evolves**.
- *"What we record today about the relationships between things must also be saved
  toward tomorrow, and a year out."* — the **relationships themselves are temporal** and
  must be **versioned forward**.
- *"Everything talks with everything"* — the connection that is currently **truncated**
  in the app (focus doesn't propagate; most focus types have no timeline). This axis is
  the fix.

The one-line thesis: **give every focus a time-section, version the relationships behind
it, and separate real narrative change from substrate churn — honestly.**

---

## 1. The universal render — an activity timeline on EVERY focus

Time is not a separate view; it is a **section every focus panel has**: thread, country,
person, theme, anomaly, subject. Today only some carry a timeline (a country / person
does not). Giving **all** of them one is how *"everything relates to everything over
time"* becomes concrete, and it closes the journey-map "truncated connection."

- **Thread** → its volume + related subjects over time (today's activity timeline, extended).
- **Country** → threads forming in it + its story volume over time.
- **Person (e.g. Trump)** → Trump's volume + stories mentioning Trump + his co-subjects
  over time.
- **Theme / anomaly / subject** → same shape.

The existing `key_subjects` section is the seed: the related subjects, rendered as their
**evolution over time**, ARE the timeline's trend lines (§3).

---

## 2. Two contexts, ONE time-state

There is a single global time-state; it is reached from two places and they stay synced.

- **Ambient (nothing selected) → REPLAY.** The scrubber moves the whole field back —
  globe, universe, all surfaces — the field *as it was*. Light honesty burden: it only
  *shows* past state. Extends the existing `map/replay` (node/heat scrub) to **edges**.
- **Focused / Workbench → DIFF, living IN the activity timeline.** No new chrome: the
  timeline *is* the focus-scoped handle on the global time-state. Scrub it and
  **everything else moves to that date** while the focus stays **anchored** (this is
  compound-focus + time — the §2 journey-map fix: hold one axis while another moves).
- **The scrubber re-labels itself** at the transition: ambient `"replay · 10 jun"` →
  focused `"changes since 10 jun"`. Without the relabel the analyst thinks they are still
  replaying when they are reading a diff.

---

## 3. The combined chart (the diff render)

One x-axis (time), one scrubber, channels as **toggles**.

- **Diverging volume bars = anchor volume + sentiment by POSITION, not color.**
  Positive-tone volume up, negative-tone down; total extent = volume, the up/down balance
  = sentiment. **Replaces** the existing red/green sentiment bars — because we now overlay
  **colored** entity lines and color-on-color clashes; encoding sentiment by position
  **frees color for the lines**. Not merely simpler — it removes a real conflict.
- **Key-subject trend lines (color per entity) = who relates, over time.** Each related
  subject's **presence WITHIN this focus** over time — **rarity-normalized** (the SAME
  formula everywhere: thread / country / person / theme → comparable, honest). A globally
  famous actor barely in *this* story = a low line; **Trump never pins every line high.**
  Top-k curated. Rising line = relationship forming; falling = fading; **line that ends =
  connection died.**
- **Voice-mix band = who COVERS it over time** (press / public, countries / languages).
  **Equal weight to key-subjects** — *"who says what, over time"* is literally the wedge on
  the time axis (when the Chinese press picked it up, when a voice went quiet).
- **Movement / surge (#219) = secondary toggle.**
- **NO discrete marker layer** (too much information). Transitions are read from the **line
  shape**; the **churn-vs-narrative label lives in the hover of a line's endpoint**, on
  demand, not as persistent chrome.
- **Default channels = diverging volume bars + key-subject lines.** The analyst adds
  voice-mix / sentiment / movement. All channels at once = noise.
- **Dataviz honesty:** bars (absolute volume) and lines (relationship strength) are
  different scales — do not fake a shared axis; normalize both to "share of attention" or
  use a clearly-labeled secondary axis.

---

## 4. The anchor — two layers, which separate real change from churn

The load-bearing honesty problem: when a relationship **disappears** between snapshots,
is it **narrative change** (the story moved on) or **substrate churn** (the topic
re-founded / merged / retired — `dt-<id>` are ephemeral)? Presenting churn as narrative
change is a coverage≠corroboration-class lie. Version relationships against **both**
anchors:

- **`identity_key` (fine, thread-level, medium-term).** Survives re-founding (a retired
  topic resurrects on centroid match with the same key), so a vanished edge is
  disambiguated: both keys alive + no edge = **narrative change**; a key retired / merged
  = **substrate event** (labeled, not narrative).
- **Entities (coarse, long-arc backbone).** Actors / places outlast threads — the
  months-long spine. **Rarity-gated over the temporal window** (else Trump-<anything>
  glues the whole backbone across all of time — #234, again).
- **Divergence between layers = signal, not bug.** Backbone alive but no current
  thread-edge = a **latent / dormant relationship** — the actors still co-appear but no
  story binds them right now; a bridge that was and may return. Name it; don't hide it.

---

## 5. The three facets (mapping)

- **(a) Relationship history — versioned edges (load-bearing).** The walk graph / kinship
  edges persisted with a timestamp each pass; the constellation gains a HISTORY (hermano →
  primo → gone; new edges form). Rendered as §3's trend lines + replay.
- **(b) Thread content evolution.** A story's framing drift ("yesterday X, today Y"). Ties
  to existing surfaces (`NarrativeBiography` lineage, `deep-history`, "active since").
- **(c) Precedence / surprise.** Kalman lead/lag, surprise (#219). **One facet, honesty-
  gated: NEVER a causal arrow** — coverage precedence ≠ event precedence; it feeds honest
  labels/ordering, not a direction glyph.

---

## 6. Substrate — reuse vs new

| Piece | Status |
|---|---|
| Per-snapshot centroids | `emergent_clusters` already stores them (universe-trajectory work) → past-date edges recomputable |
| Node/heat replay | `map/replay` exists → extend to edges |
| Content evolution | `NarrativeBiography`, `deep-history`, "active since" exist |
| Movement | Kalman feed #219 exists |
| Related subjects | `key_subjects` exists (the seed for trend lines) |
| Voice mix | voice-mix audit / `/voice-mix` exists → needs a per-time-bucket variant |
| **Edge-snapshot store** | **NEW** — persist the *derived* edge set (identity_key pair + degree + weight + basis) + the entity backbone per pass, so replay/diff is cheap and churn-labelable. Small. |

---

## 7. Honesty model

- **Replay is "reconstructed from snapshots"** — edges un-reconstructable for a past date
  are **absent**, never faked.
- **Churn vs narrative** is the core: never present a re-founded/merged topic as a
  narrative change; the two-layer anchor (§4) is how.
- **Rarity everywhere** (§2.4 of the chains spec, `0.30 + 0.68·norm_rarity`): the trend-line
  strength AND the entity backbone are rarity-gated so a ubiquitous actor is thin, not
  dominant.
- **Co-occurrence ≠ relationship** — the entity backbone is *"these actors kept appearing
  together,"* never *"these actors are related."* The backbone is MORE prone to the
  causal misread (an actor pair *feels* like a direct tie) → carry the same receipt
  discipline.
- **No causal arrow** anywhere; time gives sequence, not cause.

---

## 8. Open questions (for build)

1. **Diff anchor granularity** — the timeline itself is the anchor (scrub-anchored), with
  a possible "you were here last visit" default marker. Confirm at build.
2. **Voice-mix per-time-bucket** cost — the current audit is windowed; a per-bucket series
  needs measuring for cost.
3. **Edge-snapshot store cadence** — every walk? nightly? and retention (a year out ≠
  every 30-min snapshot; likely daily-rolled).
4. **Backbone sparsity bound** — entity-pair × time is large; rarity-gate + top-k keeps it
  sparse, but needs a measured cap.
5. **Line meaning consistency** — the trend line must measure the identical thing across
  every focus type (§3); write it as one shared function.

---

## 9. Relationship to the chains spec

This is the **versioned-relationship substrate** the walked constellation
(`2026-07-21-multi-hop-transitive-chains.md`) needs to become time-aware, and it is
**DEFERRED from the chains v1 build**. The chains ship undirected + present-tense first;
this axis makes them scrubbable/diffable afterward. Shared machinery: the rarity formula
(§2.4 of chains), the whitened edge substrate, `useFocusRelation` (#234), the Universe
field, and #219 Kalman.
