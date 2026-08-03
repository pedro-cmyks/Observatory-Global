# Gold analyst query eval — day 4 (2026-08-03), the ATTRIBUTION run for the honesty collapse

**Run at:** 2026-08-03T13:32:59+00:00 · **Base URL:** `https://atlas-api-pedro.fly.dev` · **Window:** 24h
**Gold set:** `gold-query-set-v1`, sha256 `62ae0df30463ab49…` (identical to all prior runs), 20/20 run ·
**Judge:** deepseek / `deepseek-chat`
**Harness:** `gold-query-eval-v1`, unmodified — same frozen instrument as 07-27, 07-28 and 07-31.
**Raw artifacts:** `2026-08-03-gold-query-eval.{jsonl,md}` (harness-written, same directory).
**Pre-run config verify:** `meta.fetch_mult=2`, `pool_fetched=2×limit` on live `/threads` — M=2 unchanged
since the 07-30 flip. **BUT this is NOT a pure same-config day** (stated up front, per pre-registration
honesty): since day 3 the lifecycle changed serving composition twice — **TF-3b court-gated revival
promotions ON** (revived topics enter as CANDIDATE, promotion requires court `entailed`; 244 promotions over
the weekend measured at **70.5% strict-real** by the gate-(c) census,
`docs/research/recall-229/2026-08-03-tf3b-gate-c-census.md`) and the **same-morning 72-topic demotion
surgery** (the census-failed promoted topics removed from serving ~08:10 local; this run started 08:19).
Attribution for today's numbers is therefore **M=2 + cleaner field**, not M=2 alone.

## Headline

- **Answer rate (roadmap metric): 29% — 4 of 14** real queries scored ≥2 (GQ-02, GQ-08, GQ-12, GQ-13, all
  at level 2). **Best of the series: 14% (07-27) → 7% (07-28) → 21% (07-31) → 29% (08-03).** At n=14 one
  query = ±7pp; band statement is now **7–29%**, with both readings ≥21% coming after the M=2 flip.
- **No level-3 today.** GQ-12 (the metric's only-ever 3, on the SAME identity `dynamic-topic-3805`) came
  back **2**: "single-country coverage and no origin-country data cap at level 2". Same structural facts as
  day 3 (langs=1, `origin_country_available=false`) scored 3 then and 2 now — judge-application variance on
  the level-3 bar, noted in caveats.
- **Honesty rate: 0.40** (floor 0.90) — **4 of the 10 real non-answered items earned honest-floor 1s**
  (GQ-04, GQ-09, GQ-10, GQ-14). Series: **0.17 → 0.23 → 0.09 → 0.40 — the day-3 collapse did NOT repeat;
  today is the best honesty reading of the series.** Verdict section below.
- **Distribution (real arm):** 3 → 0 · 2 → 4 · 1 → 4 · 0 → 6.
- **Conditional answer rate: 31%** over 13 items (not_in_corpus: GQ-09 only — day 3 had flagged GQ-09 AND
  GQ-13; GQ-13's exit from that list is itself a finding, below).
- **Negative controls: 6/6 PASS** (distribution 1 → 2 · 0 → 4, mean 0.33; K1 clear, K2 clear). GQ-16
  (Lesotho) and GQ-19 (oil lead/lag) earned honest-absence 1s.
- **"Informed" analog (v1 nearest rung, NOT comparable to the UI eval's 71.4%):** real items at level ≥1 =
  **8/14 = 57.1%** — also the best of the series (prior: 4/14 on 07-31).

## PERSISTENCE — 4-day per-query level trajectory

| Query | 07-27 | 07-28 | 07-31 | 08-03 |
|---|---|---|---|---|
| **GQ-01** wildfires FR/ES | **2** | **2** | 0 | 0 |
| **GQ-02** Berlin Pride | **2** | 0 | **2** | **2** |
| GQ-03 Ebola DRC | 0 | 0 | 0 | 0 |
| GQ-04 Philippines SONA | 0 | 0 | 0 | 1 |
| GQ-05 Colombia embassies | 0 | 0 | 0 | 0 |
| GQ-06 Iran strikes framing | 0 | 0 | 0 | 0 |
| GQ-07 Hormuz tanker | 0 | 0 | 0 | 0 |
| GQ-08 Indonesia governor | 0 | 0 | **2** | **2** |
| GQ-09 Nicaragua elections | 1 | 0 | 0 | 1 |
| GQ-10 Romania PSD | 0 | 1 | 0 | 1 |
| GQ-11 AJK rigging | 0 | 1 | 0 | 0 |
| GQ-12 Caspian ship strike | 0 | 1 | **3** | **2** |
| GQ-13 Sudan this week | 1 | 0 | 0 | **2** |
| GQ-14 Ebola asymmetry | 0 | 0 | 1 | 1 |

- **Adjacent-day persistence 07-31 → 08-03: 3/3 — the FIRST full hold in the metric's history.** Series:
  07-27→07-28 persisted 1/2 · 07-28→07-31 persisted 0/1 · **07-31→08-03 persisted 3/3** (GQ-02, GQ-08,
  GQ-12 all held; GQ-13 joined). The wholesale answer-set churn that day 3 named as the strongest
  structural finding **stopped on the first day-pair measured entirely under M=2 + TF-3b discipline**.
- **Identity survival is new too:** 4 of the real arm's scored thread identities are the SAME ids as day 3
  (GQ-04 `dt-7801`, GQ-08 `dt-8057`, GQ-11 `dt-8315`, GQ-12 `dt-3805`). Day 3 explicitly recorded that
  every thread id differed from day 2's. Identities survived three nights of lifecycle for the first time
  in the series — consistent with TF-3b's revival discipline, not attributable to it from one pair.
- **GQ-02 (the named instability witness): answered 3 of 4 days** (2 · 0 · 2 · 2). Today's thread is a
  re-founded but re-found identity — `dt-7647` "Berlin Pride Terror Attack" (day 3) → `dt-7711` "Berlin Gay
  Pride Attack" (today), ROR@20 1.0, entailed, 26 outlets, 2 langs. Answer persisted across an identity
  change: answer-persistence and id-persistence are distinct, and today both improved.
- **GQ-01 (the other named witness): broken a second consecutive day — but by a THIRD distinct mode.**
  Days 1–2: answered. Day 3: selector-margin loss to a niche entailed sibling (Tour-de-France). Today the
  selector picked the RIGHT event thread — `dt-8460` "France Spain Wildfire Battle", ROR@20 **1.0**,
  entailed, 30 receipts / 27 outlets — and the judge scored **0**: "Receipts are all English, single
  country code ES; fails multilingual and multi-country origin requirements" (label spans France+Spain,
  receipts are single-country — an unflagged label-vs-receipt-geography defect against the query's own
  multi-country bar). The wildfire answer's failure has now been: absent→selected-wrong→right-thread-but-
  geographically-hollow. The floor probes confirm coverage exists (213–300 rows, tier ok). Severity note:
  with ROR 1.0 and 27 outlets, 0-vs-1(b) here is a defensible-but-harsh judge call; protocol frozen, score
  stands.
- **GQ-13 Sudan: not_in_corpus (day 3) → answered 2 (today).** Day 3 served a Netanyahu–Mamdani grab-bag
  (0, no Sudan receipts) and the probe found 8 rows/1 on-topic. Today a real thread exists — `dt-9000`
  "Sudan War Atrocities", ROR@20 0.778, **confidence=thin + label_status=partial carried visibly**, judge:
  "Thin thread honestly flagged; answers Sudan war this week with caveats" — the exact "usable with its own
  caveats" level-2 mode the rubric wants. Probe now finds 70 rows/24h. Whether coverage arrived or the
  cleaned field surfaced it is not separable from here.

## HONESTY VERDICT — the run's assigned question

**Day 3's 0.09 collapse did NOT reproduce: 0.40 today, the best of the series. On this evidence the
collapse was day noise and/or was counteracted by the field cleanup — it is NOT a stable M=2 effect, and no
counterweight is warranted yet.** The pre-registered fork read: collapsed again ≈0.09 → stable effect;
recovered ≥0.17 → day noise or cleanup. Today cleared the recovery bar by >2×.

What the recovery is made of (per-item decomposition against day 3, same-identity checks in the ledger):

1. **Better adjacency (2 of 4):** GQ-09's miss is now the RIGHT event-neighbourhood (`dt-5758` "Nicaragua
   Electoral Reform", partial label, tight coherence — vs day 3's off-topic 352-receipt Iran blob) and
   GQ-10's is a genuinely neighbouring Romania Fitch thread (vs a Russian-drones story). The judge read
   both as honest 1(b) adjacency, not confabulation.
2. **Atlas self-flag flip (1 of 4):** GQ-04 scored 0→1 on the SAME identity `dt-7801` — its confidence chip
   moved `medium`→`thin` between runs, and the judge's level-1 explicitly cites the thin flag. This is the
   payload flagging its own weakness, the counterweight day 3 said was missing.
3. **Visible failed label (1 of 4):** GQ-14's adjacent Ebola thread carries `label_status=failed` in the
   payload; adjacent-and-flagged → honest floor.

So the recovery is majority *composition* (what got served and what it self-declared), not purely judge
mood. **The confound stays stated:** the field this run measured is M=2 + TF-3b court-gated promotions +
the same-morning 72-topic demotion; a single day cannot allocate credit among them, and single-rater judge
variance (no κ) is a live term in both directions — GQ-12's 3→2 on unchanged structural facts proves the
judge moves ±1 on its own. The day-3 collapse mechanism ("misses became specific-and-confident") is still
visible in residue: GQ-05 (Nicaragua-reform thread served confidently for the Colombia-embassies question),
GQ-03 (historical Ebola death-toll spread presented as live disagreement), GQ-06/GQ-07 (US-centric /
state-media-sourced Iran threads with no counter-voice) all scored 0 as confident wrong-strand answers.
The collapse was real as a *mode*; it is not (yet) a stable *rate* effect.

## ANSWER-SET CHURN — intersection with prior days

| Day | Answered set (≥2) |
|---|---|
| 07-27 | GQ-01, GQ-02 |
| 07-28 | GQ-01 |
| 07-31 | GQ-02, GQ-08, GQ-12 |
| 08-03 | **GQ-02, GQ-08, GQ-12, GQ-13** |

- **08-03 ∩ 07-31 = {GQ-02, GQ-08, GQ-12} — 3 of 3 prior answers retained, plus one new.** First day-pair
  with zero answer loss.
- **Intersection across all 4 days: still ∅** (GQ-01 answered only days 1–2; GQ-02 missed day 2). Union
  across 4 days: 5 of 14 (GQ-01, GQ-02, GQ-08, GQ-12, GQ-13).
- The structural claim therefore updates: churn was total across the M=1→M=2 boundary and the nightly
  re-founding era; on the first stable M=2 + TF-3b pair it dropped to zero. One pair is one pair — day 5
  under the same config is the cheap test of whether answer-persistence has actually become a state.

## Per-query results (from the harness report)

ROR columns are the judge-derived receipt-on-record values from the harness report (pass-1 per-receipt
verdicts, arithmetic in code), matching day 3's table — not the lexical on-topic metric.

| ID | Exp | Score | ROR@20 | ROR@all | Receipts | Outlets | Langs | Rep.head | Rules | Thread | Verdict (abridged) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GQ-01 | SA | 0 | 1.0 | 1.0 | 30 | 27 | 1 | 0.0 | — | France Spain Wildfire Battle | Right event, receipts single-country ES/English; fails the query's multi-country bar. |
| GQ-02 | SA | 2 | 1.0 | 1.0 | 31 | 26 | 2 | 0.065 | — | Berlin Gay Pride Attack | On-topic receipts; accountability strand absent; single-country. |
| GQ-03 | SA | 0 | 1.0 | 1.0 | 43 | 37 | 1 | 0.14 | — | Ebola Death Toll Reaches 600 | Historical death-toll spread presented as live disagreement. |
| GQ-04 | SA | 1 | 0.85 | 0.889 | 27 | 11 | 1 | 0.0 | G2 | Marcos SONA 2026 Coverage | Honest floor: SONA generally, not the corruption strand; thin confidence flagged. |
| GQ-05 | SA | 0 | 0.0 | 0.0 | 20 | 20 | 2 | 0.0 | G3 | Nicaragua Electoral Reform | Wrong country/story for the embassy-closures question. |
| GQ-06 | SA | 0 | 1.0 | 1.0 | 33 | 30 | 1 | 0.091 | — | US-Iran Talks Continue | No framing side-by-side; US-centric only. |
| GQ-07 | SA | 0 | 0.35 | 0.318 | 22 | 15 | 1 | 0.0 | G3 | Iran Stops Hormuz Ships | All receipts trace to Iranian state media; no independent confirmation. |
| GQ-08 | SA | 2 | 1.0 | 1.0 | 11 | 10 | 1 | 0.0 | — | Indonesia Central Bank Governor Resigns | Directly answers exit + rupiah implications; 1 country blocks level 3. |
| GQ-09 | SA | 1 | 0.95 | 0.95 | 20 | 20 | 2 | 0.0 | — | Nicaragua Electoral Reform | Rich foreign coverage, zero domestic Nicaraguan press; measured silence omitted. |
| GQ-10 | SA | 1 | 0.0 | 0.0 | 24 | 17 | 2 | 0.042 | G3 | Fitch Maintains Romania Rating | Adjacent, honestly labelled; not the PSD lawsuit. |
| GQ-11 | ST | 0 | 0.3 | 0.391 | 23 | 10 | 1 | 0.0 | G2,G3 | AJK Elections 2026 | Second-phase-heavy receipts; ROR@20 0.3 fails; no floor. |
| GQ-12 | ST | 2 | 1.0 | 1.0 | 30 | 24 | 1 | 0.0 | — | Iran Ukraine Caspian Attack | Direct answer; single-country coverage caps at 2 (was 3 on day 3). |
| GQ-13 | ST | 2 | 0.778 | 0.778 | 18 | 17 | 1 | 0.167 | — | Sudan War Atrocities | Thin thread honestly flagged; answers the week with caveats. |
| GQ-14 | ST | 1 | 1.0 | 1.0 | 43 | 37 | 1 | 0.14 | — | Ebola Death Toll Reaches 600 | Adjacent to the asymmetry question; honest. |
| GQ-15 | NC | 0 | 0.0 | 0.0 | 24 | 24 | 1 | **0.958** | G2,G3 | Ngaro Track Hike | Confident off-topic hiking thread. PASS (≤1). |
| GQ-16 | NC | 1 | 0.0 | 0.0 | 39 | 30 | 1 | 0.0 | G3 | Planning Applications Refused | Honest absence: zero Lesotho signals. PASS. |
| GQ-17 | NC | 0 | 0.0 | 0.0 | 43 | 38 | 1 | 0.163 | G3 | Seattle Police Chief Resigns | Different story served for Mongolia question. PASS (≤1). |
| GQ-18 | NC | 0 | 1.0 | 1.0 | 31 | 26 | 2 | 0.065 | — | Berlin Gay Pride Attack | First-outlet question answered with no outlet named. PASS (≤1). |
| GQ-19 | NC | 1 | 1.0 | 1.0 | 22 | 15 | 1 | 0.0 | — | Iran Stops Hormuz Ships | Honest floor: declines lead/lag + price forecast. PASS. |
| GQ-20 | NC | 0 | 0.0 | 0.0 | 15 | 14 | 1 | 0.067 | G3 | Iran Warns Ukraine | Ship-attack thread for a public-opinion question. PASS (≤1). |

Per-query `label_status` (from payload metadata, cited in the composition notes): entailed on 15 of 20
scored items; partial on GQ-05/09/13; `failed` on GQ-03/14 (both the same thread, dt-2344).

Pair gaps: GQ-18→GQ-02 **+2**, GQ-19→GQ-08 **+1**, GQ-17→GQ-04 **+1**, GQ-15/16/20 0. Three twins now beat
their controls (day 3: two) — the pair design keeps gaining signal as the real arm answers.

## Composition notes (vs day 3)

1. **Label-court composition held:** 15 of 20 scored items carry `label_status=entailed`, 3 partial (all
   honestly read as partial by the judge), 2 queries share the one `failed`-labelled thread (dt-2344 Ebola)
   — and that failed status is VISIBLE and contributed a level-1. No unchecked-label scored thread.
2. **A new residual-miss class: voice/strand failures on fully on-topic receipts.** GQ-01 and GQ-06 fail at
   ROR@20 = 1.0 and GQ-09 at 0.95 — the receipts ARE the story — on missing counter-voices (Iranian/Gulf
   framing, domestic Nicaraguan press) or the wrong receipt geography (GQ-01's France+Spain label over
   all-ES receipts). GQ-07 is the state-media variant (ROR 0.35, all receipts trace to Iranian state
   media). The failure mode has moved another level down from day 3: from *right event, wrong strand*
   toward *right story, hollow voice mix* — the #235 domestic-voice program and the origin-country gap
   (`origin_country_available=false` on every thread) showing up in the primary metric.
3. **`semantic_members_ann_timeout` fired on 3 scored payloads** (GQ-05/09/10 metadata) — the C5 depth-80
   p95 watch item from the fetch-mult postverify is visible at the eval surface; did not change any verdict.
4. **GQ-15's control thread is a 0.958 repeated-headline syndication blob** (24 outlets, one headline).
   Control passes regardless; the blob class still serves.

## Honest caveats

- **Attribution is confounded by design and stated as such:** M=2 (unchanged), TF-3b court-gated
  promotions (weekend, 244 topics at 70.5% strict-real), and the 72-topic demotion surgery (same morning,
  pre-run) all separate this field from day 3's. This run measures the ensemble, not M=2 alone. What day 4
  DOES establish cleanly: the honesty collapse is not an invariant of M=2, and answer persistence can be
  3/3 under the current ensemble.
- **Judge variance is a measured term now:** GQ-12 scored 3 (day 3) and 2 (today) on the same identity with
  the same structural profile; GQ-01's 0 today is a harsh call on ROR-1.0 receipts. Single rater, κ not
  computed (K4 caveat attached as required). K3 time-shifted placebo still not run.
- **Honesty 0.40 remains a lower bound** (v1 judge conflates 1(b) with 0 in the other direction too —
  unchanged mid-series by design).
- GQ-09 `not_in_corpus` still needs hand confirmation (known generic-token false-positive mode in the
  probe) before any #235 filing.
- Verbatim-question probe returned 0 on 20/20 (substring matcher, known defect, unchanged). G5-class
  silent-empty not re-counted here; floors behaved on every real item that needed one.
- The harness header still prints "First computation ever." — hardcoded, false since 07-28, cosmetic,
  deliberately unfixed mid-series.
- Run executed foreground-equivalent (single process, watched to exit 0), 20/20 queries, `errors: []`,
  judge chain Anthropic→DeepSeek fell to DeepSeek as expected (Anthropic dry; one attempt-1 retry, no
  exhaustion).

## Where this leaves the metric

Four days: answer rate 14% → 7% → 21% → **29%**, honesty 0.17 → 0.23 → 0.09 → **0.40**, and the first
day-pair with **zero answer churn** (3/3 held + 1 gained) alongside the first scored-identity survival
across nights. The two named witnesses split: GQ-02 is now a stable answer (3 of 4 days); GQ-01 is a stable
*miss* whose mechanism keeps changing and now points at voice-mix hollowness rather than retrieval. The
day-3 honesty-collapse question is answered for now — not a stable M=2 effect — but the attribution among
M=2, TF-3b, and the demotion surgery needs exactly what the churn finding needed: **day 5 under the same
ensemble.** If persistence holds again, the "answers are a state, not a lottery" claim becomes the series'
first positive structural claim.
