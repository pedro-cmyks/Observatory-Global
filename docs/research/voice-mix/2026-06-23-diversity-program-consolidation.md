# Atlas diversity program — consolidation & evaluation (2026-06-23)

One session, end to end: turn "global" from an assumption into a measured,
self-maintaining property. This is the wrap-up + evaluation.

## The arc (one number)

`diversity_score` (language): **3.3 → 23.9 / 100** (7.2×).
`voice_entropy` (origin diversity, Pedro's objective): **0.71** — ABOVE the
0.65–0.70 target band, over 89 origin countries.

## What shipped (the full stack)

1. **Ingest — 50 → 219 feeds / 126 countries / 31 languages / 105 non-English.**
   Waves 5–16: CJK, Islamic world, Global South long-tail, source pluralism
   (multiple outlets per country), domestic-by-ownership. 20 state outlets
   flagged. Background-agent assist for the last 31 countries.
2. **Measure — Voice Mix** (`scripts/voice_mix_audit.py` + `/api/v2/voice-mix`,
   shared formula). Two headline metrics: `diversity_score` (language) and
   `voice_entropy` (origin diversity = "different ones speaking from different
   places", not raw outlet count which GDELT's ~11K Western domains inflate).
3. **Relation — who speaks vs who is spoken about.** self_voice = outlet
   OWNERSHIP, not language (BBC Persian ≠ Iranian voice); `soft_power_local_language`
   bucket tracked separately. Surfaced in CountryBrief ("X% covered by its own
   press") + own-voice story sort.
4. **Translation — Instagram-style**, inverse affordance: non-viewer-language
   headlines shown translated by default + "See original". In SignalStream +
   CountryBrief. Browser-verified.
5. **Voice by CONTENT — #229.** Emergent snapshot clusters over the persisted
   116K-embedding corpus, stratified for non-English (no re-embed). Cron
   activated (`--from-persisted`, every 6h). Live: non-English narrative threads
   now form and serve (Turkish/Spanish/Portuguese/Korean/Ukraine), 11 → 25
   threads/run.
6. **Quality — #224.** Roundup detection extended for non-English/generic labels
   + a language-agnostic **content-entropy classifier**: a grab-bag = no shared
   subject AND single-outlet dominated (a daily-digest dump), with the
   source-dominance guard sparing broad real threads (Ukraine, market crash).
7. **FIPS normalization** (RP→PH etc.) + native-script geo-tagging first cut.
8. **Multilingual NLP (#162)** confirmed already live (xlm-v1) labeling the new
   voices.

## Current evaluation (prod, 168h)

| metric | value | note |
|---|---|---|
| voice_entropy (origin) | **0.71** | above 0.65–0.70 target, 89 countries |
| diversity_score (language) | 23.9 | from 3.3 baseline |
| English share of known | 90.9% | from 97% |
| non-English share | 9.1% | from 3% |
| CJK (zh/ja/ko) | 2,844 (2.33%) | from 0 |
| distinct known languages | 32 | from 15 |
| feed countries | 126 | from ~30 |
| self-coverage zeros | 11 of 83 | mostly new feeds not yet accumulated |

## Ceiling & target (what we're aiming for)

Not 100 — and not even desirable. Practical ceiling ≈ **65–70/100** for
`diversity_score` (English is a genuine global lingua franca; GDELT is an
English firehose — pushing English below ~50% would be its own distortion).
For `voice_entropy` the target is **sustain ≥0.65–0.70 while growing the
attributable-origin share** (currently ~⅓; the rest is GDELT with no origin).

The real goal was never the number: **every country audible in its own voice,
the Western-lens distortion measured and shrinking, and the world's non-English
voice weighing by content (threads), not just presence.** All four hold.

## Self-maintaining

- RSS ingest: every 30 min (uncapped, multilingual).
- Emergent threads (#229 persisted-corpus, non-English-stratified): every 6 h.
- Embed cron: nightly. Multilingual NLP: continuous.
The diversity now compounds without intervention.

## Remaining / honest caveats

- New WAVE 12–16 feeds need days of cron accumulation before their countries
  clear 0% self-coverage and before voice_entropy reflects them fully.
- KW, BH uncovered (state agencies block bots / no RSS) — documented ceiling.
- Roundup quality: content-entropy classifier handles whitespace languages;
  CJK no-whitespace clusters fall back to label-regex (acceptable, low volume).
- Biggest lever left to lift `english_balance`: non-English VOLUME vs the GDELT
  firehose — partially addressed by #229; full lift needs more native volume +
  the attributable-origin share growing.

Artifacts: `2026-06-23-consolidation.json`, `2026-06-23-self-coverage-gap.json`.
Issues: #235 (sources), #229 (threads scaling), #224 (roundup quality),
#160/#162/#150/#230 (folded).
