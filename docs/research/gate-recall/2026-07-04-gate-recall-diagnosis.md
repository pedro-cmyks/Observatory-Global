# Gate recall diagnosis: why "1 of 1,269" on election-legitimacy (2026-07-04)

Triggered by the Atlas-vs-web eval: the election-legitimacy coverage map served
"1 verified of 1,269 assigned → all UNVERIFIED." Measured the cause end-to-end
(read-only). It is **not a bug and not a language gate — it is a precision-first
policy that eats recall to ~0 on hard topics.**

## What the data shows (topic 4, election-legitimacy-dispute, 24h)

- 1,269 assigned · **1 gate_kept** · avg gate_score 0.086 · p50 **0.002** · p90 0.285.
- Keep is set by `atlas-scope-gate-v1-e5base` (the per-topic SCOPE gate), NOT the
  v2 reject gate.
- **74 signals score ≥ 0.50 but gate_kept=false; only the single 0.998 signal was
  kept.** → the effective per-topic keep threshold is ≈ **0.99**.
- Global sanity (all topics, 24h): kept_true 2,511 ≈ score≥0.5 2,761 — consistent
  everywhere else. **Topic 4 is an extreme outlier**, as are political topics
  generally (matches the historical "1/1,066" note).

## The rejected band is real coverage (eyeballed)

The 0.35–0.50 band (29 signals, all rejected) is mostly genuine
election-legitimacy news:
- `FBI deploying 260 analysts to Georgia election fraud inquiry` (0.367)
- `WA attorney general leads coalition opposing USPS mail-in ballot rule` (0.469)
- `Congreso notifica al JNE decisión de López Aliaga…` (Peru, 0.451)
- `Supporters of ballot measure to end Idaho's abortion ban turn in 110K signatures` (0.362)
- + Korean / Armenian / Arabic / Russian election coverage (non-Latin, 0.37–0.48).

So the model's SCORES are reasonable (these sit at 0.35–0.5, well above the
random ~0.00 garbage). The **keep DECISION** throws them away.

## Root cause (confirmed, not a bug)

`apply_scope_gate.py`: the gate embeds `"headline | topic_label"` (OpenAI
text-embedding-3-small), scores through logistic weights, and keeps at a
**per-topic threshold calibrated for ≥90% precision** (global fallback for thin
topics). For a HARD topic like election-legitimacy the on/off-topic classes don't
separate cleanly in that embedding, so holding 90% precision forces the threshold
to ≈0.99 → recall collapses to ~0. The gate is doing exactly what it was told;
the *policy* (precision-first, one target, applied to every topic) is the problem.

Two secondary confirmations: (1) HTML-entity encoding is NOT the cause —
`embed_hot_corpus.py:127` unescapes before embedding, so vectors are clean.
(2) Assignment precision is loose (the 1,269 includes real off-topic: economy,
crime), inflating the denominator — so the "1/1,269" *ratio* overstates the gap,
but the absolute recall failure (74 on-topic ≥0.5 dropped) is real.

## Three ways to attack it (weighed)

**1 — Two-tier coverage (verified + extended). RECOMMENDED.**
Keep the ≥90%-precision per-topic threshold as the **verified** set (Paper 1's
number untouched). Emit a SECOND per-topic threshold at a lower precision target
(~70–75%) = **extended coverage**. Serve the country/coverage map from
verified+extended, each labeled with its tier, replacing the "1 verified OR dump
1,269 raw" binary. The gate training already computes the per-topic PR curve, so
adding a second threshold is bounded; `apply_scope_gate` writes a `gate_tier`;
serving reads it.
- Pro: fixes the analyst-facing blocker (a graded, citable coverage map) WITHOUT
  weakening the verified claim or touching the 🔒 precision number; reversible;
  honest by construction (graded labels, no silent promotion).
- Con: the extended tier is ~70–75% precision — must be labeled, never shown as
  verified. Needs a re-emit of thresholds (OpenAI embeds + the gold set) + a
  serving change. Scoped build (good for Codex headless once agreed).

**2 — Improve embedding separation (retrain the gate). The real long fix.**
Better/multilingual embedding or topic-aware features → better PR curve → 90%
precision no longer forces threshold→1 → recall rises at the SAME precision. Also
addresses the cross-lingual under-scoring (English `topic_label` vs non-English
headline).
- Pro: fixes it at the source, lifts every topic, improves the paper honestly.
- Con: heavy program — new embeddings, retrain, re-score the whole corpus, A/B,
  gold-gated. Uncertain on intrinsically-inseparable topics (the #229/#204 recall
  ceiling). Standing engine track, not a session.

**3 — Lower the global precision target to ~75%.** Rejected: moves Paper 1's
headline number and weakens the verified claim everywhere — throws away the
precision that is the whole point of the gate.

## Recommendation

Do **#1 (two-tier)** now — it is the honest way to make the radar trustworthy: it
stops discarding the 0.4–0.9 election coverage, serves it as clearly-labeled
extended coverage, and leaves the verified bar exactly where Paper 1 needs it.
Queue **#2** as the standing engine program (recall at the source), sequenced with
#229 clustering recall + #204 taxonomy. This matches the alignment doc's #1 lever.

---

## UPDATE — the better gate is already trained (measured, not a retrain)

Pedro chose the retrain track. Measure-first found the retrain is ~80% done:
the Phase-B probe already compared embeddings, and a gate variant on **OpenAI
`text-embedding-3-small` (1536-dim), `2026-05-29-scope-gate-v1.json`, is trained
but NOT deployed**. Production runs the `-e5base` variant (local/free), which
costs a large recall penalty at the same 90% precision:

| topic | e5base (deployed) | v1 OpenAI (on disk) |
|---|---|---|
| global @90% prec | 0.749 (AUC .940) | **0.843 (AUC .956)** |
| agriculture-crop-risk | 0.032 | **0.758** |
| telecom-internet-shutdown | 0.250 | **0.864** |
| oil-gas-supply-risk | 0.033 | **0.333** |
| election-legitimacy-dispute | 0.263 | **0.395** |
| currency-debt-stress | 0.105 | 0.263 |
| sanctions-diplomatic-pressure | 0.417 | 0.278 (worse) |

v1 also has **0 abstain topics** (e5base had 3). e5base was chosen so the gate
scores locally on already-stored e5 vectors ($0); v1 needs an OpenAI embedding of
`"headline | topic_label"` at scoring time (~$0.004/day at current volume —
trivial) but lifts recall dramatically on exactly the hard topics.

**So the retrain is a DEPLOY + RE-SCORE of the existing v1 artifact, not training
from scratch.** Work: (1) point `apply_scope_gate` at `scope-gate-v1.json` +
embed `headline|label` via OpenAI in the classifier cron (needs `OPENAI_API_KEY`);
(2) backfill re-score to refresh served `gate_kept`; (3) verify 90% precision
holds (OOF says it does). election-legitimacy still only reaches 0.395 — it stays
a genuinely hard topic; going further needs more gold positives (only 38) or
topic-aware features, a smaller follow-on. Recommendation: deploy v1 (the measured
+9pp / hard-topic win) now; treat the election-legitimacy residue as a later
gold/feature pass.
