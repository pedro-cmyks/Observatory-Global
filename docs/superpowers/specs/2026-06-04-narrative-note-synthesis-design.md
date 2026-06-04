# Narrative Note Synthesis — Design

**Date:** 2026-06-04
**Status:** Draft for review
**Branch:** `v3-intel-layer`
**Track:** Product reading experience / Living Narrative Threads

## Context

F3 shipped the foundation: `signals_v2.snippet` exists, the text-bearing ingests
write it when the source provides body text, `/api/v2/signals` exposes it for the
single-signal detail panel, and thread evidence payloads now carry `snippet` as
available data.

The next product step is not to render raw snippets under every headline. That
adds noise. The next step is to make a thread open like a readable briefing:
what this thread is about, why it is moving now, what evidence supports it, and
how much confidence the reader should place in the current view.

This spec defines the first read-only Narrative Note increment. It avoids LLM
generation for now. The note is extractive and deterministic, built from the
existing thread contract plus evidence headlines/snippets. It should be useful
enough to improve the reading flow while remaining cheap, testable, and safe.

Related context:
- [[2026-06-04-signal-snippet-enrichment-design]] — persisted source snippets.
- [[2026-06-03-research-model-product-roadmap]] — information-disorder reading
  product direction.
- [[2026-05-24-living-narrative-threads]] — Living Narrative Threads contract.
- [[Narrative Intelligence]] — MOC.

## Product goal

When a user opens a thread, the first meaningful content should read like a short
intelligence note, not a metrics dashboard.

The note should answer:

- What is this thread about?
- Why is it moving now?
- Where and through which sources is it concentrated?
- What evidence is supporting the reading?
- What should be treated as limited, noisy, or provisional?

The text can mention metrics, but metrics should serve the prose. Example shape:

> Infrastructure and public-service stories are moving across Indonesia and
> Brazil, with 483 signals and a 25-signal rise in the last 10 hours. The current
> evidence is concentrated in Indonesian local outlets such as `rri.co.id`,
> `bisnis.com`, and `antaranews.com`, so this reads as a regional public-service
> attention cluster rather than a broad global event. Evidence is still headline
> heavy because few post-deploy non-GDELT sources include source body snippets.

## Scope

In scope for the first increment:

- Add a backend service that builds a deterministic `narrative_note` object from
  an existing thread dict and its `evidence_samples`.
- Add `narrative_note` to `/api/v2/threads` list rows and
  `/api/v2/threads/{thread_id}` detail rows.
- Render the note at the top of `ThreadFocusPanel`, before dense metrics and
  evidence lists.
- Keep the existing `why_now`, metrics, evidence samples, and quality fields.
  The note does not replace them; it makes them readable first.
- Include quality language when the evidence is weak, snippet-poor, too
  source-concentrated, or high-noise.

Out of scope for this increment:

- LLM-generated summaries.
- Persistence/caching tables for notes.
- Per-country narrative assembly (F2/F4). This spec creates the note-building
  pattern that country notes will reuse later.
- ThemeDetail note rendering. The backend shape should be reusable there, but
  the first UI integration is ThreadFocusPanel only.
- Full panel redesign (F1) and Narrative Threads graph re-enrichment (F5).

## Data contract

Add a nullable `narrative_note` object to thread responses:

```json
{
  "narrative_note": {
    "lede": "Infrastructure and public-service stories are moving across Indonesia and Brazil.",
    "movement": "The thread is up 25 signals in the last 10 hours across 5 countries.",
    "evidence": "The strongest visible support comes from rri.co.id, bisnis.com, and antaranews.com, with representative headlines about currency pressure, immigration documents, and public-sector operations.",
    "caveat": "Evidence is still headline-heavy because current post-deploy snippets are sparse; treat this as a provisional reading of the cluster.",
    "quality": "provisional",
    "source": "extractive-v1"
  }
}
```

Field rules:

- `lede`: one sentence naming the thread and its concentration. It should not
  overclaim causality.
- `movement`: one sentence using `changed_10h`, `signal_count`, country count,
  and source count when available.
- `evidence`: one sentence naming top sources and 1-3 representative evidence
  themes/headlines. Prefer snippets when present, but fall back to headlines.
- `caveat`: one sentence explaining limitations. It should be present when:
  snippet coverage is low, source count is low, country count is low, quality
  flags show aggregator dominance/unresolved geography/raw entities, or
  `noise_rate` is high.
- `quality`: one of `strong`, `provisional`, or `thin`.
- `source`: fixed string `extractive-v1`.

If the backend cannot build a meaningful note, return `narrative_note: null` and
leave existing UI fallback text in place.

## Backend architecture

Create `backend/app/services/narrative_note.py`.

Responsibilities:

- `build_thread_narrative_note(thread: dict) -> dict | None`.
- Normalize country/source/entity lists from existing thread fields.
- Inspect `evidence_samples` for headlines and snippets.
- Select representative evidence without adding model calls:
  - prefer samples with non-empty `snippet`,
  - diversify by `source`,
  - cap to three samples,
  - fall back to headlines if snippets are absent.
- Generate deterministic, concise prose.
- Assign quality:
  - `strong`: at least 50 signals, at least 3 sources, at least 2 countries, and
    no high-noise/major quality caveat.
  - `provisional`: enough evidence to describe, but one or more caveats.
  - `thin`: fewer than 10 signals or fewer than 2 sources.

Wire the helper in `backend/app/services/thread_intelligence.py` after each
thread dict is assembled. This keeps list and detail contracts consistent across
dynamic-topic, emergent-cluster, and atlas-topic branches.

## Frontend architecture

Modify `frontend-v2/src/components/ThreadFocusPanel.tsx`.

Add `narrative_note?: NarrativeNote | null` to the thread type and render it near
the top of the panel:

- Lede as the main paragraph.
- Movement/evidence/caveat as compact supporting prose.
- Use restrained styling, not a marketing card.
- Keep the existing metrics and evidence sections visible below.

If `narrative_note` is absent, keep the current `why_now` paragraph fallback.

## Error handling

- Missing `evidence_samples` -> return a note only from top-level thread fields
  if signal/source/country counts are sufficient; otherwise return null.
- Missing snippets -> use headlines and include a caveat that evidence is
  headline-heavy.
- High noise or low source diversity -> do not suppress the note; mark it
  `provisional` or `thin` and say why.
- Never call external APIs. The first increment must be deterministic and
  runnable in local tests without credentials.

## Testing

Backend:

- Unit tests for `build_thread_narrative_note`:
  - strong multi-source/multi-country thread returns all four prose fields.
  - snippet-rich evidence is preferred over headline-only evidence.
  - GDELT/headline-only evidence returns a caveat.
  - thin evidence returns `quality="thin"` or null, depending on counts.
- Contract tests:
  - assembled dynamic-topic/emergent/atlas thread dicts include
    `narrative_note` key.

Frontend:

- Component/build guardrail:
  - `ThreadFocusPanel` type accepts `narrative_note`.
  - `npm run build` passes.

Live smoke:

- `/api/v2/threads?hours=24&limit=1` returns `narrative_note`.
- Opening a thread on `localhost:3000/app` shows the note above dense metrics.

## Deployment

No migration is required. Deploy backend first so the new field exists, then
deploy frontend. Older frontend builds ignore the new field; newer frontend
builds fall back when the field is absent.

## Future increments

- Per-country narrative notes (F2/F4) reuse the same service with a
  country-scoped evidence corpus.
- ThemeDetail receives the same note pattern after ThreadFocusPanel is stable.
- LLM synthesis can be evaluated later as `generated-v1`, behind a separate
  spec, using the extractive note as a baseline and guardrail.
