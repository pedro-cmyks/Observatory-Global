# Reliability Sweep — 2026-07-27

**Origin:** a 5-auditor fleet (issues · roadmap · residuals · product · health) run after the
Eclipse ship. Every item below carries measured evidence from that audit or from this session.

**Already done today (context):** L1 front page restored + hardened (`c4b6ffa3`), stats honesty
(`1c89271b`), loud provider exhaustion (`e658dddf`), heavy-lock ledger de-spam (`26391599`),
merged + deployed (`be37a543`).

---

## Wave 1 — measured breakage, disjoint files, ship today

| # | Item | Evidence | Effort |
|---|---|---|---|
| 1.1 | **Person-focus timeline is dead in prod** — rewrite the `unnest/ILIKE` predicate onto the trigram index that now exists | `/api/v2/focus/trump/timeline?focus_type=person` → volume degraded, key_subjects + voice_mix unavailable, while `country` is fully live. `focus_timeline.py:343` `EXISTS (SELECT 1 FROM unnest(persons) pp WHERE LOWER(pp) LIKE …)` + stale comment `:346 "No index over persons"`. Prod has `idx_signals_v2_persons_text_trgm` on `f_unaccent(lower(f_arr_text(persons)))`, `indisvalid=true`, 108 MB | S |
| 1.2 | **Cache `/api/v2/attention/eclipse`** — 24s uncached, polled every 4 min by every open tab | Prod 200 in 23.9s vs `/threads` 6.8s. `attention_eclipse.py:112-130` has zero cache hits on grep, `statement_timeout=45000`, 3 SQL blocks/request. `EclipseModeContext.tsx:7` `POLL_MS = 4*60*1000`. Copy the pattern at `universe.py:411-424` | S |
| 1.3 | **Repair the corrupt 2026-07-25 edge snapshot** — clamp weight ≤1, wrap the write in a transaction, delete the partial day | `edge-snapshot.err.log`: `CheckViolationError … topic_edge_snapshots_weight_check`; `rc=1 @ 2026-07-25T08:15:09Z`. Prod per-day: 07-24 **8053**, 07-25 **3000**, 07-26 **12076** = exactly 6 committed batches of `BATCH_SIZE=500`. Max weight 07-25 = 1 vs 0.97-0.99 elsewhere. `snapshot_topic_edges.py:104,164` — `write_edges` has no enclosing transaction | S |
| 1.4 | **Delete the killed silent-risk endpoint** — closed in docs 07-22 ("DELETE, don't retune"), still mounted and 502-ing | `attention_threads.py:88` `_INFO_DESERT_FLOOR = 40` (measured INVERTED), served `:170`, returned `:304/:325`; mounted `main_v2.py:178`. Prod → HTTP 502 in 16.8s. **Keep** the sibling `coverage-gaps` in the same router (healthy, feeds Under the Radar) | S |
| 1.5 | **`DROP INDEX CONCURRENTLY idx_signals_v2_headline_trgm`** — 420 MB, `idx_scan = 0` for the cluster's life | Superseded by `idx_signals_headline_trgm` (`f_unaccent` form, 409 MB, idx_scan 89) when `5fa3f04c` moved every headline predicate to `f_unaccent`. Pure reclaim + removes GIN maintenance from ~200K daily inserts | XS |
| 1.6 | **Brief empty-state stops promising "stamps land within ~30 minutes"** | Copy asserts a schedule the pipeline cannot honour during an outage | XS |

## Wave 2 — money + hygiene

| # | Item | Evidence | Effort |
|---|---|---|---|
| 2.1 | **Move the 3 LLM crons out of DeepSeek peak** (peak = 2× price, UTC 01-04 and 06-10) | `scoped-snapshot` 22:00 local = **03:00 UTC** 🔴 · `threevendor-calibration` 03:00 = **08:00 UTC** 🔴 · `goldgrowth` 03:30 = **08:30 UTC** 🔴. Valley in local GMT-5: 19-20h, 23-01h, 05-19h. Respect the house rule (no heavy local compute in Pedro's working hours) and the existing heavy-job mutex | S |
| 2.2 | **Close 7 issues with evidence** | #255 (all four marker kinds shipped, `c4986265`), #220 (`stats.py:146 /api/v2/stats/funnel` meets the stated acceptance), #241 (premise stale — the HNSW index it blames is now ivfflat), #263 residues 1-2 (fixed *with* a named regression test), Council N5 (`f666c265`), the `entity backbone df=1` residual (shipped as `cooccur·rarity`), and #265's sub-claim that the persons index is INVALID (it is valid) | XS |
| 2.3 | **#264 close-out** — write-side verified live (0 encoded in 10,682 fresh GDELT rows; backfill repaired 49,573 headlines) but keep it open until Wave 3.2 lands | see 3.2 | XS |

## Wave 3 — bigger, sequenced after 1-2

| # | Item | Evidence | Effort |
|---|---|---|---|
| 3.1 | **Universe is permanently dark (0% availability)** — stop building on the request path; precompute on a schedule and make the handler a pure artifact read | `/api/v2/universe` this session: HTTP 000 after 70s; auditors measured 502 at 32.7s/61.1s and 0/5 success up to 92.5s. `universe.py:166 SET statement_timeout = 90000` — the previous 20s→90s "completion" cannot work because the ceiling is the **Fly proxy**, not the statement timeout, so the cache can never fill and there is never even a stale payload | M |
| 3.2 | **#264 derived-artifact repair** — 208,193 GDELT rows now hold correct headlines against embeddings computed from mojibake | `embed_hot_corpus.py:70-80` selects `LEFT JOIN signal_embeddings e … AND e.signal_id IS NULL` and writes `ON CONFLICT (signal_id) DO NOTHING` — a decoded headline can **never** be re-embedded. Needs a `--reembed-decoded` path (`ON CONFLICT DO UPDATE`, select rows whose headline changed after `embedded_at`), then re-run the script census + `thread_ranking` dedup check | M |

## Deferred / needs Pedro
- **Second LLM provider key** — every sanctioned lane rides one balance; Anthropic dry since ~06-29 (400 verified again today). One top-up away from the same outage.
- **Policy:** what should the Brief do when the label court is provably down for hours? Today `leadConfidence.ts:89` blocks every unstamped thread → desk cards vanish. (Wave 1 fixes the *seal*; this is the *serving* half.)
- ACLED (#46), ReliefWeb (#180), Google OAuth (#262), brand direction (#106) — all credential/decision-gated.
- **Strategic:** the roadmap's Phase 0-4 spine has not advanced since 2026-07-12 while six surfaces shipped. The roadmap's own primary metric — "≥80% of ~20 gold analyst queries answered by a useful thread" — has never been computed because the gold set does not exist.

## Rails
Every item: measured before changed, honest degradation over fabricated values, no silent filtering,
reversible (index drops and cron moves are one command back), and nothing merges without the suite green.
