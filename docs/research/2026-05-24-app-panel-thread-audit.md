# App Panel Thread Audit

**Date:** 2026-05-24.
**Purpose:** audit the current app surfaces against the Living Narrative Threads
direction.

## Summary

Atlas already has the product pieces for a thread-native experience, but the
data contracts still expose older concepts: raw GDELT themes, atlas-topic slugs,
country summaries, and signal lists. The next step is not a visual redesign. It
is a data-contract shift: make the existing panels consume thread-shaped
objects that answer the Atlas questions directly.

## Panel Map

| Surface | Current data shape | Current strength | Gap | Thread-native target |
|---|---|---|---|---|
| Brief | `/api/v2/briefing`, top themes, countries, sources, insight | Strong orientation and historical routing | Still theme/country led; does not explicitly explain `why_now` or 10h change | Lead with top living threads, each with `why_now`, `changed_10h`, source mix, evidence count. |
| Globe / Heat | nodes, flows, heat countries, focus summaries | Strong location and intensity lens | Heat is not clearly tied to narrative threads | Selecting a hot geography should show active threads concentrated there. |
| NarrativeThreads | `/api/v2/narratives` returns `theme_code` rows | Good compact thread card UI | Internally still theme-first; label comes from topic/theme mapping | Feed `thread_id`, natural label, subthreads, related threads, and evidence cues. |
| SignalStream | `/api/v2/signals` with filters and heuristics | Best evidence feed | Not ranked by thread relevance or evidence role | Show supporting, contradictory, new, repeated, and source-diverse evidence for selected thread. |
| CountryBrief | `/api/v2/nodes` + `/api/v2/signals`; client counts themes | Useful country context | Computes themes client-side from raw signals; not Atlas-topic/thread aware | Show local manifestation of global threads and local-only emerging threads. |
| ThemeDetail | `/api/v2/theme/{code}`, insight, search, trends/wiki | Useful detail shell | It is topic detail, not thread detail | Evolve to ThreadDetail or support both `theme` and `thread` modes. |
| PublicAttentionPanel | trends/wiki public attention | Useful external attention lane | Public attention can look like a peer to reporting | Link as voice lane or related signal, with provenance. |
| Workspace / Reading Mode | pinned items, graph, dossier export | Strong analyst workflow | Evidence route is implicit | Preserve the path: thread -> evidence -> pin -> dossier. |
| Search | `/api/v2/search/unified` | Good entry point | Search returns mixed object types without thread context | Search should return threads first when query matches an active narrative. |

## Findings

### 1. NarrativeThreads has the right UI intent but the wrong data identity

The component renders rows that feel like threads, but the key is
`theme_code`. Clicks set focus to `theme`, and labels use `getThemeLabel`.
This is acceptable as a compatibility layer, but it is not a living thread
model.

Action: keep the component shell and introduce a thread-shaped response before
attempting visual redesign.

### 2. Brief is the right first surface for thread promotion

Brief already has top themes, top countries, top sources, insight, prefetch,
and historical coverage. A thread summary can be assembled from the same
ingredients. This makes Brief the safest first product surface for living
threads.

Action: add a `top_threads` section in briefing or a separate `/api/v2/threads`
endpoint and let Brief consume it once stable.

### 3. SignalStream should become evidence-aware, not just filtered

The stream currently filters by severity-ish modes and raw attributes. For
threads, it should explain evidence roles:

- new evidence;
- representative evidence;
- repeated/syndicated evidence;
- local-language evidence;
- public/social commentary;
- contradictory or weak evidence.

Action: reuse the stream, but rank within a selected thread by evidence role and
source diversity.

### 4. CountryBrief needs thread-aware aggregation

CountryBrief currently counts raw `themes` from fetched signals. This is useful
for quick context but not rigorous enough for Atlas intelligence.

Action: country focus should read thread-country aggregates from backend, not
client-count raw themes.

### 5. ThemeDetail should become the transitional ThreadDetail shell

ThemeDetail already has timelines, related concepts, public attention, evidence
search, and insight. It is the best place to evolve into a thread detail view
without creating a new UI island.

Action: add a detail adapter later: `theme` mode for old links, `thread` mode
for living thread IDs.

## Current Confidence By Surface

| Surface | Confidence today | Reason |
|---|---|---|
| Storage/routing | High | Hot/cold and processed historical routing are now validated. |
| Brief | Medium-high | Good aggregate surface; needs thread contract. |
| Globe/Heat | Medium-high | Good geographic lens; needs thread linkage. |
| NarrativeThreads | Medium | Correct product intent, theme-first implementation. |
| SignalStream | Medium | Good evidence source, weak relevance model. |
| CountryBrief | Medium-low | Useful but client-side raw-theme aggregation is fragile. |
| ThemeDetail | Medium | Good shell, wrong identity model for future product. |
| Public attention | Medium-low | Valuable as a lane, risky as direct evidence. |

## Recommended Increment Order

1. Add thread contract docs and issue triage.
2. Build read-only thread assembler in backend.
3. Expose beta `/api/v2/threads`.
4. Add `top_threads` to Brief or consume `/api/v2/threads` in Brief.
5. Rewire NarrativeThreads behind a compatibility adapter.
6. Make SignalStream evidence-role aware for selected thread.
7. Convert ThemeDetail into ThreadDetail-compatible shell.

This order keeps the accepted interaction model and upgrades the data beneath
it.
