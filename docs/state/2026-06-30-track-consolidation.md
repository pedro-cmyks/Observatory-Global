# Track consolidation — two chats → one living track (decided 2026-06-30)

**Decision (Pedro, 2026-06-30):** stop the parallel-chat split. This (frontend/
L2) chat becomes the **single living track**, AFTER the engine/taxonomy chat
reaches a clean checkpoint and writes a final engine handoff. Low-risk path:
preserve the engine chat's deep context instead of reconstructing it from git.

## Why consolidate (the work converged)

The two chats were split by separability: **backend engine/taxonomy ‖ frontend
L2**. That justification is gone. The L2 audit surfaced that the Unified Engine's
**split-brain is bigger than the spec scoped**:

- `2026-06-29-atlas-unified-engine.md` §1 names **3** unreconciled construction
  pipelines (atlas-lexical ‖ dynamic-embedding ‖ discussion-attach) and unifies
  "any signal — press, forum, event."
- The L2 audit shows that "any signal" is really "any *embeddable* signal." The
  split-brain has **5 brains**, not 3 — the engine closes 3, leaves unscoped:
  - **attention** (Wiki pageviews + Google Trends — the people-side reading/
    searching proxy; `public_attention.py`/AnomalyPanel bolt-on, no role);
  - **alert/volume** (the country-anomaly layer — `CrisisContext`/`/anomalies`,
    never reconciled into a topic = the §3 split-brain that produced the CI
    fake-disaster and finding E's "XX").

So the L2 surfaces ARE where the engine's split-brain shows; the fix (two more
roles) is engine work informed by L2 evidence. One problem, two ends → one chat.
Full analysis: `docs/specs/2026-06-26-l2-deep-review.md` §"The unified-engine
connection — attention + anomaly are the missing roles."

The heavy compute (M1 crons, gold pass) runs on schedule regardless of chat
count — consolidating does not change it.

## What this (L2/frontend) chat has shipped (context to absorb)

Branch `v3-intel-layer`, pushed (commits `06167b8`, `ac6c0f2`, `72915c9`):
- **A3** scope strips (verified already shipped `6dfa6a0`), **A4** first-country-
  click walkthrough (`CountryFocusWalkthrough.tsx`, desktop-anchored / mobile-
  centered tab-aware copy), **C3** forum lane verified; **C3(b)** semantic
  trends/wiki deferred (low ROI + shared-embed-box cost).
- **Country-nav swap fix**: `handleCountryClick` clears `selectedTheme` (anomaly/
  map→country now swaps the stream slot when a ThemeDetail is open).
- **CountryBrief "Top Publishers"**: dead `<div>` → expand pattern (inline
  headlines + "Full source profile ↗"), matches ThemeDetail.
- **D** public-attention noise filter (wiki meta pages / films / non-English
  sports); **E** anomaly placeholder + historical-code filter (`isKnownCountry`)
  + missing ISO names (CI/PR/MO/EH) added to `COUNTRY_NAMES`.
- **Live L2 connectivity audit** (click-by-click): spine confirmed wired; two
  leaf bugs found + fixed (the two above). All in the L2 spec.

## What I need FROM the engine chat (the final handoff) — request

Before/at its next checkpoint, the engine chat should write one state doc
capturing, so this chat can own the engine without losing context:
1. **F3/F4 status** — unified-v2 construction + A/B result; is the read-path
   cutover flipped or still flag-gated? Which `engine_version` serves prod?
2. **Gold pass (tonight)** — the #204 taxonomy gold-growth result; κ / precision
   numbers; whether the v2 gate / reject stage changed.
3. **`topic_members` schema** — current role enum + any pending migration; the
   ETL/cron chain (embed→attach→project→build-v2) exact state.
4. **M1 cron + AtlasLocalWorker tree** — what runs when (so this chat schedules
   heavy work off-peak without stacking compute / crashing the M1).
5. **Anything mid-flight** — uncommitted engine edits, in-progress backend.

## Post-consolidation plan

1. Absorb the engine handoff → this chat is the single track.
2. **Fold** the L2 §"unified-engine connection" analysis INTO
   `2026-06-29-atlas-unified-engine.md` as the extension (2 new roles), its
   canonical home. A/B-gated like the rest of the engine.
3. **Sequence the engine extension off-peak** (after the gold pass, on the M1
   schedule):
   - `attention` role — embed wiki-title / trend-keyword → nearest topic
     centroid (reuses the C3(b) machinery); `verified=false`, never evidence.
     Makes #168 `public-led`/`uncoupled-attention` differentiate on real
     reading/searching data, not forum-only.
   - anomaly → `movement` — per-topic volume-vs-baseline as a topic property, so
     "critical/elevated" is the thread's own elevation. Closes §3 split-brain;
     retires the orphaned country-anomaly-as-lead path.
4. **Meanwhile**: this chat keeps shipping safe frontend/serving down-payments
   (the B1-style "critical from the thread's own movement", C3 surfaces) — no
   backend collision.

## Immediate next step

Pedro relays the "request FROM the engine chat" above to that chat. When it
checkpoints + hands off (or Pedro says go), this chat absorbs and proceeds with
the post-consolidation plan. Until then, this chat continues frontend-only work
that does not touch the reserved engine/taxonomy/cron tree.
