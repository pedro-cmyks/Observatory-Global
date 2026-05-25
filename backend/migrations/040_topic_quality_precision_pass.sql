-- Migration 040: Path C precision pass after all-topic quality audit.
--
-- Principle: prefer lower volume over visible false positives. These changes
-- prune broad single-word terms and generic GDELT hints that created clear
-- label/evidence mismatches in the 2026-05-25 audit.

-- `gender-violence-rights` was almost entirely riding generic HUMAN_RIGHTS,
-- KILL, PROTEST, and SOC_GENERALCRIME. Use explicit gender-violence / rights
-- vocabulary until a benchmark proves safer hints.
UPDATE atlas_topics
SET
    gdelt_theme_hints = ARRAY[]::text[],
    lexicon_terms = ARRAY[
        'femicide',
        'femicidio',
        'feminicidio',
        'gender violence',
        'gender-based violence',
        'violence against women',
        'violencia de genero',
        'violencia de género',
        'violencia machista',
        'domestic violence',
        'sexual assault',
        'rape',
        'raped',
        'women rights',
        'women''s rights',
        'reproductive rights',
        'derechos reproductivos',
        'abortion rights'
    ],
    updated_at = NOW()
WHERE slug = 'gender-violence-rights';

-- `labor-strike-disruption` had good evidence, but broad `strike` and `union`
-- admitted military strikes, sports, politics, and generic union headlines.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'wage dispute',
        'walkout',
        'labor protest',
        'labour protest',
        'workers strike',
        'worker strike',
        'nurses strike',
        'teachers strike',
        'lecturers strike',
        'strike over pay',
        'strike over wages',
        'industrial action',
        'trade union',
        'labor union',
        'labour union',
        'union leader',
        'union members',
        'union backlash',
        'huelga',
        'paro laboral',
        'sindicato',
        'grève',
        'sciopero',
        'greve'
    ],
    updated_at = NOW()
WHERE slug = 'labor-strike-disruption';

-- `transport-corridor-disruption` used bare `canal`, which matched TV channels,
-- entertainment, tourism, and drowning stories. Keep corridor-specific phrases.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'port disruption',
        'road blockade',
        'rail strike',
        'bridge collapse',
        'panama canal',
        'suez canal',
        'shipping lane',
        'shipping corridor',
        'maritime corridor',
        'maritime chokepoint',
        'strait closure',
        'port closure',
        'rail disruption',
        'railway disruption',
        'border crossing closed',
        'supply route blocked'
    ],
    updated_at = NOW()
WHERE slug = 'transport-corridor-disruption';

-- `disease-outbreak` is important, but generic HEALTH/MEDICAL/SAFETY hints
-- carried too much non-outbreak health material. Keep disease-specific hints
-- and explicit outbreak vocabulary.
UPDATE atlas_topics
SET
    gdelt_theme_hints = ARRAY[
        'WB_2663_EBOLA',
        'TAX_DISEASE_EBOLA',
        'TAX_DISEASE_DISEASE'
    ],
    lexicon_terms = ARRAY[
        'outbreak',
        'epidemic',
        'virus',
        'vaccination',
        'public health emergency',
        'ebola',
        'cholera',
        'measles',
        'dengue',
        'mpox',
        'hantavirus',
        'avian flu',
        'bird flu',
        'h5n1',
        'disease outbreak',
        'viral outbreak'
    ],
    updated_at = NOW()
WHERE slug = 'disease-outbreak';

-- `food-price-stress` had strong lex evidence but noisy generic price/poverty
-- hints. Keep FOOD_SECURITY as the only hint until benchmark labels justify
-- broader economic hints.
UPDATE atlas_topics
SET
    gdelt_theme_hints = ARRAY['FOOD_SECURITY'],
    updated_at = NOW()
WHERE slug = 'food-price-stress';

-- Single `displaced` / `evacuated` terms were pulling apartment fires and local
-- police events. Keep displacement phrases that carry crisis context.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'internally displaced',
        'forced displacement',
        'evacuated families',
        'displacement camp',
        'displacement crisis',
        'migrants stranded',
        'asylum seekers',
        'refugee camp',
        'idp camp',
        'humanitarian corridor',
        'exodus',
        'displaced persons',
        'refugees fleeing',
        'refugees flee',
        'fled fighting',
        'mass evacuation',
        'evacuation order'
    ],
    updated_at = NOW()
WHERE slug = 'forced-displacement';

-- `humanitarian-access-conflict` should be about access/relief in crisis, not
-- generic displacement.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'humanitarian corridor',
        'aid convoy',
        'relief access',
        'humanitarian access',
        'aid access',
        'blocked aid',
        'aid blockade',
        'refugee camp',
        'relief convoy'
    ],
    updated_at = NOW()
WHERE slug = 'humanitarian-access-conflict';

-- `disinformation-influence-operation` should not fire on generic "debunked"
-- or casual hoax language unless a future benchmark proves precision.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'disinformation',
        'misinformation',
        'fake news',
        'deepfake',
        'propaganda',
        'influence operation',
        'information operation',
        'coordinated inauthentic',
        'foreign influence campaign'
    ],
    updated_at = NOW()
WHERE slug = 'disinformation-influence-operation';

-- Avoid treating every refugee-camp casualty as border/migration pressure.
UPDATE atlas_topics
SET
    lexicon_terms = ARRAY[
        'asylum',
        'asylum seekers',
        'deportation',
        'mass deportation',
        'migrant caravan',
        'border crossing',
        'border pressure',
        'migrants stranded',
        'refugees fleeing',
        'refugees flee'
    ],
    updated_at = NOW()
WHERE slug = 'migration-border-pressure';
