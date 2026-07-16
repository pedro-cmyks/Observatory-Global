# Subject-Geography Inference Quality (#238) — measured 2026-07-16

Read-only measurement of `infer_receipt_subject_geography` (serving fn,
`backend/app/services/subject_geography.py`, contract
`atlas-subject-geography-v1`) against a DeepSeek judge (deepseek-chat,
temperature 0, one call per thread) over the live front page.

## Headline numbers

| Metric | Value |
|---|---|
| N threads (prod `/threads?hours=24&limit=40`) | **31** |
| Judge coverage | **31/31** (0 judge_unavailable) |
| Serving-vs-local sanity | **31/31 exact match** (status + verified set) |
| **Precision of `verified`** (judge same-or-superset) | **12/16 = 75.0%** |
| **Recall, strict** (verified AND judge-agreeing / judge-named) | **12/31 = 38.7%** |
| Recall, lenient (verified at all / judge-named) | 16/31 = 51.6% |
| Status distribution | verified 16 · partial 8 · unavailable 7 |

Method: threads list pulled 2026-07-16 ~01:40 UTC; receipts = the
`evidence_samples` each thread served (12–24 per thread, first 15 used —
the exact rows the serving inference ran over). Judge prompt: label +
receipt headlines → up to 2 ISO2 subject countries. The serving function
was re-run locally on the same receipts and reproduced the served
status/countries on all 31 threads, so every number below is about the
real serving path.

## (b) Precision of `verified` — 12/16, four disagreements

All four disagreements diagnosed with the receipts in hand:

### 1. `dynamic-topic-714` "Political Blocaj Continues" — verified **RU**, judge **RO** → **INFERENCE WRONG** (suspicion case, confirmed live)
Receipts are Romanian-language domestic politics: "Nicuşor Dan: «România
e o ţară suverană şi nu se lasă intimidată» de ameninţările Rusiei",
"Dăianu: România nu putea evita majorarea taxelor", "Criza politică -
Ludovic Orban lovește puternic în președinte". Probing the lexicon:
`România/României` (the country's own name, in its own language) matches
**nothing**, while "Donald Trump, mesaj către Putin" → `{RU, US}` — the
**leader-name proxy** (Putin→RU, Trump→US) plus "Bruxelles"→BE produced
RU(2 receipts/2 outlets) → verified. Double failure: missing Romanian
self-name + person-proxy patterns treated as verify-grade subject
evidence.

### 2. `dynamic-topic-438` "Lightning Strike Injures Child" — verified **RU**, judge **UA** → **INFERENCE WRONG (mention ≠ subject)** (suspicion case, confirmed live)
Receipts are Ukrainian-language (Cyrillic) war coverage: "У Херсоні
внаслідок російської агресії загинула жінка", "Російські дрони атакували
Суми", "Армія РФ атакувала Краматорську громаду". The Cyrillic lexicon
covers RU in nominative ("Росія" → native_pattern) → RU got 16
receipts/10 outlets. Ukraine is named via **cities** (Херсон, Суми,
Харків, Одещина) and adjectives, never the country word → UA got 1/1.
The attacker is named, the attacked location is not. RU is arguably a
co-subject (judge itself says "Russian attacks... making Ukraine the
clear subject"), but serving RU-only inverts the story. Needs
place/sub-national evidence (the NER `places` C-clean hook, gated on
#184) — no lexicon addition fixes "Херсон means UA". (The label is also
wrong for this cluster — separate thread-coherence problem.)

### 3. `dynamic-topic-644` "Argentina vs Cabo Verde World Cup 2026" — verified **[AR, ES]**, judge **[AR, GB]** → **INFERENCE HALF-WRONG (exonym gap + context over-verify)**
Receipts: Argentina vs **Inglaterra** semifinal ("Argentina fulmina a
Inglaterra... jugará la final contra España"). Spanish "Inglaterra" maps
to **nothing** (probed) → GB invisible; "España" (the *waiting
finalist*, context not subject) matched 4 receipts/3 outlets → verified.
The actual opponent missed, the bystander verified. (Label also stale —
"Cabo Verde".)

### 4. `dynamic-topic-606` "Piala Dunia 2026" — verified **[AR]**, judge **[ES, FR]** → **INFERENCE WRONG (Indonesian exonym gap)**
Indonesian receipts about Spain beating France: "Spanyol Tumbangkan
Prancis 2-0". `Spanyol`/`Prancis` match nothing (probed); "Argentina"
(same spelling in Indonesian, mentioned re: the other semifinal) matched
4/4 → verified AR. The verified answer is a side-mention; the real
subjects are invisible to the lexicon.

### Suspicion case 3 of 3 — `dynamic-topic-287` "Southern Europe Wildfires" — verified **CA**, judge **CA** → **INFERENCE RIGHT, LABEL WRONG** (cleared)
All 15 receipts are Canadian-wildfire-smoke stories ("Canadian wildfire
smoke chokes Toronto, threatens U.S. cities", "Ohio EPA issues Air
Quality Advisory due to Canadian wildfires") — CA at 16 receipts/16
outlets. The geo inference is correct; the **thread label** is stale/
wrong. This apparent geo bug is a labeling bug. (Counted as an
agreement.)

Precision caveat: 5 of the 16 verified threads are World Cup sports
threads (easy, country-named); the crisis-relevant subset is smaller and
carries both war-related errors.

## (c) Recall — 12/31 strict (16/31 lenient); miss anatomy

15 judge-named threads were not verified. By dominant receipt script:

| Miss class | Count | Threads |
|---|---|---|
| **Script gap — non-Latin, zero lexicon hits** | **3** | dt-320 (Greek→GR: Χαλκιδική tragedy, 0 candidates from 24 Greek receipts), dt-90 (Greek→IR/US: Ιράν/ΗΠΑ invisible), dt-623 (Hangul→KR: Korean weather, KR 1/1) |
| **Latin lexicon-form gap** (country IS named, form not covered) | **2** | dt-96 (**"Côte d'Ivoire" literally in every headline, matches nothing** — probed; candidates only BF/SN), dt-2469 (**"UK" not in lexicon** — probed; GB's single hit came from "London" in one headline, so 8 "UK police" receipts yielded GB 1/1) |
| **Structural: no country name in domestic headlines** (needs NER places / #184) | **9** | dt-21 (IT cronaca — Riminese/carabinieri, never "Italia"), dt-2521/66/2455/2458/1112 (US domestic — US stories don't say "US"), dt-553/565 (BR — g1.globo city-level crime/jobs), dt-245 (AL — Rama/Surrel, never "Shqipëri" in the sampled receipts) |
| **Correct suppression** (verified would be wrong) | **1** | dt-1334 "Dólar Hoy" — multi-country lottery/FX roundup; 5 single-mention candidates each 1/1; the ≥2-receipt/≥2-outlet bar did its job (the judge's AR/CO pick is itself dubious here) |

So the Greek gap named in the task is real but small in this window
(**2 Greek threads + 1 Hangul = 3/15 misses ≈ 20%**); the Latin-form
gaps are 2/15 (both single-token fixes that would flip to verified);
the **dominant miss class (9/15 = 60%) is structural** — domestic
stories that never name their own country, unfixable by lexicon, fixable
only by the NER-places corroboration path already stubbed in the
function (gated on #184) or a coverage-geography prior.

## (d) Status distribution (N=31)

verified 16 (51.6%) · partial 8 (25.8%) · unavailable 7 (22.6%).
Partial = candidates found but none clearing 2-receipt/2-outlet;
unavailable = zero candidates. Every partial/unavailable carried honest
reason codes (`subject_geography_not_independently_corroborated` /
`no_explicit_subject_geography_in_receipts`).

## (e) Caveats

- Single 24h front-page window (31 threads), World Cup week — sports
  over-represented among verified; one run, no variance estimate.
- Judge = one DeepSeek call over ≤15 headlines; fallible (dt-1334 shows
  it forcing countries onto a genuine roundup; dt-644 it dropped ES
  which is at least defensible context). Judge errors bias precision
  DOWN slightly, but all 4 disagreements were hand-verified against
  quoted receipts — none is a judge hallucination.
- Receipts capped at 15 of up-to-24 served samples (judge cost); the
  local re-run used the full set and matched served output, so the cap
  affects only the judge, not the serving comparison.
- "Same or superset" precision credits partially-right sets (dt-115
  verified ES vs judge ES+FR counts as agree).

## (f) Recommendation

**Not yet good enough to consume beyond `why_now`.** 75% precision
sounds close, but the errors are not noise — they are *systematic
inversions* (attacked country → attacker verified; domestic politics →
foreign leader verified) exactly on the crisis-relevant threads where
chips-as-subject, ranking, or C7 voice-asymmetry would consume them. A
C7 built on dt-438 would score Ukrainian coverage as "foreign coverage
of Russia". Keep `verified_subject_countries` display-labeled in
why_now; do not feed ranking/C7/chips until the top two fixes land.

Ranked next fixes (by measured impact):

1. **Demote person-proxy patterns (Putin/Trump/leader names) to
   candidate-only, never verify-grade** — directly kills the dt-714
   class (verified-RU from "mesaj către Putin"). Cheapest precision win.
2. **Actor-vs-location weighting for conflict coverage** — a country
   named only as aggressor/actor ("Росія атакувала X") should not verify
   alone when receipts consistently locate events elsewhere. Interim
   heuristic: require the verified country to not be exclusively in
   attack-verb contexts, or co-verify with location evidence. Fixes
   dt-438 class. (Full fix = NER places, item 4.)
3. **Lexicon form additions (hours of work, flips 4 threads):**
   self-names with diacritics (România/României→RO), "UK"→GB,
   "Côte d'Ivoire"→CI, Spanish exonyms (Inglaterra→GB), Indonesian
   exonyms (Spanyol→ES, Prancis→FR, Inggris→GB), Ukrainian/Cyrillic
   adjectival + genitive forms for UA. Flips dt-96 and dt-2469 to
   verified and repairs dt-644/dt-606 precision.
4. **Greek + Korean script coverage** — 3/15 misses this window; Greek
   is the largest zero-coverage script actually serving front-page
   threads (2 threads, 100% Greek receipts, 0 candidates).
5. **NER `places` corroboration (#184)** — the only path to the 9/15
   structural misses (domestic stories naming cities not countries);
   the hook already exists in `infer_receipt_subject_geography` (C-clean
   block) and is a no-op until `places` is plumbed through serving.
6. Separate but adjacent: **stale/wrong thread labels** (Southern Europe
   Wildfires = Canada smoke; Lightning Strike = Ukraine war; Argentina
   vs Cabo Verde = vs England) made geo look broken when it wasn't —
   label-refresh belongs to the #204/label-quality track, not geo.

## Reproduction

- Threads snapshot, judgments, local-inference outputs, scored rows:
  session scratchpad `subjgeo/` (threads.json, judgments.json,
  local_inference.json, scored.json) — not versioned; re-run is ~10 min
  and <$0.05 DeepSeek.
- Judge: deepseek-chat, temp 0, prompt = label + up to 15 receipt
  headlines → `{"subject_countries": [≤2 ISO2], "reason"}`.
- Local run: `backend/.venv` + `infer_receipt_subject_geography` over
  each thread's served `evidence_samples` (source→source_name); output
  matched served status + verified sets 31/31.
