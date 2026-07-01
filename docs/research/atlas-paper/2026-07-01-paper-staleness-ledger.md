# Paper Staleness Ledger (PR3.0)

Date opened: 2026-07-01 · Owner: engine track · Status: **ACTIVE**
Companion: `docs/specs/2026-07-01-atlas-engine-r3-unification.md` §8 (the PR3
paper-coherence track). Purpose (Pedro, 2026-07-01): the papers drifted from the
engine reality; instead of patching ad-hoc, **track each stale claim as a
closeable row.** Every future engine change that invalidates a paper number
APPENDS a row here. This turns "the papers are disorganized" into a list with a
route.

Seeded from the 2026-07-01 4-agent deep read (paper agent = bucket I4/M5). Cite
each finding by its `F-D-*` id in the R3 §11 ledger.

## How to use
- **On any engine change** that changes a served number (precision, topic count,
  coverage, lifecycle, taxonomy), add a row BEFORE the paper is next touched.
- A row closes when the paper text is edited (or the experiment run) to match
  reality, with the commit noted.
- The **master-plan cross-ref index** is the canonical map; when it lags (it did,
  to 2026-06-26), that is itself a ledger row (PR3-06).

## Ledger

| id | paper · loc | claim as written | current engine reality (2026-07-01) | fix | status |
|---|---|---|---|---|---|
| **PR3-01** | P1 skeleton R1 + master-plan; **precision-to-90** §obj; **session-summary**; **spend-ledger** | FOUR un-reconciled Atlas precision numbers: **41.6%** (N660/3-vendor) · **50.79%** (N189/6-model) · **59.02%** (N61) · learned-gate **90%@64%**; and LLM **78.6%** vs **95.08%** | different N + annotator panels + gold sets; the 78.6 vs 95.08 gap is the label-drift confound P1 itself warns of | **PR3.1:** declare ONE canonical regime (recommend 3-vendor N660 headline), footnote the rest; reconcile the LLM split by naming the gold set each used | OPEN |
| **PR3-02** | P1 skeleton §Benchmark; labeling-guide; methodology-outline validation-map | benchmark = **30 atlas_topics × 4 buckets**, "256 rows / 30 topics" | R3.2 collapses atlas_topics from a served population to an attribute; served pop = **418 stories** | **PR3.2:** re-scope P1 benchmark as measuring the crisis-ANCHOR precision; add open-set category coverage/coherence for emergent extensions | OPEN |
| **PR3-03** | P6 master-plan L448-451; P8 skeleton baseline L26/L115 | topic set **FROZEN**, "last updated 06-29 17:00, 54/68 active >3d stale, lifecycle not retiring" (present tense) | FIXED — former revived mindful/off-peak (P8 Intervention-1); R1 wrote 731 clusters; 418/392 served | **PR3.3:** rewrite frozen claims to past-tense before/after; note R3.7 (B1 retirement) as the lifecycle fix | OPEN |
| **PR3-04** | R3 spec v1 §2 vs CLAUDE.md top | "candidate-v2 NOT wired" ‖ "v2 reject gate LIVE" read as a contradiction | BOTH true: the reject GATE (binary demote) is live; category TYPING is unbuilt — different ops | fixed in R3 v3 §2/§3.1 (reject≠typing); no paper edit, but note in P1 taxonomy section | RESOLVED (spec) |
| **PR3-05** | master-plan L96-104; unified-engine; gdelt-decoupling; R3 §4.1 | `gdelt_hint_ablation.py` is the reproducibility GATE on the 41.6% | **the script does not exist** (referenced in 4 docs, built in 0) | **PR3.4 / §4.1 build-dep:** build `gdelt_hint_ablation.py` before any theme-hint change; it is a required P1 result (recall-delta on theme-drop) | OPEN |
| **PR3-06** | master-plan cross-ref index (L716, "Updated 2026-06-26") | index has no row for unified-engine F0-F3, the A/B, candidate-v2/κ, R0-R3, R3 | the index (the map) lags the engine by ~5 weeks; P1/P8 skeletons were updated past it | **PR3.3:** append F0-F4 / R0-R3 / candidate-v2 / R3 rows; make index-lag a standing ledger trigger | OPEN |
| **PR3-07** | master-plan pub-order L674; P1 close-criteria L179-186 | "Paper 1 closes 4-8 weeks from [2026-05-27] with current data + mig-042" | 5 weeks elapsed; mig-042 lexicon + 30-topic benchmark superseded by the unified engine + candidate-v2; the A/B + κ are now P1's two biggest sections | **PR3.1/PR3.2:** absorb A/B + κ-0.739 + R3.1 precision-lift into the close-criteria | OPEN |
| **PR3-08** | master-plan P8 L594 vs P8 skeleton | coverage "**0.2%**" ‖ "**5.6%** embedded / **2.5%** total" | different denominators (served/ingested vs embedded/embedded), presented without them → looks inconsistent | **PR3.3:** cite the denominator each time; defer to the P8-skeleton precise figures | OPEN |
| **PR3-09** | P1 + P8 validation-plan §Baseline-families | ≥1 EXTERNAL baseline (BERTopic / flat-embedding / TDT / event-graph) REQUIRED for submission | R3's A/B is v1-compat vs unified-v2 — both internal Atlas; no external baseline anywhere; P8 BERTopic "parked" | **PR3.4:** build ≥1 external baseline; the internal A/B alone does not meet the stated bar | OPEN |
| **PR3-10** | P1 methodology-outline §8; master-plan Master-criteria | temporal hold-out week; `role_noise_rate` calibration; anchoring-effect (30 blind vs hinted); Wilson/bootstrap CIs — all "not started" | R3.1/R3.2 measure on 168h windows with no temporal hold-out, no CIs, no anchoring control on the LLM-in-loop typing | **PR3.4:** schedule each as a ledger row with an owner; gate R3.1's precision claim on them | OPEN |
| **PR3-11** | P3 seed "Evidence to collect" | per-component heat ablation + Kendall-tau composite-vs-volume | unbuilt; R3.4a/R3.5 claim "volume≠importance transferred" but schedule no ablation | **PR3.4:** the movement/attention roles are the substrate — run the P3 ablation | OPEN |

## Notes
- PR3.1 + PR3.2 **gate R3.2's headline paper claim** (the "successor to 41.6%" is
  undefined until the regime is canonical + the universe re-scoped).
- Everything here is doc + offline-experiment work — **no serving risk**, runs in
  PARALLEL with the R3 build.
- The anchored-emergent category decision (R3 §3.1, E-R3-h) changes what "taxonomy
  precision" even measures: fixed-taxonomy precision for the crisis anchors,
  open-set coverage/coherence for the emergent extensions. PR3.2 must carry this.
