# Project Inventory

Generated: 2026-06-03T14:04:58.510082+00:00
Regen: `python scripts/project_inventory.py`

## Endpoints (backend)

| Method | Path | Router | Function | Tables touched |
|---|---|---|---|---|
| GET | `/` | `backend/app/routers/stats.py` | `root` | — |
| GET | `/api/indicators/allowlist` | `backend/app/routers/indicators.py` | `get_quality_allowlist` | `signals_v2` |
| GET | `/api/indicators/country/{country_code}` | `backend/app/routers/indicators.py` | `get_country_indicators` | `signals_v2` |
| GET | `/api/indicators/denylist` | `backend/app/routers/indicators.py` | `get_quality_denylist` | `signals_v2` |
| GET | `/api/indicators/tooltips` | `backend/app/routers/indicators.py` | `get_indicator_tooltips` | `signals_v2` |
| GET | `/api/v2/acled` | `backend/app/routers/geo.py` | `get_acled_conflicts` | `acled_conflicts_v2`, `signals_v2` |
| GET | `/api/v2/aircraft` | `backend/app/routers/geo.py` | `get_aircraft_positions` | — |
| GET | `/api/v2/anomalies` | `backend/app/routers/workspace.py` | `get_anomalies` | `countries_v2`, `country_hourly_v2` |
| GET | `/api/v2/anomalies/themes` | `backend/app/routers/workspace.py` | `get_theme_anomalies` | `signals_v2`, `theme_daily_v2` |
| GET | `/api/v2/briefing` | `backend/app/routers/briefing.py` | `get_briefing` | `countries_v2`, `country_hourly_v2` |
| GET | `/api/v2/briefing/insight` | `backend/app/routers/briefing.py` | `get_briefing_insight` | `countries_v2`, `country_hourly_v2`, `signals_theme_hourly`, `theme_hourly_v2` |
| GET | `/api/v2/compare` | `backend/app/routers/workspace.py` | `compare_periods` | `signals_country_hourly`, `signals_theme_hourly` |
| GET | `/api/v2/concept/{slug}` | `backend/app/routers/narratives.py` | `get_concept_narratives` | `theme_country_hourly_v2` |
| GET | `/api/v2/concepts` | `backend/app/routers/narratives.py` | `list_concepts` | — |
| GET | `/api/v2/concepts/search` | `backend/app/routers/narratives.py` | `search_concepts_endpoint` | — |
| GET | `/api/v2/conflict-markers` | `backend/app/routers/geo.py` | `get_conflict_markers` | `acled_conflicts_v2`, `events_v2` |
| GET | `/api/v2/correlation` | `backend/app/routers/geo.py` | `get_correlation` | `signals_v2` |
| GET | `/api/v2/country/{country_code}` | `backend/app/routers/geo.py` | `get_country_detail` | `country_hourly_v2`, `signals_v2` |
| GET | `/api/v2/emergent` | `backend/app/routers/emergent.py` | `get_emergent` | `emergent_clusters` |
| GET | `/api/v2/events` | `backend/app/routers/events.py` | `get_events` | `events_v2` |
| GET | `/api/v2/events/clusters` | `backend/app/routers/events.py` | `get_event_clusters` | `events_v2` |
| GET | `/api/v2/flows` | `backend/app/routers/geo.py` | `get_flows` | `signals_v2` |
| GET | `/api/v2/focus` | `backend/app/routers/themes.py` | `get_focus_data` | `signals_v2` |
| GET | `/api/v2/heat/countries` | `backend/app/routers/heat.py` | `get_country_heat` | — |
| POST | `/api/v2/heat/countries/refresh` | `backend/app/routers/heat.py` | `refresh_country_heat` | `country_heat_v2` |
| GET | `/api/v2/heatmap` | `backend/app/routers/geo.py` | `get_heatmap` | `signals_v2` |
| GET | `/api/v2/narratives` | `backend/app/routers/narratives.py` | `get_narratives` | `signals_theme_hourly`, `signals_v2`, `theme_hourly_v2` |
| GET | `/api/v2/nlp/calibration` | `backend/app/routers/nlp_corrections.py` | `calibration_report` | `nlp_corrections`, `signals_v2` |
| POST | `/api/v2/nlp/corrections` | `backend/app/routers/nlp_corrections.py` | `submit_correction` | `nlp_corrections`, `signals_v2` |
| GET | `/api/v2/nodes` | `backend/app/routers/workspace.py` | `get_nodes` | `countries_v2`, `signals_v2` |
| GET | `/api/v2/search` | `backend/app/routers/search.py` | `search` | `countries_v2`, `signals_v2` |
| GET | `/api/v2/search/unified` | `backend/app/routers/search.py` | `unified_search` | `wiki_pageviews_v2` |
| GET | `/api/v2/signals` | `backend/app/routers/signals.py` | `get_signals` | `signals_v2` |
| GET | `/api/v2/source/{domain:path}/profile` | `backend/app/routers/workspace.py` | `get_source_profile` | `signals_source_hourly`, `signals_v2` |
| GET | `/api/v2/stats` | `backend/app/routers/stats.py` | `get_system_stats` | `country_hourly_v2`, `signals_v2` |
| GET | `/api/v2/theme/{theme_code}` | `backend/app/routers/themes.py` | `get_theme_details` | — |
| GET | `/api/v2/theme/{theme_code}/drift` | `backend/app/routers/themes.py` | `get_theme_drift` | `signals_v2` |
| GET | `/api/v2/theme/{theme_code}/insight` | `backend/app/routers/themes.py` | `get_theme_insight` | `signals_v2` |
| GET | `/api/v2/theme/{theme_code}/spikes` | `backend/app/routers/themes.py` | `get_theme_spikes` | `signals_v2` |
| GET | `/api/v2/threads` | `backend/app/routers/threads.py` | `get_threads` | — |
| GET | `/api/v2/threads/{thread_id}` | `backend/app/routers/threads.py` | `get_thread_detail` | — |
| GET | `/api/v2/translate` | `backend/app/routers/translate.py` | `get_translate` | — |
| POST | `/api/v2/translate/batch` | `backend/app/routers/translate.py` | `post_translate_batch` | — |
| GET | `/api/v2/trends` | `backend/app/routers/trends.py` | `get_trends` | `signals_country_hourly`, `signals_source_hourly`, `signals_theme_hourly` |
| GET | `/api/v2/trends/match` | `backend/app/routers/trends.py` | `get_trends_theme_match` | `trends_v2` |
| GET | `/api/v2/trends/search` | `backend/app/routers/trends.py` | `get_trending_searches` | `trends_v2` |
| GET | `/api/v2/vessels` | `backend/app/routers/geo.py` | `get_vessels` | — |
| GET | `/api/v2/wiki/match` | `backend/app/routers/wiki.py` | `get_wiki_theme_match` | `wiki_pageviews_v2` |
| GET | `/api/v2/wiki/top` | `backend/app/routers/wiki.py` | `get_wiki_top_articles` | `wiki_pageviews_v2` |
| GET | `/api/v3/crisis/signals` | `backend/app/routers/signals.py` | `get_crisis_signals` | `signals_v2` |
| GET | `/api/v3/crisis/summary` | `backend/app/routers/signals.py` | `get_crisis_summary` | `signals_v2` |
| GET | `/health` | `backend/app/routers/stats.py` | `health` | `country_hourly_v2`, `nlp_progress`, `signals_v2` |

## Frontend → API map

Where `/api/...` is called from. Multiple callers = shared surface.

| Endpoint | Frontend file(s) |
|---|---|
| `/api/v2/aircraft` | `frontend-v2/src/App.tsx` |
| `/api/v2/anomalies` | `frontend-v2/src/contexts/CrisisContext.tsx` |
| `/api/v2/anomalies/themes` | `frontend-v2/src/contexts/CrisisContext.tsx` |
| `/api/v2/briefing` | `frontend-v2/src/App.tsx`<br/>`frontend-v2/src/components/Briefing.tsx`<br/>`frontend-v2/src/components/SourceIntegrityPanel.tsx`<br/>`frontend-v2/src/lib/briefingPrefetch.ts`<br/>`frontend-v2/src/pages/BriefNewspaper.tsx` |
| `/api/v2/briefing/insight` | `frontend-v2/src/App.tsx`<br/>`frontend-v2/src/components/Briefing.tsx`<br/>`frontend-v2/src/lib/briefingPrefetch.ts`<br/>`frontend-v2/src/pages/BriefNewspaper.tsx` |
| `/api/v2/compare` | `frontend-v2/src/components/CompareBar.tsx` |
| `/api/v2/conflict-markers` | `frontend-v2/src/contexts/FocusDataContext.tsx` |
| `/api/v2/correlation` | `frontend-v2/src/components/CorrelationMatrix.tsx` |
| `/api/v2/country/` | `frontend-v2/src/contexts/WorkspaceContext.tsx` |
| `/api/v2/flows` | `frontend-v2/src/contexts/FocusDataContext.tsx`<br/>`frontend-v2/src/hooks/useFocusData.ts` |
| `/api/v2/focus` | `frontend-v2/src/components/EntityPanel.tsx`<br/>`frontend-v2/src/contexts/FocusDataContext.tsx`<br/>`frontend-v2/src/contexts/WorkspaceContext.tsx` |
| `/api/v2/heat/countries` | `frontend-v2/src/components/AtlasHeatList.tsx` |
| `/api/v2/narratives` | `frontend-v2/src/components/DiscoveryPanel.tsx` |
| `/api/v2/nodes` | `frontend-v2/src/components/ChokepointPanel.tsx`<br/>`frontend-v2/src/components/CountryBrief.tsx`<br/>`frontend-v2/src/contexts/FocusDataContext.tsx`<br/>`frontend-v2/src/hooks/useFocusData.ts`<br/>`frontend-v2/src/pages/BriefNewspaper.tsx` |
| `/api/v2/search` | `frontend-v2/src/components/CustomConceptModal.tsx`<br/>`frontend-v2/src/components/SearchBar.tsx` |
| `/api/v2/search/unified` | `frontend-v2/src/components/CompareSearchModal.tsx`<br/>`frontend-v2/src/components/PublicAttentionPanel.tsx`<br/>`frontend-v2/src/components/SearchBar.tsx`<br/>`frontend-v2/src/components/ThemeDetail.tsx`<br/>`frontend-v2/src/contexts/WorkspaceContext.tsx` |
| `/api/v2/signals` | `frontend-v2/src/components/ChokepointPanel.tsx`<br/>`frontend-v2/src/components/CountryBrief.tsx`<br/>`frontend-v2/src/components/SignalStream.tsx`<br/>`frontend-v2/src/hooks/useSavedWatches.ts`<br/>`frontend-v2/src/lib/exportFormatters.ts`<br/>`frontend-v2/src/pages/BriefNewspaper.tsx` |
| `/api/v2/source/` | `frontend-v2/src/components/SourceProfile.tsx`<br/>`frontend-v2/src/contexts/WorkspaceContext.tsx` |
| `/api/v2/stats` | `frontend-v2/src/App.tsx` |
| `/api/v2/theme/` | `frontend-v2/src/components/CountryThemePanel.tsx`<br/>`frontend-v2/src/components/ExportMenu.tsx`<br/>`frontend-v2/src/components/NarrativeDrift.tsx`<br/>`frontend-v2/src/components/ThemeDetail.tsx`<br/>`frontend-v2/src/contexts/WorkspaceContext.tsx`<br/>`frontend-v2/src/lib/themeDetailDynamicInsight.test.ts` |
| `/api/v2/threads` | `frontend-v2/src/components/NarrativeThreads.tsx` |
| `/api/v2/threads/` | `frontend-v2/src/components/ThreadFocusPanel.tsx` |
| `/api/v2/translate/batch` | `frontend-v2/src/components/ThreadFocusPanel.tsx` |
| `/api/v2/trends/match` | `frontend-v2/src/components/ThemeDetail.tsx` |
| `/api/v2/trends/search` | `frontend-v2/src/lib/publicAttention.test.ts`<br/>`frontend-v2/src/lib/publicAttention.ts` |
| `/api/v2/vessels` | `frontend-v2/src/App.tsx` |
| `/api/v2/wiki/match` | `frontend-v2/src/components/ThemeDetail.tsx` |
| `/api/v2/wiki/top` | `frontend-v2/src/lib/publicAttention.test.ts`<br/>`frontend-v2/src/lib/publicAttention.ts` |

## DB tables (from migrations)

| Table | Created by | Read by (router) |
|---|---|---|
| `atlas_topics` | `backend/migrations/019_atlas_topic_intelligence.sql` | — |
| `country_baseline_stats` | `backend/migrations/003_anomaly_baseline.sql` | — |
| `data_lifecycle_config` | `backend/migrations/004_data_lifecycle_config.sql` | — |
| `dynamic_topic_members` | `backend/migrations/048_dynamic_topics.sql` | — |
| `dynamic_topics` | `backend/migrations/048_dynamic_topics.sql` | — |
| `emergent_clusters` | `backend/migrations/046_emergent_clusters.sql` | `backend/app/routers/emergent.py` |
| `historical_archive_coverage` | `backend/migrations/029_historical_processed_tables.sql` | — |
| `historical_evidence_samples` | `backend/migrations/029_historical_processed_tables.sql` | — |
| `historical_processing_runs` | `backend/migrations/029_historical_processed_tables.sql` | — |
| `historical_topic_country_daily` | `backend/migrations/029_historical_processed_tables.sql` | — |
| `ingest_file_log` | `backend/migrations/005_ingestion_tracking.sql` | — |
| `ingest_watermark` | `backend/migrations/005_ingestion_tracking.sql` | — |
| `nlp_corrections` | `backend/migrations/018_nlp_corrections.sql` | `backend/app/routers/nlp_corrections.py` |
| `nlp_progress` | `backend/migrations/015_nlp_progress.sql` | `backend/app/routers/stats.py` |
| `nlp_sample_queue` | `backend/migrations/016_nlp_method.sql` | — |
| `public` | `backend/migrations/032_historical_source_daily.sql` | — |
| `signal_topic_assignments` | `backend/migrations/019_atlas_topic_intelligence.sql` | — |
| `signal_translations` | `backend/migrations/047_signal_translations.sql` | — |
| `signals_country_hourly` | `backend/migrations/006_aggregates.sql` | `backend/app/routers/trends.py`<br/>`backend/app/routers/workspace.py` |
| `signals_source_hourly` | `backend/migrations/006_aggregates.sql` | `backend/app/routers/trends.py`<br/>`backend/app/routers/workspace.py` |
| `signals_theme_hourly` | `backend/migrations/006_aggregates.sql` | `backend/app/routers/briefing.py`<br/>`backend/app/routers/narratives.py`<br/>`backend/app/routers/trends.py`<br/>`backend/app/routers/workspace.py` |
| `theme_country_hourly_v2` | `backend/migrations/010_theme_country_hourly.sql` | `backend/app/routers/narratives.py` |
| `topic_learning_examples` | `backend/migrations/019_atlas_topic_intelligence.sql` | — |

## Cron jobs (launchd)

| Label | Program | Schedule | RunAtLoad | Last log mtime | Last log line |
|---|---|---|---|---|---|
| `com.atlas.atlas-topic-classifier` | `/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh` | every 1800s | True | 2026-06-03T13:34:58.363764+00:00 | } |
| `com.atlas.emergent-snapshot` | `/Users/pedro/AtlasLocalWorker/run-emergent-snapshot.sh` | 0:00, 6:00, 12:00, 18:00 | True | 2026-06-03T11:05:13.547947+00:00 | } |
| `com.atlas.local-hot-cold-catchup` | `/Users/pedro/AtlasLocalWorker/run-local-hot-cold-catchup.sh` | 0:10, 1:10, 2:10, 3:10, 4:10, 5:10 | True | 2026-06-03T10:11:01.032397+00:00 | } |
| `com.atlas.threevendor-calibration` | `/Users/pedro/AtlasLocalWorker/run-3vendor-calibration.sh` | — | False | 2026-06-03T08:16:03.098547+00:00 | 2026-06-03T08:16:03Z calibration done -> /Users/pedro/AtlasLocalWorker/calibration/2026-06-03-calib-agreement.json |

## Recent commits (last 2 weeks)

- `8be3181 2026-06-02 feat(phase6): read product threads from dynamic topics`
- `8e1a621 2026-06-02 fix(ops): retry transient hot-cold export disconnects`
- `ac0ed14 2026-06-02 docs: close phase6 and ollama validation handoff`
- `b0803c6 2026-06-02 feat(phase6): guarded dynamic topic dedup`
- `8dfd9f0 2026-06-02 feat(phase6): incremental dynamic_topics lifecycle wired into the snapshot cron`
- `ddab9a0 2026-06-02 feat(phase6): evidence-role student noise gate for dynamic_topics`
- `3bcb563 2026-06-02 feat(phase6): dynamic_topics shadow lifecycle (Sub-A)`
- `c463171 2026-06-02 feat(phase6): emergent topic identity resolver (Sub-A', read-only)`
- `927fda5 2026-06-02 feat(infra): daily 3-vendor calibration cron at 03:00`
- `65be407 2026-06-02 feat(validation): evidence-role student v2 (DB features) -- near-null result`
- `a24b9e4 2026-06-02 feat(validation): M3 remediation -- theme-hint tail + worst-topic gating`
- `fe47ba9 2026-06-02 feat(validation): M1<->M2 bridge -- gate-kept errors are recoverable evidence`
- `3c53f9c 2026-06-02 feat(validation): M2 -- train real evidence-role student v1`
- `c9f3e01 2026-06-02 feat(validation): quantify M1 -- scope gate lifts precision 41% -> 70%`
- `231733b 2026-06-02 docs(paper): RQ1 improvement methods grounded in failure anatomy`
- `0f82272 2026-06-02 feat(validation): RQ1 final result at scale (n~660)`
- `73b08a2 2026-06-02 feat(validation): scale RQ1 benchmark to 691 rows with 3-vendor consensus`
- `6370bcf 2026-06-01 fix(threads): drop redundant momentum verb from thread label`
- `77828cd 2026-06-01 feat(validation): add lexicon recall baseline metric`
- `8edea59 2026-06-01 docs(research): diagnose coverage root-cause as lexicon recall`
- `81f83ed 2026-06-01 feat(validation): three-vendor evidence role gold set (605 rows)`
- `bb6a46e 2026-06-01 feat(validation): widen evidence role sampler window`
- `6b2e7fc 2026-06-01 feat(validation): complete evidence role multi-vendor smoke`
- `cb29ef7 2026-06-01 docs(obsidian): connect evidence role pilot`
- `7a8ec51 2026-06-01 feat(validation): add evidence role student readiness report`
- `ad660ac 2026-06-01 feat(validation): build evidence role teacher consensus`
- `f6c73a7 2026-06-01 feat(validation): add evidence role teacher runner`
- `109d6d6 2026-06-01 feat(validation): sample evidence role teacher packet`
- `9e3c66b 2026-06-01 fix(validation): harden evidence role schema`
- `caa1700 2026-06-01 feat(validation): add evidence role schema`
- `c2dde0d 2026-06-01 docs(plan): implement evidence role pilot`
- `553e74a 2026-06-01 docs(spec): design narrative evidence role layer`
- `cbd495f 2026-06-01 feat(ops): report scope gate coverage`
- `7a66b3a 2026-06-01 docs: align next priorities after translation phase`
- `afeaa4b 2026-06-01 fix(ops): move hot-cold archive to external disk`
- `f6d524d 2026-06-01 fix(ops): run emergent snapshot cron off desktop`
- `955f8da 2026-06-01 docs(obsidian): add session hygiene maps`
- `e6ccca5 2026-06-01 docs(obsidian): add 000-INDEX.md vault entry point + gitignore .obsidian/`
- `86df741 2026-06-01 docs: inventory tool + ARCHITECTURE refresh + CLAUDE.md compact`
- `7cd9dc4 2026-05-31 feat(threads): bilingual evidence in ThreadFocusPanel`
- `bf3d8f2 2026-05-31 feat(translate): lazy headline translation layer (Phase 5)`
- `c0b4cee 2026-05-31 docs: close threads-wiring milestone in CLAUDE.md`
- `b076298 2026-05-31 feat(threads): augment /api/v2/threads with emergent-cluster rows`
- `2c1cfc3 2026-05-30 docs: clarify which surface Phase 2 wired (correction)`
- `a36f70c 2026-05-30 fix(brief): null-safe avg_confidence + dynamic source for emergent rows`
- `042b61e 2026-05-30 feat(emergent): wire emergent_clusters into brief Watchlist (Phase 2)`
- `ef6d81a 2026-05-30 feat(emergent): topic discovery POC + precision gate + design spec`
- `bedbcf7 2026-05-30 feat(brief): atlas-topic gated view + honest Watchlist framing`
- `75bb8d1 2026-05-29 docs: handoff — scope gate deployed to production (issue #203 closed)`
- `ee71215 2026-05-29 feat(api): wire scope gate into production (mig 045 + scorer + gated counts)`
- `2b29417 2026-05-29 feat(research): local $0/signal scope gate (e5-base) — production encoder`
- `c23784d 2026-05-29 feat(research): scope-gate inference engine (Phase C) + validation`
- `641e82d 2026-05-29 feat(research): persist production scope gate v1 (emb+conf, per-topic calibrated)`
- `a972486 2026-05-29 feat(research): semantic scope gate — keep@90% precision 64% -> 84% recall`
- `3e7c54e 2026-05-28 feat(research): Phase A 5k 3-vendor consensus — scope gate clears 90% precision`
- `eefbe41 2026-05-28 feat(research): Phase B scope-gate probe — learned gate beats Atlas confidence 30x`
- `08040e6 2026-05-28 docs: refresh handoff with 3-vendor 7-model consensus (47.69%)`
- `40f5f89 2026-05-28 feat(research): third vendor (DeepSeek) — 3-vendor 7-model consensus`
- `a33d74c 2026-05-28 docs: pause handoff — precision roadmap to 90-95% + tracking update`
- `bcbddc9 2026-05-28 feat(research): balanced 6-model panel reveals annotator vendor camps`
- `d43ab5c 2026-05-28 feat(research): cross-vendor annotator panel (GPT-4.1) breaks lineage caveat`
- `23628d2 2026-05-28 feat(research): 3-model annotator panel resolves the gold-standard question`
- `69c9621 2026-05-28 feat(research): multi-annotator agreement tool (Cohen + Fleiss kappa)`
- `166ee1f 2026-05-28 feat(research): dual-annotator precision picture exposes 35pp annotator gap`
- `f73041b 2026-05-28 feat(research): migration 044 theme-hint removals lift precision to 73.77%`
- `c69a856 2026-05-27 feat(research): migration 043 gold-guided removals lift precision +6.55pp`
- `5a9e63e 2026-05-27 feat(research): measure migration 042 lift on reviewed gold (null effect)`
- `162bcc9 2026-05-27 docs(research): close 2026-05-27 session — migration 042 applied to prod`
- `d7f3b45 2026-05-27 feat(research): llm multilingual vocab mining and migration 042 draft`
- `d9b723e 2026-05-27 docs(research): atlas papers master plan (series of 8 papers)`
- `01d5afb 2026-05-27 feat(research): llm annotator, kappa, and reasoning distillation`
- `6807df8 2026-05-27 feat(research): bootstrap CIs and Sonnet 4.6 baseline for atlas benchmark`
- `ca3bb3b 2026-05-27 feat(research): score reviewed atlas batch two`
- `a08324c 2026-05-26 feat(research): prepare batch two review ui`
- `ff07162 2026-05-26 feat(research): score reviewed atlas batch one`
- `855c698 2026-05-25 feat(research): finalize atlas review workflow`
- `30beca8 2026-05-25 feat(research): add atlas review templates`
- `82ef06d 2026-05-25 feat(research): add atlas label review packets`
- `9c29690 2026-05-25 feat(research): render atlas validation reports`
- `5fb3293 2026-05-25 feat(research): organize phase 1 atlas validation workflow`
