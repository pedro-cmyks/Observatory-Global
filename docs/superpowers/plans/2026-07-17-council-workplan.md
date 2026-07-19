# Council Work Plan — 2026-07-17

**Source:** `docs/research/ux-council/2026-07-17-council.md` (6-persona production walkthrough + roundtable). This plan is the execution translation: every wish, bug and move from the council captured into phased, checkable work. Nothing the personas said is dropped — items not scheduled live in the Parking Lot with reasons.

**The one-line diagnosis (unanimous):** the honesty layer is built and believed; the substrate feeding it fails most visibly where the product is most prominent. All six "big ideas" are one program: **make the labels earn what the receipts already have.**

---

## Phase 0 — Hygiene batch (days; pure surface; no new capability)
The trust-per-line cheapest fixes. Every item is a council P0/P1 bug.

**STATUS: DONE 2026-07-17.** Three lanes + two fix rounds, each closed by a
Ponepeross acceptance re-run: round 1 verdict "phase0 leaks" (5 repros + 3 new
regressions incl. the China-click-opens-Switzerland ISO/FIPS collision the click
fix made visible), round 2 verdict **"round2 clean"** (0 repros, 0 regressions).
503 vitest green / build green at commit. Bonus finds along the way: Taiwan +
Kosovo gained their real polygons (`featureIso` audit), `data-tip::before`
phantom layout boxes were the console's 61px horizontal scroll, backend
`/heat/countries` still serves legacy-FIPS residue rows (CH+CN, RQ/VQ) —
frontend reads them safely via `countryCodeBoundary.ts`; upstream normalization
= backend follow-up.

- [x] **HTML entities sweep** (`decodeEntities.ts`) — Under the Radar, search dropdown, archive receipts, signal stream, gap cards. [P0-3]
- [x] **One sentiment scale** (`sentimentScale.ts` + `reconcileSentimentProse.ts` — global-scoped: per-country figures never rewritten). [P1-4]
- [x] **Count qualifiers** (`countQualifier.tsx` — bases gated/raw/frozen stated truthfully per surface; the 212-vs-408 row/detail pair now labeled honestly). [P1-5, wish 5]
- [x] **Placeholder-title flash** — loading path under the #204 rule; focus chip stores the opener's real label (`focus.knownLabel`), generic never stored. [P1-7]
- [x] **Landing template failures**. [P1-12]
- [x] **Jargon purge** (`humanizeInternals.ts`, matches `Label: key=value` anywhere; verbatim internals on hover). [wish 7]
- [x] **Export/share feedback** — Copied ✓ / Copy failed in place; menu stays open on failure. [wish 12]
- [x] **Map click reliability** — ISO-first contract end-to-end (`countryCodeBoundary.ts`; CN≠CH, BN/BJ class frozen by hygiene test); tiny-island nearest-wins assist; polygon-less microstates get centroids (`microstates.ts`, 37 entries — Malta/Singapore clickable + fly-to works); MAP KEY collapsed by default. [P1-8, wish 14]
- [x] **Universe reliability** — honest unavailable + RETRY state. [P1-6, wish 19]
- [x] **Scrubber ergonomics**. [wish 13]
- [x] **Translate receipts in the Brief lead**. [wish 6]
- [x] Constellation ≥2-pins hint; camera fly-to dominant coverage country. [wishes 21, 22]

**Acceptance: PASSED** — Ponepeross re-run round 2 = zero reproductions, zero new regressions.

## Phase 1 — Stop the front page lying (label trust; days–week)
The council's Move 1 core. The confidence number exists (21% served as lead vs 96–100% on real stories) — use it.

**STATUS: DONE 2026-07-17.** Backend + frontend, two Marcos-persona gate rounds
(round 2 = "phase1 clean") + a live-DOM verification pass that caught a reconcile
bug the static gate missed. Live proof: prod `/briefing` serves `label_status`;
all 10 top threads judged FAILED by the court — including the 0.893 "Job and
Course Openings" (a Brazilian police roundup the confidence floor alone let
through) — so the front page shows the honest "no story clears the bar" empty-lead
and the Greek blob sits in the tray with translated receipts. Commits: `8cbe3999`
(Label Court engine), `ae8af35a` (serve label_status), `80a1f119` (front page +
reconcile round-3 + sealed_at). 555 vitest green.

- [x] **Confidence-gate the Brief lead slot + share card** — FLOOR 0.70 (`lib/leadConfidence.ts`); label_status='failed' blocks the lead even above floor; share card refuses non-eligible.
- [x] **"Unassembled signals" tray** — below-floor/failed threads → honest desk, receipts grouped by source country, translated; no thread vanishes. Country edition gated identically.
- [x] **"Label under review" chip** — ONE shared `lib/labelReviewChip.tsx` across Brief/NarrativeThreads/ThemeDetail (unified).
- [x] **Label Court (engine, #204/#224):** `backend/scripts/label_court.py` — DeepSeek temp-0 entailment label-vs-receipts → entailed/partial/failed + receipt-derived neutral proposal (never auto-served) + JSONL training ledger. mig 080, wired into the nightly runner, run live (25 failed / 4 entailed / 3 partial of 32).
- [x] **Brief staleness ops** — failure-mode fixed (`108026ef` snapshot failure budget) + banner what/why/when (`lib/staleBanner.ts` + `investigation.py` sealed_at). [P0-2, wish 20]

**Acceptance: PASSED** — Marcos re-run "phase1 clean"; the Job-Openings/FIFA/Meloni class cannot lead L1 (all court-failed → tray). Follow-up: the court judged only 32 topics (thin substrate); the full active set gets judged on the next complete nightly snapshot.

## Phase 2 — Complete the capture loop (product-surface; ~1 week)
Council Move 2 = the #1 wish (5/6 personas). Carolina's claim ledger is the spec.

**STATUS: DONE 2026-07-17.** Pipeline (foundation → build → gate), Carolina
persona gate = **"phase2 clean"** (0 leaks, 0 regressions, 11 confirmed, DOM-driven:
the 4,734-vs-4,930 death-toll table rendered without a hand-typed note, verdict
log 0→N, merge/dedupe/undo/Escape live). 638 vitest, build green. Commit `eca17716`.

- [x] **Receipt-level pinning** — `lib/workbench.ts` Citation (frozen provenance: source, country, language, gate status, published+captured dates); `PinReceiptButton` on every evidence row (ThemeDetail, CountryBrief, ResearchPlan, Brief lead+tray, SignalStream); WorkbenchPanel CITATIONS section. [wish 1, W4/#227]
- [x] **Claim ledger** — `lib/claimLedger.ts` (CORROBORATES/CONTRADICTS/CONTEXT + figure extraction + official-source-missing detection); DossierView "Contested figures" table (the death-toll demo), in the MD export; WorkbenchPanel select-two → mark-relation.
- [x] **Investigation merge/move-pin + ergonomics** — dedupe silent duplicates, mergeInvestigations (pins+citations+claims union), movePin, remove-with-undo (6s toast), Escape closes. [P1-11, wish 4]
- [x] **Verdict chips = the flywheel** — `lib/verdictChips.ts` + `VerdictChip`: each dossier self-critique → actionable chip (split-relabel / drop-receipt / needs-corroboration / request-snapshot); `lib/verdictLog.ts` logs every resolution with provenance = the #204 gold, generated as a byproduct of real work. [wish 9]

**Acceptance: PASSED** — Carolina files her claim table without hand-typing a note; a dossier session emits provenance-carrying verdict-log entries.

## Phase 3 — Make the dossier publishable (engine/data)
Council Move 3, ordered by leverage. Verdict today: 6/6 "use internally yes, publish no".

**STATUS: core DONE 2026-07-17 (a/b/c).** Professional-panel gate =
**"phase3 publishable-with-caveats"** — the honesty architecture moves the dossier
from the unanimous "publish no" to "publishable WITH NAMED CAVEATS". The two
publishable-blocker bugs the panel found (DOC 2.0 `import json` NameError; the
Markdown export bypassing the prose validator) are FIXED. 676 vitest / 28
corroboration pytest / build green. Commit `cd157198`. **Full-history unlock**
(Pedro): corroboration queries hot ∪ cold (historical_evidence_samples May-3→
present, refreshed by tonight's catch-up chain) — no SERP/Brave key needed.

- [x] **(a) Corroboration lane** — GDELT DOC 2.0 (query-time, free, no key) ∪ full-history Atlas corpus (hot signal_embeddings + cold historical_evidence_samples); relation is math not LLM; HONEST degraded mode (per-lane source_status, never fakes complete); per-receipt verdicts. [P1-9, wish 3]
- [x] **(b) Prose-vs-tables validator** — `lib/proseValidator.ts`: "confirmed/verified/corroborated" downgraded to "reported (uncorroborated)" unless a corroboration verdict backs it; wired into on-screen synthesis AND the Markdown export + auto-title. [P1-10, wish 8]
- [x] **(c) Source credibility tiers** (#217) — coarse wire/state/major/local/unknown (unknown terminal); chips on citations + Brief receipts + dossier source-mix rollup. [wish 10]
- [x] Discussion-attach relevance honesty (#248 class). [P1-14, wish 17] — BUILT 2026-07-19 (`1373cf47`, pending deploy): community-discussion items serve their MEASURED attach similarity (tm.confidence, absent when unrecorded) + noise lane tags (hobby/sports/etc via the shared forum classifier), damped never dropped; UI shows similarity chip + lane tag + showing-X-of-N.
- [x] Voice-mix/self-voice panel inside thread view (Carolina). [wish 18] — BUILT 2026-07-19 (`b0a281c4`+`e3dfaefb`, pending deploy): `GET /api/v2/topic/{id}/voice` (thread-voice-v0) over typed evidence members + VOICE MIX · WHO SPEAKS section in ThemeDetail (languages w/ unknown count, self-voice by OWNERSHIP vs dominant subject, soft power, unattributed stated, thin flagged).
- [ ] NER/subject garbage chips — P2.5 actor-quality track. [P1-13] — deferred

**Acceptance: PASSED (with named caveats)** — panel scores "publishable with named caveats". Remaining caveats the panel would still print: corroboration leans on the Atlas corpus while a fresh IP is needed for a clean live DOC 2.0 `ok`; single-source (esp. single-local) is labelled but still a caveat; atlas_hot url=null dedup falls back to headline key; #248/voice-mix/NER-garbage deferred.

## Parking Lot (explicitly deferred, council's reasons kept)
- **Full Reconciliation Desk** (Tomás, L) — Phase-0 count chips deliver ~80%; revisit when they prove insufficient.
- **Dossier-voice front page** (Diana, L) — gated on Phase 3(b)'s validator (the −0.1 Editor's-Analysis bug is the cautionary tale).
- **Mobile #236 + map-click precision beyond Phase 0** — real, but no persona's publish-blocker.
- **Sibling-vs-constellation relation vocabulary** (wish 16) — fold into the connection-layer track when it next opens.
- **Junk in "Fastest rising"** [P1-15] — resolves via Label Court + #248, not its own fix.

## Accounts-v1 SHIPPED (2026-07-18 — the market primitive)
Plan `2026-07-18-accounts-sync.md` executed subagent-driven (3 batches, two-stage
review each; 6 real review findings fixed with TDD before landing). Supabase Auth
magic-link + RLS `user_investigations` (mig 081+082) + local-first LWW sync with
tombstones + AccountSection in the Workbench + pseudonymous `user_id` on
telemetry. **E2E proven without email**: two-origin device sim — push → RLS row →
cross-device pull → UI; funnel `sign_in → workbench_open → investigation_created
→ sync_done` all carrying user_id. W0-D5 privacy stance PRESERVED (anonymous =
pure localStorage, server sees only anonymous events). **Nothing paywalled** —
accounts are the measurement apparatus; monetization stays gated on readiness
≥70 (reliability ≥70) + 4 clean weeks of real-user L3 retention. Pedro's one
manual step: confirm the Email provider in the Supabase dashboard + add the two
VITE_SUPABASE_* vars to Vercel env (local .env.local already configured).

## In flight now (don't double-run)
- **#229 whitening gold gate** — control pass done (2,268 clusters); whitened pass chained behind tonight's real snapshot run; then 2-vendor judge. Outcome feeds substrate depth (more real stories = less label starvation).
- **Issues/papers/constellation chip** (separate session) — already landing PRs (NLP selector root-cause fix merged).
- **#238 remainder** — actor-vs-location weighting (dt-438 class) = the C7-ranking unlock; schedule after Phase 1.

## Sequencing summary
Phase 0 (days) → Phase 1 (the front page stops lying) → Phase 2 (capture loop + flywheel) → Phase 3 (publishable dossier). Engine tracks (Label Court, whitening wire-up, actor-vs-location) run parallel where marked. Each phase closes with a persona re-run as its acceptance gate — the council is now the product's regression suite.

*Marcos's closing line is the plan's north star: "Trust the receipts, not the labels." These phases make the labels earn what the receipts already have.*
