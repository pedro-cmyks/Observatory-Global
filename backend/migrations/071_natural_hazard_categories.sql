-- Migration 071: add the two natural-hazard categories the taxonomy always
-- flagged but never inserted (#204-class typing bug, 2026-07-06).
--
-- ROOT CAUSE: candidate-v2.json flagged `earthquake-volcano-disaster` and
-- `wildfire-storm-disaster` as FLAGGED_ADD, but they were never written to
-- atlas_topics. compute_category_typing.py --deepseek builds its category
-- MENU from `atlas_topics WHERE is_active`, so a seismic story
-- ("Double Séisme Venezuela", "Venezuela Earthquakes Kill 32") had NO
-- earthquake bucket to land in → DeepSeek force-fit it into the nearest
-- surviving crisis category. High-casualty language ("bilan des victimes",
-- "morts", "Kill 32") pushed quakes into "Armed conflict escalation" /
-- "Flood and landslide disaster" / "Weather and Climate". The earlier correct
-- "Earthquake or volcanic disaster" typings came from an OLD run that used
-- the candidate-v2 fallback menu (which HAS the category) — the live menu
-- had drifted out of sync.
--
-- FIX: seed both categories so the live menu (and the lexical/theme
-- assignment path) offer them. Labels match candidate-v2 EXACTLY so the
-- existing correct typings stay consistent. Theme hints are disaster-specific
-- (NATURAL_DISASTER_*), deliberately NOT KILL — KILL on armed-conflict-
-- escalation (migration 019) is what pulls casualty language into conflict.

INSERT INTO atlas_topics (slug, label, description, parent_domain, lexicon_terms, gdelt_theme_hints, origin)
VALUES
    ('earthquake-volcano-disaster', 'Earthquake or volcanic disaster',
     'Seismic or volcanic events causing casualties, damage, or evacuation: earthquakes, aftershocks, tsunamis, volcanic eruptions, ashfall evacuations.',
     'climate-disaster',
     ARRAY['earthquake','quake','seismic','aftershock','tremor','magnitude','epicenter','volcano','eruption','tsunami','seisme','sisme','sismo','terremoto','temblor','erupcion'],
     ARRAY['NATURAL_DISASTER_EARTHQUAKE','NATURAL_DISASTER_VOLCANO','NATURAL_DISASTER_TSUNAMI','UNGP_DISASTER'],
     'seed'),
    ('wildfire-storm-disaster', 'Wildfire or severe-storm disaster',
     'Wildfires, hurricanes/cyclones, tornadoes, or severe storms causing harm, damage, or evacuation.',
     'climate-disaster',
     ARRAY['wildfire','bushfire','forest fire','hurricane','typhoon','cyclone','tornado','blizzard','storm surge','incendio','huracan','ciclon','tornado','tormenta'],
     ARRAY['NATURAL_DISASTER_WILDFIRE','NATURAL_DISASTER_HURRICANE','NATURAL_DISASTER_TORNADO','NATURAL_DISASTER_STORM','UNGP_DISASTER'],
     'seed')
ON CONFLICT (slug) DO UPDATE SET
    label = EXCLUDED.label,
    description = EXCLUDED.description,
    parent_domain = EXCLUDED.parent_domain,
    lexicon_terms = EXCLUDED.lexicon_terms,
    gdelt_theme_hints = EXCLUDED.gdelt_theme_hints,
    is_active = true,
    updated_at = now();
