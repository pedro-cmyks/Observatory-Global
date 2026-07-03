# Does Kalman velocity/surprise LEAD volume? — backtest (2026-07-04)

**Question (#219 gate).** `topic_movement` smooths signal-volume movement with a
tiny Kalman filter (velocity/surprise/trend). The claim that justifies wiring it
into the **front-page thread ordering** is that velocity/surprise is a *leading*
indicator — it predicts where volume goes NEXT. If it only describes the present,
it stays a display-only chip and `changed_10h` remains the ordering source.

**Method.** Read-only REPLAY (`backend/scripts/backtest_movement_leading.py`)
over the durable `emergent_clusters` snapshot series (99 snapshots / 33.2d, ≈8h
cadence). Per topic, walk a sliding point t; at t estimate Kalman
velocity/surprise from the PAST snapshots only (no leakage); target = FUTURE
growth = log-volume over the next H snapshots minus the prior H. Forward
Spearman with a paired-bootstrap 95% CI. All 4 lifecycle states pooled
(candidate/deprecated carry the richest history). n = 786–879 (t) points across
36–52 topics — powered.

**Result — velocity does NOT lead; it mean-reverts.**

| horizon | velocity → future | surprise → future | changed_10h → future | velocity − naive |
|---|---|---|---|---|
| 1 (~8h)  | **−0.477** [−0.53, −0.42] | +0.005 (ns) | −0.390 | **−0.15** [−0.15, −0.02] |
| 2 (~16h) | **−0.347** [−0.41, −0.29] | −0.038 (ns) | +0.025 (ns) | **−0.37** [−0.44, −0.30] |
| 3 (~24h) | **−0.224** [−0.29, −0.15] | −0.089 | +0.038 (ns) | **−0.26** [−0.34, −0.19] |

- **Velocity is negatively, significantly correlated with future growth** at every
  horizon → **mean reversion**: a topic that just accelerated tends to *cool*
  next, not accelerate. Attention spikes exhaust themselves.
- **Surprise ≈ 0** — no forward signal.
- Velocity is **significantly worse than the naive `changed_10h`** at forward
  prediction (diff CI below 0 everywhere).

**Definitional-artifact check (rejected as the sole cause).** `future_growth`
compares the next window to the trailing window, which mechanically depresses the
correlation for any trailing-window signal. But `changed_10h` is built from the
*same* trailing window and comes out ≈0 at h2/h3, while velocity is −0.35/−0.22.
So velocity's anti-prediction is a real property beyond construction, not an
artifact shared by all trailing signals.

**Decision (item 1).** **Do NOT wire `topic_movement` into thread ordering.**
There is no leading signal to exploit, and velocity would over-rank topics about
to cool. Keep `changed_10h` as the ordering movement term (contemporaneous,
honest, not worse). `topic_movement` stays a **display-only** velocity/trend chip
— the smoothed Kalman form of the same lineage, shown but not ranked-on. No
split-brain: ordering reads one number.

**Honest limits / follow-ups.**
- 33d of ~8h snapshots is a modest window; re-run as the series lengthens.
- A cleaner target (future vs a FIXED per-topic baseline, not the trailing
  window) would sharpen the magnitude — the *sign/no-lead* conclusion is already
  robust, so it doesn't change the decision.
- Paper value (P4/P8): on this corpus the Kalman movement is **descriptive, not
  predictive**; attention series are mean-reverting at the snapshot cadence. A
  genuine leading indicator would need a different observable (e.g. cross-source
  attention/coverage ratio, early-forum velocity) — not smoothing of volume.

Artifacts: `2026-07-04-h{1,2,3}.json` (full reports, reproducible; fixed
bootstrap seeds).
