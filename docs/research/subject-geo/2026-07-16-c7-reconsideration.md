# C7 Reconsideration after the #238 subject-geo fixes — 2026-07-16

Read-only, measure-first re-run of the C7 voice-asymmetry detector
(`backend/scripts/voice_asymmetry_report.py`, `voice-asymmetry-v0`,
unchanged code, same parameters as 2026-07-12: `--hours 168 --limit 100`).
Prior artifact: `docs/research/voice-asymmetry/2026-07-12-c7-pilot.{md,json}`.
Re-run outputs (scratchpad, regenerable):
`c7-rerun-2026-07-16.{md,json}`. No UI, ranking, cron, or DB writes.

## What C7 actually reads (the gap, stated first)

C7 does **not** consume the fixed serving inference
(`subject_geography.infer_receipt_subject_geography`, #238 commit
`0a981e54`). Its subject country is its own path: the biggest member
cluster's `emergent_clusters.top_country_codes[1]` — a coverage proxy
built from `signals_v2.country_code`, i.e. **ingest-time** geo tagging.

Consequence: of the #238 fix pass, only the **ingest-side lexicon
recall** (`ingest_rss.extract_country`: Greek script, UA city/oblast
stems, `UK`, exonyms, RO/CI entries — `1c1b4cb2` 07-13 + `0a981e54`
07-16; plus the earlier title-only fix `261026c1`) reaches C7,
indirectly, as clusters re-form over freshly-tagged signals. The
**person-proxy demotion and the dominance cap never reach C7** — they
live in the serving inference C7 doesn't call. This gap is why the
verdicts below differ per surface.

## Headline before/after

| | 2026-07-12 | 2026-07-16 re-run |
|---|---|---|
| Topics inspected | 100 | 32 |
| Eligible | 49 | 31 |
| Review hits (score ≥ 60) | 18 (16 distinct) | 3 |
| Hit rate among eligible | 36.7% | 9.7% |
| Hits with an obvious proxy geo mismatch (hand inspection) | **~12/16 (75%)** | **1/3 (33%)** |
| Scored topics vs independent DeepSeek judge (overlap) | **5/7 mismatch (71%)** | **2/30 mismatch (6.7%)** |
| `insufficient_attribution` topics | 51 | 1 |

The judge comparison is the strong number: the 2026-07-16 subject-geo
remeasure (`snapshots-2026-07-16-postfix/judgments.json`) judged the
subject countries of 31 threads from their receipts, and 30 of the 31
C7-scored topics in this re-run are those same threads. Joining C7's
proxy against the judge set: **28/30 match, 2 mismatch**. Joining the
*07-12* run's proxies for the same topic ids against the same judge:
**2/7 match, 5/7 mismatch** — dt-320 BG→GR, dt-21 CH→IT, dt-49 AE→IR,
dt-115 PA→ES, dt-66 CA→US all flipped to correct.

Honest caveats on the comparison:
- The substrate shrank (100 → 32 active non-junk dynamic topics with
  recent members), so denominators are not equal; the *rates* and the
  per-topic before/after flips are the evidence, not raw counts.
- Cluster membership rolled with the window; part of the improvement is
  clusters re-forming over signals tagged by the improved
  `extract_country`. That is the fix working as designed (better
  ingest geo → better proxy), but it is indirect, not a C7 code change.
- The judge itself has measured variance (see the post-fix remeasure
  §Judge stability); used here as a reference, not ground truth.

## Hand-inspected examples (receipts read)

**1. dt-457 "Ukraine Conflict Casualties" — hit 83.9, proxy UA, judge UA.
A GENUINE find.** Receipts: Russian-language coverage of the death of the
Zaporizhzhia NPP chief engineer («МИД России выступил с заявлением после
убийства главного инженера ЗАЭС», «Гросси осудил удар ВСУ…»). A
Ukraine-subject story carried ~95% by RU-origin voices (subject voice
5%, dominant origin RU). This is exactly the asymmetry C7 was built to
surface, and the proxy is correct.

**2. dt-90 "Trump FIFA World Cup Scandal" — hit 98.5, proxy IR, judge IR.
Proxy right, topic dirty.** Receipts: Greek-language coverage of
Trump/Iran/Hormuz («Τραμπ: Απειλεί με πλήγματα σε ενεργειακές υποδομές
του Ιράν…») — but mixed with unrelated Greek domestic items (a delivery
rider's fatal crash in Agia Paraskevi, university admission cutoffs, a
waste-tax vote). On 07-12 this same topic carried proxy **RU** (wrong);
now IR (judge-agree). The residual problem is **cluster contamination +
a garbage label (#204)** inflating the "GR covers IR with 0% Iranian
voice" signal — thread coherence, not geo inference.

**3. dt-287 "Southern Europe Wildfires" — hit 64.2, proxy US, judge CA.
The one remaining hit mismatch.** Receipts are Canadian wildfire smoke
degrading US air quality ("Canadian wildfire smoke chokes Toronto,
threatens U.S. cities", "Ohio EPA issues Air Quality Advisory due to
Canadian wildfires"). The label is wrong (#204) and the proxy picks the
covering/impacted side (US) where the judge names the source of the
event (CA). Multi-party stories where coverage concentrates on one side
remain a coverage-proxy failure — same family as the actor-vs-location
weighting gap the remeasure left open.

**4. dt-320 "17-Year-Old British Teen Fall" — proxy GR (07-12: BG),
judge GR. Fixed class.** Greek-script receipts about the Chalkidiki
tragedy were invisible to ingest tagging on 07-12 (proxy landed on BG);
the Greek-script table now tags them → proxy GR, judge-agree. Same
pattern: dt-21 "Cronaca e Incidenti" CH→IT, dt-49 "US Iran Exchange
Strikes" AE→IR.

**5. dt-1206 "Mbappe Double Powers France" — 55.3 (below hit bar),
proxy FR, judge ES.** Receipts: "Spain blank France 2-0 to reach FIFA
World Cup final" ×8. Both countries are participants; proxy picked FR,
judge ES. Mild multi-party ambiguity + stale label; correctly below the
review threshold.

## Are the 07-12 mismatch classes gone?

**The 07-12 class — arbitrary coverage-country served as subject
(Greek heatwave→JP, Canicule en Belgique→PK, Venezuela Earthquake→ES,
Germany Policy→CN, Monaco→MN, Colombia election→PM) — is effectively
gone from this window.** Nothing of that "absurd third country" class
appears in the 31 scored topics; 28/30 judge-match. The eligibility
starvation also healed: `insufficient_attribution` 51→1 (origin/lang
attribution improved with the same ingest hygiene).

**Residual/new failure classes (both pre-existing, now the visible
frontier):**
- **A. Multi-party stories** — proxy names one legitimate party, judge
  the other (dt-287 US/CA, dt-1206 FR/ES). Needs actor-vs-location
  weighting or the serving inference's multi-country verified set.
- **B. Cluster contamination + label rot (#204)** — dt-90's score is
  real but the topic mixes Greek domestic junk; wrong labels (dt-287,
  dt-1206) make review harder. Not a geo problem; C7 inherits it.
- No new geo-inference failure class was observed.

## Verdict

- **(a) Review-only surface: UNBLOCK.** The blocking condition ("obvious
  coverage-proxy geo mismatches") is measurably resolved: hit mismatch
  ~75%→33% (1 of 3, and that one is a defensible multi-party call, not
  an absurdity); scored-population mismatch 71%→6.7% on the judged
  overlap. Every row already serves `subject_geo_is_coverage_proxy` +
  reason codes, and a review surface keeps a human between score and
  claim. Condition: keep the proxy guardrail text and a #204 label
  caveat visible.
- **(b) Ranking: STILL BLOCKED.** Three specific blockers: (1) C7's geo
  is still the cluster coverage proxy — it does not consume the fixed
  `infer_receipt_subject_geography` (no person-proxy discipline, no
  dominance cap, no verified/partial honesty tiers); (2) residual
  class A would silently order threads on a one-sided proxy; (3) the
  substrate is thin (32 topics) → high-variance scores. Unblock path is
  mechanical: swap C7's subject source to the serving inference's
  `verified_subject_countries` (eligibility = status verified), then
  re-measure on a ≥80-topic substrate.
- **(c) Cron: BLOCKED as-is, conditionally fine paired with (a).** A
  nightly read-only artifact write (no DB/UI) is low-risk once the
  review surface exists to consume it; standalone it is compute without
  a consumer. Do not cron anything that feeds ranking until (b)'s swap
  lands.

## Reproduction

```
cd backend && set -a && source /Users/pedro/AtlasLocalWorker/.env && set +a
PYTHONPATH=. .venv/bin/python scripts/voice_asymmetry_report.py \
  --hours 168 --limit 100 --output-json out.json --output-md out.md
```
Judge reference: `docs/research/subject-geo/snapshots-2026-07-16-postfix/judgments.json`
(join on `dynamic-topic-<id>`). Repo state at measurement: `0a981e54` + docs-only dirt.
