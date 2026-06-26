# Spec — Truncated Narrative Threads (entering from a specific item)

Date: 2026-06-26 · Branch: `v3-intel-layer` · Status: DRAFT for Pedro's review
(do NOT implement until approved). Author: Claude (Opus 4.8).

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

- **Forums are dark.** Reddit is ingested (`source_family='social'`) but has
  **0 topic assignments** (verified: 0/71 over 14d). Clicking a forum post can't
  show "its thread" because forums are not in the thread inference at all. Root
  cause (verified): the atlas-topic classifier `classify_topics.py` matches GDELT
  GKG themes (`WHERE themes IS NOT NULL ... JOIN ON s.themes && t.gdelt_theme_hints`)
  and forum posts carry no GDELT themes → structurally excluded. ~28/71 forum
  posts *do* have embeddings.
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

---

## 3. Architecture

Two layers, each shippable on its own.

### Layer A — Forums (and other no-GDELT-theme sources) enter the inference

Goal: forum signals become **semantically-assigned members** of threads, labeled
discussion, never gated evidence.

- **Mechanism:** the classifier currently requires GDELT theme overlap. Add a
  **semantic assignment pass**: for signals with an embedding but no GDELT-theme
  assignment (forums, some RSS), assign to the atlas topic / dynamic topic whose
  centroid is nearest above a calibrated threshold. Write to
  `signal_topic_assignments` with `method='semantic'`, `gate_kept = false`
  (discussion is never gate-kept), and a new role marker (`evidence_role='discussion'`).
- **Serving:** thread detail + `/threads` already separate `signal_count` from
  `gated_signal_count` (L2 B2). Discussion members add to a NEW
  `discussion_count` (people-side), never to `gated_signal_count`. Thread cards
  can then show "N verified · M discussed."
- **Where it runs:** the M1 cron pipeline (next to `classify_topics` /
  `embed_hot_corpus`); offline, no API hot-path cost. Threshold calibrated like
  #223 (semantic evidence) but looser, since discovery tolerates more recall.

### Layer B — The truncated-thread VIEW (item → connections)

Goal: any item → a thread-shaped connections projection.

- **Signals/forums** (have an `id`): reuse `/api/v2/signal/{id}/context`
  (threads + semantic_neighbors). The forum item already carries its `id` from
  `/api/v2/public-attention`. The view = render that context as a truncated
  thread. No new backend needed for the forum MVP.
- **Typed items (person / event / topic)** (no single signal id): a new resolver
  `GET /api/v2/connections?kind=person|event|topic&value=...` that returns the
  connected threads + distinctive shared entities + neighbor evidence, reusing
  the rarity-weighted entity overlap (#234) and the thread spine. (Topic chips
  already resolve to a thread; person/event are the new ones.)
- **Frontend:** a single `TruncatedThreadPanel` (one component, one contract)
  that takes `{kind, ref}` and renders the section list in §2. Reachable from:
  forum rows (Pulse), Key Subjects person/place chips, event markers, signal
  detail, topic chips. This is the "one surface, many entry points" pattern.

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
- Don't gate the MVP on Layer A. Layer B (forum→context view) ships standalone.

**What I'd cut from a first release:** typed-item resolver for events; topic-chip
truncated view (topics already open a real thread); persistence/pinning. Keep the
MVP to **forum/signal → connections view** + the honest empty state.

---

## 5. Tiered plan (ship + verify each, like the L2 review)

**Tier 1 — Forum/signal → truncated-thread VIEW (frontend-mostly, reuses
`/signal/{id}/context`).**
- T1.1 Add `id` to the AnomalyPanel forum item type (carry it from
  `/public-attention`).
- T1.2 `TruncatedThreadPanel` component (contract = the `/signal/{id}/context`
  shape adapted to §2): renders the item, connected threads (from
  `semantic_neighbors[].has_topic` resolved to their thread label), neighbor
  evidence with gate badges, honest empty state.
- T1.3 Wire forum click → open `TruncatedThreadPanel` (replaces the current
  PublicAttentionPanel route for forums); keep ↗ Reddit as secondary.
- T1.4 Reach it from Signal Detail too (unify with the existing context UI).
- *Verify:* a forum post with embedding shows its nearest verified thread; a
  conversational one shows the honest empty state; ↗ still opens Reddit.

**Tier 2 — Forums in the inference (Layer A, backend cron).**
- T2.1 Semantic assignment pass for embedded-but-unthemed signals →
  `signal_topic_assignments(method='semantic', gate_kept=false,
  evidence_role='discussion')`. Threshold calibrated offline.
- T2.2 Serve `discussion_count` separate from `gated_signal_count`; thread cards
  show "N verified · M discussed."
- T2.3 The truncated view's `connected_threads` now include real `member`
  connections for forums, not only semantic.
- *Verify:* a known forum post (r/colombia water) becomes a discussion member of
  the water thread; `gated_signal_count` unchanged; no centroid pollution (#224
  guard holds).

**Tier 3 — Typed-item connections (person / event).**
- T3.1 `GET /api/v2/connections?kind=&value=` resolver (rarity-weighted entity
  overlap + neighbor evidence).
- T3.2 Key Subjects person/place chips + event markers → `TruncatedThreadPanel`.
- *Verify:* clicking a person shows the threads they connect to with basis
  badges; distinctive-entity filter keeps "donald trump" from linking everything
  (the #234 lesson).

**Tier 4 — First-class + pinnable (later, gated on demand).**
- Persist a truncated thread into Workbench as an investigation node; per-pin
  note. Only if Phase-3 dossier needs it.

Recommended order: **T1 → T2 → T3 → T4.** T1 delivers the felt value with no
inference risk; T2 makes it richer; T3 generalizes; T4 is optional.

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

1. **Discussion-membership count** — surface it on thread cards as
   "N verified · M discussed", or keep discussion only inside the truncated view
   for now? (I lean: show it on cards — it's the honest "people are talking"
   signal, clearly separated from evidence.)
2. **Empty truncated thread** — is "this looks like local chatter, no strong
   narrative connection" the right honest framing, or do you want a softer "no
   match yet"?
3. **Entry points for T1** — forums + signal detail only first, or also Key
   Subjects person chips in the same release?
4. **Naming** — "truncated narrative thread" internally; what should the USER see
   on the card header? (candidates: "Connections", "Where this fits", "Related
   narrative threads".)

---

## 8. Self-review (spec checklist)

- *Placeholder scan:* none — every tier names files/contracts and a verify step.
- *Internal consistency:* the honesty model (basis + strength, discussion ≠
  evidence) is applied uniformly in §2/§3/§4; counts stay separate
  (`gated_signal_count` vs `discussion_count`) consistent with L2 B2.
- *Scope:* decomposed so Tier 1 ships alone (no inference change); Layer A is
  isolated to the cron; nothing forces a graph build.
- *Ambiguity:* "connection basis" enumerated (member/semantic/entity/
  co-occurrence) so it can't be read two ways; empty state is specified, not
  implied.
