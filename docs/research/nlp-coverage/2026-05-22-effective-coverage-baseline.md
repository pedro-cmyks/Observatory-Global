# NLP Effective Coverage Baseline — 2026-05-22

This baseline measures effective NLP coverage in the cells the product
actually serves, not raw row-level transformer ratios. It answers: "of the
country/topic cells we render in briefing/heat/theme/country views, what
fraction qualifies for transformer-sourced sentiment under the fusion rule?"

Fusion rule (`app/services/sentiment_fusion.py`):

> Briefing returns transformer sentiment when bucket `nlp_coverage >= 0.30`;
> otherwise falls back to GDELT V2Tone.

The `nlp_signal_count` column in `country_hourly_v2` and
`theme_country_hourly_v2` counts any row with `nlp_sentiment IS NOT NULL`.
That includes transformer **and** lexicon **and** fast_neutral fallback,
because all three populate `nlp_sentiment`.

## Hot window (24h)

| Surface | Cells | Cells `nlp_coverage >= 0.30` | Pct qualified | Signals served | Signals weighted under NLP |
|---|---:|---:|---:|---:|---:|
| `country_hourly_v2` | 221 | 221 | **100%** | 157,914 | 100% |
| `theme_country_hourly_v2` | 104,295 | 103,256 | **99%** | 738,825 | 99.84% |

Distribution of country cells across coverage buckets: all 221 cells fall in
`80-100%`. There are no cells in `0%` … `30-50%` buckets, so there is no
country surface that silently drops to GDELT V2Tone.

## Historical window (7d, `historical_topic_country_daily`)

| Metric | Value |
|---|---:|
| Daily cells | 10,553 |
| Cells `sentiment_coverage >= 0.30` | 3,883 (36.8%) |
| Signals served | 916,198 |
| Signals weighted under NLP | 312,907 (34.15%) |
| Avg cell coverage | 36.78% |
| Day range | 2026-05-15 .. 2026-05-21 |

Historical coverage is meaningfully lower than hot because the older days
predate the fast-lane lexicon expansion and stratified sampling cycles. The
gap explains why long-window views show more GDELT-sourced sentiment than
hot views.

## Method breakdown of the hot window (raw `signals_v2`, 24h)

| Method | Rows | Share |
|---|---:|---:|
| `lexicon` | 146,591 | 83.7% |
| `fast_neutral` | 20,127 | 11.5% |
| `transformer` | 8,330 | 4.8% |
| `topic_lexicon` | 0 | 0% |
| Any `nlp_sentiment` non-null | 175,048 | 100% |

100% of hot rows have a non-null `nlp_sentiment`. The fusion threshold is
clearing on signal count alone, regardless of method quality.

## What the 4% transformer number actually means

The 4% transformer figure is the share of hot rows refined by the heavy
multilingual transformer pipeline. It does NOT mean the rest of the rows
are unprocessed. The remainder is:

- 83.7% lexicon-sourced sentiment (multilingual keyword/score matching).
- 11.5% `fast_neutral` fallback (`nlp_sentiment = 0.0` when no evidence).

The dilution risk for product-served sentiment is the 11.5% `fast_neutral`
share, not the 96% non-transformer share. Lexicon scores are real signal
and meaningfully better than GDELT V2Tone.

## Implications for next-step issue selection

| Issue | Reduces 11.5% fast_neutral | Raises 4.8% transformer | Notes |
|---|---|---|---|
| #185 corpus-mine lexicon vocab | Yes — converts `fast_neutral` rows to `lexicon` when mined terms hit. | No | Highest ROI for product-cell honesty. Zero new infra. |
| #184 bump `NLP_WORKER_LIMIT` | Partial — more transformer-eaten rows that were lexicon/fast_neutral before. | Yes | Needs DB pressure measurement before bumping. |
| #163 split NLP worker process | Partial — priority queue can target gap countries first. | Yes | Architectural; bigger lift. |
| #171 bulk SQL topic classifier | No — solves topic assignment dilution, not sentiment dilution. | No | Separate quality axis. |

## Reproduction

```bash
DATABASE_URL=... .venv/bin/python -m scripts.nlp_coverage_report \
    --hot-hours 24 --historical-days 7
```

`docs/research/nlp-coverage/2026-05-22-effective-coverage-baseline.json`
holds the raw JSON for this baseline.
