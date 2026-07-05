# L1 Deep Review — the Brief (front door), end to end

**Date:** 2026-07-05 (madrugada, same session as the L3 review/execution)
**Status:** REVIEW COMPLETE → WORK SPEC (§7). Pending Pedro's read + decisions (§8).
**Method:** 3 exhaustive sweeps (Brief frontend, briefing backend + AI prompts,
docs/issues/telemetry) + live prod verification (insight endpoints curled,
telemetry funnel queried, why_now source grep-settled). Every AI prompt quoted
verbatim in §4 — Pedro's explicit ask.

---

## 0. Verdict in one paragraph

L1 is in **far better shape than L3 was**: the 06-12 rebuild landed the #225
design (lead story, watchlist, honest standfirst, heating strip, demoted map),
#249 already swapped BY THEME → BY CATEGORY (R3 lens, GDELT only as fallback),
the PWA front door is real (7/8 tasks), and top_threads flows through
`fetch_threads` so the 07-04 stories-only change reached the Brief for free.
Three real problems: (1) **the Brief's only AI narrative — Editor's Analysis —
is silently DEAD in prod** (`insight_no_credits`, Anthropic key dry since
~06-29; the theme insight is dead the same way; nothing alerts); (2) **the
funnel says people open but don't drill**: 8 sessions/14d, ~4.4 opens each
(PWA habit is forming), but only 1 session ever clicked a thread — 12.5%
conversion to the value moment; (3) the front door is **inconsistent with the
translation-by-default principle** (evidence headlines render raw; the
Instagram-style affordance shipped everywhere but here) and **has zero bridge
to L3** (nothing saveable/pinnable). The "what is missing" wedge element (gap
box, #172) is still an empty slot — and the W2d category-gap machinery built
tonight is exactly the substrate it was waiting for.

---

## 1. What L1 is today (verified inventory)

Route `/brief` (`BriefNewspaper.tsx`, ~980 lines), PWA `start_url=/brief`,
keep-alive mounted beside the console (`main.tsx` AppBriefKeepAlive).

Sections in render order (file:line in the agent trace; condensed):

| Section | Feeds from | Clickable → |
|---|---|---|
| Offline banner | `navigator.onLine` | — ("Offline — showing last Brief") |
| Masthead + range selector | local state | range buttons |
| Country filter | `top_countries` + autocomplete | scopes the Brief |
| **LEAD STORY** | `selectLeadThread(top_threads)` — same ranking as `/threads` | whole card → `/app?theme=…&country=…` |
| Watchlist (8) | `top_threads[1:9]` — movement arrow, chips, sparkline | row → console |
| Standfirst | `/briefing/insight` (AI) **or** factual fallback line | — |
| Heating Up (4) | `heat_countries` + dominant component named | card → `/app?country=` |
| Minimap (demoted) + Most Active (8) | `top_countries` | country → console |
| Most Negative/Positive (4+4) | `negative/positive_sentiment` + `SentimentSourceBadge` (NLP% vs GDELT) | country → console |
| Sources (5) | `top_sources` | — |
| **By Category** (8) / By Theme fallback | `category_counts` (R3.1) / `top_themes` (GDELT legacy) | `/app?q=category` |
| Saved Watches | localStorage `useSavedWatches` + delta vs lastSeenCount | open in Atlas |
| Country view (when filtered) | `/nodes?focus_type=country` + `/threads?country_code=` | threads → console |

**Honesty inventory:** "Covered from" chips (coverage ≠ subject, tooltip),
sentiment-source badges, historical-processed badge (>24h windows),
UNVERIFIED never mixed in, standfirst falls back to a counted fact — the
Math.random essay era is confirmed dead (no `buildGlobalFallback` anywhere).

**Not in the Brief:** translation (TranslatableHeadline exists, unused here),
pins/saves into L3, gap box, polls (warm-cache damps them by design).

## 2. Data plumbing

Calls on mount: `GET /api/v2/briefing?hours=` + `GET /api/v2/briefing/insight`
(parallel, after sessionStorage cache check). Country filter adds `/nodes` +
`/threads?country_code=`.

**Cache stack (4 layers, worst-case staleness adds up):**
| Layer | TTL |
|---|---|
| briefingPrefetch (Landing warms it) | 4 min sessionStorage |
| fetchWarmCache shim (all GET /api/v2/*) | 10 min + background revalidate |
| Redis `briefing_data:{hours}` | 15 min (≤24h) / 30 min (>24h) |
| Redis `briefing_insight:{hours}` | 30 min |

**Cadence (Brief block → upstream job → frequency):**
| Block | Upstream | Freq |
|---|---|---|
| stats, top/neg/pos countries, theme_country | `country_hourly_v2`/`theme_country_hourly_v2` (matview, M1 cron; API-side refresh retired 07-02) | 30min ingest / ~2h matview |
| top_themes (≤24h) | `theme_hourly_v2` (ingest upsert) | 30 min |
| top_themes (>24h) | `historical_topic_country_daily` | daily compaction |
| heat strip | `country_heat_v2` matview — **window hardcoded 24h** | ~2-4h |
| top_threads | classifier cron → `fetch_threads` (stories-only since 07-04 ✓) | 30 min |
| top_atlas_topics | `dynamic_topics` → `emergent_clusters` → legacy assignments (source_table exposed) | realtime / 6h / 30min |
| category_counts | `dynamic_topics.category` (R3.1 typing, 30-min incremental) + snapshot membership | 30min-6h |

## 3. Ground truth (measured tonight)

- **Funnel (14d):** 8 sessions opened the Brief · 35 brief_opens (~4.4/session
  — real re-entry, the PWA is being used as a habit) · **1 session clicked a
  thread** (12.5% → `first_value_moment{brief_thread}` = 1). People read the
  front page and stop.
- **AI narrative DEAD in prod:** `/briefing/insight` →
  `{"insight": null, "error": "insight_no_credits"}`; `/theme/{code}/insight`
  → same. Both are Anthropic-key paths; key dry since ~06-29. The Brief
  renders the honest fallback line, so users see no error — and no one was
  alerted either. **Silent-death class, again** (same family as the dead
  matview / dead crons).
- #249 CLOSED (`f41da128`): By Category live, GDELT only as fallback.
- PWA: 7/8 shipped (share-card image deferred; Lighthouse pass pending eyeball).

## 4. AI layer — every prompt, verbatim (the ask)

| # | Where | Model · temp · max_tok | Cache | LIVE? |
|---|---|---|---|---|
| 1 | Brief standfirst — `GET /briefing/insight` (`briefing.py:903-1023`) | claude-haiku-4-5 · default · 200 | Redis 30min | **DEAD** (`insight_no_credits`) |
| 2 | Theme insight — `GET /theme/{code}/insight` (`themes.py:1380-1660`) | claude-haiku-4-5 · default · 256 (Ollama fallback via `INSIGHT_PROVIDER`) | Redis 15min | **DEAD** (same key) |
| 3 | Headline translation — `/translate`(+`/batch`) (`translate.py`) | deepseek-chat · 0.1 · 200 | `signal_translations` table (permanent) | LIVE (unused by Brief) |
| 4 | Dynamic-topic labels (what the Brief displays as thread names) — `claude_label.py` | Claude CLI (Max subscription, M1) | written to `dynamic_topics.label` | LIVE |
| 5 | Category typing (feeds By Category + badges) — `compute_category_typing.py` | deepseek-chat · 0 | `dynamic_topics.category/crisis_class` | LIVE (30-min incremental) |
| 6 | Thread note lede/movement/caveat — `deepseek_narrative.py` | deepseek-v4-flash · 0.2 · 420 | opt-in only (`?llm` / env flag) on `/threads/{id}` | OFF by default |
| — | `why_now` + `narrative_note` on every thread | **NOT AI — pure templates** (`thread_intelligence._why_now`, `narrative_note.py`) | — | LIVE |

**1. Briefing insight — system:**
```
You are an intelligence analyst giving a morning media briefing.
Describe what the world's press is covering and how, using the data provided.
Be concise, neutral, and analytical. No markdown, no bullet points — flowing prose only.
```
**user (data: stats + top-5 countries w/ tone from `country_hourly_v2`, themes from `theme_hourly_v2`):**
```
Summarize the global information landscape over the last {hours} hours.
- Total coverage: {total:,} articles across {countries} countries
- Global sentiment: {avg_sent:+.1f} (negative = concern/crisis, positive = stability/progress)
- Dominant topics: {themes_str}
- Most-covered countries (with their tone): {countries_str}

Write 2-3 sentences describing what the world's media is focused on right now,
what emotional tenor dominates, and any notable geographic patterns in coverage.
```
Expected: 2-3 sentences prose. UI labels it "EDITOR'S ANALYSIS" with the
tooltip "AI-generated pattern reading… does not reflect Atlas editorial
opinion". On null → factual fallback `${total} signals across ${countries}
countries from ${sources} sources · lead: {label}` with NO analysis tag.

**2. Theme insight — system (rules abridged headers, full text in `themes.py:1571`):**
```
You are an intelligence analyst summarizing global media trends. …
1. Never use raw database taxonomy names … 2. Do not write like a robot listing
statistics … 3. Highlight interesting contrasts … 4. Keep it exactly 2-3
sentences … 5. Never use em-dashes or en-dashes.
```
**user:** volume/sources/tone/top-countries-with-tone/momentum → 2-3 sentences.

**3. Translation:**
```
Translate this news headline to {target_lang} (ISO 639-1). Preserve named
entities, dates, and numbers verbatim. Do not add commentary or quotation marks.

Return JSON only: {"translated": "..."}

Headline:
{headline}
```

**4. Topic labeling (Claude CLI):**
```
You are labeling a cluster of news headlines for a narrative intelligence brief.

Given these representative headlines:

{headlines}

Return JSON only, no other text:
{
  "label": "3-5 word topic name in title case",
  "description": "one-line description of what this cluster is about",
  "confidence": 0.0-1.0
}
```

**5. Category typing (temp 0, candidate-v2 32 categories; seed-anchor cosine
@0.80 primary, DeepSeek fallback):**
```
Classify this news TOPIC into the Atlas crisis taxonomy. Pick the SINGLE best
category from the list, or answer OUT_OF_SCOPE if it is not a crisis /
narrative-intelligence topic (sport, entertainment, lifestyle, travel, product
launch, routine obituary, market-data roundup).

TOPIC: "{label}"

CATEGORIES:
{category_list}

Answer with ONLY the exact category label, or OUT_OF_SCOPE.
```

**6. Thread note (opt-in) — system:**
```
You write concise Atlas narrative intelligence notes. Use only the provided
JSON. Do not invent facts. If evidence is mixed, noisy, or not a coherent
story, say that clearly. Return strict JSON only with keys: lede, movement,
evidence, caveat, quality. quality must be one of strong, provisional, thin.
```

## 5. Findings

- **F1 (HIGH, cheap): Editor's Analysis silently dead** — both insight
  endpoints return `insight_no_credits`; the front door's AI voice has been
  off ~6 days with zero alerting. The fallback is honest, so it LOOKS fine —
  which is exactly why nobody noticed. Same silent-death class as the dead
  matview/crons; needs both a fix and a monitor.
- **F2 (HIGH, product): open-without-drill funnel** — 4.4 opens/session says
  the habit loop works; 12.5% thread-click says the page either satisfies at
  the surface or fails to invite depth. Can't distinguish without scroll/dwell
  or per-section click events — the Brief has exactly 2 client events.
- **F3 (MEDIUM): no translation at the consumer front door** — evidence
  headlines render raw (unian.ua leads in Ukrainian); the translated-by-default
  affordance exists (`TranslatableHeadline`, DeepSeek path LIVE) and is wired
  into console + CountryBrief but not the Brief. Inconsistent with the
  06-22 decision.
- **F4 (MEDIUM): L1→L3 bridge absent** — nothing in the Brief can be saved
  into an investigation (Saved Watches is a separate localStorage mechanism
  that never reaches the Workbench). The wedge ramp jumps L1→L2 only.
- **F5 (MEDIUM): gap box (#172) still an empty slot** — "what is missing" is
  a wedge pillar and the #225 spec reserved the slot. NEW: the W2d
  category-scoped coverage-gap machinery (research-plan-v1, tonight) computes
  exactly this; the box can now be fed without new research.
- **F6 (LOW): heat strip window dishonesty at >24h ranges** — `country_heat_v2`
  is hardcoded 24h; selecting 7d re-scopes everything else but the heating
  strip silently stays 24h. One label fixes the honesty; multi-window heat is
  the real fix.
- **F7 (LOW): legacy `top_themes` (GDELT) still in the payload** — hidden by
  the By Category render when present; consumers must check
  `top_themes_source`. Fine, documented.
- **F8 (LOW): four stacked cache layers** — prefetch 4m + warm 10m + Redis
  15-30m + insight 30m; worst-case a "fresh" open shows ~40-min-old numbers.
  Acceptable for a brief; document, don't fix.
- Corrections to stale docs: Math.random essays are GONE; #249 is CLOSED
  (By Category live); `why_now` is templated, NOT LLM (several docs imply
  otherwise).

## 6. L1 vs the wedge

"The real story" ✓ (lead = same ranking as /threads, stories-only). "Who is
saying what across countries/languages" ⚠ half — coverage chips + voice
metrics exist upstream but the Brief shows no voice section and no
translation. "Press vs public" ✗ absent at L1 (forum lane never surfaces
here). "What is missing" ✗ (gap box unbuilt). "Fast, with receipts" ✓
(evidence headlines + sources, honest fallbacks, offline-last-brief).

## 7. Work spec

### B0 — Revive the AI voice + alert on its death (S)
(a) Port the briefing-insight + theme-insight calls to a provider chain:
Anthropic if key present → **DeepSeek fallback** (already funded + live for
translation/typing; same prompt, `deepseek-chat`, temp 0.2). (b) The response
already carries `error: insight_no_credits` — surface it in the weekly read
(PB-8/`research_usage_report.py` gains an endpoint-health line) so an AI-lane
death is never silent again.
**Acceptance:** prod `/briefing/insight` returns prose again; report flags
provider used; fallback line still honest when both fail.

### B1 — Instrument the fold (XS-S)
Per-section click events (`brief_section_click {section}`) + one scroll-depth
event. Answers F2 (satisfies-at-surface vs fails-to-invite). Fold into weekly
read.

### B2 — Translate the front door (S-M)
`TranslatableHeadline` on lead + watchlist evidence headlines (viewer-language
default, "See original" toggle — the 06-22 affordance). DeepSeek per-headline,
cached permanently in `signal_translations`; volume is small (≤3 evidence ×
9 threads).

### B3 — Gap box, fed by W2d (M)
The #225 reserved slot, powered by the category-scoped coverage gaps that
research-plan-v1 now computes: "attention/categories with no verified
coverage" (e.g. "election-legitimacy: PE has 12 extended, 0 verified").
Reuses `coverage_gaps` + `category_summary`; no new research. Closes the
"what is missing" wedge pillar at L1. (#172's silent-risk research stays its
own track; this is the layout slot, honestly labeled.)

### B4 — L1→L3 bridge (S, gated on B1 telemetry)
"Save to investigation" on lead/watchlist rows (reuses the W1 unified pin
path + W4 auto-create). Converts Saved Watches users into investigation users.
Gate: ship after B1 shows where readers actually engage (anti-goal).

### B5 — Heat-strip honesty (XS now, M later)
Now: label the strip "last 24h" when the selected range >24h. Later:
multi-window `country_heat_v2` (own decision, costs a matview).

Order: B0 → B1 → B5-label (same day, all small) → B2 → B3 → B4 (gated).

## 8. Decisions for Pedro

- **D-L1-1 Insight provider:** DeepSeek fallback chain (rec — zero new spend,
  key already live) vs recharging Anthropic credits vs leaving the fallback
  line as the permanent standfirst (no AI at L1).
- **D-L1-2 Translation default at L1:** translated-by-default like the console
  (rec, consistency) vs original-first at the front door.
- **D-L1-3 Gap box content:** category-gaps version (rec, substrate exists
  tonight) vs waiting for #172 silent-risk research.
- **D-L1-4 B4 timing:** gate on B1 read (rec) vs ship with B2.
