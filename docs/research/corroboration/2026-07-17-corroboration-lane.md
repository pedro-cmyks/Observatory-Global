# Corroboration lane — full-history corpus + DOC 2.0 degraded contract

**Council Phase 3(a).** 2026-07-17. Backend only (LANE A). No Fly deploy.

Marcos's closing line was the whole council's verdict: *"the single feature that
would make the dossier publishable"* is **corroboration** — answering, for a
specific receipt, "does an official/wire or full-history source **corroborate**
or **contradict** this claim?" This lane is that answer, computed at query time,
by math, over two corpora.

## What ships

- `backend/app/services/corroboration.py` — the P0.6b pure-math independence
  functions stay untouched; the Phase-3a lane is appended (term extraction,
  figure/official mirrors of `claimLedger.ts`, the relation classifier, the
  hot∪cold query builders, dedup, the per-receipt verdict, and the
  `corroborate_claim` orchestrator with every I/O boundary injectable).
- `POST /api/v2/corroborate` (`backend/app/routers/corroborate.py`, contract
  `corroboration-v1`). Body `{headline, figure?, country?, published_date?}` →
  `{claim, source_status, corroborating[], contradicting[], context[], verdict,
  meta}`. Each match: `{basis, source, url, country, date, snippet, relation,
  official, similarity}`.
- `backend/tests/test_corroboration_lane.py` — 25 tests: term extraction, the
  relation math, the query builders, dedup, the verdict, and the degraded-mode
  contract (mocked throttle → `source_status.doc20 == "throttled"` **and** the
  Atlas matches still returned).

## The full-history corpus rationale

The hot `signals_v2` window is ~8 days. A dossier claim is often weeks or months
old — corroborating it against only the hot window would silently answer "no
coverage found" for anything older than a week, which is a *lie by omission*. So
the lane unifies **three** corpora, all reachable by prod (the 42 GB M1 archive
is **not** reachable by Fly and is deliberately excluded):

| basis | source | span | match |
|---|---|---|---|
| `doc20` | GDELT DOC 2.0 (`api.gdeltproject.org`, free, no key) | rolling ~months | query-time keyword (implicit-AND) |
| `atlas_hot` | `signal_embeddings` (halfvec/768, HNSW) | last ~8 days | e5 semantic ANN |
| `atlas_archive` | `historical_evidence_samples` (Supabase) | **May-3 → present** | ILIKE-ANY over claim terms |

`atlas_archive` is the reason corroboration spans months instead of a week: it is
materialized in Supabase (refreshed nightly) and holds `headline`, `source_url`,
`source_name`, `country_code`, `day` back to May 3. Text match (no embeddings on
that table) is fine here — the ILIKE OR-match is a *recall* pass; a Python
same-event term-recall filter (`SAME_EVENT_TERM_RECALL = 0.40`) then drops loose
matches before a relation is assigned.

## Relation is math, never an LLM stance guess

Same discipline as the reserved `contested` status in the P0.6b module: stance
detection is not a token count, so we don't fake it.

- **figure comparison** — `extract_figure` mirrors `claimLedger.ts` exactly.
  Within `FIGURE_MATCH_TOLERANCE = 0.01` = same figure → *corroborates*;
  materially different → *contradicts*. (The death-toll demo: 4,930 vs 4,734 =
  4.1 % > 1 % → contradicts, matching Carolina's contested-figure table.)
- **same event** — the candidate restates ≥ 40 % of the claim's distinctive
  terms, **or** (hot lane) e5 cosine ≥ `SAME_EVENT_SIMILARITY = 0.86`.
- **relation** — same-event + conflicting figure → `contradicts`; same-event
  with a matching/absent figure or strong term recall → `corroborates`;
  everything weaker → `context` (related coverage, not a restatement).

`is_official_source` mirrors the frontend wire-agency token list plus UN/WHO/gov
bodies, so backend and client agree on what "official source present" means — the
answer to the claim ledger's *"official source missing"* caveat. The verdict
reports `official_corroborating`, so a `CONTRADICTS` pair whose only official/wire
source sits on the *contradicting* side is legible.

## DOC 2.0 honest-degraded contract (Marcos's requirement)

DOC 2.0's free tier throttles hard: **one request / 5 s per IP**, and it answers
over-limit requests with a **plain-text notice, not JSON** (verified live this
session — `"Please limit requests to one every 5 seconds…"`, and separately HTTP
429). The lane must never present a throttled empty result as "nothing
corroborates this."

`doc20_fetch_status` classifies the outcome explicitly:

- HTTP 429 **or** non-JSON body (the notice) → `throttled`
- timeout / connection refused / 5xx → `down`
- JSON with articles → `ok`

`corroborate_claim` records that per-corpus in `source_status`
(`{doc20, atlas_hot, atlas_archive}` each ∈ `ok | throttled | down | unavailable
| not_queried`) and **still returns the Atlas-corpus matches** when DOC 2.0 is
throttled/down. It shares the `external_depth` per-process 1-req/5 s throttle so
this lane never trips the limit on top of the depth lane. The frontend renders
"external corroboration temporarily unavailable — showing Atlas-corpus matches"
from `source_status`, pre-announcing the gap rather than hiding it.

## Per-receipt inline verdict

`citation_verdict(matches)` → `{status, corroborating, contradicting,
official_corroborating, note}`, where `status ∈ {corroborated, contradicted,
uncorroborated}`. This is the compact chip the dossier renders next to a Citation
(Phase 2): *"corroborated by N sources, incl. M official/wire"* /
*"contradicted by K"* / *"no corroborating coverage found in the queried
corpora."* The same endpoint serves both the full match view and this verdict, so
the dossier can show a chip per receipt and expand to the matches on demand.

## Live smoke (real DOC 2.0)

Run this session against the real API. GDELT's per-IP throttle is aggressive: the
first smoke tripped it, and the lane **correctly** reported
`source_status.doc20 = "throttled"` while the Atlas lanes remained available —
i.e. the honest-degraded contract was exercised end-to-end against the live API,
not a mock. (A clean `ok` response requires respecting the 5 s spacing from a
cold IP; the degraded path is the one that matters for publishability and it is
proven live.) See the session log for the raw throttle-notice body.

## Not in scope / follow-ups

- No Fly deploy (per the lane brief). The endpoint is registered and import-clean;
  it ships on the next backend deploy.
- Frontend wiring of the verdict chip + `source_status` banner is a separate lane.
- `atlas_hot` matches don't carry `source_url` from the current
  `fetch_semantic_signal_matches` join (url is `null`); dedup falls back to the
  headline key. Adding `s.source_url` to that SELECT is a cheap follow-up.
- Prose-vs-tables validator (Phase 3b) consumes this lane's measured verdict so
  generated prose is never "confirmed" while corroboration is unmeasured.
