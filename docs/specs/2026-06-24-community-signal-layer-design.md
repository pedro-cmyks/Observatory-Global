# Community Signal Layer — Design Spec

Date: 2026-06-24
Status: concept (approved by Pedro 2026-06-24; phased, Phase 1 buildable now)
Author: brainstorm session (Pedro + Claude)
Scope: non-institutional inputs into Atlas narrative threads — non-traditional
sources now, direct human contribution later — always separated from verified
evidence.

> Working name: **Community Signal Layer**. "Forum" is one mechanism inside
> Phase 2, not the goal. The goal is **non-institutional signal**: voices and
> sources that are not traditional media.

---

## 1. Why this exists

Atlas today is fed almost entirely by **institutional sources**: GDELT, RSS
press, news APIs. The diversity program (voice-mix, self-coverage, native-script
geo-tagging) has been fighting the *language/ownership* monoculture. This spec
attacks a different monoculture: **source type**. A narrative often lives on
non-traditional surfaces (Reddit, Telegram, citizen blogs, NGO field reports)
*before*, *around*, or *instead of* press coverage. Atlas should capture that
layer — as discussion and early movement, never as verified fact.

Pedro's framing (2026-06-24): *"quiero interacción con gente o por lo menos
fuentes que no sean medios tradicionales."* Two distinct values were hiding
inside the word "foro":

- **A. Direct human interaction** — people contribute to / discuss a thread.
  This is the forum.
- **B. Non-traditional sources** — inputs that are not press: Reddit (already
  ingested), Telegram, Mastodon, independent/citizen blogs, NGO feeds.

A forum (A) needs a userbase Atlas does not yet have — an empty forum is a dead
forum. Source expansion (B) is buildable today, needs no user moderation, and
feeds threads immediately. Decision: **build B now, document A as Phase 2.**

## 2. The load-bearing guardrail (already canon)

Everything in this layer is **non-evidence / public-discussion**. It can
suggest branches, contextualize, show emergence, and trace the *origin* of a
viral claim — but it **never counts as corroboration** and never inflates a
thread's confidence band.

This is not new policy; it is already written across the system:

- **CLAUDE.md guardrail:** "Reddit/forum discussion belongs in a
  public-attention / narrative-discovery lane. It can suggest branches and show
  claims/questions/links, but it is not verified evidence by default."
- **`signal_class='social_commentary'`** — derived in
  `backend/app/services/_signal_class.py` for `source_family='social'`;
  `geo_confidence` default `0.5`.
- **`#149` scoring rule** (docs/STATUS.md): Reddit must NOT count as an
  independent unique source in the corroboration formula.
- **Research-workflow spec** (`docs/specs/2026-06-09-research-thread-builder-workbench.md`):
  - §"Reddit / public-discussion lane is DB-served by default" (lines ~100-104):
    the lane reads **ingested** rows, never live-fetches at query time.
  - "Second Forcing Case: Claim Verification" (lines ~326-395): the viral
    "Iran stole the rain" claim lives FIRST on social media; Atlas shows it as
    public attention / narrative spread, clearly **not** as verified fact, and
    applies `unsupported_claim_adjustment`. *"Atlas verifies and contextualizes
    claims. Atlas does not endorse or amplify them."*

The Community Signal Layer is the product surface for this already-specified
lane.

## 3. Current state (what exists, what's missing)

**Exists:**
- Reddit ingestion, **credential-free via combined RSS feeds**
  (`backend/app/services/ingest_reddit.py`, commit `c58b048`), runs every 4th
  GDELT cycle. Writes `source_family='social'`,
  `signal_class='social_commentary'`, `attribution_method='reddit_rss'`.
- ReliefWeb NGO feeds (`ingest_reliefweb.py`, `source_family='ngo'`).
- Schema slot: the labeling guide's `public_attention` class
  (`docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md`) =
  "Search, wiki, **social**, or attention signal."

**Missing (the gap this spec closes):**
- **Reddit/social is invisible.** Per the `#229` diagnosis: "Reddit IS ingested
  but invisible — no surface exposes it." It flows into the generic corpus and
  the source-mix breakdown, but nothing presents it as the early-discussion /
  claim-origin layer the docs already promise.
- **Not deliberately wired into threads.** Community signals can land in threads
  via clustering, but there is no explicit `evidence_role=commentary`
  membership that guarantees they never inflate confidence.
- **Stale string:** `_signal_class.py` checks
  `attribution_method == "reddit_public"`, but the ingest now writes
  `"reddit_rss"`. Harmless (the `source_family=='social'` branch still catches
  it) but should be reconciled.

## 4. Phase 1 — Non-traditional source layer + social surface (now)

### 4.1 Source expansion
Add non-traditional, non-press ingest sources alongside Reddit. Candidates, in
rough priority:
- **Telegram** public channels (geopolitics / regional crisis channels).
- **Mastodon** public timelines / hashtags.
- **Independent / citizen blogs** and Substack-style feeds (RSS).
- **NGO field feeds** beyond ReliefWeb where available.

Each ingested with: `source_family='social'` (consider a finer `'community'`
value), `signal_class='social_commentary'`, low `geo_confidence`,
`is_state_media=False`, and an explicit `attribution_method` per source. None of
these are evidence.

> Per-source onboarding follows the same low-cost pattern as Reddit RSS:
> credential-free where possible, ingested into `signals_v2`, never live-fetched
> at query time.

### 4.2 Wire to threads (the missing link)
Community signals become **thread members carrying `evidence_role=commentary`**.
Consequences:
- They appear on a thread's member list and timeline.
- They **never** count toward the thread's independent-source corroboration or
  raise its `confidence_band` (`#149` respected, Paper 4 contract preserved).
- They power the "appears here before press" temporal signal.

Implementation touches `backend/app/services/thread_intelligence.py` (thread
assembly / evidence sampling) and the thread-detail contract.

### 4.3 Social surface (UI)
A dedicated section in the thread / theme-detail view:
- **"Discussion / early movement"** — community signals rendered distinctly,
  each with an **UNVERIFIED** badge and source-family chip (reddit, telegram…).
- **Temporal lead indicator** — when community signal precedes press on the same
  thread, surface "seen in discussion Nh before coverage."
- **Claim-origin trace** — for viral claims, show where the narrative first
  appeared (the forcing-case behavior, made visible).

This closes the `#229` invisibility gap and delivers the lane the
research-workflow spec already designed.

### 4.4 Paper value (Phase 1 produces measurable research artifacts)
- **Paper 2 (source-quality scoring):** Reddit/community is the canonical
  *low-credibility / high-recall* anchor that proves the quality vector
  down-weights correctly. Produces the **cross-source coverage matrix** (which
  crises does community cover that press does not?) and **aggregator-share per
  thread**.
- **Paper 4 (thread aggregation):** community as `evidence_role=commentary`
  member is a direct test of the evidence-role contract; the "leads press"
  hypothesis is a thread-temporal claim.
- **Paper 8 (open-set discovery):** community as an early-emergence signal for
  topics not yet in the taxonomy.

## 5. Phase 2 — Forum / human contribution (later, gated on traffic)

Built on the **same social surface** as Phase 1. Adds a human-contribution
affordance.

- **Contribution unit — hybrid-progressive** (Pedro's choice): structured
  aports for everyone (link-to-source, claim, question); **free-text unlocked by
  earned trust**. Structured-first keeps moderation light and keeps every
  contribution machine-usable as a typed community signal.
- **Identity — OAuth** (Google/GitHub). Persistent identity is required for the
  trust model and gives cheap anti-Sybil without building auth. *Parked: a
  Phase 2 decision.*
- **Moderation — structured-first + trust tiers + post-moderation + report.**
  Detailed model deferred to Phase 2 open questions.
- **Contributions are non-evidence too** — a user-submitted link/claim enters as
  a community signal (`evidence_role=commentary`), identical boundary to an
  ingested social signal. Human contribution does not get a credibility
  promotion by virtue of being typed by a person.

### 5.1 Phase 2 entry gate
Do not start Phase 2 until a thread view is not an empty room. Define a concrete
trigger before building, e.g. a DAU threshold or median thread-views/day. (Exact
number TBD when Phase 1 traffic data exists — intentionally not guessed here.)

### 5.2 Phase 2 open questions (resolve at Phase 2 kickoff)
- Trust accrual mechanics (what earns trust, decay, abuse of the trust path).
- Moderation tooling at solo-maintainer scale.
- Legal / liability surface for hosted user content.
- Whether human claims feed the same clustering as ingested signals or a
  separate review queue first.

## 6. Out of scope (YAGNI)
- No free-text comments at launch (Phase 2 trust-gated only).
- No real-time chat.
- No anonymous posting.
- No custom auth — OAuth only, and only in Phase 2.
- No promotion of any community/human input to "evidence."

## 7. Relationships (what this touches)

| Area | Link |
|------|------|
| Reddit ingest | `backend/app/services/ingest_reddit.py` (`c58b048`, RSS, credential-free) |
| Signal class derivation | `backend/app/services/_signal_class.py` (stale `reddit_public` string to reconcile) |
| Thread assembly | `backend/app/services/thread_intelligence.py` |
| Public-discussion lane spec | `docs/specs/2026-06-09-research-thread-builder-workbench.md` §lane + §2nd forcing case |
| Diversity / voice program | `docs/research/voice-mix/2026-06-23-diversity-program-consolidation.md` |
| Paper 2 (source quality) | `docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md` §Paper 2 |
| Paper 4 (thread aggregation) | master-plan §Paper 4 |
| Paper 8 (open-set discovery) | master-plan §Paper 8 |
| Issue #229 | threads coverage scaling — "Reddit invisible" diagnosis |
| Issue #234 | focus propagation — community signal as another input that re-scopes surfaces |
| ISSUES.md ENH-003 | "Reddit for discussion threads" (original seed) |

## 8. Success criteria

**Phase 1:**
- Non-traditional sources (≥2 beyond Reddit) ingest into `signals_v2` as
  non-evidence community signals.
- Community signals attach to threads as `evidence_role=commentary` and
  verifiably do NOT change confidence bands or corroboration counts.
- Thread view renders a "Discussion / early movement" section with UNVERIFIED
  badges; Reddit is no longer invisible.
- Cross-source coverage matrix produced as a repeatable script (Paper 2 input).

**Phase 2 (future):**
- A logged-in user can attach a structured link/claim/question to a thread.
- Contribution enters as a community signal, never as evidence.
- Moderation/trust model documented and resolved before any free-text path
  opens.

## 9. Decision log (this session)
- Purpose = **aportar señal al hilo** (not pure discussion / not engagement).
- Contribution unit = **híbrido-progresivo** (structured for all, free-text by
  trust).
- Identity = OAuth (parked to Phase 2).
- Reframed forum → **two values (human interaction A + non-traditional sources
  B)**; chose **both, phased**: B now, A documented as Phase 2.

---

## Execution status (2026-06-26, spec-driven sync)

Drift reconciled — this spec said community signal was "not deliberately wired
into threads" and framed the forum as Phase 2. That is now PARTLY superseded:

- **Social surface → threads as DISCUSSION is LIVE.** The truncated-thread spec
  (`docs/specs/2026-06-26-truncated-narrative-thread.md` T2) ships semantic
  discussion-membership: forum/social signals (`source_family='social'`) are
  attached to the topic of their nearest gate-kept neighbour
  (`method='embedding'`, `model_version='semantic-discussion-v1'`, `gate_kept=
  false`), served as a SEPARATE `discussion_count` + `forum_sentiment`, never
  folded into evidence. This is the Phase-1 "social surface feeds threads as
  discussion / early movement" goal — delivered, honestly labelled.
- **Forum surfaced**: `GET /api/v2/public-attention` + the mobile Pulse tab +
  the AnomalyPanel forum lane (`verified=false`). Items also project onto the
  living threads via the ConnectionsSection (`/signal/{id}/context`).
- **Still Phase 2 (unchanged):** the *human-contribution* forum (A) — needs a
  userbase Atlas doesn't have yet. Not built; correctly deferred.
- **Gap:** "seen in discussion Nh before coverage" (§4 lead-time signal) is not
  yet computed — discussion membership exists but the lead/lag-vs-media timing
  is future work.
