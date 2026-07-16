# Gap-pool relevance audit — how much real signal does the gate hide in the Brief coverage gaps?

**Date:** 2026-07-16 · **Window:** 24h, single snapshot · **Method:** DeepSeek-chat (temp 0) relevance judge over below-gate signals in the two live `coverage_gaps` categories, mirroring Pedro's by-eye pass on the Under-the-Radar raw pool. Read-only; no product code touched. Judge cost ≈ $0.004 (5.2K prompt / 4.5K completion tokens).

## Setup

`GET /api/v2/briefing?hours=24` → `coverage_gaps` (raw≥20, 0 gate-kept):

| category | raw (briefing) | verified | scored |
|---|---|---|---|
| telecom-internet-shutdown | 232 | 0 | 232 |
| mining-royalty-risk | 70 | 0 | 70 |

Samples judged against the candidate-v2 canonical definitions (includes/excludes):
- **Telecom**: theme-endpoint sample (35) + DB sample of the true 232-pool — full census of the 7 rows ≥ extended threshold + 40 random below-threshold rows. Extended threshold (scope_gate_extended_thresholds, served as `extendedThreshold`) = **0.8031**.
- **Mining**: full census, all 70 rows. Extended threshold = **0.4589**.

## Results

### Per-category table

| category | pool | sampled | judge YES | YES+borderline | extended-tier recoverable (rel.) | lang split of relevant |
|---|---|---|---|---|---|---|
| telecom-internet-shutdown | 232 | 47 (7 ext census + 40 random) | **~6%** (est. ~13 items) | ~38% (est. ~87, but see syndication caveat) | ext tier = 7 rows → **2 YES + 1 borderline (43% precision incl. borderline)** | rel: 11 en / 4 non-en · pool: 31 en / 9 non-en |
| mining-royalty-risk | 70 | 70 (census) | **4%** (3 items) | 19% (13 items) | ext tier = 1 row → 1 borderline, 0 YES | rel: 8 en / 5 non-en · pool: 44 en / 26 non-en |

### What the judged-YES rows actually are (telecom, all 6 unique across samples)

| gate_score | ≥ extThr? | headline |
|---|---|---|
| 0.983 | ✅ | Telegram's t.me short-link domain inaccessible globally |
| 0.845 | ✅ | Nowe ograniczenia na Krymie: 16 godzin dziennie bez sieci komórkowej (Crimea, 16h/day mobile shutdown) |
| 0.666 | ❌ | [ar] Sudan NIC statement: t.me links down, Telegram app working (Arabic, state-source) |
| 0.480 | ❌ | Total Blackout in Kerch After Ukrainian Strikes |
| 0.074 | ❌ | US Treasury sanctions a VPN provider and its administrator for the first time |

Mining judged-YES (3): polluted Lyon County copper-mine land protest (0.005), Ghana unclaimed excavators / illegal-mining crackdown (0.0), Yemen landmine casualties (0.009 — judge stretch, arguably a NO). All far below even the 0.4589 extended threshold.

### Lever quantification

**(a) Extended tier (~75% bootstrap-precision thresholds):**
- Telecom: recovers **7 receipts of which ~2-3 are genuinely relevant** — and they are the two *most newsworthy* items in the entire pool (Crimea shutdown, Telegram global block). Precision of the recovered set ≈ 29% strict / 43% incl. borderline — well below the advertised ~75%, because gap categories are by construction the junk-heavy hard ones.
- Mining: recovers **1 receipt, borderline** (EU sanctions on Sudan gold trade, 0.905).
- **Recall against real signal: only 2 of 6 judged-YES telecom rows (33%) and 0 of 3 mining rows clear the extended threshold.** The gate scores genuinely relevant items *low* in these categories (VPN sanctions 0.074, Kerch blackout 0.48, Arabic Telegram confirmation 0.666).

**(b) Language mix:** no strong language skew in this window. Non-English is roughly proportional among relevant vs pool (telecom rel 27% non-en vs pool 23%; mining rel 38% vs pool 37%). Notable single case: the *only* primary-source confirmation of the Telegram block (Sudan NIC, Arabic) scores 0.666 — real, non-English, missed by both tiers. Small-n; not evidence of systematic language bias here (contrast the 2026-06 CO 0/44 Spanish case).

**(c) Semantic similarity of relevant rows to category:** **not measured** — no trivially accessible embedding path from this session (gate scores already ARE the OpenAI-space similarity proxy); skipped per no-heroics rule.

### Count-semantics finding (side catch)

Briefing `coverage_gaps.raw_signals=232` (assignments by `assigned_at`, 24h) vs theme detail `rawTotal=35` for the same slug/window — the gap box and the click-through disagree by 6.6× (#214 class, different windowing). Also **syndication inflates raw**: 8 of the 40 random telecom rows are one story (UK teen social-media curfew proposal, judged borderline — a proposal, not a shutdown); 232 assignments = 216 distinct headlines but far fewer distinct *stories*.

## The honest read

**This window's gap box is hiding mostly junk, not mostly signal — the CO-election case (0/44 kept, all 44 relevant) is not the general regime.** Strict relevance is 4-6%; the yes+borderline 38% telecom figure is inflated by one syndicated policy story. The dominant pool contents are category force-fits: telecom-industry business news (5G rollouts, OnePlus restructuring) and mining-stock/ETF trades — exactly the OUT_OF_SCOPE class the taxonomy revision measured at 46%.

**BUT the gate does hide the best 2-5 items per category, and Pedro's by-eye impression was right about those**: the Crimea 16h/day mobile shutdown and the global Telegram block are textbook category hits sitting at 0 verified. A gap box that says "232 raw · 0 verified" and shows nothing buries them identically with the junk.

## Caveats

- Single 24h window, 2 categories — gap composition varies (CO election was ~100% relevant); re-run before generalizing.
- LLM judge, single vendor, headline-only: fallible on borderline calls (Yemen landmine as mining = stretch; "The Day WhatsApp Goes Dark" could be either way). No human gold, no κ.
- Telecom below-threshold estimate rests on n=40 random of 225 (±~7pp at 95% for the yes-rate).
- The extended-tier precision here (29-43%) is measured on *gap* categories only — the tier's ~75% bootstrap calibration is over all topics and is not contradicted by this hard-slice number.

## Ranked recommendation

1. **Wire top-K extended-tier receipts into the gap box** (`briefing.coverage_gaps` → attach up to 3 signals with `gate_score ≥ extended_threshold`, labeled **UNVERIFIED · extended (~75% model)**, ordered by score). Cheapest lever; the thresholds file and per-signal scores already exist in the serving path (theme detail computes exactly this). Expected recovery **in this window: 2-3 genuinely-relevant receipts for telecom, 1 borderline for mining** — it converts the dead-end "0 verified" row into clickable evidence and would have surfaced the Crimea + Telegram stories. Keep K small (≤3): measured precision on gap slices is ~29-43%, so more rows = more visible junk.
2. **Don't sell the extended tier as the recall fix — it recovers only ~⅓ of the real signal.** Most judged-relevant rows score far below even the extended threshold (0.0-0.67). The real lever for gap categories is per-topic gate recall: gold-growth labeling on the gapped topics specifically (the nightly accumulator already exists) or the semantic lane, both out of scope here.
3. **Fix gap-box count honesty**: (a) reconcile `raw_signals` (assignment-window) with theme-detail `rawTotal` (6.6× apart for the same click); (b) consider distinct-headline or story-level counts — syndication makes "232 raw" overstate the underlying attention by a lot.

## Artifacts

- Judgments: session scratchpad `gap_judgments.json`, `telecom_extra_judged.json` (ephemeral); reproduce via one DeepSeek batch per 25 headlines against `GET /api/v2/theme/<slug>?hours=24` `signals[]` + the `signal_topic_assignments` 24h pool.
- Extended thresholds read from prod serving (`extendedThreshold` field), matching `backend/app/data/scope_gate_extended_thresholds.json`.
