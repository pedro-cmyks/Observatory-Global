# Silent-risk detection (#172) — methodology + measure-first findings

Date: 2026-06-29 · Status: **scaffold shipped, data source DISPROVED**

## The idea

A **silent risk** = a topic the PUBLIC is paying attention to but the PRESS is
NOT covering. It is Atlas's strongest differentiator vs GDELT wrappers: GDELT has
no public-attention layer, so it structurally cannot show "what is missing."
Endpoint: `GET /api/v2/attention/silent-risks[?country=&hours=&days=&limit=]`.

## What shipped (correct + reusable)

- `app/services/silent_risk.py` (pure, 6 tests): `is_noise_title`,
  `normalize_title`, `is_silent_risk` (attention + low-coverage + surge gate),
  `why_silent` (honest explanation incl. language-barrier hint).
- `app/routers/attention_threads.py`: pulls Wikipedia pageviews, drops
  housekeeping + sports/entertainment noise (reusing the #177 editorial lane —
  composes with the 2026-06-29 thread-ranking work), measures media coverage,
  flags silent, ranks.

## Measure-first findings (three iterations, all on prod data)

1. **Coverage must be LEXICAL, not semantic.** First cut measured coverage by
   embedding the topic and finding nearest media signals (≥0.82). It returned
   `media=0` for EVERYTHING — including "2026 FIFA World Cup" (8.9M views), which
   has **1,255** media signals/24h. A bare Wikipedia entity title is an
   entity-match question, not a semantic-neighbour one: an entity name rarely
   clears the query↔headline floor against event-shaped headlines. Switched to
   generous lexical token matching (biases toward "covered" → conservative silent
   flagging). Coverage then measured correctly (World Cup 851, Cape Verde 185…).

2. **Absolute pageviews surface sports/celebrity, not news.** With correct
   coverage, the global top-views list is football players (Ronaldo, Messi,
   Haaland, Yamal…) and Netflix shows (Supergirl, Obsession…). None are news
   silent-risks; most show coverage and drop out, the residue is trivia.

3. **Velocity (surge vs baseline) can't be computed from this table.**
   `wiki_pageviews_v2` stores only each day's TOP-N articles, not a consistent
   per-article panel. A topic surging into today's top was not in prior days'
   stored rows → no baseline → `v_base = 0` for ALL → velocity collapses back to
   absolute views. The "silent" residue is then obscure curiosity spikes
   (*Tubifex tubifex* the worm, *Scarface*, *Dalida*), not hidden news.

## Verdict

**Wikipedia top-pageviews is the WRONG attention source for news silent-risk.**
It is driven by sports, entertainment, and random curiosity — not by news gaps —
and the table cannot support the velocity signal #172 specified. The endpoint is
honest (coverage is real, labels are honest) but the source yields noise, so it
must NOT be surfaced as a headline UI feature on this source.

## The real path (recommended next)

The scaffold is source-agnostic; swap the attention source:
1. **Reddit/forum lane** (already ingested, `source_family='social'`) — far more
   news/discussion-oriented than Wikipedia pageviews. A forum topic with public
   discussion but no media thread is a much truer silent risk.
2. **Google Trends, news-filtered** — rising news queries with no media coverage.
3. **Full Wikipedia Pageviews API** (per-article daily history, not top-N) — would
   restore the velocity signal if a Wikipedia source is still wanted.

Until a news-oriented source is wired, `is_silent_risk` + the coverage measurement
+ the noise/lane filters are reusable as-is; only the source query changes.
