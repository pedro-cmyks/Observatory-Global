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

- [ ] **Confidence-gate the Brief lead slot + share card** — floor (~70%); below it the story cannot lead and the card refuses to freeze.
- [ ] **"Unassembled signals" tray** — low-confidence clusters drop to an honest desk showing raw receipts grouped by geography (reuse the loved Under-the-Radar pattern) instead of a fake headline.
- [ ] **"Label under review" chip** on demoted labels (the L2 lens already ships one — unify).
- [ ] **Label Court (engine, parallel track, #204/#224):** cheap entailment check label-vs-its-own-top-N-receipts before any label reaches a surface; failures auto-demote to receipt-derived neutral labels ("Iran: Hormuz blockade & US strikes — from 6 receipts") + logged as labeler training data.
- [ ] **Brief staleness ops** — the 2-day-stale sealed edition: fix the daily-publication chain failure mode + banner gains what/why/when. [P0-2, wish 20]

**Acceptance:** no served lead below the confidence floor; the FIFA/Meloni/Job-Openings class cannot reach L1; Marcos persona re-run scores the front page "no lies found".

## Phase 2 — Complete the capture loop (product-surface; ~1 week)
Council Move 2 = the #1 wish (5/6 personas). Carolina's claim ledger is the spec.

- [ ] **Receipt-level pinning** — every evidence row / semantic match / archive-day headline / Brief receipt pinnable as a first-class citation carrying provenance (source, country, language, gate status, frozen timestamp). [wish 1, W4/#227 lineage]
- [ ] **Claim ledger** — mark receipt pairs CORROBORATES / CONTRADICTS; dossier renders a claim table (the 4,734-vs-4,930 death-toll demo: each figure, outlet, date side by side, official source marked missing).
- [ ] **Investigation merge/move-pin + ergonomics** — silent duplicate investigations, tiny ◆ targets, rows moving under the cursor, badge lag, toast+undo, Escape closes. [P1-11, wish 4]
- [ ] **Verdict chips = the flywheel** (Inés's big idea) — every dossier self-critique ("label unreliable", "unrelated receipt", "single-sourced") renders as an actionable chip: drop receipt / split-relabel / needs-corroboration / request snapshot. Each resolution logged with provenance = the gold labels #204 is starved for, generated as a byproduct of real work. [wish 9]

**Acceptance:** Carolina persona re-run files her claim table without hand-typing a note; a session of dossier work emits ≥N logged verdicts.

## Phase 3 — Make the dossier publishable (engine/data)
Council Move 3, ordered by leverage. Verdict today: 6/6 "use internally yes, publish no".

- [ ] **(a) Wire the corroboration lane** — SERP/Brave key or GDELT DOC 2.0 fix (Marcos: "the single feature that would make the dossier publishable"); pre-announce when down; cached-corpus degraded mode; inline per-receipt verdicts. [P1-9, wish 3, task_ce252c2b]
- [ ] **(b) Prose-vs-tables validator** — generated prose (Editor's Analysis, dossier lens/actor claims, auto-titles) validated against its own measured tables before render; never "confirmed" while corroboration unmeasured. Diana's dossier-voice-upstream (wish 11) ships ONLY behind this validator. [P1-10, wish 8, task_07cdda75]
- [ ] **(c) Source credibility tiers** (#217) past "unknown 19 · wire 1" — coarse wire/state/local/unknown rollout. [wish 10]
- [ ] Discussion-attach relevance honesty (#248 class — Brazil tariffs inside the VE quake thread). [P1-14, wish 17]
- [ ] Voice-mix/self-voice panel inside thread view (Carolina). [wish 18]
- [ ] NER/subject garbage chips ("states states", "catia a sea") — P2.5 actor-quality track. [P1-13]

**Acceptance:** a professional-persona panel re-run scores the dossier "publishable with named caveats" (vs today's unanimous "publish no").

## Parking Lot (explicitly deferred, council's reasons kept)
- **Full Reconciliation Desk** (Tomás, L) — Phase-0 count chips deliver ~80%; revisit when they prove insufficient.
- **Dossier-voice front page** (Diana, L) — gated on Phase 3(b)'s validator (the −0.1 Editor's-Analysis bug is the cautionary tale).
- **Mobile #236 + map-click precision beyond Phase 0** — real, but no persona's publish-blocker.
- **Sibling-vs-constellation relation vocabulary** (wish 16) — fold into the connection-layer track when it next opens.
- **Junk in "Fastest rising"** [P1-15] — resolves via Label Court + #248, not its own fix.

## In flight now (don't double-run)
- **#229 whitening gold gate** — control pass done (2,268 clusters); whitened pass chained behind tonight's real snapshot run; then 2-vendor judge. Outcome feeds substrate depth (more real stories = less label starvation).
- **Issues/papers/constellation chip** (separate session) — already landing PRs (NLP selector root-cause fix merged).
- **#238 remainder** — actor-vs-location weighting (dt-438 class) = the C7-ranking unlock; schedule after Phase 1.

## Sequencing summary
Phase 0 (days) → Phase 1 (the front page stops lying) → Phase 2 (capture loop + flywheel) → Phase 3 (publishable dossier). Engine tracks (Label Court, whitening wire-up, actor-vs-location) run parallel where marked. Each phase closes with a persona re-run as its acceptance gate — the council is now the product's regression suite.

*Marcos's closing line is the plan's north star: "Trust the receipts, not the labels." These phases make the labels earn what the receipts already have.*
