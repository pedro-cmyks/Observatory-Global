-- Migration 019: Atlas Topic Intelligence normalized topic layer.
-- Issue #167, docs/superpowers/plans/2026-05-19-topic-intelligence-and-source-visibility.md.
--
-- Design principle:
--   signals_v2.themes remains raw source taxonomy/provenance, especially for GDELT.
--   signal_topic_assignments is the normalized product semantics layer used to compare
--   every source, including GDELT, RSS, APIs, ReliefWeb, and Reddit.
--
-- Learning principle:
--   topic_learning_examples stores auto-accepted, rejected, corrected, and benchmarked
--   examples so Atlas can calibrate thresholds by source/language/model over time.

CREATE TABLE IF NOT EXISTS atlas_topics (
    id                BIGSERIAL PRIMARY KEY,
    slug              TEXT NOT NULL UNIQUE,
    label             TEXT NOT NULL,
    description       TEXT,
    parent_domain     TEXT NOT NULL,
    lexicon_terms     TEXT[] NOT NULL DEFAULT '{}',
    gdelt_theme_hints TEXT[] NOT NULL DEFAULT '{}',
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT atlas_topics_slug_format
        CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);

CREATE INDEX IF NOT EXISTS idx_atlas_topics_domain_active
    ON atlas_topics (parent_domain, is_active);

CREATE INDEX IF NOT EXISTS idx_atlas_topics_lexicon_terms
    ON atlas_topics USING GIN (lexicon_terms);

CREATE INDEX IF NOT EXISTS idx_atlas_topics_gdelt_theme_hints
    ON atlas_topics USING GIN (gdelt_theme_hints);

CREATE TABLE IF NOT EXISTS signal_topic_assignments (
    signal_id      BIGINT NOT NULL,
    topic_id       BIGINT NOT NULL,
    method         TEXT NOT NULL,
    confidence     DOUBLE PRECISION NOT NULL,
    model_name     TEXT,
    model_version  TEXT NOT NULL DEFAULT 'atlas-topic-v1',
    evidence       JSONB NOT NULL DEFAULT '{}'::jsonb,
    assigned_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT signal_topic_assignments_signal_fk
        FOREIGN KEY (signal_id) REFERENCES signals_v2(id) ON DELETE CASCADE,
    CONSTRAINT signal_topic_assignments_topic_fk
        FOREIGN KEY (topic_id) REFERENCES atlas_topics(id) ON DELETE CASCADE,
    CONSTRAINT signal_topic_assignments_confidence_range
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT signal_topic_assignments_method_valid
        CHECK (method IN (
            'lexicon',
            'embedding',
            'zero_shot',
            'hybrid',
            'analyst',
            'benchmark'
        )),
    PRIMARY KEY (signal_id, topic_id, method, model_version)
);

CREATE INDEX IF NOT EXISTS idx_signal_topic_assignments_topic_confidence
    ON signal_topic_assignments (topic_id, confidence DESC, assigned_at DESC);

CREATE INDEX IF NOT EXISTS idx_signal_topic_assignments_signal
    ON signal_topic_assignments (signal_id);

CREATE INDEX IF NOT EXISTS idx_signal_topic_assignments_method_version
    ON signal_topic_assignments (method, model_version, assigned_at DESC);

CREATE INDEX IF NOT EXISTS idx_signal_topic_assignments_evidence
    ON signal_topic_assignments USING GIN (evidence);

CREATE TABLE IF NOT EXISTS topic_learning_examples (
    id                  BIGSERIAL PRIMARY KEY,
    signal_id           BIGINT,
    topic_id            BIGINT,
    corrected_topic_id  BIGINT,
    candidate_slug      TEXT,
    candidate_label     TEXT,
    source_family       TEXT,
    attribution_method  TEXT,
    source_lang         TEXT,
    country_code        TEXT,
    headline_hash       TEXT,
    headline_sample     TEXT,
    method              TEXT NOT NULL,
    model_name          TEXT,
    model_version       TEXT NOT NULL DEFAULT 'atlas-topic-v1',
    confidence          DOUBLE PRECISION,
    decision            TEXT NOT NULL,
    analyst_id          TEXT,
    evidence            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT topic_learning_examples_signal_fk
        FOREIGN KEY (signal_id) REFERENCES signals_v2(id) ON DELETE SET NULL,
    CONSTRAINT topic_learning_examples_topic_fk
        FOREIGN KEY (topic_id) REFERENCES atlas_topics(id) ON DELETE SET NULL,
    CONSTRAINT topic_learning_examples_corrected_topic_fk
        FOREIGN KEY (corrected_topic_id) REFERENCES atlas_topics(id) ON DELETE SET NULL,
    CONSTRAINT topic_learning_examples_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    CONSTRAINT topic_learning_examples_decision_valid
        CHECK (decision IN (
            'auto_accept',
            'auto_reject',
            'analyst_confirm',
            'analyst_reject',
            'analyst_correct',
            'threshold_review',
            'benchmark_label'
        )),
    CONSTRAINT topic_learning_examples_method_valid
        CHECK (method IN (
            'lexicon',
            'embedding',
            'zero_shot',
            'hybrid',
            'analyst',
            'benchmark'
        ))
);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_signal
    ON topic_learning_examples (signal_id);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_topic_decision
    ON topic_learning_examples (topic_id, decision, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_source_lang
    ON topic_learning_examples (source_family, attribution_method, source_lang, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_model
    ON topic_learning_examples (model_version, method, decision, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_headline_hash
    ON topic_learning_examples (headline_hash);

CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_evidence
    ON topic_learning_examples USING GIN (evidence);

INSERT INTO atlas_topics (slug, label, description, parent_domain, lexicon_terms, gdelt_theme_hints)
VALUES
    ('armed-conflict-escalation', 'Armed conflict escalation', 'Armed violence, battlefield escalation, attacks, or territorial conflict.', 'conflict-security', ARRAY['armed conflict','clashes','offensive','airstrike','shelling','militia','rebels'], ARRAY['ARMEDCONFLICT','MILITARY','KILL']),
    ('humanitarian-access-conflict', 'Humanitarian access under conflict', 'Aid access, corridors, displacement, or relief operations constrained by violence.', 'migration-humanitarian', ARRAY['humanitarian corridor','aid convoy','relief access','displaced','refugee camp'], ARRAY['DISASTER_RESPONSE','REFUGEES','CRISISLEX_C03_DEAD_WOUNDED']),
    ('gang-control-urban-security', 'Gang control and urban security', 'Criminal armed groups controlling neighborhoods, transport, prisons, or urban services.', 'conflict-security', ARRAY['gang','cartel','extortion','prison riot','urban violence'], ARRAY['CRIME','TAX_TERROR','ARREST']),
    ('election-legitimacy-dispute', 'Election legitimacy dispute', 'Election fraud claims, contested results, institutional disputes, or legitimacy challenges.', 'political-legitimacy', ARRAY['election fraud','contested election','vote count','electoral court','ballot'], ARRAY['ELECTION','GOVERNMENT','PROTEST']),
    ('constitutional-institutional-crisis', 'Constitutional or institutional crisis', 'Constitutional conflict, court-government confrontation, impeachment, or institutional rupture.', 'political-legitimacy', ARRAY['constitutional crisis','supreme court','impeachment','state of emergency','parliament dissolved'], ARRAY['GOVERNMENT','COURT','LEADER']),
    ('corruption-investigation', 'Corruption investigation', 'Bribery, embezzlement, procurement corruption, investigations, or anti-corruption probes.', 'political-legitimacy', ARRAY['corruption','bribery','embezzlement','procurement scandal','kickback'], ARRAY['CORRUPTION','INVESTIGATION','COURT']),
    ('fuel-subsidy-unrest', 'Fuel subsidy unrest', 'Fuel price, subsidy, or transport-cost disputes linked to strikes or protests.', 'economic-stress', ARRAY['fuel subsidy','gasoline price','diesel price','transport strike','fuel protest'], ARRAY['ECON_INFLATION','PROTEST','STRIKE']),
    ('food-price-stress', 'Food price stress', 'Food inflation, shortages, staples, hunger, or affordability pressure.', 'economic-stress', ARRAY['food prices','bread price','rice price','shortage','food inflation','hunger'], ARRAY['ECON_INFLATION','FOOD_SECURITY','HEALTH']),
    ('currency-debt-stress', 'Currency and debt stress', 'Currency collapse, sovereign debt, IMF negotiations, reserves, or default risk.', 'economic-stress', ARRAY['currency crisis','debt default','imf bailout','foreign reserves','devaluation'], ARRAY['ECON_BANKRUPTCY','ECON_INFLATION','ECON_STOCKMARKET']),
    ('mining-royalty-risk', 'Mining royalty and resource risk', 'Mining taxes, royalties, concessions, investment disputes, or resource nationalism.', 'resources-energy', ARRAY['mining royalty','copper royalty','concession','resource nationalism','mining permit'], ARRAY['ECON_TRADE','TAX_FNCACT','ENV_MINING']),
    ('energy-grid-instability', 'Energy grid instability', 'Power outages, grid stress, rationing, generation shortages, or energy infrastructure failures.', 'resources-energy', ARRAY['power outage','blackout','grid failure','energy rationing','electricity shortage'], ARRAY['ENERGY','INFRASTRUCTURE','ENV_CLIMATECHANGE']),
    ('oil-gas-supply-risk', 'Oil and gas supply risk', 'Oil, gas, pipeline, LNG, refinery, or energy export disruption.', 'resources-energy', ARRAY['pipeline','oil export','gas supply','lng','refinery'], ARRAY['ENERGY','ECON_TRADE','SANCTION']),
    ('water-stress-drought', 'Water stress and drought', 'Drought, reservoir stress, water rationing, or water conflict.', 'climate-disaster', ARRAY['drought','water rationing','reservoir','water shortage','dry season'], ARRAY['ENV_CLIMATECHANGE','UNGP_DISASTER','WATER_SECURITY']),
    ('flood-landslide-disaster', 'Flood and landslide disaster', 'Flooding, landslides, heavy rains, evacuations, or disaster response.', 'climate-disaster', ARRAY['flood','landslide','heavy rain','evacuation','mudslide'], ARRAY['UNGP_DISASTER','DISASTER_RESPONSE','ENV_CLIMATECHANGE']),
    ('heat-health-risk', 'Heat and public health risk', 'Heat waves, thermal stress, mortality, health warnings, or climate-health risk.', 'public-health', ARRAY['heat wave','extreme heat','heatstroke','public health warning','thermal stress'], ARRAY['HEALTH','ENV_CLIMATECHANGE','UNGP_DISASTER']),
    ('disease-outbreak', 'Disease outbreak', 'Emerging disease, outbreak, epidemic, vaccination, or public health emergency.', 'public-health', ARRAY['outbreak','epidemic','virus','vaccination','public health emergency'], ARRAY['HEALTH','MEDICAL','CRISISLEX_C07_SAFETY']),
    ('migration-border-pressure', 'Migration and border pressure', 'Migration flows, border crossings, deportations, asylum, or refugee movement.', 'migration-humanitarian', ARRAY['migrant caravan','border crossing','asylum','deportation','refugee'], ARRAY['MIGRATION','REFUGEES','HUMAN_RIGHTS']),
    ('forced-displacement', 'Forced displacement', 'Internal displacement, evacuations, expulsions, or conflict/climate displacement.', 'migration-humanitarian', ARRAY['internally displaced','forced displacement','evacuated families','displacement camp'], ARRAY['REFUGEES','HUMAN_RIGHTS','ARMEDCONFLICT']),
    ('labor-strike-disruption', 'Labor strike disruption', 'Labor strikes, unions, wage disputes, or service shutdowns.', 'social-unrest-labor', ARRAY['strike','union','wage dispute','walkout','labor protest'], ARRAY['LABOR','STRIKE','PROTEST']),
    ('student-youth-protest', 'Student and youth protest', 'Student movements, youth protests, campus mobilization, or education unrest.', 'social-unrest-labor', ARRAY['student protest','campus protest','youth movement','tuition protest'], ARRAY['PROTEST','EDUCATION','SOC_POINTSOFVIEW']),
    ('gender-violence-rights', 'Gender violence and rights', 'Femicide, gender violence, reproductive rights, or gender-rights mobilization.', 'social-unrest-labor', ARRAY['femicide','gender violence','women rights','reproductive rights'], ARRAY['HUMAN_RIGHTS','KILL','PROTEST']),
    ('transport-corridor-disruption', 'Transport corridor disruption', 'Ports, roads, canals, railways, bridges, or chokepoints disrupted.', 'technology-infrastructure', ARRAY['port disruption','road blockade','rail strike','canal','bridge collapse'], ARRAY['TRANSPORT','INFRASTRUCTURE','ECON_TRADE']),
    ('cyberattack-infrastructure', 'Cyberattack on infrastructure', 'Cyberattacks against government, finance, utilities, telecoms, or critical infrastructure.', 'technology-infrastructure', ARRAY['cyberattack','ransomware','data breach','critical infrastructure','hackers'], ARRAY['CYBER_ATTACK','TECHNOLOGY','INFRASTRUCTURE']),
    ('telecom-internet-shutdown', 'Telecom or internet shutdown', 'Internet shutdowns, telecom outages, censorship, or connectivity disruption.', 'technology-infrastructure', ARRAY['internet shutdown','telecom outage','network disruption','censorship','connectivity'], ARRAY['TECHNOLOGY','MEDIA_CENSORSHIP','HUMAN_RIGHTS']),
    ('disinformation-influence-operation', 'Disinformation and influence operation', 'Coordinated disinformation, propaganda, influence operations, or information manipulation.', 'information-environment', ARRAY['disinformation','propaganda','influence operation','fake news','bot network'], ARRAY['MEDIA_MSM','SOC_POINTSOFVIEW','TAX_FNCACT']),
    ('press-freedom-crackdown', 'Press freedom crackdown', 'Journalist arrests, media censorship, press restrictions, or newsroom attacks.', 'information-environment', ARRAY['journalist arrested','press freedom','media censorship','newsroom raid','reporter detained'], ARRAY['MEDIA_CENSORSHIP','HUMAN_RIGHTS','ARREST']),
    ('sanctions-diplomatic-pressure', 'Sanctions and diplomatic pressure', 'Sanctions, diplomatic expulsions, treaties, negotiations, or international pressure.', 'political-legitimacy', ARRAY['sanctions','diplomatic pressure','embassy','treaty','negotiations'], ARRAY['SANCTION','TAX_DIPLOMACY','TREATY']),
    ('trade-export-restriction', 'Trade and export restriction', 'Export bans, tariffs, trade disputes, shipping restrictions, or customs barriers.', 'economic-stress', ARRAY['export ban','tariff','trade dispute','customs','shipping restriction'], ARRAY['ECON_TRADE','SANCTION','TAX_DIPLOMACY']),
    ('housing-cost-pressure', 'Housing cost pressure', 'Rent spikes, housing affordability, evictions, mortgages, or urban cost pressure.', 'economic-stress', ARRAY['rent increase','housing crisis','eviction','mortgage','affordable housing'], ARRAY['ECON_INFLATION','SOC_ECONCOSTOFLIVING','PROTEST']),
    ('agriculture-crop-risk', 'Agriculture and crop risk', 'Crop failures, pests, fertilizer, harvest shocks, or farm production risk.', 'climate-disaster', ARRAY['crop failure','harvest','fertilizer','pest outbreak','farmers'], ARRAY['AGRICULTURE','FOOD_SECURITY','ENV_CLIMATECHANGE'])
ON CONFLICT (slug) DO UPDATE SET
    label = EXCLUDED.label,
    description = EXCLUDED.description,
    parent_domain = EXCLUDED.parent_domain,
    lexicon_terms = EXCLUDED.lexicon_terms,
    gdelt_theme_hints = EXCLUDED.gdelt_theme_hints,
    is_active = TRUE,
    updated_at = NOW();
