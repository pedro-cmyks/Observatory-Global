# Signal Snippet Enrichment — Design

**Date:** 2026-06-04
**Status:** Draft for review
**Branch:** `v3-intel-layer`
**Track:** Product (reading experience / narrative enrichment — F3)

## Context

Atlas should be a **reading experience** at its entry levels: Brief = level 1,
App = level 2, Workbench = level 3 (graphs, numbers, deep connections). Today the
entry panels deliver mostly numbers. The narrative threads and theme/topic detail
panels feel empty because the only per-signal text we surface is the headline.

Investigation finding (2026-06-04): several ingestion sources already extract
text **beyond the headline** but we discard it.

- `ingest_reddit.py` extracts `selftext` (capped 300 chars).
- `ingest_newsapi.py` extracts `description` (capped 500 chars, as `snippet`).
- `ingest_rss.py` extracts `summary`/`description` (capped 500 chars, as `snippet`).

`signals_v2` has **no** column for this text. The `INSERT INTO signals_v2` in
each ingest never writes it, so the snippet is used for country/topic extraction
and then thrown away.

GDELT (the main `ingest_v2.py` path) brings no body text — only headline + URL +
themes + tone. That is expected; GDELT signals will simply have a NULL snippet.

There is **no single insert helper** — each source owns its own
`INSERT INTO signals_v2`: `ingest_v2` (GDELT), `ingest_reddit`, `ingest_newsapi`,
`ingest_newsdata`, `ingest_mediastack`, `ingest_rss`, `ingest_reliefweb`.

This design persists that discarded text and exposes it in the reading panels, so
the narrative threads and theme detail carry real sentences, not just counts. It
is the foundation for the per-country narrative assembly (F2/F4) and the panel
reading redesign (F1), which are separate specs.

Related context:
- [[2026-06-03-research-model-product-roadmap]] — information-disorder reading
  product direction.
- [[2026-06-03-frontend-surface-data-map]] — which panels consume which detail
  contracts.
- [[Frontend Product Surfaces]] — MOC.

## Scope

In scope:
- Migration: add `signals_v2.snippet TEXT` (nullable).
- Wire every ingest that already extracts body text to persist it into `snippet`,
  capped at 500 chars: `ingest_reddit`, `ingest_newsapi`, `ingest_rss`,
  `ingest_newsdata`, `ingest_mediastack`, `ingest_reliefweb`.
- Leave GDELT (`ingest_v2`) snippet NULL.
- Carry `snippet` in thread evidence payloads as available data (no raw line
  rendering in the thread/theme panels).
- Surface `snippet` as reading text in the single-signal detail: add it to
  `/api/v2/signals` and render it in `SignalDetailPanel`.

Out of scope (separate specs):
- **Narrative note synthesis:** turning the per-thread / per-country headline +
  snippet corpus into a written editorial note (word-cloud / extractive /
  generated summary). This is the "strong" use of the snippet — Atlas as a note,
  the thread as an article — and gets its own spec on top of this foundation.
- Per-country narrative assembly over un-topic'd signals (F2/F4).
- Reddit / public-attention / events cross-feeding into thread assembly (F4).
- Narrative Threads panel re-enrichment: country edges, evolutive connection
  graph, interactive sentiment history (F5).
- Panel reading redesign / level-1/level-2 UX (F1).
- Backfill. The discarded text is gone; only new signals get a snippet. The
  reading experience fills in going forward as new signals land.

## Data model

Migration `backend/migrations/052_signals_v2_snippet.sql`:

```sql
-- Migration 052: signals_v2.snippet — persist source-provided body text
--
-- Several ingestion sources (Reddit selftext, NewsAPI/RSS/NewsData/Mediastack
-- description, ReliefWeb body) already extract text beyond the headline but it
-- was never persisted. This column captures up to ~500 chars so the reading
-- panels (threads, theme detail) can show real sentences, not only counts.
-- GDELT brings no body text, so GDELT signals leave this NULL. Additive,
-- nullable, no backfill.

ALTER TABLE signals_v2 ADD COLUMN IF NOT EXISTS snippet TEXT;
```

No index (snippet is read alongside an already-filtered evidence row by id, never
queried/filtered on its own).

## Ingestion wiring

For each of the six text-bearing ingests:

1. Take the already-extracted snippet/description/selftext value.
2. Normalize: strip, cap to 500 chars, coerce empty to NULL.
3. Add `snippet` to that ingest's `INSERT INTO signals_v2 (...)` column list and a
   `$N` placeholder + the value to the args.

Per source, the text field that becomes `snippet`:

| Ingest | Source field |
|--------|--------------|
| `ingest_reddit` | `selftext` (already cut to 300) |
| `ingest_newsapi` | `description` (already `snippet`, 500) |
| `ingest_rss` | `summary`/`description` (already `snippet`, 500) |
| `ingest_newsdata` | article `description`/`content` |
| `ingest_mediastack` | article `description` |
| `ingest_reliefweb` | report `body`/`body-html` stripped |
| `ingest_v2` (GDELT) | none — snippet stays NULL |

A shared tiny helper (e.g. `clean_snippet(text: str | None) -> str | None` in a
common module the ingests already import, such as `signals_service.py`) keeps the
strip/cap/empty-to-NULL logic DRY across all six.

## Exposure

The snippet is **information for the engine to leverage**, not a caption stacked
under every headline. It is surfaced two ways, with different intent:

**1. As available data (no raw rendering).** Add `snippet` to the evidence rows
that thread/theme detail already return, so the snippet travels in the payload
and is available for downstream narrative synthesis (the follow-up "narrative
note" feature builds an editorial note per thread/country from the headline +
snippet corpus). This is a data-only change — the thread/theme panels do **not**
render a snippet line under each headline (that was explicitly rejected: a
headline with its body stacked under it adds noise, not reading value).

- `backend/app/services/thread_intelligence.py` (`_serialize_evidence`): add a
  NULL-safe `snippet`; evidence SELECTs add the column.

**2. As reading text in the single-signal detail.** When a user clicks a signal
in the Signal Stream, `SignalDetailPanel` opens and should show roughly *what the
signal says* — the snippet — alongside the existing sentiment, themes, people,
related signals, and "read original". This is the one place a raw snippet is the
right rendering.

- `backend/app/routers/signals.py` (`/api/v2/signals`): add `snippet` to the
  SELECT + response (this endpoint feeds the `Signal` objects the stream and
  detail panel use).
- `frontend-v2/src/components/SignalDetailPanel.tsx`: add `snippet` to the
  `Signal` interface and render it (when present, non-empty) as a short readable
  paragraph under the headline. Absent → render nothing.

Explicitly NOT in scope here (follow-up "narrative note" spec): turning the
per-thread / per-country headline + snippet corpus into a synthesized editorial
note (word-cloud / extractive / generated). This spec only persists the text and
makes it available + readable per single signal.

## Error handling

- Ingest: a missing/oversized/empty source field yields NULL, never an error. The
  500-cap prevents unbounded row growth.
- DB: the column is additive + nullable; existing inserts that don't yet write it
  keep working during a partial deploy.
- API: evidence serialization is NULL-safe; old rows (pre-052) and GDELT rows
  return `snippet: null`.
- Frontend: treat `null`/empty as "no snippet" and render headline only.

## Testing

- Migration shape guardrail (additive `ADD COLUMN IF NOT EXISTS snippet`).
- Per-ingest source-string guardrails (matching existing
  `test_*_router_shape`/ingest test style): each of the six INSERTs includes a
  `snippet` column, and `clean_snippet` caps at 500 + empties to NULL (unit
  test on the helper).
- Evidence contract: theme detail + thread detail serialized rows include a
  `snippet` key (NULL-safe).
- Frontend: `npm run build` passes; evidence row renders snippet when present and
  omits it when null.

## Deployment order

1. Apply migration 052 (Supabase MCP).
2. Deploy backend with `scripts/deploy-fly-api.sh`. Per `fly.toml` the `app`
   process group runs **API + ingestion** (the `nlp_worker` group is NLP
   enrichment only), so this single deploy ships both the evidence-serialization
   changes and the ingest snippet wiring. New signals start writing `snippet`
   immediately; no separate worker deploy is required.
3. Frontend (Vercel) once `npm run build` passes.
4. Smoke: confirm new non-GDELT signals carry a snippet in DB; confirm theme and
   thread detail evidence rows return + render it.

## Obsidian connections

- Linked from [[Frontend Product Surfaces]] and [[000-INDEX]].
- Upstream rationale: [[2026-06-03-research-model-product-roadmap]].
- Foundation for follow-up specs: per-country narrative assembly (F2/F4),
  thread re-enrichment (F5), reading-panel redesign (F1).
