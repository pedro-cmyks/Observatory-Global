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
   Haaland, Yamal…) and Netflix shows (Supergirl, Obsession…). **CLASSIFY, don't
   drop** (Pedro 2026-06-29 — the no-silent-filtering guardrail): a sports/
   entertainment topic may still carry relevant info, so it is LABELLED, never
   discarded. The #177 keyword lane can't classify bare entity titles ("Nico Paz"
   → general), so each title is classified by its **Wikipedia categories**
   ("Argentine footballers" → sports, "1983 films" → entertainment) via the
   MediaWiki API (`category_to_lane`, batched ≤12 to avoid the ~500-category
   response cap, `redirects=1`). Live: 19/25 classified by real category, the
   rest fall back to keyword; response carries `lane` + `lane_basis` per item and
   a `silent_by_lane` breakdown so a consumer filters news vs sports vs
   entertainment instead of us dropping anything. Only true housekeeping/scraper
   artifacts (Main_Page, `.phtml`) are dropped — those are not topics.

3. **Velocity (surge vs baseline) can't be computed from this table.**
   `wiki_pageviews_v2` stores only each day's TOP-N articles, not a consistent
   per-article panel. A topic surging into today's top was not in prior days'
   stored rows → no baseline → `v_base = 0` for ALL → velocity collapses back to
   absolute views. The "silent" residue is then obscure curiosity spikes
   (*Tubifex tubifex* the worm, *Scarface*, *Dalida*), not hidden news.

## Verdict

**Wikipedia top-pageviews is sports/celebrity-heavy and the table can't support
velocity** (top-N only, no per-article baseline). The endpoint is now honest AND
useful: it CLASSIFIES every topic (news/sports/entertainment via Wikipedia
categories) and measures coverage correctly, so a consumer can filter to the
`general` (news-relevant) silent set instead of drowning in sports. But the
news-silent signal from this source stays thin (the `general` residue is still
partly curiosity trivia, e.g. *Tubifex tubifex*), and the velocity signal #172
specified is unavailable here. So: ship the endpoint as a CLASSIFIED scaffold,
but the headline UI feature wants a stronger source.

## Forum-source pivot — BUILT + VALIDATED, does NOT clearly improve (2026-06-29)

Pedro asked to pivot the source to the Reddit/forum lane AND validate it actually
improves. Built (`source=forum`, `_forum_topics`, prefers news subreddits) and
measured head-to-head (global, 48h):

| source | silent risks surfaced |
|---|---|
| wiki | 2 — *Tubifex tubifex* (a worm), *Dalida* (trivia) |
| forum | 1 — "Active Conflicts & News Megathread" (a recurring container, artifact) |

**The forum pivot does not clearly improve the news case.** The Reddit news
subreddits (r/geopolitics, r/worldnews, r/CredibleDefense) discuss MAINSTREAM
geopolitics (Iran/Israel/Ukraine) — which the press covers heavily, so
`media_count` is high (178 / 61 / 17) and they are NOT silent. The country
subreddits (r/myanmar, r/Nigeria, r/colombia) are daily-life chatter ("where can
I buy a cardigan", "90 Day Fiancé"), not news.

**Root finding (both sources): the silent-risk phenomenon is RARE.** Mainstream
public attention TRACKS media coverage; the residual gaps are trivia (wiki) or
daily-life chatter (country forums), not hidden news. #172's premise — meaningful
"topics the public cares about that the press isn't covering," detectable from
top-pageviews or forum discussion — is only weakly supported by the data.

## What WOULD work (reframe, not yet built)

- **Attention/coverage RATIO, not absolute-zero.** Absolute "0 media" is rare and
  trivia-dominated. A relative imbalance — public attention HIGH but media
  coverage DISPROPORTIONATELY low for the same country/topic — is a softer,
  findable signal (an under-covered, not un-covered, story).
- **Local/regional sources** (local-language outlets, regional subreddits) where
  global press genuinely has gaps — needs the diversity-ingest program (#235) to
  mature first.
- **Velocity** (surge vs baseline) — unavailable from `wiki_pageviews_v2` (top-N
  only); needs the full Wikipedia Pageviews API.

The scaffold (wiki + forum sources, lexical coverage, Wikipedia-category
classification, honest labels) is reusable for any of these; only the
source/metric changes. Recommendation: PARK the headline silent-risk feature
until the ratio reframe or a local source is available — the current sources
don't support it.
