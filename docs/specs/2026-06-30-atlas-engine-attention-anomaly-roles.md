# Spec — Atlas Engine: the two missing roles (attention + anomaly→movement)

Date: 2026-06-30 · Branch: `v3-intel-layer` · Status: **DRAFT — RE-SCOPED after
self-eval vs the numbers (2026-06-30).** Author: Claude (Opus 4.8). **Companion +
extension** to `2026-06-29-atlas-unified-engine.md` (the approved engine).
Empirical evidence: `2026-06-26-l2-deep-review.md` §3 + §"unified-engine connection".

> **⚠ PRIORITY CAVEAT (self-eval, verified vs live numbers).** This spec enriches
> the EXISTING topic surface — but that surface is tiny: **68 active topics vs
> 176,104 signals/24h = 0.04% coverage.** Both roles only attach to those 68
> topics. So the engine's dominant lever is **RECALL (#229 — scoped regional
> passes to form >68 topics)** and **taxonomy precision (#204 — the measured
> 40–52% on-topic ceiling)**, NOT new roles. The CI fake-disaster was a COVERAGE
> failure (no topic formed); this spec does not fix that — `anomaly→movement`
> only retires the fake *lead*, leaving an honest gap. **Sequence: recall +
> taxonomy FIRST; then `anomaly→movement` (cheap, ships now); `attention` =
> HOLD, data-gated (§2.1).** Do NOT run the hot-PK migration (§3 D1) for the
> attention role until recall makes the topic surface worth enriching.

> **One sentence.** The Unified Engine unified the *embeddable signal* corpus
> (press/forum/event → evidence/discussion/mood/movement) but left two layers as
> separate bolt-ons — **attention** (Wikipedia reading + Google Trends searching)
> and the **alert/volume** layer (country anomaly). The split-brain has **five
> brains, not three**; the engine closed three. This spec adds the last two as
> first-class, A/B-gated, honesty-preserving roles so a topic finally carries
> press + forum + events + **what people read/search** + **its own volume
> elevation** — and the alert layer stops being orphaned country volume.

---

## 1. Why (the verified gap, with the cost)

`topic_members.role` is a 4-value enum (`evidence|discussion|mood|movement`); its
"attention" (#168 `public-led`/`uncoupled-attention`) is **forum-only**. The
unified-engine §14 defers only causal linking — so these two are **unscoped, not
deferred**. The cost is the L2 audit's worst dishonesty:

- **No `attention` role.** `wiki_pageviews_v2` / `trends_v2` are surfaced by a
  side pipeline (`public_attention.py`, AnomalyPanel) and never join a topic. A
  thread can't say "N people read its Wikipedia article / searched its terms."
  C3(b) (semantic trends/wiki) is the frontend symptom; the attention role is the
  root fix that subsumes it.
- **Anomaly never reconciled.** Country volume (`/anomalies`, z-scores) and the
  topic layer are different pipelines = the **§3 split-brain** that produced the
  CI fake-disaster (26× spike → no gate-passing thread → fake "Flood disaster"
  lead). Finding **E** ("XX" anomaly) is the same family: orphaned volume spikes
  with no topic to anchor.

**Why absent:** the engine substrate is "embeddable signal → nearest centroid."
Wiki/trends are *aggregates* (title/keyword+country, not signal text); anomaly is
a *country statistic*. Neither fit "embed a row, assign it."

## 2. The two extensions

### 2.1 `attention` role — Wikipedia + Google Trends  ·  **STATUS: HOLD (data-gated)**
A topic gains an `attention` lane: the people-side reading/searching proxy,
bound to the topic **semantically** (the same machinery C3(b) needs).

**Data reality (verified 2026-06-30, corrects the earlier "trends/wiki is thin"
claim that deferred C3(b)):** the two sources are NOT alike —
- **trends_v2: 24,902 rows/24h across 99 countries** → real volume. The earlier
  "thin" call over-generalized the CI-specific 0. Trends is worth binding FIRST.
- **wiki_pageviews_v2: 1,700 rows/7d across 17 countries** → genuinely thin +
  evergreen-noisy (the D fix). Wiki waits on #104 / better coverage.
Even so, both bind only to the **68 active topics**, so attention volume is
capped by the topic surface, not the source — which is why this whole role is
HOLD behind recall (#229). Build the trends half first, and only after recall
makes more topics; skip wiki until its coverage improves.

- **Source rows:** `wiki_pageviews_v2.article_title` (+ `language`, `views`,
  `fetch_date`, `country_code`) and `trends_v2.keyword` (+ `approximate_volume`,
  `hour_bucket`, `country_code`).
- **Binding:** embed the title/keyword via the e5 embed service (`research_semantic
  .embed_texts`, `passage: {text}`), cosine vs `dynamic_topics.centroid_vec`,
  threshold (knob, start 0.80 like C3-forum), country+time co-occurrence as a
  weak prior. NOT lexical theme-code (today's dead path for dynamic topics).
- **Honesty (carried invariants):** `attention` is `verified=false`, NEVER
  evidence, never folded into `gated_signal_count`. It is a *third lens* beside
  discussion/mood — what the public READS/SEARCHES, distinct from what it SAYS
  (discussion) and FEELS (mood). Surface the wiki **edition language** (a `de`
  spike about a country = German-audience attention, not local — the §4.2 honesty).
- **Payoff:** #168 `public-led` / `uncoupled-attention` finally differentiate on
  real reading/searching data, not forum-only. Closes C3(b). Makes "searched +
  discussed + reported" cross-surface corroboration real (L2 §4.2).

### 2.2 `anomaly → movement` — per-topic volume-vs-baseline
The alert layer becomes a **property of the topic**, not an orphaned country stat.

- **Compute:** per topic, signal volume per hour (count `topic_members` role=
  evidence by `assigned_at`) vs a trailing baseline (e.g. 168h median) → a
  z-score / multiplier the topic carries. This is the construction-side root fix
  the L2 **B1** serving fix ("critical from the thread's own movement") was the
  down payment for.
- **Not a member row — a topic property.** Lighter than §2.1: no new member
  references, just a per-topic computed field (materialize in a small
  `topic_movement` table or as a serving-time CTE). Distinct from the
  event-`movement` role (vessels/ACLED, #232) which needs the member-ref schema
  (§3); this is volume-baseline, computable from `signals_v2`/`topic_members`
  ALONE — so it ships WITHOUT the #232 blocker.
- **Payoff (precise — not over-claimed):** retires the fake *lead* — a
  below-gate single thread dressed as "critical" stops leading, because its OWN
  movement is nil. It does NOT fix the CI root, which was a COVERAGE failure (no
  topic formed for the 26× surge); that needs recall (#229). So the honest
  outcome on a CI-class country becomes "volume spike, no verified moving thread"
  — the honest gap the L2 review wanted, not a fabricated disaster. "XX" is
  already handled at the frontend (finding E); this reconciles it at the source.

## 3. Schema

- **Role enum:** `ALTER` the `topic_members.role` CHECK to add `'attention'`
  (migration). Roles → `evidence|discussion|mood|movement|attention`.
- **Non-signal member reference (the unifying extension).** `topic_members` PK is
  `(signal_id, topic_id, role, engine_version)`, `signal_id` NOT NULL — but
  wiki/trends rows are not `signals_v2`. Add `member_kind TEXT` (`signal|wiki|
  trend|event`) + `member_ref TEXT` (the source-table id; equals `signal_id::text`
  for signals); make `signal_id` nullable; PK → `(member_kind, member_ref,
  topic_id, role, engine_version)`. **This same extension unlocks event-`movement`
  (#232)** — one schema change, two roles. *(Decision D1: this vs a separate
  `topic_attention` table — see §7.)*
- **Movement (anomaly) property:** `topic_movement(topic_id, window_end,
  volume, baseline, zscore, multiplier, engine_version)` — small, recomputed on
  the cron. No member rows.

## 4. Honesty invariants (verbatim from the engine spec)
Evidence never mixes discussion/mood/movement/**attention**. `gated_signal_count`
stays evidence-only. `verified=false` on social AND attention. No silent
filtering — attention items show provenance (`wikipedia:<lang>` / `google_trends`)
+ a coverage note when empty (never a silent blank). GDELT themes stay an optional
feature until the P1 ablation.

## 5. A/B measurement (same gate as the rest of the engine)
Extend `engine_ab_report.py`: with-attention vs without on (a) #168 type
differentiation (does `public-led`/`uncoupled-attention` ever fire on real data?),
(b) cross-surface corroboration rate, (c) anomaly→movement vs the old country
z-score on the CI-class cases (does the fake-disaster stop leading?). Flag-gated
(`ATLAS_ENGINE_ATTENTION`, `ATLAS_ENGINE_TOPIC_MOVEMENT`), isolated
`engine_version`, cutover only on measured win — identical discipline to F3/F4.

## 6. Phases (executable; heavy steps OFF-PEAK around the embed cron)

> **Re-sequenced (self-eval):** the engine's lead work is **recall (#229) +
> taxonomy (#204)**, tracked separately — those go FIRST. Of the G-phases below,
> only **G2 (`anomaly→movement`, no heavy compute) is near-term**; G0/G1 (the
> `attention` role + its hot-PK migration) are **HELD** until recall makes the
> topic surface worth enriching and the trends-half is validated. Do not run G0
> for attention alone.

- **G0 — schema (no compute).** Migration: role CHECK + `member_kind`/`member_ref`
  (nullable `signal_id`) + `topic_movement`. Reversible. *Daytime-safe.*
- **G1 — attention binding (compute → off-peak).** A cron step after the embed
  cron: embed recent wiki/trends text (bounded N per run, magnitude-ranked),
  cosine vs active-topic centroids, write `attention` members
  (`engine_version='attention-v1'`, `verified=false`). Reuses `embed_texts` +
  the C3-forum ANN pattern. Runs on the M1 embed schedule (17:30/23:30/05:30),
  NOT during work hours.
- **G2 — anomaly→movement (no heavy compute).** Pure-SQL per-topic volume-baseline
  → `topic_movement`, on the 30-min classifier cron (counting, cheap). *Daytime-safe.*
- **G3 — serving (no compute).** `/theme/{id}` adds an ATTENTION section (badged,
  edition-language, corroboration chip); `/topic/{id}/relationship` reads real
  attention counts; AnomalyPanel/Brief "critical" reads `topic_movement` not
  country volume. ThemeDetail C3(b) section swaps lexical→attention members.
- **G4 — A/B + cutover (off-peak).** Run the §5 report; flip serving flags only
  on a measured win.

## 7. Decisions (need Pedro) + defaults I'll take if silent
- **D1 — member-ref vs separate table.** *Default:* extend `topic_members`
  (member_kind/member_ref) — on-thesis ("ONE typed table") + unlocks #232 movement
  too. *Alt:* a separate `topic_attention` table (less invasive to the hot PK,
  but re-splits the model). I lean extend.
- **D2 — attention magnitude in ranking.** Does attention volume feed thread
  RANKING, or stay a lens only? *Default:* lens only at first (honesty: reading ≠
  importance — same volume≠importance principle as Paper 3); revisit after A/B.
- **D3 — anomaly→movement replaces vs augments the country anomaly.** *Default:*
  augments now (topic movement is the new lead signal; country anomaly stays as a
  separate "volume spike" badge, honestly labeled), full replacement after G4
  proves the CI-class cases are fixed.

## 8. Risks / guardrails
- **Compute discipline (the crash lesson):** G1 embed runs ONLY on the M1 embed
  schedule, bounded N, efficiency cores — never stack during work hours (M1
  crashed at load 177). G0/G2/G3 are no-heavy-compute.
- **Hot-PK migration:** the `topic_members` PK change (D1) is the riskiest DDL —
  do it reversibly, off-peak, after backing up the v1-compat ETL parity check.
- **Attention noise:** wiki/trends are noisy (the D fix proved it). The semantic
  threshold + `verified=false` + edition-language label keep it honest; bind only
  ABOVE threshold (uncoupled-attention is the honest gap, not a forced match).
- **Don't regress F3/F4:** this is additive to the unified-v2 build; A/B isolated.

## 9. Cross-refs (corrected — honest paper mapping)
L2 §3 (split-brain) + §"unified-engine connection"; unified-engine spec (roles,
#168, A/B discipline); C3(b) (subsumed by §2.1); finding E (orphaned volume);
#232 (event-movement — unlocked by the §3 member-ref); #172 (silent-risk ratio);
#104 (wiki coverage the attention role waits on).
**Papers (self-eval corrected):**
- **Paper 8 (open-set discovery / recall)** — the paper the numbers actually
  point to (0.04% coverage). This spec does NOT serve it; recall (#229) does.
  Flagged so we don't mistake role-enrichment for the coverage result.
- **Paper 3 (volume≠importance)** — `anomaly→movement` + D2 (attention-as-lens,
  not ranking). SOLID.
- **Paper 7 (people-side proxy, honest surfacing)** — the `attention` lens, once
  data + recall support a measurable result.
- **Paper 1 (evidence-role classification)** — WEAK link (earlier over-claimed):
  `attention`/`anomaly` are `verified=false` / non-evidence, so they don't touch
  the evidence-role experiment. Paper 1's real ceiling is taxonomy (#204, the
  40–52% on-topic), not roles.
