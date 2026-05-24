# Project Status

## Current Handoff — 2026-05-24 (Living Narrative Threads M1 + M2 + M3a)

### What shipped this session

Three branches, two merged to `v3-intel-layer`, one in open PR.

| PR | Title | State | Branch |
|---|---|---|---|
| [#209](https://github.com/pedro-cmyks/Observatory-Global/pull/209) | feat(threads): living Narrative Threads beta (M1) | MERGED `9669755` | `codex/living-threads-canon` (deleted) |
| [#210](https://github.com/pedro-cmyks/Observatory-Global/pull/210) | feat(briefing): top living Narrative Threads (M2) | MERGED `5d9ef8d` | `codex/brief-top-threads-m2` (deleted) |
| [#211](https://github.com/pedro-cmyks/Observatory-Global/pull/211) | feat(threads): enrich response with parent_domain, entities, timeline (M3a) | OPEN, CLEAN, MERGEABLE, Vercel SUCCESS | `codex/threads-enrichment-m3a` |

Issue [#207](https://github.com/pedro-cmyks/Observatory-Global/issues/207) umbrella commented after each milestone.

### Milestone 1 — read-only `/api/v2/threads` beta (PR #209)

- New service `backend/app/services/thread_intelligence.py` (~370 lines).
- New router `backend/app/routers/threads.py` exposing:
  - `GET /api/v2/threads?hours=N&limit=M`
  - `GET /api/v2/threads/{thread_id}?hours=N`
- Contract `living-narrative-threads-v0`. Thread fields: `thread_id`, `label`, `summary`, `anchor_topics`, `signal_count`, `source_count`, `country_count`, `changed_10h`, `sentiment_swing_10h`, `top_countries`, `top_country_names`, `top_sources`, `source_mix`, `confidence` band, `why_now`, `subthreads`, `related_threads`, `evidence_samples`.
- `confidence_band()` classifier with thresholds `high / medium / thin / degraded` over evidence count, source diversity, geographic spread, and average assignment confidence.
- Stable `thread_id` of the form `<topic-slug>--<cc1>-<cc2>-<cc3>` so the detail endpoint round-trips.
- First live verification confirmed the endpoint contract, deduped evidence shape,
  and movement fields. The later quality audit supersedes the initial optimistic
  read of topic coherence.

**Bug fixed before merge:** initial evidence sample for `armed-conflict-escalation` surfaced the same syndicated headline 25 times across US wire affiliates. `THREAD_EVIDENCE_SQL` now `DISTINCT ON (LOWER(headline))` inside a subquery, exposes `syndication_count` via window function, and the serializer reports `evidence_role` (`representative` / `repeated` / `syndicated`).

### Milestone 2 — Brief consumes `top_threads` (PR #210)

- `fetch_threads(conn=...)` refactor with new `_fetch_threads_with_conn` helper so the briefing handler reuses its open pool connection. The threads router and the briefing reader share a single executor.
- Briefing handler calls `fetch_threads(hours=hours, limit=10, conn=conn)` after `top_atlas_topics` and degrades to `[]` via the same `degraded_segments` pattern used elsewhere.
- Response gains `top_threads` and `top_threads_contract: "living-narrative-threads-v0"`.
- Limit configurable via `BRIEFING_TOP_THREADS_LIMIT` (default 10).
- Deployed to Fly (`atlas-api-pedro`) via `scripts/deploy-fly-api.sh`. Live `/api/v2/briefing?hours=24` returns `top_threads` populated and the thread contract correct. Other briefing segments may still degrade independently.

### Milestone 3a — enrich `/api/v2/threads` for frontend parity (PR #211, open)

After looking at the visible NarrativeThreads card on mobile, **clarified product direction**: `atlas_topics` are internal anchors, not the visible taxonomy. All Narrative Threads are live by definition because Atlas keeps ingesting and reprocessing signals. The existing `NarrativeThreads.tsx` is the visible product surface and the backend work is for enriching the data that feeds it, not adding parallel sections.

M3a adds the fields required so M3b can swap `NarrativeThreads.tsx` from `/api/v2/narratives` (raw GDELT theme codes) to `/api/v2/threads` (atlas-enriched living threads) without losing any per-card slot:

| New field | Drives |
|---|---|
| `parent_domain` (e.g. `conflict-security`) | Cluster badge replacing `getThemeCluster()` |
| `avg_confidence` (float) | Numeric form of the existing % confidence pill |
| `first_seen` (ISO timestamp) | `Started Xh ago` pill |
| `top_entities` (raw values from `signals_v2.persons`) | Audit-only entity signal; not frontend-ready as a people chip |
| `hourly_timeline` (JSONB array of `{hour, count}`) | Sparkline |
| `trend` (`surging` / `stable` / `fading`) | Direction pill derived from `changed_10h / signal_count` ratio |

**Performance work:**
- `COUNT(*)` replaces `COUNT(DISTINCT signal_id)` in `topic_agg`. PK `(signal_id, topic_id, method, model_version)` already guarantees uniqueness within (topic, model_version) groups, so the DISTINCT was paying for a sort that returned the same value. EXPLAIN ANALYZE showed the `GroupAggregate` sort cost dominated.
- The `scoped` CTE (`signal_topic_assignments` JOIN `signals_v2` JOIN `atlas_topics` over ~25k rows in 24h) is the floor cost at ~700ms in production.
- Threads router gains Redis cache: 5min on `/threads`, 3min on `/threads/{id}`. Brief calls `fetch_threads(conn=...)` directly and is independently cached at 15min.

**Tests:** 34 passed across `test_thread_intelligence`, `test_threads_router`, `test_briefing_performance_shape`. New coverage:
- `assemble_thread_contract` verifies all 6 new fields land in the assembled dict.
- `trend_label_classifies_volume_delta` covers surging/stable/fading + divide-by-zero guard.
- `threads_sql_exposes_enriched_fields` locks SQL shape.
- `threads_router_caches_responses_in_redis` pins cache keys + TTL constants.

**Live verification on production data:**

| topic_slug | parent_domain | signal_count | top_entities | timeline_points |
|---|---|---|---|---|
| armed-conflict-escalation | conflict-security | 7401 | donald trump, selina wang, andrew wolfe | 31 |
| gang-control-urban-security | conflict-security | 2355 | donald trump, selina wang, kash patel | 31 |
| gender-violence-rights | social-unrest-labor | 1490 | jesus christ, darren jones, keir starmer | 31 |
| water-stress-drought | climate-disaster | 635 | el nino, vladimir putin, pacific ocean | 31 |
| election-legitimacy-dispute | political-legitimacy | 1540 | ahmed tinubu, pedro sanchez, marie machado | 31 |

### Quality issues identified before UI promotion

1. **Entity typing in `signals_v2.persons`** — "jesus christ", "el nino", "pacific ocean" appear as `top_entities`. Some are not necessarily noise: `El Niño` and `Pacific Ocean` can be meaningful climate/geography entities. The defect is that they are stored/exposed through a person-like field without type. NER needs a person/place/organization/event/climate disambiguation pass.
2. **Mobile UX** — signal stream growth pushes NarrativeThreads card off-screen on mobile. Needs sticky container, max-height with internal scroll, or carousel pattern, but this should wait until data quality gates are clear.
3. **`countries_v2` data quality** — rows where `name == code` for non-FIPS codes (e.g. RB="RB", BW="BW"). Threads degrade gracefully via `COALESCE(c.name, s.country_code)` but labels read "intensifies in Italy and RB" when these enter top-2.
4. **Aggregator dominance in `top_sources`** — `zazoom.it` (IT aggregator) tops 6 of 10 threads. Source ranking should weight against aggregator domains; currently shows highest-count source regardless of independence.
5. **US dominance in `top_countries`** — same #149 volumetric bias leaks into thread geography. Threads should probably use a heat-voluminous-style adjusted ranking.
6. **Label voice variation** — "X intensifies in Y and Z" repeated 10× per Brief is mechanical. Atlas voice should vary verb/structure per card.

### Quality audit correction — 2026-05-24 PM

`docs/research/2026-05-24-thread-quality-audit.md` supersedes the earlier quick
read that "all 10 returned threads were coherent." A random sample shows mixed
quality:

- Strong or promising: `heat-health-risk`, `mining-royalty-risk` (but label
  should become mining/resource risk), `sanctions-diplomatic-pressure`, and
  selected `food-price-stress` evidence.
- Needs tuning before UI promotion: `armed-conflict-escalation`,
  `disease-outbreak`, `labor-strike-disruption`,
  `election-legitimacy-dispute`, `water-stress-drought`,
  `forced-displacement`.
- Not ready for UI promotion: `gender-violence-rights` and
  `transport-corridor-disruption`.

Entity clarification: NER means Named Entity Recognition. `El Niño` and
`Pacific Ocean` may be valid entities in climate contexts, but they are not
persons. Do not expose `signals_v2.persons` as a generic frontend person chip
row without entity typing.

### Quality-first M3a patch — local implementation

New product model docs:

- `docs/specs/2026-05-24-atlas-focus-model.md` — defines Thread, Country,
  Entity, Signal, and Workspace Focus. Main decision: Narrative/Thread Focus is
  the strongest analytical unit; country and entity/person focus should become
  lenses into active threads.
- `docs/superpowers/plans/2026-05-24-thread-first-focus-quality.md` — next
  implementation plan for patching #211 quality metadata, adding repeatable
  thread audit, then preparing focus types/copy without swapping UI early.

Implemented locally on branch `codex/threads-enrichment-m3a`:

- `/api/v2/threads` assembly now exposes additive quality metadata:
  `quality.lex_pct`, `quality.method_mix`, `quality.source_flags`,
  `quality.geo_flags`, and `quality.entity_flags`.
- `top_entities` remains raw audit-only compatibility data. New `top_people`
  is intentionally `[]` until typed entity support exists.
- `lex_pct` is derived from assignment `evidence.lex_count`, not from
  `method='lexicon'`, because the v2 classifier writes all rows under the
  `lexicon` method and stores actual lexical support in JSON evidence.
- Added repeatable audit script:
  `backend/scripts/thread_quality_report.py`.
- Added frontend focus preparation only: `thread` and `entity` are valid focus
  types, `person` remains compatible, and FocusSummaryPanel copy now frames
  evidence/source/thread context without claiming typed entities.
- Legacy backend safety: `thread` and `entity` live in `GlobalFilter`, but the
  outbound legacy `focus` object still maps them to backend-safe `theme` and
  `person` params until native Thread/Entity Focus endpoints exist.

Still do not swap `NarrativeThreads.tsx` to `/api/v2/threads` until a fresh
quality audit passes.

### Next session — rerun quality audit, then decide Milestone 3b

After deployment or local API verification with the new quality metadata,
re-run:

```bash
cd backend
./.venv/bin/python -m scripts.thread_quality_report \
  --api-url http://localhost:8000 \
  --hours 24 \
  --limit 15 \
  --out ../docs/research/thread-quality/YYYY-MM-DD-thread-quality-snapshot.md
```

Only then:

Before M3b, merge #211 and redeploy Fly so `/api/v2/threads` serves the enriched response. Then:

- `frontend-v2/src/components/NarrativeThreads.tsx`: replace `fetch('/api/v2/narratives?hours=N&limit=M')` with `fetch('/api/v2/threads?hours=N&limit=M')`. Map fields:
  - `theme_code` → `thread_id`
  - `getThemeLabel(theme_code)` → `label` (raw, no transform)
  - `getThemeCluster(theme_code)` → `parent_domain`
  - momentum → `trend` (`surging`/`stable`/`fading`)
  - `top_countries` → `top_countries`
  - signal count → `signal_count`
  - entity chip row → only typed entities; do not map directly to `top_entities`
  - sparkline → `hourly_timeline`
  - "Started Xh ago" → `first_seen`
  - % confidence → `avg_confidence`
- Click handler default: keep `setFocus('theme', anchor_topic_slug, label)` so existing ThemeDetail still works. M4 introduces a real ThreadDetail panel per the spec audit.
- Use `why_now` as tooltip on the card or inline subtitle.

### Operational state

- Cron `com.atlas.atlas-topic-classifier.plist` still running every 30 min — feeds fresh assignments into all three reads (`/api/v2/threads`, `/api/v2/briefing` → `top_threads`, `/api/v2/briefing` → `top_atlas_topics`).
- Fly API live at `9669755 + 5d9ef8d` (M1 + M2). M3a not yet deployed (waiting on PR #211 merge).
- Vercel auto-deploys frontend; no frontend changes shipped this session, so no Vercel deploy was triggered for the threads work.

---

## Previous Handoff — 2026-05-23 (Path A pilot — mig 036 multilingual lex)

### What shipped this session

Branch `feat/path-a-pilot-election-multilingual-lex`. One migration file, no code change.

**GitHub roadmap**
- Issue #202 — Path A: Multilingual lexicon expansion via LLM (atlas-topics) ← THIS pilot
- Issue #203 — Path B: Bootstrap-trained encoder classifier
- Issue #204 — Path C: LLM-assisted taxonomy revision (quarterly)
- All three issues link to `docs/specs/2026-05-23-ai-assisted-taxonomy.md`.

**Migration**
- `backend/migrations/036_election_legitimacy_multilingual_lex.sql` — expands `atlas_topics.lexicon_terms` for `election-legitimacy-dispute` from 5 English terms to 43 terms across 8 languages (EN/ES/IT/PT/FR/DE/TR/EL).

### Pilot methodology (validated for rollout)

1. Topic selection: lex_pct < 20%, vol > 500/24h → `election-legitimacy-dispute` (6.3%, 1502/24h).
2. SQL sample pull (Supabase MCP): 25 high-confidence positives, 30 theme-only negatives.
3. Claude (the LLM in this implementation) reads samples and proposes 39 candidate substring matchers across the languages observed in the headlines.
4. SQL verification per candidate: `LIKE` against 24h headlines for volume + 4-headline random sample for precision per heavy hitter.
5. Rejected `scrutin` (matched "scrutiny", "escrutinável", ~25% precision). Accepted 38.
6. Migration applied via `apply_migration`. Deleted 1,508 prior assignments. Re-backfilled 1,194 fresh assignments.

### Live results

| Metric | Pre mig 036 | Post mig 036 |
|---|---|---|
| election-legitimacy lex_pct | 6.3% | **31.6%** (5× lift, gate cleared) |
| election-legitimacy high_conf | 5 | **27** (5×) |
| election-legitimacy v2_sigs | 1,502 | 1,194 (noise filtered) |
| Global coverage (24h) | 13.08% | 13.35% |

**Term distribution post-pilot** (74% of lex hits came from multilingual terms):

| Term | Lang | Hits |
|---|---|---|
| elecciones | ES | 156 |
| elezioni | IT | 101 |
| presidential primary | EN | 68 |
| ballot | EN (existing) | 31 |
| comicios | ES | 12 |
| urnas | ES | 9 |
| ... | mixed | tail of 1-2 hits each |

### Methodology rollout candidates

The 5 remaining topics with lex_pct < 20% and meaningful volume:

| Topic | lex_pct | vol/24h |
|---|---|---|
| armed-conflict-escalation | 2.2% | 3,165 |
| fuel-subsidy-unrest | 10.4% | 886 |
| mining-royalty-risk | 12.5% | 120 |
| housing-cost-pressure | 13.6% | 774 |
| food-price-stress | 19.0% | 817 |

Each is a single-session pass following the same workflow.

### Operational state

- Cron `com.atlas.atlas-topic-classifier.plist` keeps refreshing every 30 min — the new election-legitimacy terms are now part of every cycle.
- No backend deploy needed (data-only mig). Mig is already live on Supabase.
- 4 PRs merged today: #198 (briefing top_atlas_topics), #199 (mig 034 precision), #200 (mig 035 recall), #201 (hierarchy + related_topics). This is PR #205.

---

## Previous Handoff — 2026-05-23 (briefing hierarchy + related topics + AI taxonomy spec)

### What shipped this session

Branch `feat/briefing-hierarchy-related-topics`. One backend file, one test file, one new spec doc, no migrations.

**API**
- `backend/app/routers/briefing.py` — `/api/v2/briefing` now returns:
  - `topics_by_domain`: parent_domain → [topics] hierarchy (10 domains, 2-5 topics each)
  - `related_topics`: topic_slug → [top-3 co-occurring topics] map (Jaccard-proxy strength)
- Both queries only touch `signal_topic_assignments` (no signals_v2 join) — assigned_at is the time filter. Critical perf detail: the related_topics CTE without signals_v2 join runs in **47 ms**; with it, 605 ms (13× slowdown).

**Tests**
- `backend/tests/test_briefing_performance_shape.py` — two new shape tests pin the SQL shape, the assigned_at filter, the Jaccard formula, and block regressing back to the signals_v2 join. Full backend suite: **319 passed, 6 skipped**.

**Spec**
- `docs/specs/2026-05-23-ai-assisted-taxonomy.md` — three paths for AI-assisted taxonomy expansion. Not implemented yet. Sequencing recommends Path A (multilingual lex via LLM) first.

### Why this matters

Analyst question: "the variety of topics is very important, right? Could there be clustering, big themes contain subthemes? When a topic enters, does the system tell me this is related to those other topics?"

Answer: the hierarchy already existed in `atlas_topics.parent_domain` but was not exposed in the API. The co-occurrence signal was also already in the data (1,698 signals had 2 topics in 24h, 18 had 3 — the v2 classifier allows top-2 per signal). This session exposes both without writing any new models or migrations.

### Live data after deploy

Top co-occurrence pairs (24h, currently in API):

| Topic A | Topic B | Co-signals | Narrative |
|---|---|---|---|
| fuel-subsidy-unrest | labor-strike-disruption | 373 | Economic protest cluster |
| food-price-stress | housing-cost-pressure | 210 | Cost-of-living |
| water-stress-drought | flood-landslide-disaster | 149 | Water cycle disruption |
| fuel-subsidy-unrest | food-price-stress | 123 | Inflation chain |
| migration-border-pressure | forced-displacement | 95 | Migration |
| armed-conflict-escalation | forced-displacement | 56 | War → refugees |

These are conceptually coherent — co-occurrence detection works as a related-topic mechanism without any ML.

### Sentiment vs. tone (analyst clarification)

Same metric (avg polarity), different sources. The briefing already returns a `sentiment_source` label per row: `gdelt` (V2Tone), `nlp` (transformer), or `nlp_weighted` (confidence-weighted mix). The frontend may show the word "tone" in legacy places and "sentiment" in newer ones — both refer to the same numeric scale; the source label disambiguates provenance. Documented in CLAUDE.md.

### AI taxonomy — current state and proposed path

- **Current**: zero ML for topics. Rule-based (lex substring + theme intersection). Sentiment uses pre-trained `xlm-roberta-base`, never fine-tuned on Atlas data. NER and framing use pre-trained spaCy / distilroberta NLI — also never fine-tuned.
- **Proposed (spec, not implemented)**:
  - Path A: LLM expands `atlas_topics.lexicon_terms` per topic with multilingual variants. Single migration. 4 hours total. Targets the 64% `xx` recall gap.
  - Path B: bootstrap-trained sentence encoder on the 21,919 high-confidence v2 assignments. New worker + new table. 2-3 weeks. Refines, doesn't replace, the lex classifier.
  - Path C: LLM proposes taxonomy revisions (split/merge/add/retire topics) every 4-8 weeks based on the unclassified pool.
- Sequencing: A first, then B once A confirms data richness, then C quarterly.

### Operational state

- Cron `com.atlas.atlas-topic-classifier.plist` still running every 30 min — feeds fresh assignments that flow into both top_atlas_topics, topics_by_domain, and related_topics.
- Three open PRs from earlier today already merged (197, 198, 199, 200). This work is PR #201.

---

## Previous Handoff — 2026-05-23 (mig 035+035b — recall lift + global coverage audit)

### What shipped this session

Branch `feat/atlas-topic-hint-recall-mig-035`. Two migration files, data-only (no code changes).

**Audit (Supabase MCP, 24h window)**:
- 119,129 signals eligible (headline length >= 20)
- 12,787 (10.73%) received any atlas_topic — **89% unclassified**
- Of unclassified: 87% HAVE themes (classifier wasn't matching them), 64% in `xx` language (multilingual lex gap)
- Pareto: 4 topics = 50% volume, 10 = 80%, 19 = 95% — diversity OK across 30 active topics / 10 domains

**Migrations**
- `backend/migrations/035_atlas_topic_hint_recall.sql` — adds GDELT codes that appear frequently in signals_v2 but weren't in any hint. Sample-verified precision per candidate; only added hints with >=75% sample precision.
- `backend/migrations/035b_disease_outbreak_restore_medical.sql` — corrects a mistake in mig 035 that dropped MEDICAL from disease-outbreak by analogy with mig 034's heat-health-risk fix. MEDICAL is noisy for heat-health-risk but specific for disease-outbreak during a live Ebola outbreak.

### Live measurement (Supabase MCP)

Coverage **10.73% → 13.08%** (+2.35pp = +2,770 signals/24h classified).

Per affected topic:

| Topic | Pre sigs | Post sigs | Pre high_conf | Post high_conf | Notes |
|---|---|---|---|---|---|
| disease-outbreak | 5,246 | 4,719 | 142 | **590** | Ebola-specific hints lift confidence 4× |
| armed-conflict-escalation | 2,121 | 3,165 | 1 | 21 | TERROR adds +1,044 sigs |
| forced-displacement | 332 | 362 | 2 | 2 | EVACUATION small lift |
| sanctions-diplomatic-pressure | 236 | 230 | 1 | 0 | WB_2473_DIPLOMACY |

### Sample-verified hint methodology

Tested precision per candidate hint via random sample of 24h headlines:

| Hint | Volume/24h | Sample precision | Added? |
|---|---|---|---|
| TERROR | 3,899 | 4/4 conflict | ✅ armed-conflict |
| WB_2473_DIPLOMACY_AND_NEGOTIATIONS | 982 | 4/4 diplomacy | ✅ sanctions-diplomatic |
| EVACUATION | 574 | 3/4 evac | ✅ forced-displacement |
| WB_2663_EBOLA | 967 | 10/10 Ebola | ✅ disease-outbreak |
| TAX_DISEASE_EBOLA | 715 | 10/10 Ebola | ✅ disease-outbreak |
| TAX_DISEASE_DISEASE | 2,001 | mostly disease | ✅ disease-outbreak |
| CRISISLEX_T02_INJURED | 12,091 | ~30% conflict (accidents mixed) | ❌ rejected |
| WB_2462_POLITICAL_VIOLENCE_AND_WAR | 1,012 | 2/4 (Airbus/Albanian noise) | ❌ rejected |
| WB_2495_DETENTION_PRISON | 1,041 | 2/4 (random noise) | ❌ rejected |
| CRISISLEX_C06_WATER_SANITATION | 673 | 1/4 (butchery/storage noise) | ❌ rejected |
| SCANDAL | 970 | 1/4 (meta-news + humor) | ❌ rejected |
| WB_2507_HUMAN_RIGHTS_ABUSES | 538 | 1/4 (random) | ❌ rejected |

### Operational lesson (added to CLAUDE.md)

Dropping a broad hint (like MEDICAL) requires per-topic precision measurement, not analogy. MEDICAL is 99% noise for heat-health-risk but 50% signal for disease-outbreak during an active outbreak. Mig 035's analogy reasoning cost 447 lex-supported disease assignments; mig 035b restored them.

### Next recall levers

- 64% of unclassified is `xx` language (multilingual lex gap). #185 extended to atlas_topics is the largest remaining lever.
- 3 topics still at <10% lex_pct (election-legitimacy 6.3%, fuel-subsidy 10.4%, mining 12.5%) — candidates for similar audit pass.

---

## Previous Handoff — 2026-05-23 (mig 034 — atlas topic hint precision fix)

### What shipped this session

Branch `feat/atlas-topic-hint-precision-mig-034`. Single migration file, no code changes (data-only fix). Cron + briefing pick up the new hints automatically.

**Migration**
- `backend/migrations/034_atlas_topic_hint_precision.sql` — prunes overly-broad GDELT theme hints from 8 atlas_topics that were producing false positives, expands lexicon_terms 4-7 → 15-18 with natural-language phrases real headlines use.

### Why this matters

After PR #198 surfaced `top_atlas_topics` in the briefing, per-topic audit revealed catastrophic false-positive rates on the topics dominating the ranking:

| Topic | Pre-034 sigs/24h | lex_pct | Worst hint |
|---|---|---|---|
| constitutional-institutional-crisis | 5,522 | 4.7% | `EPU_POLICY_GOVERNMENT` matches any government story |
| telecom-internet-shutdown | 4,100 | 1.0% | `WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES` matches any IT |
| heat-health-risk | 3,584 | 1.1% | `MEDICAL` matches any medical headline |
| currency-debt-stress | 2,338 | 0.0% | `TAX_ECON_PRICE` matches any equity/commodity price story |
| disinformation-influence-operation | 1,988 | 2.8% | `WB_694_BROADCAST_AND_MEDIA` matches all media |
| press-freedom-crackdown | 1,452 | 0.3% | `ARREST` matches any arrest story |
| student-youth-protest | 1,060 | 0.3% | `EDUCATION` matches any school news |
| forced-displacement | 239 | 0.0% | Hints fine, lex too narrow |

Briefing was ranking topics by GDELT-pollution volume, not actual narrative density.

### Live measurement post-034 (Supabase MCP)

After applying mig 034 + deleting 20,283 stale v2 assignments + re-backfilling 24h in 4× 6h chunks (14,815 new rows):

| Topic | Post-034 sigs/24h | lex_pct | Lift vs pre |
|---|---|---|---|
| forced-displacement | 307 | 26.1% | 0% → 26.1% |
| heat-health-risk | 257 | **100%** | 1.1% → 100% |
| currency-debt-stress | 212 | 84.9% | 0.0% → 84.9% |
| constitutional-institutional-crisis | 178 | **100%** | 4.7% → 100% |
| telecom-internet-shutdown | 102 | **100%** | 1.0% → 100% |
| disinformation-influence-operation | 71 | **100%** | 2.8% → 100% |
| student-youth-protest | 5 | **100%** | 0.3% → 100% |
| press-freedom-crackdown | 3 | **100%** | 0.3% → 100% |

5 of 8 topics now at 100% lex-supported (every assignment has a real headline match). Sharp recall drop is welcome — the dropped volume was almost entirely false positives that were drowning the briefing.

### New honest top-10 atlas topics

Briefing now surfaces actual narratives instead of theme-hint pollution:

1. disease-outbreak (5,246) — 14.6% lex
2. labor-strike-disruption (2,680) — 30.3% lex
3. armed-conflict-escalation (2,121) — 4.6% lex
4. flood-landslide-disaster (1,684) — 35.2% lex
5. election-legitimacy-dispute (1,480) — 6.3% lex
6. gang-control-urban-security (1,017) — 41.4% lex
7. fuel-subsidy-unrest (853) — 10.4% lex
8. transport-corridor-disruption (831) — 20.0% lex
9. food-price-stress (810) — 19.0% lex
10. housing-cost-pressure (767) — 13.6% lex

### Operational rule established

Added to CLAUDE.md: when adding a new topic to `atlas_topics`, after the first 24h backfill audit lex_pct. If lex_pct < 10% AND volume > 500/24h, the hint set has a precision leak — replace broad hints with narrower siblings (`MEDIA_CENSORSHIP` instead of `WB_694_BROADCAST_AND_MEDIA`).

### Follow-up

- The 30-min cron will keep maintaining quality automatically. No deploy needed (data-only change).
- 3 topics still have <10% lex (armed-conflict 4.6%, election-legitimacy 6.3%, fuel-subsidy 10.4%) — could benefit from a similar hint+lex pass in a future iteration.

---

## Previous Handoff — 2026-05-23 (briefing exposes atlas topics + cron live)

### What shipped this session

Branch `feat/briefing-top-atlas-topics`. Two files modified (no migrations, no DB schema changes):

**API**
- `backend/app/routers/briefing.py` — `/api/v2/briefing` now returns `top_atlas_topics` parallel to legacy `top_themes`. Reads `signal_topic_assignments JOIN atlas_topics` with `COUNT(*)` (not `COUNT(DISTINCT signal_id)` — PK uniqueness lets us avoid the 200ms external sort; measured 40ms vs 225ms on 33k rows). Section degrades to `[]` via `to_regclass('signal_topic_assignments')` guard.
- Response shape: `{ slug, label, parent_domain, signal_count, avg_confidence, high_confidence_count, source_table, model_version }`. Filters on `method='lexicon' AND model_version='theme-hint-lex-v2'` so v1 rows (when re-introduced) don't leak through.

**Tests**
- `backend/tests/test_briefing_performance_shape.py` — new test `test_briefing_top_atlas_topics_reads_signal_topic_assignments` pins SQL shape, blocks the `COUNT(DISTINCT)` perf trap, asserts `to_regclass` guard + product response keys.

**Local cron infra (lives on Pedro's machine, not in repo)**
- `/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh` — wraps `backfill_lexicon_topics.py --window-hours 0.5`. Pulls DATABASE_URL from Fly if not in env.
- `~/Library/LaunchAgents/com.atlas.atlas-topic-classifier.plist` — `StartInterval=1800` (every 30 min), `RunAtLoad=true`. Loaded via `launchctl bootstrap gui/$UID`. First live run confirmed: 511 upserts, 396 distinct signals.

### Why this matters

Before this session: 33,279 v2 assignments sitting in `signal_topic_assignments` with ZERO API consumers. The v2 classifier output was effectively dead data — no surface in `/api/v2/briefing` or anywhere else. `top_themes` shipped raw GDELT codes (`WB_2670_JOBS`) instead of the curated atlas taxonomy (`labor-strike-disruption`). The atlas taxonomy is precisely what makes Atlas a "narrative intelligence console, not a GDELT wrapper" — exposing it via the briefing closes that loop.

### Live verification (Supabase MCP)

- Hot-path query EXPLAIN ANALYZE: 39ms on 33,279 assignments. Comfortable under the briefing per-section budget.
- DB state after first cron tick: total v2 rows = 33,790 (up from 33,279 manual backfill), distinct signals = 26,371. Cron is writing.
- Frontend rendering of `top_atlas_topics` is OUT OF SCOPE for this branch — the section is live in the API and ready for the frontend team to consume.

### Operational notes

- Two LaunchAgents now run on Pedro's machine: `com.atlas.local-hot-cold-catchup` (6x/day, archive + prune) and `com.atlas.atlas-topic-classifier` (every 30 min, atlas topic classification).
- Logs at `/Users/pedro/AtlasLocalWorker/logs/atlas-topic-classifier.{out,err}.log`.
- After editing `backend/scripts/backfill_lexicon_topics.py`, MUST `cp` into `/Users/pedro/AtlasLocalWorker/backend/scripts/` (separate copy, NOT a symlink).

---

## Previous Handoff — 2026-05-23 (topic classifier v2 + A/B baseline — PR #197)

### What shipped this session

Branch `claude/status-check-wD1og`, draft PR #197 against `v3-intel-layer` (CI green — Vercel preview only; no GitHub Actions Python suite). Three new files, no migrations, no DB writes from CI.

**Backend scripts**
- `backend/scripts/backfill_lexicon_topics.py` — Issue #171. Single-statement bulk `INSERT … SELECT` topic classifier (v2). Writes `method='lexicon'`, `model_version='theme-hint-lex-v2'`, isolated from v1 (`theme-hint-lex-v1`) by the PK `(signal_id, topic_id, method, model_version)`. Idempotent `ON CONFLICT … DO UPDATE`; doubles as the 15-min incremental cron path via `--window-hours 0.5`. Accelerated by the mig 022 trigram GIN on `lower(headline)` + GIN on `signals_v2.themes`.
- `backend/scripts/topic_classifier_baseline.py` — read-only A/B reporter (candidate count, recall per `model_version`, v1-vs-v2 top-1 agreement, per-topic distribution, confidence histogram). No table mutation.

**Why v2 vs editing v1**
- v1 (`classify_topics.py`) required "lex OR >=3 theme hits" and capped recall at ~0.8% of 24h volume after the mig 031 hint realignment.
- v2 widens qualification to "lex >=1 OR theme_hits >=1" and holds precision with a higher confidence floor (0.55 vs v1's 0.30).
- v2 confidence: `LEAST(0.95, 0.55 + 0.10*LEAST(lex,3) + 0.05*LEAST(theme_hits,4) + cross_bonus)` where cross_bonus = 0.05 when lex>0 AND theme_hits>=2. Top-2 per signal; headline length filter >=20 chars.
- Both coexist so the lift is measurable before retiring v1.

**Tests**
- `backend/tests/test_backfill_lexicon_topics.py` — 11 shape tests (v2-only model_version, upsert semantics, OR qualification, formula components, evidence keys, top-N ranking, headline filter, dry-run is read-only). 16/16 pass alongside `test_topic_intelligence_schema.py`. Shape-only because the container has no DB / no asyncpg.

### Live measurement (2026-05-23, via Supabase MCP)

**Threshold sweep on 6h window (~38k candidate signals):**

| Config | Distinct signals | Recall | avg_conf | Notes |
|--------|-----------------|--------|----------|-------|
| v1 (`theme-hint-lex-v1`) | 841 | 2.2% | 0.613 | 96.5% lex-supported, precision-heavy |
| v2@0.55 (script default) | 27,942 | 73.5% | 0.608 | Only 1.6% lex-supported — too noisy |
| **v2@0.65 (chosen)** | **6,121** | **16.1%** | **0.653** | **7.3× v1; 30 topics fired** |
| v2@0.70 | 398 | 1.0% | 0.710 | Collapses below v1 |

**Top1 agreement v1↔v2@0.65 on overlap (812 signals):** 753 same / 59 different = **92.73%**.

**Decision: promote v2 with `DEFAULT_MIN_CONFIDENCE = 0.65`** (was 0.55 in script). All four gate criteria cleared:
- ✅ recall lift 7.3× (>= 5× target)
- ✅ top1 agreement 92.73% (>= 70% target)
- ✅ avg_confidence 0.653 ≈ v1's 0.613 (precision parity)
- ✅ 30 topics fired, top topic = 13.7% (no collapse)

**Live backfill applied 2026-05-23 in 4× 6h chunks via Supabase MCP over the 24h window:**
- 33,279 assignments upserted into `signal_topic_assignments` (`model_version='theme-hint-lex-v2'`).
- 25,975 distinct signals (16.84% of the 154,226-signal 24h candidate window).
- avg_confidence 0.654; 30 topics fired.
- Top: disease-outbreak 4,544, constitutional-institutional-crisis 4,391, telecom-internet-shutdown 3,566, heat-health-risk 3,401. Tail down to humanitarian-access-conflict (30). No single topic >14%.
- v1 (`theme-hint-lex-v1`) remains 0 rows in `signal_topic_assignments` (the May 21 backfill was wiped by the hot/cold prune of May 20); re-backfilling v1 is optional since the 92.73% top1 agreement already validates that v2 agrees with v1 on the easy cases.

### Operational follow-up
- Schedule v2 incremental cron at `--window-hours 0.5` once the local-hot-cold runner is happy (issue #171 close).
- Future: extend `atlas_topics.lexicon_terms` via #185 mining; v2 will pick up the new terms automatically.

---

## Current Handoff — 2026-05-20 (session 17 close — Opción A end-to-end + atlas_heat surface)

### What shipped this session

Six commits on `v3-intel-layer` (`09b95bb` → `43732a9`), six Fly deploys (versions 156 → 161), DB-level changes via Supabase MCP. Production verified live throughout.

**Database**
- Migration **025** — `theme_hourly_v2` + `theme_country_hourly_v2` gained `nlp_signal_count INTEGER NOT NULL DEFAULT 0` and `avg_nlp_sentiment NUMERIC`. Additive, metadata-only `ALTER ADD COLUMN`, no rewrite.
- Migration **026** — `country_hourly_v2` matview swapped to add the same NLP coverage columns. Build-populate-rename so briefing reads never saw an empty matview.
- ADR-0004 prune ran end-to-end via Supabase MCP — **241,656 rows deleted** in batches (25k → 50k), `VACUUM ANALYZE` completed, `signals_v2` size unchanged on disk but `dead_tup = 0` and ~240k pages available for new INSERTs.
- `signals_v2` autovacuum tuned: `scale_factor = 0.05`, `cost_delay = 10`. NLP backfill UPDATE bloat now triggers vacuum at ~107K dead tuples instead of ~475K.
- `nlp_sample_queue` truncated (610K zombie ids; worker preferred fresh since commit `7472aba`, queue never drained).
- `nlp_progress` synced to ground truth (worker's cached delta math went stale after the external DELETE; manual `UPDATE` until #186 fixes the recompute path).

**Backend code**
- `app/routers/briefing.py` — every country-shaped SQL is now a CTE that pulls both `gdelt_sentiment` and `nlp_sentiment` per bucket and a `chosen_sentiment_raw` expression that ORDER BYs honestly.
- `app/services/sentiment_fusion.py` — new module. `choose_sentiment(gdelt_raw, nlp_raw, nlp_coverage)` picks NLP transformer when bucket coverage ≥ 0.30 and rescales by `NLP_SENTIMENT_SCALE = 2.37` so the value lands on the same ±0.1 frontend threshold as GDELT. Both constants env-tunable.
- Briefing response gains `sentiment_source` (`"nlp"` | `"gdelt"`) and `nlp_coverage` on every country row + on global stats.
- New section `heat_countries` reads `country_heat_v2` (#165) and ranks by `atlas_heat`. Each entry exposes the full component breakdown (velocity, surprise, diversity, voice, polyphony, geo_confidence, duplication).
- `top_themes` switched from dead `signals_theme_hourly` to live `theme_hourly_v2`.
- `top_sources` switched from dead `signals_source_hourly` to `signals_v2` direct scan (Redis-cached 15–30 min, single bounded GROUP BY per cache miss).
- `/briefing/insight` mirrors the `/briefing` hardening — `country_hourly_v2` instead of raw `signals_v2`, parameterized `$1::int * INTERVAL '1 hour'`, every section through `_fetch_section` with degraded fallback.
- `ingest_v2.refresh` writes `nlp_signal_count` + `avg_nlp_sentiment` via `FILTER (WHERE nlp_sentiment IS NOT NULL)` in the same INSERT pass — zero IO overhead.
- Lexicon vocab expanded: EN +110 terms, ES/PT +50, new `IT` and `DE` seed lexicons. Hit rate measured live at 12% (news headlines are mostly factual — manual seeds have a ceiling). Coverage moved 7.8% → 8.0%.

**Tests**
- `tests/test_briefing_performance_shape.py` — guardrails for sentiment-preagg use, parameterized intervals, degraded response shape, top_themes ≠ dead-table, top_sources ≠ dead-table, heat_countries section structure.
- `tests/test_briefing_sentiment_fusion.py` — 7 cases for `choose_sentiment` boundary behavior.
- `tests/test_ingest_pre_agg_nlp_coverage.py` — pins the NLP coverage SQL into both pre-agg INSERTs.
- Full suite: **236 passed, 6 skipped, 0 failed**.

### Live production state (2026-05-20 13:55 UTC)

| Metric | Value |
|---|---|
| Image | `deployment-01KS2P*` (v160) — see `fly status` |
| `signals_v2` total | 2,191,567 |
| Over-15d unprocessed | 0 (post-prune) |
| Lexicon-tagged | 7,300 |
| Transformer-tagged | 35,550 |
| Global NLP coverage | **8.0%** |
| Briefing fusion threshold | 0.30 (env-tunable) |
| Briefing API | `degraded=false`, all 6 sections populated |
| heat_countries top 5 | LB · NI · GZ · DO · MB |
| top_countries top 5 | US · CN · GB · RU · IN |
| top_sources top 3 | zazoom.it · indiatimes.com · 163.com |

### Issues touched

- ✅ **Closed #149** (volumetric US dominance) — heat_countries lens ships dual-rank.
- ✅ **Closed #165** (Atlas composite heat) — atlas_heat consumed in briefing.
- ✅ **Closed #182** (briefing sentiment timeout) — already done; this session reinforced via `/briefing/insight` parallel hardening.
- 📝 **Progress comment #164** — ADR-0004 prune executed end-to-end, lexicon backfill shipped.
- 📝 **Progress comment #171** — lexicon vocab expanded, plateau measured, follow-up tracked.
- 🆕 **#183** — frontend rendering of sentiment_source badge + heat_countries panel. OPEN.
- 🆕 **#184** — NLP_WORKER_LIMIT bump experiment with decision rule. OPEN.
- 🆕 **#185** — corpus-mine lexicon vocab from transformer-tagged rows (breaks the 12% plateau). OPEN.
- ✅ **#186** — `nlp_progress` recompute landed in commit `613a21e`. /health.unprocessed_total now stays honest after external DELETEs. CLOSED.
- ✅ **#187** — `heat_voluminous_countries` lens landed in commits `613a21e` + `3e0fce8`. Top-quartile-by-volume re-ranked by atlas_heat surfaces CO, NG, AR, AJ, BR right now. CLOSED.

### Routes / paths reference

- New module: `backend/app/services/sentiment_fusion.py` (importable, pure, unit-testable, free of FastAPI circular imports).
- New migrations: `backend/migrations/025_pre_agg_nlp_coverage.sql`, `backend/migrations/026_country_hourly_v2_nlp_coverage.sql`.
- New tests: `backend/tests/test_briefing_sentiment_fusion.py`, `backend/tests/test_ingest_pre_agg_nlp_coverage.py`.
- Lexicon: `backend/enrichment/lexicon_sentiment.py` (EN/ES/FR/PT/AR/IT/DE).
- Existing matview consumed: `country_heat_v2` (mig 017) — read via briefing `heat_countries` section.

### Honest verdict

The architecture is correct and the API is honest. Coverage is still 8% because the worker can't outrun ingest at `NLP_WORKER_LIMIT=25` and the lexicon seed approach caps at ~12% hit rate. Fusion will not flip to `sentiment_source = "nlp"` at scale until either (a) the worker is bumped per #184, (b) corpus-mined vocab ships per #185, or (c) the coverage threshold is dropped from 0.30 via the `BRIEFING_NLP_COVERAGE_THRESHOLD` env var.

Backend foundation for the next visible UX leap is in place — frontend wiring tracked in #183.

---

## Previous handoff — 2026-05-19 (session 16 start — signal_class landed)

### Session 16 — `signal_class` semantic provenance live (Track B.1)

**Migration 021** applied in Supabase + ingest services updated. Foundation for #149 cluster scoring, Voice Mix (#160), and topic intelligence ranking gate (#167).

| signal_class | rows |
|---|---:|
| reporting | 2,288,194 |
| state_media | 2,641 |
| wire | 2,127 |
| social_commentary | 351 |
| humanitarian | 3 |

**Files added**:
- `backend/migrations/021_signal_class.sql`
- `backend/app/services/_signal_class.py` (centralized derivation helper)
- `backend/tests/test_signal_class.py` (23 tests, all pass)
- `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md` (3-track attack plan)

**Files patched** (signal_class write):
- `backend/app/services/ingest_v2.py` (GDELT)
- `backend/app/services/ingest_rss.py` (RSS — uses helper for state/wire/independent split)
- `backend/app/services/ingest_reliefweb.py` (humanitarian)
- `backend/app/services/ingest_newsdata.py` (reporting)
- `backend/app/services/ingest_newsapi.py` (reporting)
- `backend/app/services/ingest_mediastack.py` (reporting)
- `backend/app/services/ingest_reddit.py` (social_commentary)

**Observation**: humanitarian = 3 reveals broken ReliefWeb ingestion (historical, separate followup, not blocking).

**Next**: migration 022 trigram index + `country` param in `/api/v2/search/unified` (Track A), then bulk SQL lexicon classifier (Track B.2).

---

## Previous handoff — 2026-05-19 (session 15 + Codex parallel work)

**Production branch**: `v3-intel-layer`
**Frontend**: Vercel auto-deploy — `v3-intel-layer` latest
**Backend**: Fly.io `atlas-api-pedro` — healthy, **2,279,950 signals**, deployment `01KS0EG5FJAY5507G729FNVACQ`
**NLP worker**: Fly.io `nlp_worker` — 4GB (`shared-cpu-2x:4096MB`), `xlm-v1` multilingual active

PR [#144](https://github.com/pedro-cmyks/Observatory-Global/pull/144) open against `main` (220+ commits ahead).

---

## Session 15 work — Multi-source ingestion + NLP stabilization

### Track A — Multi-source ingestion (Claude session)

Addressed GDELT US/English volumetric bias. 4 new sources live on Fly.io.

| Source | File | Coverage | Cadence | Daily quota |
|--------|------|----------|---------|-------------|
| NewsData.io | `ingest_newsdata.py` | 7 buckets ES/PT/AR/FR/SW/SE-Asia/S-Asia (post-edit: country-primary, 10 per page) | every 60 min | 200 req/day |
| MediaStack | `ingest_mediastack.py` | ES/PT 17 LatAm countries | every 2 hours | 500 req/month |
| NewsAPI.org | `ingest_newsapi.py` | 8 EN crisis queries (7-day window, dedupe-driven) | every 2 hours | 100 req/day |
| Reddit | `ingest_reddit.py` | 14 geopolitics subreddits (no API key) | every 60 min | unlimited (60 req/min) |

**Fly.io secrets deployed**: `NEWSDATA_API_KEY`, `MEDIASTACK_API_KEY`, `NEWSAPI_KEY`

**Volume projection**:
- GDELT: ~72K signals/day (unchanged)
- New sources: +~27.6K/day (NewsData ~8.4K, Reddit ~16.8K, MediaStack ~1.2K, NewsAPI ~1.3K)
- Total: ~99.7K signals/day

**Files added**:
- `backend/app/services/ingest_newsdata.py`
- `backend/app/services/ingest_mediastack.py`
- `backend/app/services/ingest_newsapi.py`
- `backend/app/services/ingest_reddit.py`
- `backend/.env.example`

**Files changed**:
- `backend/app/services/ingest_loop.py` — 4 new service calls (cycle%4 for NewsData+Reddit, cycle%8 for MediaStack/NewsAPI)

### Track B — NLP worker stabilization + Topic Intelligence (Codex parallel)

Commit `e4e8f92 feat(data): add topic intelligence schema and stabilize nlp worker`

**Fly.io infra changes**:
- `nlp_worker` machine size: `shared-cpu-2x:4096MB` (was undersized, OOM risk)
- Standby worker stopped (single-worker mode at 4GB)
- `NLP_SAMPLE_REFRESH_EVERY=0` — heavy refresh explicitly OFF
- `NLP_SAMPLE_CLEANUP_LIMIT=50` — bounded queue cleanup in prod

**Migrations applied**:
- `019_atlas_topic_intelligence.sql` — Topic Intelligence base layer: `atlas_topics`, `signal_topic_assignments`, `topic_learning_examples`, 30 seed topics
- `020_nlp_progress_indexes.sql` — indexes so worker stops full-scanning signals_v2 for progress math

**Verified prod state**:
- `ingest_lag_minutes`: 4.1
- `rows_ingested_last_15m`: 3,849
- last NLP cycle: 2026-05-19T16:00:16Z, duration 231.5s, `error=no`
- Logs: `Sentiment[xlm-v1]`, `NER[xlm-v1]`, `Framing[xlm-v1]` — **multilingual NLP confirmed running**

**Tests**: 27 passed
```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_nlp_pipeline_selection.py \
  tests/test_nlp_worker.py \
  tests/test_topic_intelligence_schema.py -q
```

**Operational debt logged**:
- NLP throughput: 25 rows/cycle stable but low — do NOT raise to 100/200 until DB pressure observed for hours
- `country_heat_v2` refresh hit timeout once in logs — pending operational item
- HuggingFace warned about `twitter-xlm-roberta-base-sentiment` tokenizer — verify before trusting multilingual quality
- Issue traceability comments left on `#167`, `#163`, `#164`

---

## Guru-brain design analysis (recorded for next session)

Deep self-critical pass on session 15 ingestion design. Key findings:

1. **Volume is not the problem.** GDELT already gives 2M signals. New sources matter for **non-English voice + emergent narrative + source diversity** — not raw volume. Without UI exposing this, value invisible to users.
2. **NewsAPI weak point**: 8 EN-language queries on crisis zones GDELT already covers in EN. Reframe as "international English framing" not "crisis coverage". Redesign: 6 evergreen + 2 dynamic from GDELT spikes + 36 req/day reserve for analyst UI probing.
3. **NewsData weak point**: language batches collapse geography. Refactor to country-primary buckets → `geo_confidence` rises from 0.65 to ~0.85 at fetch time (no NER inference needed). *(Partially addressed by Codex edit: split into 7 smaller country buckets.)*
4. **Reddit is commentary, not corroboration.** Needs `signal_class = "commentary"` in schema; must NOT count as independent unique source in #149 scoring formula.
5. **Multilingual NLP**: ✅ verified by Codex — `xlm-v1` runs. Tokenizer warning still to validate.

### Priority list for next session

1. ~~Verify multilingual NLP~~ — **DONE by Codex** (`xlm-v1` running)
2. `signal_class` + `narrative_cluster_id` in signals_v2 (migration 021)
3. **Voice Mix** component in CountryBrief: stacked bar local-lang / international / social. Endpoint `/api/v2/countries/{iso}/voice-mix`.
4. NewsAPI refactor: 6 evergreen + 2 dynamic + 36 req reserve + `/api/v2/analyst/probe-newsapi` endpoint
5. ~~NewsData country-primary buckets~~ — **PARTIAL by Codex edit**; revisit after measuring `geo_confidence` distribution
6. Validate tokenizer warning on `twitter-xlm-roberta-base-sentiment`
7. Resolve `country_heat_v2` refresh timeout

---

## P1 Pass — completed 2026-05-18 (recap)

All code issues from UX video review resolved:
- #143 Map layer clarity (Legend + Panel Help)
- #135 Landing live stats
- #69 Spanish compound search routing
- #133 Signal dossier export
- #141 Reading Mode newspaper view
- #56 Terminator twilight gradient
- #124 Saved watches live counts

## P0 Pass — completed 2026-05-17 (recap)

- #136 Brief prefetch (sessionStorage 4-min TTL)
- #137 Editor's Analysis fallback (rotating prose)
- #138 Investigation context persistence
- #142 Public Attention country-scoped
- #104 Google Trends rate-limiting
- #139 Narrative Threads timeout
- #128 Trail / Pinned graph separation

---

## Open Issues

| # | Issue | Status |
|---|-------|--------|
| #145 | Filter Wikipedia infrastructure/entertainment from Public Attention | P0 quick |
| #146 | Narrative Threads empty state explanation | P0 UX |
| #147 | Full map state reset (pitch + bearing + zoom) | P1 |
| #148 | "See all publishers" expansion in CountryBrief | P1 |
| #149 | Source-weighted scoring normalization | P1 core |
| #150 | Add 20+ non-English RSS feeds (Wave 5) | P1 data |
| #151 | Financial/commodity price overlay | P2 |
| #152 | Command bar redesign | P1 |
| #153 | Prototype MediaStack + Reddit ingestion | done session 15 |
| #163, #164, #167 | NLP worker / topic intelligence traceability | tracked by Codex commits |
| #140, #134 | Use-case docs | Needs Pedro to record |
| #46, #106 | ACLED / mascot | Blocked |

ACLED = optional connector. No `ACLED_API_KEY` → empty layer, no errors.

---

## Architecture

| Layer | Stack | Deploy |
|-------|-------|--------|
| Frontend | React 18 + TypeScript + Vite + deck.gl + MapLibre | Vercel auto-deploy from `v3-intel-layer` |
| Backend | FastAPI + asyncpg + PostgreSQL | Fly.io `atlas-api-pedro` (IAD) |
| NLP worker | xlm-roberta sentiment/NER/framing | Fly.io `nlp_worker` 4GB |
| Database | Supabase PostgreSQL | Migrations 007–020 applied |
| Cache | Upstash Redis | atlas-redis |

**All active ingestion sources**:

| Source | File | Family | Cadence |
|--------|------|--------|---------|
| GDELT GKG | `ingest_v2.py` | gdelt | 15 min |
| GDELT Events | `ingest_events.py` | gdelt | 15 min |
| Google Trends | `ingest_trends.py` | trends | 30 min |
| RSS curated | `ingest_rss.py` | varies | 60 min |
| ReliefWeb | `ingest_reliefweb.py` | ngo | 60 min |
| **NewsData.io** | `ingest_newsdata.py` | api | 60 min |
| **Reddit** | `ingest_reddit.py` | social | 60 min |
| **MediaStack** | `ingest_mediastack.py` | api | 2 h |
| **NewsAPI.org** | `ingest_newsapi.py` | api | 2 h |
| Wikipedia | `ingest_wiki.py` | wiki | 24 h |
| ACLED (opt) | `ingest_acled.py` | conflict | 60 min |

**Key endpoints**:
- `GET /api/v2/signals` — raw signals (filter by country/theme/person)
- `GET /api/v2/briefing` — aggregated brief (frontend caches 4 min)
- `GET /api/v2/narratives` — theme threads, detail capped at 48h
- `GET /api/v2/nodes` — country nodes
- `GET /api/v2/flows` — narrative co-occurrence
- `GET /api/v2/conflict-markers` — ACLED or empty
- `GET /health` — pipeline health + total_signals

---

## Key Technical Patterns

- **Country names**: `resolveCountryName(code, name)` always — never raw API strings
- **Theme labels**: `getThemeLabel(code)` always — never raw GDELT codes
- **Tooltips**: `data-tip` attribute — never native `title=`
- **Workspace persistence**: localStorage `atlas-workspace`, `atlas_saved_watches_v1`
- **Briefing prefetch**: sessionStorage `atlas_briefing_prefetch_v1` 4-min TTL
- **Compound search**: `parseCompoundQuery(q)` extracts countryCode before backend
- **ForceGraph2D**: Two instances mounted always, CSS `visibility: hidden` preserves simulation
- **Terminator**: 5-band PolygonLayer array, spread `...terminatorLayers`
- **New ingest sources**: all set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, `is_state_media` (signals_v2 convention)
- **Reddit signals**: `source_family="social"`, `attribution_method="reddit_public"` — commentary layer, NOT independent corroboration
- **`geo_confidence` defaults**: NewsData 0.7, MediaStack 0.65, NewsAPI 0.65, Reddit 0.5, GDELT GKG 0.9, RSS 0.6
- **NLP env flags**: `NLP_SAMPLE_REFRESH_EVERY=0`, `NLP_SAMPLE_CLEANUP_LIMIT=50` set in prod

---

## Validation (last run 2026-05-19)

```
npm run build       ✅ clean (Vite + tsc -b)
backend pytest      ✅ 139 main + 27 NLP/topic = 166 tests passing
fly deploy backend  ✅ deployment 01KS0EG5FJAY5507G729FNVACQ
fly secrets         ✅ NEWSDATA_API_KEY, MEDIASTACK_API_KEY, NEWSAPI_KEY deployed
NLP worker          ✅ 4GB, xlm-v1 multilingual, 231.5s cycle, error=no
/health             ✅ 2,279,950 signals, lag 4.1min, 3849 rows/15min
API validation      ✅ all 4 new sources return data
```
