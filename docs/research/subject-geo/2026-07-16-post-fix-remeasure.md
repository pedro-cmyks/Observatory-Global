# Subject-Geography Inference — POST-FIX re-measure (#238), 2026-07-16

Re-measurement of `infer_receipt_subject_geography` after the fix pass,
same harness and definitions as the baseline
(`2026-07-16-inference-quality.md`). The fixes measured here are the
**uncommitted working-tree changes** to
`backend/app/services/subject_geography.py` (person-proxy demotion) and
`backend/app/services/ingest_rss.py` (RO/CI lexicon entries, `UK`,
Spanish/Indonesian exonyms, Ukrainian city/oblast stems → UA, Greek-script
table) plus `backend/tests/test_subject_geography_person_proxy.py`.
**Prod still runs the PRE-fix code** (verified: all 31 served
status/verified fields byte-identical to the baseline pull), so the
comparison of record is **JUDGE vs LOCAL-POST-FIX**; served-vs-local
deltas are reported as evidence the fixes change outcomes.

**Measurement luck worth stating:** the fresh prod pull
(`/threads?hours=24&limit=40`, 2026-07-16 ~06:10 EDT) returned the SAME
31 threads with receipt sets **identical 31/31** to the baseline window
(front page did not rotate). That turns this re-measure into a
controlled experiment: same threads, same receipts, same baseline
DeepSeek judgments — only the code changed. A second, fresh judge pass
was also run (§Judge stability).

## Headline before/after (measurement of record = replay: post-fix code, baseline judgments)

| Metric | Baseline (pre-fix) | Post-fix | Δ |
|---|---|---|---|
| Precision of `verified` (judge same-or-superset) | 12/16 = **75.0%** | 10/15 = **66.7%** | **−8.3pp** |
| Recall strict (verified AND agreeing / judge-named) | 12/31 = **38.7%** | 10/31 = **32.3%** | **−6.4pp** |
| Recall lenient (verified at all / judge-named) | 16/31 = 51.6% | 15/31 = 48.4% | −3.2pp |
| Status: verified / partial / unavailable | 16 / 8 / 7 | 15 / 11 / 5 | — |
| Served(pre-fix) vs local(post-fix) outcome deltas | — | **14/31 threads change** | — |

**The headline numbers went DOWN — and the artifact would be lying if it
buried that.** The decomposition below shows why this is not "the fixes
failed": every targeted error class flipped correctly, the systematic
crisis inversions are gone, and the losses are two *new, different*
classes the fixes exposed (§Regressions). A measured one-line follow-up
(dominance cap, §Simulation) takes the same window to **86.7% precision
/ 41.9% strict recall — above baseline on both**.

## Fate of each baseline disagreement

| Baseline case | Baseline → Post-fix | Verdict |
|---|---|---|
| **dt-714** "Political Blocaj" (RO politics verified RU via Putin-proxy) | verified [RU] → **verified [RO]**, judge RO, **agree** | **FIXED, cleanly.** RO now 10 receipts/7 outlets (new România/Rusiei forms); RU demoted to candidate — its only non-proxy receipt is "ameninţările Rusiei" (1), the Putin hits carry `person_proxy` + the thread serves `person_proxy_evidence_demoted`. Both halves of the fix (missing self-name + proxy demotion) verified live. |
| **dt-438** "Lightning Strike" (UA war verified RU-only; attacked country invisible) | verified [RU] → **verified [RU, UA]**, judge UA, still disagree | **HALF-FIXED.** UA now 8 receipts/6 outlets via the new city/oblast stems (Херсон/Суми/Краматорськ…) — the story is no longer inverted; both parties are named, RU first (16/10, genuinely named as actor via Росія). Scored-agree still fails because actor-vs-location weighting (baseline fix #2) was NOT implemented — only its interim location-stem half. |
| **dt-644** "Argentina vs Cabo Verde" (GB invisible via "Inglaterra"; ES context over-verified) | verified [AR, ES] → **verified [AR, GB, ES]**, judge [AR, GB], still disagree | **HALF-FIXED.** Inglaterra→GB works: GB jumped 0→24 receipts/18 outlets, equal-first with AR. ES (the waiting finalist, 4/3) still clears the 2/2 bar — the context-over-verify half remains. Under the dominance cap it drops → exact judge match. |
| **dt-606** "Piala Dunia" (Indonesian exonyms invisible; side-mention AR verified) | verified [AR] → **verified [ES, FR, AR, GB]**, judge [ES, FR], still disagree | **SUBSTANTIVELY FIXED, not scored-agree.** Spanyol/Prancis now dominate exactly as they should (ES 22/13, FR 13/10 vs AR 4/4, GB 5/5) — the RANKING is now correct and the real subjects lead; the uncapped verified set still includes the side-mentions. Dominance cap → [ES, FR] = judge exact. |
| **dt-287** wildfires-label case (geo right, label wrong) | verified [CA] → verified [CA], agree | Unchanged, still correct (label problem stays with #204). |

Baseline miss classes:

| Miss class | Post-fix fate |
|---|---|
| Greek script (dt-320, dt-90; 24 Greek receipts, 0 candidates) | **Recall delivered:** dt-320 unavailable → verified GR (15/11); dt-90 unavailable → verified IR+US (7/4, 2/2). But both now co-verify a low-count extra country (§Regression B) so neither scores agree. |
| "UK" gap (dt-2469) | **FIXED:** partial → verified [GB], judge GB, agree. The case-sensitive `\bUK\b` entry works (8 receipts). |
| "Côte d'Ivoire" gap (dt-96) | **Lexicon fixed, corroboration honest:** CI 0 → **24 receipts** — but all from ONE outlet (aip.ci), so the ≥2-outlet bar correctly holds it at partial with `subject_geography_not_independently_corroborated`. The baseline's "flips to verified" prediction was wrong about the outlet mix, not the lexicon. |
| Hangul (dt-623) | **NOT ADDRESSED** — no Korean forms shipped (baseline fix #4 was "Greek + Korean"; only Greek landed). KR still 1/1 candidate, partial. |
| Structural 9 (domestic stories naming cities, no country word) | Unchanged as expected — NER `places` (#184) still not plumbed; all 9 remain partial/unavailable. |
| dt-1334 correct suppression (multi-country FX roundup) | **Still correctly suppressed** — 1/1 candidates each, partial. The fixes introduced no false verify here. |

## New regressions the fixes introduced

**A. Person-proxy demotion has a measured recall cost: 4 threads lost a
judge-agreeing verification.** All four verified pre-fix ONLY through a
leader name; the judge considers the country correct:

| Thread | Pre-fix | Post-fix | Proxy evidence |
|---|---|---|---|
| dt-372 "Trump Attacks Meloni" | verified [IT] | partial | IT 12 receipts/7 outlets, **0 non-proxy** (all "Meloni") |
| dt-2369 Keystone Pipeline | verified [US] | partial | US 24/24, 1 non-proxy (rest "Trump") |
| dt-2493 Daylight Saving bill | verified [US] | partial | US 2/2, 0 non-proxy |
| dt-2536 US Mint Trump coin | verified [US] | partial | US 13/13, 0 non-proxy |

Plus dt-49 (US-Iran strikes): US demoted (4/4 all Trump-proxy) →
verified [IR] only; still scores agree (subset), but a real co-subject
was lost. This is the flip side of the dt-714 fix: **US domestic
stories say "Trump", not "US"** — the person proxy was quietly carrying
the structural-miss class the baseline diagnosed. The demotion is honest
(every one serves `person_proxy_suppressed` + the reason code — visible,
never silent), and no new WRONG verification appeared; but −4
verified-agree is the dominant term in the precision/recall drop.
Possible refinements: (i) let a proxy verify when the person is a HEAD
OF STATE and no competing country has non-proxy evidence (would recover
all 4 without re-breaking dt-714, where RO had strong non-proxy
evidence); (ii) NER places (#184) — Keystone/DST/Mint receipts are full
of US places.

**B. Wider lexicon + the low 2-receipt/2-outlet bar = over-inclusive
verified sets (2 new precision failures).** The Greek fix made dt-320
and dt-90 produce candidates for the first time — and cluster-mixed
side-mentions cleared the bar alongside the real subject: dt-320
verified [GR, **IR**] (IR = 2 Greek receipts about Iran mixed into the
Chalkidiki-tragedy cluster — thread coherence, not lexicon), dt-90
verified [IR, **FR**, US] (FR 4/4 in a World-Cup-adjacent Greek
cluster). Same mechanism keeps ES in dt-644 and AR/GB in dt-606. This
class did not exist at baseline only because most of these countries
were invisible: **fixing recall exposed that `verified` has no dominance
discipline.**

## Simulation: dominance cap (measured next fix)

Applying, post-hoc on the same replay ledger: *verified country must
have receipt_count ≥ ⅓ of the leading verified country's, cap 2, order
by receipts*:

| Metric | Post-fix as shipped | + dominance cap |
|---|---|---|
| Precision | 10/15 = 66.7% | **13/15 = 86.7%** (> baseline 75.0%) |
| Recall strict | 10/31 = 32.3% | **13/31 = 41.9%** (> baseline 38.7%) |
| Recall lenient | 15/31 = 48.4% | 15/31 = 48.4% |

Flips: dt-320 → [GR] agree, dt-644 → [AR, GB] agree, dt-606 → [ES, FR]
agree; dt-90 → [IR, FR] (still disagree — FR is genuinely frequent in
those receipts). dt-438 unchanged (UA 8 ≥ 16/3 — survives, correctly).
The cap costs nothing on this window and repairs exactly the
over-inclusion class. Recommend shipping it in
`infer_receipt_subject_geography` (as a serving discipline on
`verified_subject_countries`, ledger keeps ALL candidates — no silent
filtering).

## Judge stability (fresh judge pass, secondary)

A fresh DeepSeek pass (temp 0, reconstructed prompt) on the identical
receipts changed its subject set on 9/31 threads — mostly narrowing
2-country answers to 1 (dt-457/387 [UA,RU]→[UA], dt-1206/1649
[ES,FR]→[ES], dt-644 [AR,GB]→[AR], dt-606 [ES,FR]→[] …). Against the
fresh judgments the post-fix numbers read precision 7/15 = 46.7% /
strict 7/30 = 23.3%. This spread (66.7% vs 46.7% on identical
predictions) is judge/prompt variance, not code — a caveat that applies
to the baseline's single-judge numbers too. The replay against the
baseline's own judgments is the honest delta and is what the table of
record uses.

## Status distribution (N=31)

verified 15 (48.4%) · partial 11 (35.5%) · unavailable 5 (16.1%)
(baseline 16/8/7). The two unavailable→verified are the Greek threads;
the 4 verified→partial are the person-proxy demotions; dt-96/dt-623
stay partial. All non-verified threads carry honest reason codes;
`person_proxy_evidence_demoted` serves on 6 threads.

## Recommendation

Unchanged from baseline in direction, updated in content: **still not
ready for ranking/C7/chips as-is, but the blocker moved.** The
systematic crisis inversions the baseline flagged are gone (dt-714
verified RO; dt-438 serves both parties; a C7 on this output would no
longer score Ukrainian coverage as "coverage of Russia"). Before
consuming beyond `why_now`:

1. **Ship the dominance cap** (measured above: 86.7%/41.9%, beats
   baseline on both axes; one function, no lexicon work).
2. **Soften person-proxy for head-of-state-with-no-rival-evidence** or
   land NER places (#184) — recovers the 4 US/IT domestic regressions.
3. Korean forms (dt-623) — the un-shipped half of baseline fix #4.
4. Actor-vs-location weighting stays the real dt-438-class fix.

## Reproduction

- Harness: `snapshots-2026-07-16-postfix/run_remeasure.py` (versioned;
  synchronous replay + fresh pull + judge + scoring), run with
  `backend/.venv/bin/python`. Cost: 31 deepseek-chat calls ≈ $0.01.
- Judge: deepseek-chat, temperature 0, prompt = label + up to 15 receipt
  headlines → `{"subject_countries": [≤2 ISO2], "reason"}`.
- Definitions identical to baseline: agree = verified set ⊆ judge set
  (non-empty); precision over verified threads; recall over judge-named.
- **Snapshots VERSIONED this time** in `snapshots-2026-07-16-postfix/`:
  - `threads.json` `judgments.json` `local_inference.json` `scored.json`
    — the fresh window (pull ~2026-07-16 10:10 UTC).
  - `replay_local_inference.json` `replay_scored.json` — post-fix code
    over the baseline receipts + baseline judgments (table of record).
  - `baseline-threads.json` `baseline-judgments.json`
    `baseline-local_inference.json` `baseline-scored.json` — the
    baseline session's snapshots, copied here so the 2026-07-16 baseline
    artifact is now verifiable too (its metrics recompute exactly:
    16 verified / 12 agree / 31 named).
  - `metrics_summary.json` — machine-readable headline numbers.
- Code under measure: working-tree (uncommitted) diff to
  `subject_geography.py` + `ingest_rss.py` at repo state `df276d95`+dirty.
