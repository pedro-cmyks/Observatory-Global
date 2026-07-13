# Cold-editor pass — daily / Iran / NATO (2026-07-13)

**Question (P0.6 publishable bar):** would a cold editor publish this as news
with a byline? Judged against a fixed rubric: (1) a written, cited article
exists; (2) every load-bearing claim ends in a receipt; (3) 5W+H — who/what/
when/where/how present, why honestly bounded; (4) subject geography coherent
(no grab-bag umbrella); (5) corroboration status per claim; (6) an honest
"what we don't know"; (7) fresh enough to be "news". Grounded in the live data
and the documented record, not transcribed.

## Verdict summary

| Package | Article (prose) | 5W+H | Coherence | Freshness | Cold-editor verdict |
|---|---|---|---|---|---|
| Daily edition | **none** (`prose_status: not_requested`) | 5/5 ready, why partial | grab-bags now flagged | **12.1 h lag** | **not publishable as news yet** — a data contract + newspaper layout, no written cited article, and its cutoff is half a day old |
| Iran investigation | **none** (package only) | 5/5 ready | coherent (co-occurrence 1.0) | live | **not publishable as news yet** — the substrate is there; no generated article |
| NATO-Ankara | **yes** (dossier-synthesis-v2) | mixed | improved post-fixes | frozen | **closest, still short** — last Frank v2 = "usable-with-caveats, barely; working draft, not a briefing"; the completed-artifact cold-read is still pending |

**Overall: none of the three currently clears the byline bar.** The composition,
5W+H contract, receipts, and — new today — grab-bag disclosure all work, but the
publishable *product* is a written, cited article, and only NATO has one.

## Daily edition

- Freshly rebuilt read-only: 546 candidates traversed, cursor exhausted,
  readiness `who/what/when/where/how = ready`, `why = partial`, 71 receipts.
- The grab-bag detector fired correctly in the build — "Sinner Wins Wimbledon"
  was flagged `subject_geography_grab_bag`, so an incoherent umbrella is now
  disclosed rather than led with.
- Two blockers to publishability, both real:
  1. **No article.** `prose_status = not_requested`. The package carries the
     data (stories, receipts, 5W+H, gaps) and the Brief renders a newspaper
     layout, but there is no generated, cited prose an editor can publish.
  2. **Stale cutoff.** Even a fresh build measures **12.1 h data lag** — the
     edition ends at the latest completed top-level snapshot, and the M1
     clustering cadence leaves that ~12 h behind wall-clock. "A new story is the
     last 24 hours"; a 12 h-old cutoff is defensible as a daily but must be
     labeled, and the freshness is bounded by snapshot cadence, not the build.

## Iran investigation

- The forcing-case package reaches `who/what/when/where/how = 5/5`, subject
  geography coherent (Israel-US-Iran co-occur, not a grab-bag), receipts and
  typed relations present, exported as one package.
- No generated article. As with the daily, the substrate is publishable-grade
  but the written cited piece has not been synthesized.

## NATO-Ankara

- The only package with a synthesized cited article (dossier-synthesis-v2).
- Its own record is the honest ceiling: the last cold reader (Frank v2,
  2026-07-11) returned **"usable-with-caveats — barely; internal working draft,
  not a briefing"** and listed six defects — a headline finding contradicted by
  its own quoted evidence, junk entities inside a "confirmed" link, no dates, a
  lead pin showing zero evidence, clustering garbage in the assembled stories,
  and an unacknowledged coverage-lens skew. Fixes for several landed 2026-07-12
  (evidence-freeze, dates, synthesis glass-box, corroboration), but the
  **completed-artifact cold-read remains pending** (marquee doc, "Pending").

## The gap to a byline (what each needs)

1. **Generated cited prose for the daily and Iran.** ✅ **Shipped for the daily
   lead (`dd5c7013`).** The grounded synthesis was extracted to a FastAPI-free
   service (`app/services/publication_synthesis.py`) so the headless M1 daily
   builder can call it, and the daily build now synthesizes its lead story into
   a cited front-page mini-article. Verified on a fresh build: the lead "Dino
   Blocks Cunha Funds" produced a dated lede, a 3-paragraph body with `[n]`
   markers on every claim, **6 citations resolved against the frozen receipts**,
   and 4 honest unknowns — `prose_status: generated`, provider DeepSeek (the
   Anthropic-out-of-credits fallback degraded openly). A single coherent lead is
   one article; the 12 unrelated top stories are never fused. Remaining under
   this item: per-story prose for the secondary rows, and the same over the Iran
   package.
2. **Freshness labeling + cadence.** The daily cutoff is snapshot-bound (~12 h);
   either tighten the clustering cadence or label the window honestly ("data to
   HH:MM UTC") so "daily" is not oversold.
3. **NATO completed-artifact cold-read.** Regenerate post-fixes and run the
   pending Frank test; resolve any surviving defects from the six.

Only after (1)–(3) do the daily, Iran, and NATO packages pass the same citation
and cold-editor rubric — the gate the roadmap places immediately before any
public/LinkedIn artifact.
