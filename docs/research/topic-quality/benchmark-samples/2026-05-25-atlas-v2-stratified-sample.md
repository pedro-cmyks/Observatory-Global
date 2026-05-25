# Atlas V2 Stratified Sample

Date: 2026-05-25  
Schema: `atlas-topic-benchmark-v2`  
Output:
`docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl`

## Purpose

This is the first Phase 1 validation sample for the Atlas Narrative Intelligence
paper track. It is designed for semantic/evidence-role labeling, not only
topic-correctness labeling.

Use the labeling guide:

```text
docs/research/atlas-paper/2026-05-25-atlas-v2-labeling-guide.md
```

## Generation Command

The sample was generated read-only from production assignments:

```bash
DATABASE_URL="$(fly ssh console -a atlas-api-pedro --pty=false -C 'printenv DATABASE_URL' 2>/dev/null | tail -n 1 | tr -d '\r')" \
backend/.venv/bin/python backend/scripts/topic_benchmark_harness.py sample \
  --hours 24 \
  --per-bucket 4 \
  --output docs/research/topic-quality/benchmark-samples/2026-05-25-atlas-v2-stratified-sample.jsonl
```

## Summary

| Metric | Value |
|---|---:|
| Rows | 256 |
| Active topics represented | 30 |
| Time window | 24h |
| Max per topic/bucket | 4 |

Bucket distribution:

| Bucket | Rows |
|---|---:|
| `lex_high_conf` | 65 |
| `lex_low_conf` | 116 |
| `theme_high_conf` | 7 |
| `theme_low_conf` | 68 |

Source family distribution:

| Source family | Rows |
|---|---:|
| `gdelt` | 252 |
| `independent` | 4 |

Top source languages:

| Source language | Rows |
|---|---:|
| `en` | 179 |
| `xx` | 77 |

Top countries:

| Country | Rows |
|---|---:|
| `IN` | 32 |
| `US` | 25 |
| `GB` | 20 |
| `CN` | 16 |
| `ID` | 12 |
| `IL` | 11 |
| `NG` | 9 |
| `AU` | 9 |
| `IT` | 8 |
| `ES` | 6 |

## Notes

- The sample covers all 30 active Atlas topics.
- The sample is still dominated by GDELT and English/`xx` language rows. This is
  useful for the first validation pass because it tests the current production
  assignment layer, but later paper-grade samples should intentionally broaden
  provider and language coverage.
- `theme_high_conf` is small because most current high-confidence assignments
  are lex-supported. This is a useful signal for baseline design: theme-only
  confidence is limited after the precision-first migrations.
- The sample is unlabeled. It should be labeled with `gold_scope`,
  `gold_evidence_role`, parent/child candidates, and supported Atlas questions
  before being used for answerability metrics.
