# MVP Thread Volume And Issue Sprint — Design

**Date:** 2026-06-04  
**Status:** Draft for review  
**Branch:** `v3-intel-layer`  
**Track:** MVP launch sprint, narrative coverage, issue cleanup  

## Context

Atlas is preparing for an MVP deployment next week. The paper track remains
valuable, but the immediate operating priority is product readiness: visible
Narrative Threads must feel coherent, sufficiently populated, and inspectable,
and the GitHub issue backlog must stop carrying stale or superseded work.

The current product symptom is coverage loss. In one live 24h window Atlas has
about 200k signals across about 160 countries, but the largest visible dynamic
thread has only hundreds of signals. The visible threads are often high quality,
but the product is likely discarding or hiding too much useful information before
it reaches the user-facing Narrative Thread layer.

GDELT themes are already present before Atlas processing as `signals_v2.themes`.
Historically Atlas has treated GDELT taxonomy as unreliable for final product
truth. That guardrail remains correct. The new decision is narrower: use GDELT
themes as a weak, measurable support signal for candidate recall and thread
diagnostics, not as the final classifier or a proof of significance.

Related docs: [[2026-05-25-atlas-narrative-intelligence-framework]],
[[2026-06-03-research-model-product-roadmap]],
[[2026-05-25-production-cycle-and-backlog]],
[[2026-06-04-thread-intelligence-packet-design]].

## Decision

For the MVP sprint, prioritize narrative coverage and issue cleanup in this
order:

1. Build a read-only GDELT weak-support audit for dynamic Narrative Threads.
2. Run a small recall pilot to test whether GDELT weak support can recover more
   thread volume without unacceptable noise.
3. Update the thread/detail UI contracts only where the product currently
   contradicts the data.
4. Re-triage and close/update open GitHub issues after the thread-volume path is
   measured.

Paper 1 and broader validation work move to "active refinement" during this
sprint. They should not block MVP work unless a product decision would make an
unsupported methodological claim.

## GDELT Role

GDELT themes are not a judge. They are a weak prior:

- `weak_support`: GDELT themes are semantically compatible with the thread.
- `weak_contradiction`: GDELT themes are incompatible or dominated by irrelevant
  domains.
- `theme_entropy`: GDELT themes are scattered across many unrelated categories,
  suggesting the thread is mixed or over-broad.
- `semantic_coverage`: a larger candidate pool shares enough compatible GDELT
  evidence to be worth inspecting.

This can help recover volume because GDELT has broad multilingual/global
taxonomy coverage even when Atlas's current precision gates are conservative.
The support signal must remain inspectable: every score should expose the top
GDELT themes and representative examples.

## Bias Guardrail

GDELT has coverage and taxonomy bias, including a Western/English-language and
institutional-media tilt. The sprint should measure that bias instead of hiding
it.

Minimum bias diagnostics:

- support by `source_lang`;
- support by `country_code` / region;
- support by `source_family`;
- support for Western/global-north countries vs global-south countries;
- support concentration in large syndicated sources;
- disagreement examples where local/regional sources contradict the dominant
  GDELT theme pattern.

Promotion rule: GDELT weak support can raise a candidate to "inspect" or
"candidate evidence"; it cannot raise a candidate to "verified evidence" by
itself.

## MVP Workstreams

### 1. GDELT Weak-Support Audit

Create a read-only report/script over active `dynamic_topics`.

For each thread:

- current thread label, id, volume, countries, sources, noise rate;
- top GDELT themes among member/sample signals;
- `weak_support_pct`, `weak_contradiction_pct`, `theme_entropy`;
- source/country/language distribution of support;
- examples: 5 supported, 5 contradicted, 5 ambiguous;
- recommendation: `expand_candidate_pool`, `keep_current`, `split_thread`,
  `label_review`, or `suppress_noise`.

No migration. No automatic product promotion.

### 2. Recall Pilot

Pick 5-10 representative active threads:

- one high-volume global conflict/policy thread;
- one country-heavy regional thread;
- one public-attention-linked thread;
- one source-family/social lane thread;
- one noisy or mixed thread.

For each, compare current visible evidence to a weak-support expanded candidate
set.

Measured outputs:

- added signal count;
- added countries and sources;
- weak-support score distribution;
- manual quick precision over a small sample;
- main noise types;
- whether the added evidence improves one of the seven Atlas questions.

Stop rule: if added volume mainly increases context/noise and does not improve
answerability, do not promote it into the visible thread layer.

### 3. Central Panel Contract

Keep `ThemeDetail` as the canonical central reader for resolvable Narrative
Threads. `ThreadFocusPanel` remains temporary fallback only for unresolved thread
ids.

Needed for MVP:

- dynamic-topic titles must use backend labels, not raw ids;
- country edge/cards must render from the best available country aggregate;
- related GDELT themes must be labeled as GDELT co-occurrence, not source
  categories;
- dynamic-topic drift should be implemented from dynamic-topic membership or
  identity history, not `$theme = ANY(signals_v2.themes)`;
- source lanes should distinguish source family (`social`, `api`, `ngo`, etc.)
  from GDELT theme names such as `MEDIA_SOCIAL`.

### 4. Issue Cleanup

After the weak-support audit and central-panel fixes are defined, re-triage open
issues into:

- `mvp-now`: required for next week's MVP;
- `close-after-verify`: already shipped or superseded, needs comment + smoke;
- `merge-into-umbrella`: duplicate or absorbed by #207/#174;
- `paper/refinement`: useful, but not MVP-blocking;
- `parking`: visual polish or future product bets;
- `blocked`: external credentials/assets.

Likely MVP umbrellas:

- #207 Living Narrative Threads;
- #174 active scope coherence;
- #177 relevance/noise in Signal Stream;
- #146 Narrative Threads explanation, updated to the current living-thread
  model;
- #175 empty states only where the product still lies;
- #193 long-window routing if MVP shows 1w/1m as supported.

Likely parking/refinement:

- #203/#204 model/paper taxonomy work during this sprint;
- #212 projection;
- pure visual polish such as #147/#148/#152 unless it blocks the walkthrough.

Blocked/external:

- #46 ACLED credentials;
- #106 mascot/assets.

## Success Criteria

The MVP sprint succeeds when:

- the top Narrative Threads explain materially more of the 24h signal universe
  without hiding uncertainty;
- each thread exposes why evidence was included, weakly supported, contradicted,
  or excluded;
- GDELT bias is visible in reports, not baked invisibly into scoring;
- `ThemeDetail` is the central reader for threads/themes instead of a duplicate
  panel split;
- open issues are reduced or clearly classified so next work is not buried under
  stale backlog;
- paper-track docs remain accurate but no longer block MVP execution.

## Non-Goals

- Do not treat GDELT themes as validated Atlas topics.
- Do not lower precision gates blindly to increase volume.
- Do not use GDELT support alone to mark evidence as verified.
- Do not add user-facing correction UI in this sprint.
- Do not build persistent graph tables before the weak-support report shows
  where volume can be recovered safely.

## Testing And Verification

Minimum verification for the first implementation plan:

- focused unit tests for GDELT compatibility mapping and entropy/support
  metrics;
- read-only live smoke over active `dynamic_topics`;
- report artifact with before/after candidate counts;
- small manual review sample for added evidence;
- frontend build if any UI labels/contracts change;
- GitHub issue triage log with actions taken and remaining blockers.

## Open Questions For Implementation Plan

1. Where should the first report live: `docs/research/topic-quality/` or
   `docs/research/mvp/`?
2. Should weak-support compatibility start as a hand-written domain map or be
   inferred from current dynamic-topic member themes?
3. What is the minimum manual review sample per pilot thread: 10, 20, or 30
   added signals?

