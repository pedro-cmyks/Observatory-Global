# NER Throughput Measurement — Model Residency vs Batched Inference

**Date:** 2026-07-13

**Issue:** #253
**Status:** model residency rejected; batched token classification measured and
activated on the single M1 worker.

## Finding

The proposed first lever in #253 was based on the belief that multilingual
model loading consumed about 140 seconds per cycle. Fresh timestamps from the
single M1 worker do not support that diagnosis:

| Phase | Representative load/dispatch | Representative inference |
|---|---:|---:|
| XLM sentiment | about 6 seconds | 203–474 seconds |
| Davlan multilingual NER | about 3 seconds | 1,005–1,027 seconds |
| multilingual framing | about 8 seconds | 159–295 seconds |
| complete cycle | — | 1,576–1,686 seconds |

Loading is under 2% of the observed complete-cycle runtime. Retaining all phase
models would therefore buy little throughput while keeping multiple large
models resident on an 8 GB M1 already operating with substantial compressed
memory. The attempted resident-cache change was removed before deployment.

## Root cause and replacement

The multilingual Hugging Face NER path invoked the token-classification
pipeline once per headline. The replacement groups headlines by the model they
actually require (Davlan or the Cyrillic WikiNEuRal route) and submits list
input with a configurable conservative batch size of eight. English spaCy and
unsupported-language fallbacks remain unchanged.

Safety properties:

- no model is retained between phases or cycles;
- Cyrillic and Davlan routes remain separate;
- result order is reconciled back to signal IDs;
- a batch exception or length mismatch falls back to the proven per-headline
  path;
- Fly and local workers share the same default contract;
- no LLM call, classification rule or database schema changes.

## Controlled operational receipt

The pre-change worker completed its last clean 300-row NER phase in about 874
seconds inside a 1,562.3-second full cycle.

Two normal write-enabled NER phases were then run with the stable M1 runtime:

| Batch | Wall time | Phase rate | Max RSS | Peak footprint | Swaps |
|---:|---:|---:|---:|---:|---:|
| 300 | 67.90 s | 15,906 rows/hour | 944 MB | 893 MB | 0 |
| 1,200 | 166.29 s | 25,978 rows/hour | 970 MB | 1.16 GB | 0 |

The 300-row comparison is approximately 12.9× faster than the immediately
preceding per-headline phase. The larger batch improves model amortization
again without a meaningful RSS increase.

The first autonomous run then exposed a distribution/runtime caveat that the
two initial controlled samples missed. With batch size eight it did write 1,200
NER rows, but the complete cycle took 1,183.8 seconds. The NER phase alone ran
from the 10:18:10 sentiment receipt to 10:31:34, so the optimistic full-cycle
projection below did not hold under that real cycle.

A second controlled run used the next live priority batch, internal route
telemetry and batch size 16:

| Rows | spaCy | primary HF | Cyrillic HF | NER duration | Max RSS | Peak footprint | Swaps |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,200 | 204 | 953 | 43 | 160.82 s | 1.07 GB | 1.54 GB | 0 |

That batch is deliberately representative of the expensive path: 996/1,200
rows used a transformer route and both multilingual models were loaded. The M1
runner therefore keeps the base sentiment/framing limit at 300, sets an
independent NER budget of 1,200 and now uses batch size 16. The library/Fly
default remains eight. `run_nlp_enrichment` returns actual per-phase write
counts, so the worker checkpoint records 1,200 rather than claiming its 300-row
base request.

Replacing the 874-second NER segment in the observed 1,562.3-second cycle with
the representative 160.82-second/1,200-row segment projects about 5,090 NER
rows/hour for the complete three-phase loop. The current 116,355-row hot window
averages about 4,848 rows/hour, so the batch-16 configuration can mathematically
match inflow on one worker. This remains a projection until the restarted
autonomous worker completes the same configuration and the daily average
confirms it.

The restarted autonomous worker then passed that gate. Its batch-16 NER phase
wrote 1,200 rows in 131.20 seconds (`750` spaCy, `450` primary HF, `0`
Cyrillic) and the complete sentiment + NER + framing cycle finished in 266.4
seconds with no error. That is about 16,216 NER rows/hour at the complete-cycle
cadence, 3.3 times the observed 4,848-row/hour inflow. Across the validation
window, a directly repeated 24-hour backlog query moved from 86,307 to 85,455
unprocessed rows despite continuing ingestion.

## Remaining acceptance

The throughput lever is operationally accepted. Keep #253 open for a daily
trend receipt and its explicitly bundled small residues (UK/BG feed checks,
post-retrain role-noise recheck and temporal holdout), not because the current
M1 throughput remains blocked. The batch-eight autonomous receipt prevents a
false historical claim; the passing batch-16 cycle is the current runtime
truth.
