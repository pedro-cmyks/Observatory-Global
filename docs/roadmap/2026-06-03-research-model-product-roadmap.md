# Atlas Research-to-Product Roadmap

**Date:** 2026-06-03  
**Status:** Active roadmap for the current work block  
**Branch:** `v3-intel-layer`

## Core Direction

Atlas exists to help users reason through information disorder by showing how
narratives move, what evidence supports them, which sources amplify them, and
how their shape changes over time.

The product should not only say whether a claim is true or false. Its stronger
role is to expose narrative movement:

- sudden volume changes around a topic or frame;
- source-family and geography shifts;
- emerging child threads under a broader narrative;
- evidence that supports the movement;
- context and noise that should not be treated as verified evidence;
- related threads that explain how the story is mutating.

This makes the research track operational. Each paper should improve the model,
explain why the improvement is justified, and leave behind reproducible evidence
for future decisions.

## Current Position

Paper 1 is not closed as a manuscript. It is closed enough as a measured RQ1
milestone to guide the next implementation decisions.

The current result is:

- Atlas v2 single-layer classifier: `41.6%` precision on the 660-row usable
  consensus-gold benchmark.
- LLM zero-shot baseline: `78.6%`.
- LLM few-shot baseline: `81.1%`.
- 3-vendor annotator consensus: deepseek-chat, gpt-4.1, claude-sonnet-4-6,
  Fleiss kappa `0.625`.
- Main failure modes: `off_topic` and `scope_mismatch`; substring noise is only
  `0.6%` of incorrect rows.

Interpretation:

The old classifier is not failing mainly because of bad keywords. It is failing
because one topic assignment is being asked to represent domain, parent thread,
child thread, entity thread, context, evidence, and noise at the same time.

## Paper 1 Completion Gate

Before treating Paper 1 as closed, finish these research tasks:

1. Convert the current outline into a result-bearing draft skeleton.
2. Update the validation map with the 2026-06-02 RQ1 numbers, replacing older
   N=61 pilot claims as the headline evidence.
3. Add the improvement pathway as a first-class paper contribution:
   - M1 scope gate raises precision on scored rows.
   - M2 evidence-role student separates primary evidence, context, and noise.
   - M3 topic remediation identifies theme-only and dead-topic failure tails.
   - M4 dynamic topics replaces brittle static topic surfacing with
     self-curating narrative identities.
4. Keep local Ollama deprecated unless a materially different hardware/model
   hypothesis is tested.
5. Define the remaining manuscript gaps explicitly:
   - temporal generalization holdout;
   - baseline ablations beyond LLMs;
   - final table/figure set;
   - limitations and threat-to-validity language.

Paper 1 should then become the methodological basis for why Atlas moves from
static topic assignment toward scope gates, evidence roles, and dynamic topics.

## Product Gate After Paper 1

After the Paper 1 documentation pass, the next engineering block is product
verification of the dynamic-topic cutover:

1. Deploy the backend canonical `dynamic_topics` read path with
   `scripts/deploy-fly-api.sh`.
2. Verify Fly `/health`.
3. Smoke Fly endpoints:
   - `/api/v2/threads?hours=24&limit=5`;
   - `/api/v2/briefing?hours=24`;
   - `/api/v2/theme/dynamic-topic-<id>?hours=24`.
4. Browser-smoke the deployed frontend:
   - `/brief`;
   - Watchlist clicks;
   - Narrative Threads;
   - ThreadFocusPanel.
5. Confirm row counts, focus-panel counts, source, evidence samples, and empty
   states agree.
6. Only then call the dynamic-topic product cutover shipped.

## Research Loop

The papers should create a feedback loop:

1. Measure a model decision against a defensible benchmark.
2. Identify the actual failure mode.
3. Improve the model with the smallest justified change.
4. Re-score against the same or stricter benchmark.
5. Promote only model behavior that improves precision, answerability, or
   coverage without hiding uncertainty.
6. Document why the decision was made and where the evidence lives.

This is how Atlas earns trust: each visible product decision should trace back
to a measured model decision, not to intuition or visual preference alone.

## Obsidian Route

Use this route when resuming the current phase:

1. `[[2026-06-03-research-model-product-roadmap]]`
2. `[[2026-05-27-methodology-paper-outline]]`
3. `[[2026-06-03-paper-1-result-skeleton]]`
4. `[[2026-06-02-rq1-improvement-methods]]`
5. `[[2026-06-02-dynamic-topics-shadow-result]]`
6. `[[Narrative Intelligence]]`
7. `[[Validation and Paper Track]]`
8. `[[Frontend Product Surfaces]]`

The roadmap is intentionally between research and production. It tells future
agents why Paper 1, model correction, and browser smoke are one sequence rather
than unrelated tasks.
