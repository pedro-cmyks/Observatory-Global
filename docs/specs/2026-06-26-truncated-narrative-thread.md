# Spec — Truncated Narrative Threads (entering from a specific item)

Date: 2026-06-26 · Branch: `v3-intel-layer` · Status: DRAFT **rev2** (incorporates
Pedro's 2026-06-26 review — P-ADD/P-FOCUS/P-STREAM + the GDELT-deprecation
correction). Do NOT implement until approved. Author: Claude (Opus 4.8).

> Companion to `docs/specs/2026-06-26-l2-deep-review.md`. This spec turns a
> design direction Pedro stated into a buildable, tiered plan with a product
> judgment. It is deliberately written "analyze before attacking."

---

## 0. The idea in one sentence

When you enter Atlas **from a specific item** — a forum post, a person, an
event, a single signal, a topic chip — Atlas should build a **truncated
narrative thread**: a small, honest, ad-hoc projection that answers *"this
specific thing — which living narrative threads does it connect to, and how?"* —
instead of either (a) doing nothing, (b) dumping you on an external link, or (c)
pretending the item is itself a full aggregated thread.

Pedro's framing (verbatim intent): *a narrative thread works by aggregating many
things; entering from a specific item should create a **truncated** thread that
shows this specific thing and which threads it connects to — because right now
those things aren't connected to each other.* And: *narrative threads should use
forums in the inference, obviously.*

The product value he named: it **differentiates "you are inside a thread
(aggregate)" from "you are on a specific item (not a thread)" and connects the
two** — a connection that does not exist today.

---

## 1. Why this matters (problem statement)

Atlas has two kinds of objects that never meet:

1. **Threads** — aggregates (dynamic clusters + atlas topics), the product's
   story model. Rich: evidence, movement, countries, key subjects.
2. **Items** — a forum post, a person, an event, one signal, a topic chip. Today
   clicking one either (a) re-scopes some panels (focus #234, partial), (b) runs
   a noisy text search, or (c) opens an external link. None of them say *"here
   is where this item lives in the narrative graph."*

Three concrete failures this causes (all observed this session):

- **Forums are dark — and the deeper cause is a deprecated mechanism.** Reddit is
  ingested (`source_family='social'`) but has **0 topic assignments** (verified:
  0/71 over 14d). The shallow reason: the classifier `classify_topics.py` assigns
  signals to Atlas topics through a **GDELT-theme bridge**
  (`atlas_topics.gdelt_theme_hints`, `JOIN ON s.themes && t.gdelt_theme_hints`),
  and forum posts carry no GDELT themes. But the REAL point (Pedro, correcting an
  earlier framing): **GDELT themes are already declared obsolete — they must not
  be the source of truth; Atlas topics are.** So the bridge itself is the wrong
  mechanism. The honest assignment is **semantic → Atlas topic** (embedding →
  topic centroid), which is *source-agnostic*: it includes forums, non-English,
  and anything without GDELT themes, in one move. ~28/71 forum posts already have
  embeddings; the path exists. (This is the same root as the L2 split-brain
  finding: the gate is English-lexical-on-GDELT; semantic is the cross-source,
  cross-language path.)
- **A specific signal's context is a leaf, not a hub.** `/api/v2/signal/{id}/context`
  already returns the threads a signal is in + its semantic neighbors, but it is
  only reachable inside the Signal Stream's detail panel — not from forums,
  people, events, or topic chips.
- **The analyst can't pivot from a particular to the general.** "I'm looking at
  *this* forum chatter / *this* person — what real narrative is this part of?"
  has no answer surface.

This is the same split-brain the L2 review named (alert layer ↔ evidence layer
never reconcile), one level up: **item layer ↔ thread layer never reconcile.**

---

## 2. What a "truncated narrative thread" IS (and is not)

A truncated thread is a **projection of the living thread set through one item**.
It is rendered as a thread-shaped card so it feels native, but it is explicitly
labeled as a *projection from <item>*, not a stored thread.

It contains, in priority order:
1. **The item itself** (headline / name / event, with provenance + lane label —
   e.g. `forum · discussion`).
2. **Connected threads** — the existing narrative threads this item belongs to or
   is nearest to, each with a **connection basis** badge and strength:
   - `member` (the item is an assigned member of the thread),
   - `semantic` (nearest by embedding; carries similarity),
   - `entity` (shares a distinctive entity — rarity-weighted, per #234),
   - `co-occurrence` (same primary geography / time window).
3. **Nearest evidence neighbors** — the closest real signals (news), each
   gate-status-tagged, so the user sees the *verified* material around a possibly
   *unverified* item.
4. **A connections honesty line** — e.g. "this forum post is discussion; its
   closest verified thread is X (sim 0.78)."

It is NOT:
- a new stored row in `dynamic_topics`/`atlas_topics` (it's ephemeral);
- counted in any gated/evidence total (a forum item never becomes evidence);
- a claim that the item *caused* or *belongs to* a thread beyond the labeled
  basis (semantic ≠ membership; we show the basis, never launder it).

Guardrail reconciliation: "forums = discussion, not evidence" **survives**. A
forum item can be a thread *member for discovery* (so threads use forums in the
inference, as Pedro wants) while never entering `gated_signal_count`. Discovery
membership and evidence are separate columns, exactly as the L2 B2 work made
`gated_signal_count` separate from `signal_count`.

### 2.1 Three principles from Pedro's review (these are binding)

**P-ADD — additive, never a replacement.** The truncated thread is a NEW section
*added* to the existing item panels, not a new screen that replaces them. When
Pedro clicks a person he *likes* what EntityPanel shows; the connections go where
"Related Topics" sits today → that slot becomes **"threads this connects to."**
Same for event, public attention, search, signal. The job is to connect the two
worlds, not to swap one for the other. Every existing item view keeps its current
content and *gains* a connections section.

**P-FOCUS — the item stays the subject; its country/context is secondary.**
Observed anti-pattern: clicking a *conflict event* in the UK flew the map to the
UK and then talked about **the UK**, swallowing the event. Correct behavior: the
**event** is the subject ("this conflict event"), the UK is context ("it lives in
this country; here's what's happening around it; here's how it relates"). The
truncated thread centers the item first, then situates it. This applies to every
entry: a public-attention item must show *what theme/thread it relates to*, not
just its Wikipedia blurb + "no recent media coverage" (today's dead end).

**P-STREAM — forums are a different stream, not noise.** Calling forum/social
"noisy" and down-ranking it at entry is pre-judging information before reading it
("clasificar sin haber visto"). Reframe: social is a **separate stream with
different properties** — you don't merge it with media (peras y manzanas), but
both are fruit. Concretely this unlocks a real analytic: **forum sentiment vs
media sentiment on the same topic** — does the public read it differently than
the press frames it? That divergence is *interesting precisely because* forums
aren't verified: it's a people-side-vs-press-side signal, surfaced side by side,
never blended into the gated total.

---

## 3. Architecture

Two layers, each shippable on its own.

### Layer A — Semantic Atlas-topic assignment (source-agnostic), incl. forums

Goal: stop assigning topics through the **deprecated GDELT-theme bridge** and
assign by **Atlas-topic semantics** (embedding → topic centroid). This is the
right mechanism for *everything* (it fixes the cross-language recall gap too); it
just happens to be the only way forums and non-English can enter at all.

- **Mechanism:** add a **semantic assignment pass** alongside the lexical one: for
  any signal with an embedding, assign to the Atlas topic whose centroid is
  nearest above a calibrated threshold. Write to `signal_topic_assignments` with
  `method='semantic'`. Provenance/role marks the lane: a forum/social assignment
  is `evidence_role='discussion'` and `gate_kept=false` (discussion is *never*
  gate-kept); a news assignment follows the existing gate. The GDELT-theme bridge
  stays only as a fallback/seed, never the source of truth (Atlas topics are).
- **Serving:** thread detail + `/threads` already separate `signal_count` from
  `gated_signal_count` (L2 B2). Discussion members add to a NEW **separate**
  `discussion_count` (people-side stream), never to `gated_signal_count`. Thread
  cards can show "N verified · M discussed" — two streams side by side, never
  merged (P-STREAM).
- **Forum-sentiment lens (P-STREAM payoff):** because discussion is a separate
  stream, compute its sentiment separately and serve `forum_sentiment` next to
  the thread's media sentiment, so a thread/topic can show *"press −0.6 ·
  public −0.1"* — the divergence is the signal. No new model: the NLP sentiment
  pass already runs on social rows; this is a serve-time split by `source_family`.
- **Where it runs:** the M1 cron pipeline (next to `classify_topics` /
  `embed_hot_corpus`); offline, no API hot-path cost. Threshold calibrated like
  #223 (semantic evidence) but looser for discovery; guarded by the #224
  anchor-centroid rule so discussion members never re-train / pollute identities.

### Layer B — The truncated-thread SECTION, added to existing item views (P-ADD)

Goal: every item view *gains* a "threads this connects to" section; nothing
existing is replaced. The section is one component, one contract, many hosts.

- **Signals/forums** (have an `id`): reuse `/api/v2/signal/{id}/context`
  (threads + semantic_neighbors). The forum item already carries its `id` from
  `/api/v2/public-attention`. No new backend needed for the forum MVP.
- **Typed items (person / event / topic / search)** (no single signal id): a new
  resolver `GET /api/v2/connections?kind=person|event|topic|query&value=...` that
  returns connected threads + distinctive shared entities + neighbor evidence,
  reusing rarity-weighted entity overlap (#234) and the thread spine.
- **Where the section is HOSTED (added, not replacing):**
  - **Person** → EntityPanel, in the slot where "Related Topics" sits today →
    becomes "Threads <person> participates in." (Pedro: keep what EntityPanel
    already shows; add this.)
  - **Event** (conflict marker, etc.) → a panel that *centers the event* (P-FOCUS:
    "this event, in <country>"), then lists the threads it relates to — instead of
    today's "fly to country and talk about the country."
  - **Public attention** (wiki/trend/forum) → the PublicAttentionPanel keeps its
    blurb but *gains* "relates to thread(s) X" so it's no longer a dead end with
    "no recent media coverage."
  - **Search** → search results stay; *add* a "truncated thread" block: "your
    query connects to these living threads." Search creates BOTH (results +
    connections).
  - **Signal** → SignalDetail already has this; unify the component.
- **Frontend:** one `ConnectionsSection` component takes `{kind, ref}` and renders
  the connected-threads + neighbor list from §2; each host mounts it in its own
  "related" slot. "One section, many hosts."

### Contract sketch (`connections-v0`)

```jsonc
{
  "contract": "connections-v0",
  "from": { "kind": "forum", "ref": 10092888, "label": "Fracking Sostenible?",
            "lane": "discussion", "verified": false },
  "connected_threads": [
    { "thread_id": "dynamic-topic-50", "label": "Water stress in Colombia",
      "basis": "semantic", "strength": 0.78, "gated_signal_count": 12 },
    { "thread_id": "energy-extractives--co", "label": "Energy & extractives",
      "basis": "entity", "strength": 0.41, "shared": ["ecopetrol"] }
  ],
  "neighbor_evidence": [
    { "id": 999, "headline": "...", "similarity": 0.81, "gate_status": "kept",
      "country": "CO", "source": "semana.com" }
  ],
  "notes": ["forum item is discussion; nearest verified thread sim 0.78"]
}
```

---

## 4. Product judgment (Pedro asked me to judge it as a product)

**Verdict: build it, in this order, and resist two temptations.** It is the
highest-leverage *connective* feature on the board because it makes every leaf in
the app lead somewhere true, and it is the natural completion of #234
(focus-propagation) and the L2 review (every path off the thread spine currently
lands on raw material presented as product).

**Why it's worth it**
- It converts dead-ends (forum link-out, noisy search) into navigation into the
  product's core object (threads). Retention/depth lever, not a vanity feature.
- It is *cheap for the MVP*: the forum case reuses `/signal/{id}/context` — a
  view, not new inference. We can ship value before paying for Layer A.
- It operationalizes a real research question (Paper 7 analyst-workflow + Paper 4
  thread model): *how should a specific entity be related to the living thread
  set, honestly?* The connection-basis labels are the method.

**Risks / what could go wrong (and the mitigation)**
1. **Semantic laundering.** Showing a `semantic` connection as if it were
   membership repeats the exact sin we keep fixing (volume≠importance,
   GDELT-overlap-relatedness). *Mitigation:* basis badge + visible strength on
   every connection; never merge baskets; a forum item is never evidence.
2. **Empty truncated threads.** Conversational forum posts ("Congelado! jajaja")
   have weak embeddings → no connection. *Mitigation:* honest empty state ("no
   strong narrative connection — this looks like local chatter") + keep the ↗
   source link. Do NOT fabricate a connection to fill the card. An honest empty
   is a feature, not a failure (it tells the analyst this chatter is noise).
3. **Layer A recall/precision drift.** Loosely assigning forums to topics could
   pollute thread identities (the #224 black-hole failure). *Mitigation:*
   discussion members live in a SEPARATE count, never re-train centroids, and are
   gated by the same anchor-centroid guard #224 added.
4. **Scope creep into "build the connections graph."** *Mitigation:* the
   truncated thread is a per-item projection, NOT a global graph build. Ship the
   projection; the graph is a later paper artifact.

**The two temptations to resist**
- Don't make the truncated thread a *stored* object yet (no new table). Ephemeral
  projection first; persistence only if pinning demands it (Workbench, later).
- Don't gate the MVP on Layer A. Tier 1 (the ConnectionsSection on forum/signal)
  ships standalone on the existing `/signal/{id}/context`.

**What I'd defer (not cut) from the first release:** person/event/search
connections (T3) and the semantic-assignment cron + forum-sentiment (T2). MVP =
**T1: the ConnectionsSection ADDED to forum + signal**, with the honest empty
state. Everything is additive (P-ADD), so each tier only *grows* existing views.

**Pedro's review made three things binding (see §2.1):** P-ADD (never replace,
always add to the existing item view), P-FOCUS (the item stays the subject; its
country is context), P-STREAM (forums are a separate stream, not "noise" — and
that unlocks the forum-vs-media sentiment lens). The earlier draft's "replace the
PublicAttentionPanel route" was wrong and is corrected to "add a section."

---

## 5. Tiered plan (ship + verify each, like the L2 review)

**Tier 1 — `ConnectionsSection`, ADDED to forum + signal (frontend, reuses
`/signal/{id}/context`).** P-ADD from day one.
- T1.1 Add `id` to the AnomalyPanel forum item type (carry from `/public-attention`).
- T1.2 `ConnectionsSection` component (contract = `/signal/{id}/context` adapted to
  §2): connected threads (from `semantic_neighbors[].has_topic` resolved to their
  thread label), neighbor evidence with gate badges, honest empty state. It is a
  SECTION, not a screen.
- T1.3 Mount it in the forum entry: forum click opens the item context with the
  ConnectionsSection added; PublicAttentionPanel KEEPS its blurb (P-ADD) and gains
  the section; ↗ Reddit stays secondary.
- T1.4 Mount the same section in Signal Detail (unify with the existing context UI).
- *Verify:* a forum post with embedding shows its nearest verified thread *added*
  to the existing panel; a conversational one shows the honest empty state; the
  existing panel content is untouched; ↗ still opens Reddit.

**Tier 2 — Semantic Atlas-topic assignment + forum-sentiment lens (Layer A, cron).**
- T2.1 Semantic assignment pass (embedding → Atlas-topic centroid) →
  `signal_topic_assignments(method='semantic')`; social rows get
  `evidence_role='discussion', gate_kept=false`. Threshold calibrated offline,
  #224 anchor-guard on.
- T2.2 Serve `discussion_count` separate from `gated_signal_count`; thread cards
  show "N verified · M discussed" (two streams, never merged — P-STREAM).
- T2.3 Serve `forum_sentiment` next to media sentiment (serve-time split by
  `source_family`); thread/topic shows "press X · public Y".
- T2.4 ConnectionsSection now includes real `member` connections for forums.
- *Verify:* r/colombia water post becomes a discussion member of the water thread;
  `gated_signal_count` unchanged; sentiment divergence visible; no centroid
  pollution (#224 holds).

**Tier 3 — Typed-item connections: person / event / search (P-FOCUS).**
- T3.1 `GET /api/v2/connections?kind=person|event|query&value=` resolver
  (rarity-weighted entity overlap + neighbor evidence + connected threads).
- T3.2 Person → EntityPanel "Related Topics" slot becomes "Threads <person>
  participates in" (ADDED, EntityPanel keeps the rest).
- T3.3 Event → an event-centered panel (P-FOCUS): "this conflict event, in
  <country>" first, threads it relates to second — fix the "fly to UK and talk
  about the UK" anti-pattern.
- T3.4 Search → results stay; ADD a "connects to these living threads" block.
- *Verify:* person shows connected threads with basis badges (distinctive-entity
  filter keeps "donald trump" from linking everything, #234 lesson); an event
  keeps the event as the subject; a search shows results + connections.

**Tier 4 — First-class + pinnable (later, gated on demand).**
- Persist a truncated thread into Workbench as an investigation node + per-pin
  note. Only if the Phase-3 dossier needs it.

Recommended order: **T1 → T2 → T3 → T4.** T1 delivers felt value with no inference
risk; T2 adds the semantic membership + the forum-sentiment lens; T3 generalizes
to person/event/search with the item-stays-focus rule; T4 is optional.

---

## 6. Paper alignment (the librarian agent is folding these in parallel)

- **Paper 4 (living narrative threads / thread model):** discussion-membership as
  a separate count from evidence (extends the #214 gated/raw result); the
  connection-basis taxonomy (member/semantic/entity/co-occurrence) as the
  thread-relation model.
- **Paper 7 (viz / analyst workflow):** the truncated thread is the method answer
  to "how should a specific entity relate to the living thread set, honestly?" —
  basis badges + visible strength + honest empty state are the contribution.
- **Paper 8 (open-set discovery):** forums entering the inference semantically
  (no GDELT-theme requirement) is an open-set recall result; measure recall/
  precision of discussion-membership vs the GDELT-theme gate.

---

## 7. Open questions for Pedro

Resolved by Pedro's 2026-06-26 review: additive not replacement (P-ADD);
item-stays-focus (P-FOCUS); forums are a separate stream + add the forum-vs-media
sentiment lens (P-STREAM); search creates results AND connections. Remaining:

1. **Naming on the card header** (user-facing). Candidates: "Where this fits",
   "Threads this connects to", "Connections". I lean "Where this fits" for items,
   and "Threads <person> participates in" for the person case specifically.
2. **Forum-sentiment lens timing** — ship it in T2 (with semantic assignment) as
   speced, or pull a thin version earlier (serve `forum_sentiment` from the
   already-NLP'd social rows even before semantic membership)? I lean T2 to keep
   tiers clean, but it's cheap enough to pull forward if you want it sooner.
3. **Empty connection state wording** — "no strong narrative connection — looks
   like local chatter" (honest, my lean) vs a softer "no match yet."
4. **T1 reach** — forum + signal first (my lean), with person/event/search in T3;
   or stretch person into T1 since EntityPanel is a clean host?

---

## 8. Self-review (spec checklist) — rev2 after Pedro's review

- *Correction logged:* the rev1 framing "the classifier matches GDELT themes" was
  treated as a mere mechanism detail; Pedro's point is that the GDELT-theme bridge
  is the *deprecated* mechanism — Atlas topics are truth. §1/§3 now make semantic
  Atlas-topic assignment the design, not a forum workaround.
- *Binding principles:* P-ADD (additive, never replace), P-FOCUS (item stays the
  subject), P-STREAM (forums = separate stream + sentiment lens) added to §2.1 and
  threaded through §3/§4/§5. The rev1 "replace the PublicAttentionPanel route"
  error is corrected.
- *Placeholder scan:* none — every tier names files/contracts and a verify step.
- *Internal consistency:* honesty model (basis + strength, discussion ≠ evidence)
  uniform in §2/§3/§4; counts stay separate (`gated_signal_count` vs
  `discussion_count`; media vs `forum_sentiment`) consistent with L2 B2.
- *Scope:* decomposed so Tier 1 ships alone (no inference change); Layer A is
  isolated to the cron; nothing forces a global graph build; everything additive.
- *Ambiguity:* "connection basis" enumerated (member/semantic/entity/
  co-occurrence); empty state specified, not implied.
