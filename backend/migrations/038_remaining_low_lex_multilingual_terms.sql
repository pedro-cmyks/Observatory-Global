-- Migration 038: Path A rollout for remaining low-lex atlas topics.
--
-- Spec: docs/specs/2026-05-23-ai-assisted-taxonomy.md
-- Tracking: GitHub issue #202 (Path A) — multilingual lex via LLM.
--
-- Topics covered:
--   - fuel-subsidy-unrest
--   - food-price-stress
--   - housing-cost-pressure
--   - mining-royalty-risk
--
-- Methodology:
-- 1. Pulled live 24h metrics, current lexicon terms, lex-supported samples,
--    and theme-only samples for each topic.
-- 2. SQL-counted candidate multilingual phrase matchers against 24h
--    signals_v2 headlines.
-- 3. Spot-checked heavy hitters before accepting them.
-- 4. Rejected broad/noisy terms even when they increased volume.
--
-- Baseline before this migration:
--   food-price-stress:      371 assignments, 65 lex,  7 high_conf, lex_pct 17.52
--   fuel-subsidy-unrest:    519 assignments, 27 lex,  2 high_conf, lex_pct  5.20
--   housing-cost-pressure:  315 assignments, 32 lex,  0 high_conf, lex_pct 10.16
--   mining-royalty-risk:     73 assignments,  9 lex,  0 high_conf, lex_pct 12.33
--
-- Rejected / removed:
--   - food-price-stress: "shortage" matched fuel, lifeguard, organ donor,
--     water, port, and other non-food shortages. "hunger" matched charity
--     drives as well as food insecurity.
--   - housing-cost-pressure: "mortgage" matched stock/financial tickers and
--     market notes; "eviction" matched Delhi Gymkhana Club land/legal stories,
--     not household housing pressure.
--   - mining-royalty-risk: "concession" matched ports, beaches, diplomacy,
--     school rooms, and dealerships. "gold mine" matched idioms/recipes.
--   - Across all topics: avoid exact one-word roots such as "fuel", "food",
--     "rent", "mining", and "royalty".

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing precise English
        'fuel subsidy',
        'gasoline price',
        'diesel price',
        'transport strike',
        'fuel protest',
        -- English expansion
        'fuel price',
        'fuel prices',
        'fuel price hike',
        'fuel rates',
        'petrol price',
        'petrol prices',
        'petrol diesel price',
        'petrol-diesel price',
        'diesel prices',
        'rising petrol',
        'rising diesel',
        'gas prices',
        -- Spanish / Portuguese
        'subsidio combustible',
        'subsidio gasolina',
        'precio gasolina',
        'precios gasolina',
        'precio de gasolina',
        'precios de gasolina',
        'precio diesel',
        'precio diésel',
        'precios combustibles',
        'aumento gasolina',
        'aumento combustibles',
        'combustibles',
        -- French / Italian / German / Turkish
        'prix carburant',
        'carburant',
        'carburants',
        'benzinpreise',
        'preise benzin',
        'akaryakıt',
        'akaryakit'
    ],
    updated_at = NOW()
WHERE slug='fuel-subsidy-unrest';

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing precise English
        'food prices',
        'bread price',
        'rice price',
        'food inflation',
        -- English expansion
        'food price',
        'bread prices',
        'rice prices',
        'grocery prices',
        'rising food',
        'staple food',
        'food insecurity',
        -- Spanish / Portuguese
        'canasta basica',
        'canasta básica',
        'precios alimentos',
        'precio alimentos',
        'precios de alimentos',
        'inflacion alimentaria',
        'inflación alimentaria',
        'alimentos caros',
        'precios comida',
        -- French / German / Turkish
        'prix alimentaires',
        'inflation alimentaire',
        'preise lebensmittel',
        'lebensmittelpreise',
        'gida fiyat',
        'gıda fiyat'
    ],
    updated_at = NOW()
WHERE slug='food-price-stress';

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing precise English
        'rent increase',
        'housing crisis',
        'affordable housing',
        -- English expansion
        'rent increases',
        'rising rents',
        'rental prices',
        'housing affordability',
        'home prices',
        'house prices',
        -- Spanish / Portuguese
        'crisis vivienda',
        'crisis de vivienda',
        'precio vivienda',
        'precios vivienda',
        'precio de vivienda',
        'precios de vivienda',
        'precios del alquiler',
        'alquileres',
        'desahucio',
        'vivienda protegida',
        'vivienda digna',
        -- French / German / Turkish
        'logement abordable',
        'crise logement',
        'prix logement',
        'mietpreise',
        'mieten steigen',
        'konut fiyat',
        'kira artışı',
        'kira artisi'
    ],
    updated_at = NOW()
WHERE slug='housing-cost-pressure';

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing precise English
        'mining royalty',
        'copper royalty',
        'mining permit',
        'resource nationalism',
        -- English expansion
        'mining royalties',
        'mining concession',
        'mining concessions',
        'mining permits',
        'mining tax',
        'mining taxes',
        'mining project',
        'mining law',
        'mining investment',
        'copper mine',
        'lithium mine',
        'coal mine',
        'mine explosion',
        'coal mine explosion',
        'mine blast',
        -- Spanish / Portuguese
        'royalty minera',
        'regalia minera',
        'concesion minera',
        'concesión minera',
        'concesiones mineras',
        'permiso minero',
        'mineria ilegal',
        'minería ilegal',
        'mina de carbon',
        'mina de carbón',
        'explotacion minera',
        'explotación minera',
        -- French
        'redevance minière',
        'concession minière',
        'permis minier'
    ],
    updated_at = NOW()
WHERE slug='mining-royalty-risk';
