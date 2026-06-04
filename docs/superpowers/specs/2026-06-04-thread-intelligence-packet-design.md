# Thread Intelligence Packet — Design

**Date:** 2026-06-04
**Status:** Shipped, with frontend architecture correction
**Branch:** `v3-intel-layer`
**Track:** Product (narrative unification — F5)

## Context

Threads were wired to dynamic/atlas/emergent sources and got a narrative note
(extractive + DeepSeek) and country-scoped fetch, which fixed the country
dissociation (Colombia now returns country-scoped threads). The remaining gap was
the rich intelligence that still only lived in `ThemeDetail`.

Frontend correction after review: visible product concepts should not diverge
between "theme detail" and "narrative thread detail". A Narrative Thread is the
user-facing theme/thread unit. The canonical shell is therefore the existing
`ThemeDetail` panel, with the thread `narrative_note` embedded at the top when a
thread opened it. `ThreadFocusPanel` remains only as a fallback for thread ids
that cannot yet resolve to a ThemeDetail route, currently `emergent-cluster-*`.

Original gap (ThemeDetail had, ThreadFocusPanel lacked):

- `countryBreakdown` — per-country count + sentiment (country edges).
- `topSources` **with `source_family`** — source lanes (media / social / state).
- `timeline` — hourly count + sentiment.
- `graphSignals` — the signal node set.
- `relatedThemes` / relations.
- public attention (Google Trends + Wikipedia) match.
- a social/Reddit lane.

Key finding: the aggregation already exists. `backend/app/routers/themes.py`
`_dynamic_topic_detail` and `_emergent_cluster_detail` build exactly
`graphSignals / countryBreakdown / topSources / timeline` from a topic/cluster's
sample signals. Thread detail in `thread_intelligence.py` resolves the **same**
`sample_signal_ids`. So unification = extract that aggregation into one shared
builder and have both theme detail and thread detail use it.

This is the "Thread Intelligence Packet": one server-side packet attached to the
thread detail response, shared with `ThemeDetail` aggregation where possible, so
thread-origin details and direct theme details stop drifting.

Related: [[2026-06-04-signal-snippet-enrichment-design]] (snippet now persisted +
in evidence), [[Narrative Intelligence]], [[Frontend Product Surfaces]].

## Scope

In scope (full packet, one pass — user decision):
- A shared `build_thread_packet(signal_rows)` producing `graphSignals`,
  `countryBreakdown`, `topSources` (with `source_family`), `timeline`, `lanes`
  (media / social / state split by family), and `relatedThemes`.
- Extend the thread sample-signals SQL to select `themes` + `source_family`
  (currently missing) so the builder has its inputs.
- Attach `packet` to every thread-detail path (`_fetch_dynamic_thread_detail`,
  `_fetch_emergent_thread_detail`, atlas thread detail) in
  `thread_intelligence.py`.
- Server-side `public_attention` in the packet: best-effort Google Trends +
  Wikipedia match on the thread label/keywords (null on miss).
- Refactor `themes.py` `_dynamic_topic_detail` / `_emergent_cluster_detail` to
  consume the same shared builder (DRY; keeps theme detail and thread packet
  byte-identical and prevents drift).
- `ThreadFocusPanel` initially rendered the packet, but post-review frontend
  routing now sends resolvable Narrative Threads to `ThemeDetail` and embeds the
  narrative note there. The fallback panel remains null-safe for unsupported
  thread ids.

Out of scope:
- The DeepSeek/extractive narrative note (already shipped).
- Per-country narrative assembly over un-topic'd signals (F2/F4, separate).
- Statistical weighting changes — the packet is descriptive, not a metric.

## Architecture

```
thread_id ──► fetch_thread_detail (dispatch by prefix)
                 ├─ atlas        ─┐
                 ├─ emergent     ─┼─► sample signal rows (themes + source_family added)
                 └─ dynamic      ─┘        │
                                           ▼
                              build_thread_packet(rows) ──► packet{
                                  graphSignals, countryBreakdown,
                                  topSources(+family), lanes,
                                  timeline, relatedThemes }
                                           │
                              + public_attention(label) (trends + wiki match)
                                           ▼
                              thread detail response.packet
                                           ▼
                              ThreadFocusPanel renders sections
```

`themes.py` dynamic/emergent detail call the same `build_thread_packet` so the
two surfaces never diverge.

## Data model

No migration. `signals_v2.snippet`, `source_family`, `themes` already exist; the
change is selecting `themes` + `source_family` in the sample-signals SQL.

## Backend

### New module `backend/app/services/thread_packet.py`

`build_thread_packet(rows: list) -> dict`. Each row carries: `country_code`,
`nlp_sentiment`/`sentiment`, `source_name`, `source_family`, `timestamp`,
`themes`, `headline`, `snippet`, `id`. Returns:

- `graphSignals`: list of `{id, headline, country, sentiment, source}`.
- `countryBreakdown`: `[{code, count, sentiment}]` grouped by `country_code`,
  sorted by count desc.
- `topSources`: `[{name, count, sentiment, family}]` grouped by `source_name`,
  carrying `source_family`, sorted by count desc.
- `lanes`: `{media: n, social: n, state: n, other: n}` counts split by
  `source_family` (social = reddit + social families; state = state media;
  media = wire/api/independent; other = rest).
- `timeline`: `[{hour, count, sentiment}]` bucketed by hour, sorted asc.
- `relatedThemes`: `[{theme, count}]` from the unnested `themes` arrays
  (excluding the thread's own topic), top-N by count.

Pure function over rows (no DB), so it is unit-testable and shared.

### SQL change

Extend `_EMERGENT_SAMPLE_SIGNALS_SQL` (and any sibling sample-signal query feeding
thread detail) to also `SELECT themes, source_family`. The atlas thread evidence
query likewise selects `themes, source_family`.

### Thread detail wiring

In `_fetch_dynamic_thread_detail`, `_fetch_emergent_thread_detail`, and the atlas
thread detail builder, after fetching the sample signal rows, set:

```python
detail["packet"] = build_thread_packet(rows)
detail["packet"]["public_attention"] = await _thread_public_attention(conn, label)
```

`_thread_public_attention` reuses the existing trends/wiki match services
(`/api/v2/trends/match`, `/api/v2/wiki/match` logic) keyed on the thread label;
returns `{trends: [...], wiki: [...]}` or `None`. Best-effort, wrapped so a miss
never fails the detail.

### themes.py DRY

`_dynamic_topic_detail` / `_emergent_cluster_detail` replace their inline
aggregation blocks with `build_thread_packet(rows)` and map its keys to the
existing `graphSignals/countryBreakdown/topSources/timeline` response keys so the
`ThemeDetail` contract is unchanged.

## Frontend

`ThreadFocusPanel` consumes `detail.packet`:

- Country edges: render `countryBreakdown` (reuse ThemeDetail's country list /
  bar pattern).
- Source lanes: render `topSources` grouped/colored by `family`, plus the `lanes`
  summary (media / social / state).
- Timeline: render the sentiment timeline chart (ThemeDetail already has a
  timeline chart component/pattern to reuse).
- Graph: render `graphSignals` (or feed the existing graph view).
- Public attention: render `packet.public_attention` (trends + wiki), null-safe.
- Related: keep `related_threads`, augment with `relatedThemes`.

Add the packet types to the `ThreadDetail` interface. Null-safe everywhere: a
thread with a thin sample still renders (empty sections collapse).

## Caveat: sample size

Thread detail aggregates over `sample_signal_ids` (small, ~8–24), not the full
member set — same limitation `ThemeDetail`'s dynamic-topic path already has. The
packet is preview-grade. Optional follow-up: bump the snapshot
`sample_signal_ids` cap (8→~24) so the aggregates are denser. Flag, don't block.

## Error handling

- Empty/thin sample → builder returns empty lists / zeroed lanes; panel collapses
  empty sections.
- `public_attention` failure → `None`, never fails the detail.
- Missing `source_family` on a row → counted as `other` lane.

## Testing

- `build_thread_packet` unit tests: country grouping, source+family grouping,
  lane split, timeline bucketing, relatedThemes, empty input.
- Thread detail contract test: response includes `packet` with the expected keys
  (null-safe) for dynamic + emergent + atlas prefixes.
- themes.py regression: theme detail contract unchanged after the DRY refactor.
- Frontend `npm run build` passes; panel renders packet sections and collapses
  empties.

## Deployment

`scripts/deploy-fly-api.sh` (API serves thread detail) + Vercel frontend. No
migration, no worker change. Smoke: `dynamic-topic-*`, `emergent-cluster-*`, and
an atlas thread all return a populated `packet`; ThreadFocusPanel renders country
edges, lanes, timeline, attention.

## Obsidian connections

- Linked from [[Narrative Intelligence]] and [[Frontend Product Surfaces]] and
  [[000-INDEX]].
- Builds on [[2026-06-04-signal-snippet-enrichment-design]].
