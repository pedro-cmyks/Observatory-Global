# Workbench Article Enrichment — fetch pinned pages, AI-read them, feed the investigation

**Date:** 2026-07-20 · **Status:** APPROVED (Pedro) — F1 BUILDING · **Owner:** L3 track

## 0. Product framing (Pedro, this session)

We are enriching the **Workbench** (the living investigation), not the dossier.
The dossier is the frozen photo; it *inherits* whatever the Workbench substrate
carries. Today a pin freezes only headlines (`PinSnapshot.evidence[].url` —
workbench.ts). The pinned URLs are a curated, tiny set (5–50 per
investigation) — the exact scope cut that makes selective scraping viable where
mass scraping is not.

Two layers, per the project rule (engine math-first / LLM only in sanctioned
glass-box surfaces):

- **Mechanical layer** (fetch + extract + token/NER/embed): feeds the measured
  relation machinery. No LLM.
- **Reading layer** (AI-read): the Workbench IS the sanctioned LLM surface
  (synthesize, corroborate, insight already live there). Heavy-model inference
  over fetched text, glass-box, investigation-scoped, **never writes to the
  Atlas engine substrate**.

## 1. Design decisions (judged 2026-07-20, Pedro approved all 5)

1. **Partial yield is a normal state, not an error.** Real-world fetch yield
   will be ~50–70% (paywalls, bot walls, consent walls, JS rendering). No bot
   evasion, ever. Surfaces report yield as data: "8 of 12 sources with full
   text". Dead links (404/410/DNS) get a Wayback Machine fallback, labeled
   `via: wayback`.
2. **No open proxy.** The fetch endpoint would otherwise be a free scraping
   proxy + SSRF surface (pins are anonymous localStorage; endpoint is public).
   Gates, in order: (a) scheme http/https only; (b) **SSRF guard** — resolve
   host, reject private/reserved IPs, re-check on every redirect hop, cap
   redirects; (c) **known-domain gate** — only domains observed in
   `signals_v2` (last 30d, cached in-process 1h). Interim trade documented:
   exact-URL matching needs an index `signals_v2` can't afford today
   (churn/bloat history); domain gate + SSRF + per-IP rate limit is the
   honest v1. (d) per-IP rate limit bucket (rate_limit.py).
3. **Cross-read hallucination guard.** Every AI-read claim MUST carry an exact
   quote span from the fetched text; claims without a quote are dropped at
   parse time. Cross-read only compares quoted claims and labels findings
   "possible tension — verify quotes", never asserts contradiction as fact.
4. **F3b (body embeddings → neighbors) is gated on measurement.** e5 space +
   whitening were measured on headlines; 800-word docs shift the distribution.
   Needs its own measurement pass (per engine-surgery rule) before serving.
   F3a (token match over bodies) is safe.
5. **NATO-Ankara is the gold.** The manual corroboration run (4/4 claims
   established, marquee doc) is ground truth for F2 acceptance: AI-read over
   the same pins must reproduce what Frank validated, or it does not serve.

Other hard constraints:

- **Article text never enters localStorage or accounts sync** (5MB cap; LWW
  payload bloat). Server-side cache keyed by URL; the pin's existing `url` is
  the join key. Zero pin-schema change.
- **Frozen-evidence discipline:** a fetched text is never silently
  overwritten (`content_hash`, `fetched_at`); re-fetch creates no mutation of
  a successful row.
- **Legal:** UI + markdown export show excerpts (~60 words) + citation, never
  full republished text. Full text lives server-side as analysis substrate
  only.
- **Engine boundary:** nothing here assigns topics, edits topic_members, or
  feeds engine training. Investigation-scoped.

## 2. Data model — migration 086

```sql
-- 086_pinned_articles.sql
CREATE TABLE pinned_articles (
  url_hash      TEXT PRIMARY KEY,            -- sha1(url)
  url           TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','ok','paywall','robots','error','unsupported')),
  http_status   INT,
  via           TEXT NOT NULL DEFAULT 'live' CHECK (via IN ('live','wayback')),
  title         TEXT,
  outlet        TEXT,
  lang          TEXT,
  extracted_text TEXT,
  excerpt       TEXT,                        -- first ~60 words, display-safe
  word_count    INT,
  content_hash  TEXT,
  fetch_error   TEXT,
  fetched_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_readings (                    -- F2 (schema ships now)
  url_hash       TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model          TEXT NOT NULL,
  reading        JSONB NOT NULL,             -- {claims:[{text,quote,attribution}],actors,numbers,gaps}
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (url_hash, prompt_version)
);
```

Both tables get 082-style hardening (RLS enabled, no policies, REVOKE from
`anon`/`authenticated`): server-only via asyncpg, never PostgREST.

`pending` rows older than 10 min are re-eligible (a deploy can kill a
background task; no queue infra — re-trigger at read time).

## 3. Backend

`app/services/article_fetch.py`
- `is_fetchable_url(url)` — scheme + SSRF + known-domain gates (decision 2).
- `fetch_and_extract(url)` — aiohttp GET (timeout 10s, size cap 2MB, honest
  UA `AtlasResearch/1.0 (+atlas contact)`), then **trafilatura** extract →
  status machine: ok (≥120 words) / paywall (heuristic: 200 with <120 words
  extracted) / robots (401/403) / error / unsupported (non-HTML, PDFs out of
  v1). Wayback fallback on 404/410/DNS-dead.
- `enqueue_fetches(urls)` — dedupe by hash, insert pending, spawn bounded
  asyncio tasks (concurrency 3, per-domain serial).

`app/routers/research_articles.py`
- `POST /api/v2/research/articles/fetch {urls: [...]}` → gate → enqueue →
  immediate per-URL status. Rate-limited (research bucket).
- `GET /api/v2/research/articles?urls=` → cached rows: status, excerpt,
  title, outlet, word_count, fetched_at, via. `full_text` is NOT served in v1
  responses (legal + payload); synthesize/AI-read read it server-side.
  Contract `research-articles-v0`.

`publication_synthesis.py` — `SynthPin` gains optional
`excerpts: list[str]`… **server-side**: the synthesize path looks up
`pinned_articles` for the pin evidence URLs it already receives and appends
numbered evidence lines labeled `— full text excerpt, <outlet>` (same [n]
citation discipline). Client sends nothing new.

## 4. Frontend

- `lib/articleEnrichment.ts` — `enqueueSnapshotFetch(snapshot)` fire-and-forget
  POST of `evidence[].url`; `fetchArticleStates(urls)` for display. Silent
  degrade on failure — a pin never waits on the network (same contract as
  updatePinSnapshot).
- Hook points: wherever a `PinSnapshot` lands (addPin with snapshot /
  updatePinSnapshot call sites).
- **WorkbenchPanel:** per-pin badge — `FULL TEXT ✓` / `fetching…` / honest
  degrade (`paywall`, `no text`); expanding a pin shows the excerpt + link.
- **DossierView:** on generate, `fetchArticleStates`; pending → bounded wait
  (≤10s, existing LoadingMoment); per-citation block
  `FROM THE SOURCE · fetched <date>` with excerpt; yield line
  "N of M sources with full text". Old pins (e.g. NATO-Ankara) enqueue at
  generate time — same path.

## 5. F2 — AI-read + cross-read (next session)

- `article_read.py`: one grounded pass per article (chain reuse:
  `insight_llm.generate_insight` pattern, Anthropic→DeepSeek, cost →
  `log_ai_cost('workbench-ai-read', …)`). Output schema = claims WITH exact
  quote spans (decision 3), assertion-vs-attribution, actors+roles, numbers/
  dates, per-article gaps. Cached in `ai_readings` by (url_hash,
  prompt_version) — regenerating never re-pays.
- Cross-read: one pass over all pin readings → corroboration/tension map
  ("pin A claims X [quote]; pin C's quote points the other way — verify").
  Feeds claimLedger (workbench.ts) as `AI READ · <model> · <date>` entries.
- Acceptance: NATO-Ankara pins vs the manual 4/4 gold (decision 5).
- Extraction model: DeepSeek temp0 (mechanical); cross-read: chain (dense).

## 6. F3 — mechanical relation upgrades (after F2)

- **F3a:** `/dossier/connections` text_mention basis extended over
  `extracted_text` (pure token match, basis label `body-text`, never mixed
  with `headline` basis silently).
- **F3b:** body-embed neighbors — GATED on a measurement artifact
  (headline-space vs body-length distribution) before serving. Not scheduled.

## 7. Tests / acceptance (F1)

- pytest: SSRF guard (private IPs, redirect hop, scheme), domain gate, status
  machine on HTML fixtures (ok/paywall/short/non-HTML), excerpt builder,
  router contract + pending-requeue.
- vitest: articleEnrichment states; WorkbenchPanel badge render; DossierView
  yield line + degrade.
- Browser-verify: pin → badge appears → generate dossier → FROM THE SOURCE
  block; paywalled URL shows honest degrade. Prod smoke post-deploy.

## 8. Out of scope (explicit)

Bot/CAPTCHA evasion (never) · user-supplied external URLs (needs auth) ·
PDFs · full-text in API responses · any engine write · corroborate-with-
bodies (F2.5, after F2) · body-embed serving without measurement (F3b gate).
