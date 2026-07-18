# #229 Whitening gold gate — full-run dry-run pair, judged. Verdict: DO-NOT-WIRE

**Date:** 2026-07-18 · **Status:** MEASURED — verdict against the pre-registered
bar from `2026-07-16-whitening-recall-harness.md` §"Gold gate REQUIRED"
**Inputs:** two full `run_scoped_snapshot --dry-run` passes over all 151
eligible countries at the production config (168h, mcs=5, ms=2, min_kept=8):
control `whiten_k=0` (snapshot 2026-07-16T20:10Z) vs whitened `whiten_k=1`
(2026-07-17T23:00Z). Dumps live in the session scratchpad (`goldgate/
{control,whitened}.json`, ~5 MB each, not committed); analysis scripts +
judged sample + summaries are versioned in `snapshots-gold-gate/`.

## 1. Structural comparison (full 151-country run)

| metric | control (k=0) | whitened (k=1) | Δ |
|---|---|---|---|
| kept clusters (write floor ≥8) | 2,268 | 2,706 | **+438 (+19.3%)** |
| ≥12 promotable (volume_min proxy) | 919 | 1,070 | **+151 (+16.4%)** |
| kept signal mass | 29,974 | 34,273 | +14.3% |
| kept size p50 | 10 | 10 | flat |
| max kept cluster (blob check) | **256** (CI syndication) | **102** (ES World-Cup final) | −60% — **no mega-blob; whitening shrinks the largest** |
| mean cohesion (raw space) | 0.9685 | 0.9661 | −0.0024 |
| p10 cohesion | 0.9518 | 0.9481 | −0.0037 |

The harness's 137-blob (US, top-11 sample run) does not reproduce as a
mega-blob in either full run: the biggest US cluster in both arms is the same
junk "Article <UUID>" scrape cluster (kept 63 control / 71 whitened — a junk-
gate item, not a whitening item; next US clusters are ≤50). The full-run blob
story is CI 256 → 102, same direction as the harness's 137 → 44.

**Window-shift confound, measured:** the two dry-runs were snapshotted 27h
apart, so their 168h windows differ at both ends. Marginal clusters (whitened
kept cluster with <50% member overlap vs every control cluster in the same
country) total **1,204**; restricting to shared-window clusters (≥80% of
members already existed at control snapshot time, by signal_id ≤ control max)
leaves **1,061 genuine whitening marginals** (276 of them ≥12) — the recall
lift is real, not a window artifact. 143 are window-new. Reverse direction:
799 control clusters have no ≥50% match in whitened — part window-aging, part
re-partitioning; boundary churn under whitening is substantial (harness risk 1
confirmed at full scale). Countries appearing in only one arm: KP, MG
(control-only) vs NE, ZM (whitened-only) — threshold-edge, 2 each.

## 2. Gold judge (the wire decision)

`snapshots-gold-gate/gold_judge_run.py`: 40 shared-window marginal whitened
clusters (non-Latin monoculture stratum RU/UA/CN/IR/GR oversampled to 50%) +
40 matched control clusters drawn from the same country mix. DeepSeek
(deepseek-chat, temp 0) judged all 80 — "do these ≤12 headlines cover the
same real-world story?" — with a GPT-4o agreement spot-check on a random 20
(100 LLM calls total, ~$0.03). Vendor agreement **19/20 (95%)** — the judge
is stable. Full per-cluster verdicts: `snapshots-gold-gate/gold-judgments.json`.

| arm | n | same-story | precision |
|---|---|---|---|
| **marginal (whitened-new)** | 40 | 23 | **57.5%** |
| — non-Latin stratum | 20 | 13 | **65.0%** |
| — other | 20 | 10 | **50.0%** |
| **control (matched mix)** | 40 | 31 | **77.5%** |
| — non-Latin stratum | 21 | 17 | 81.0% |
| — other | 19 | 14 | 73.7% |

### Against the pre-registered bar

1. **Marginal precision within 10pp of control: FAIL.** 57.5% vs 77.5% =
   **−20.0pp**. (Binomial 95% CI on the marginal ≈ 42–72%; even the CI top
   barely reaches control's point estimate.)
2. **Non-Latin stratum ≥60%: PASS** (65.0%). The harness's RU-grab-bag fear
   is present but not dominant — the monoculture slice actually held up
   *better* than the Latin/"other" slice (50%).
3. **No mega-blob: PASS** (max 102 vs control's 256; p50 flat).

### What the failures actually are (17/40)

- **Topical-bin roundups, not stories** — the dominant class, concentrated in
  the "other" stratum: same-region local-news bins (Rivne oblast traffic+gas+
  evacuation; GB "two taken to hospital" crashes across different roads;
  Danlí court cases + onion protests, HN; Malawi court drama mix), and
  same-template finance items (ETF 13F filings bin, US; Tatarstan inflation +
  gasoline prices, RU). Whitening removes the shared style/language axis, and
  what clusters in the residue is *topic/template* similarity — coherent as a
  category, false as a story.
- **Monoculture residue grab-bag** — the harness's RU class, reproduced once
  at scale: a 66-member RU cluster mixing Arabic-language RT content on war,
  gold, World Cup, floods (cohesion 0.958 in raw space — raw cohesion again
  useless as a purity signal for whitened-formed clusters).
- **Near-misses** — a real core plus a wrong-location tail (Solnechnogorsk
  drone-attack 7/9 + 2 Stavropol; multi-oblast strike roundup). The judge's
  ≥80% bar counts these false; a softer bar would pass some.

Control's own 77.5% is worth registering: the production raw-space path also
serves ~1-in-5 non-story bins by this strict judge — a baseline number the
label court / junk work can use.

## 3. Verdict: DO-NOT-WIRE

`ATLAS_CLUSTER_WHITEN_K` stays **unset (0)** in the nightly runner env. The
recall lift is real (+16% promotable clusters, no blob risk, non-Latin slice
acceptable), but the marginal clusters miss the pre-registered precision bar
by 2× the allowed gap, and the failure mass is exactly the roundup/topical-bin
class the product already fights (#224 roundup detection, junk gate). Wiring
now would grow the substrate by feeding the promotion pipeline ~40%
non-story bins at the margin.

**What would change the verdict** (in order of leverage, for a future pass):
1. **Post-cluster story-coherence guard on whitened-formed marginals** — the
   failures are detectable: same-template/roundup shape (subject-entropy vs
   source-entropy, the #224 classifier) or a cheap LLM court pass (the
   label-court machinery) on marginal clusters only (~40/night). Gate the
   *marginals*, keep the wins.
2. **Judge with a control-matched bar per stratum** — non-Latin already
   passes; a stratified wire (whiten only the monoculture batches where
   raw-space compression is worst) is a smaller, measurable step.
3. Re-run the pair **same-night** (two dry-runs off one snapshot window) to
   kill the 27h confound entirely and re-measure churn cleanly.

**Rollback line (if it is ever wired):** unset `ATLAS_CLUSTER_WHITEN_K` (or
`=0`) in the nightly runner env — next snapshot re-forms clusters raw; no
schema/identity-space change (identity, gate, centroids never left raw e5).
