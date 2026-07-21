-- 088_markets_l4_skeleton.sql — L4 markets relational schema (the SKELETON).
--
-- Lays out ALL product-facing relational tables NOW, dormant, so the surface can be
-- wired and the ingest can fatten; the analysis is cracked open later (design
-- docs/research/markets-l4/2026-07-21-markets-relational-axis-design.md). Everything
-- here is DESCRIPTIVE or an EMPTY result ledger — nothing is a claim, a forecast, a
-- direction, or a trade signal. Every causal / lead-lag row stays gated on the #226
-- re-run (event study at ~150 trading days).
--
-- Homes (design §6): the markets-side sqlite (markets/store.py) is the ACCUMULATION
-- working copy (market_price_daily, news_daily_intensity, comovement_result). THIS
-- migration is the canonical Atlas-DB home for the thin descriptive product tables +
-- the empty relation/result ledgers the frontend + endpoint read.
--
-- Server-only (read via FastAPI/asyncpg, never the anon Supabase client): RLS enabled
-- with NO policies + REVOKE ALL from anon/authenticated (the 086 pattern), so the
-- service role reaches them and clients never do.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. market_series — the descriptive PRICE NODE (thin; last close + 30d spark).
--    Populated by the M1 accumulator push (markets/push_atlas_db.py). Level+trend
--    only; NO forward value, NO signed field, NO signal.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_series (
    symbol        text PRIMARY KEY,          -- 'CL=F', 'COP=X', 'EC'
    label         text NOT NULL,             -- 'Brent crude, front-month'
    asset_class   text NOT NULL,             -- energy|metal|fx|fx-index|equity-index|equity-etf|equity-single|risk|ag|rate
    last_close    numeric,                   -- NULL until the accumulator pushes
    last_close_at date,
    spark_30d     numeric[],                 -- trailing daily closes → node sparkline
    updated_at    timestamptz DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. country_instrument_universe — the DESCRIPTIVE backbone (design §5). Each
--    country's OWN instruments by identity (FX / index / champion / export-commodity).
--    basis='descriptive': COP *is* Colombia's currency — no discovery, no #226 gate.
--    NOTE role='export-commodity' is stored (a customs fact) but the Brief COUNTRY
--    card must NOT render it as a tile (a globally-moving price beside country news
--    is the strongest post-hoc causal trap; design §7).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS country_instrument_universe (
    country_code char(2) NOT NULL,
    symbol       text NOT NULL,              -- loose ref to market_series.symbol (no FK: a
                                             -- prior may name an instrument not yet tracked)
    role         text NOT NULL CHECK (role IN ('currency','index','champion','export-commodity')),
    basis        text NOT NULL DEFAULT 'descriptive',
    note         text,
    PRIMARY KEY (country_code, symbol, role)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. category_instrument_map — the PRIOR/hint (design §4), demoted from the m0
--    INSTRUMENT_MAP. A pre-registered, FALSIFIABLE guess at where to look; NEVER a
--    relation. A mapped pair with no measured co-movement is a WRONG prior, reported
--    as such once the study runs.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS category_instrument_map (
    category_slug text NOT NULL,
    symbol        text NOT NULL,
    basis         text NOT NULL DEFAULT 'domain-prior',
    note          text,
    PRIMARY KEY (category_slug, symbol)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. comovement_result — the DISCOVERY ledger (positives AND nulls). Written by the
--    event study (forward + reverse) when it runs; canonical schema home here, the
--    sqlite store mirrors it for the offline study. EMPTY until the study runs; tier
--    2 ('established') is structurally unreachable until #226 clears (design §8).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS comovement_result (
    axis_kind       text NOT NULL,           -- 'category' | 'topic' | 'country'
    axis_id         text NOT NULL,
    symbol          text NOT NULL,
    study_direction text NOT NULL CHECK (study_direction IN ('news->market','market->news')),
    lag             int NOT NULL,            -- t+1 / t+2 (forward) or δ=-1/-2 (reverse); never t0
    stat            numeric,                 -- ratio / co-movement magnitude
    n_events        int,
    n_effective     int,                     -- block/cluster-adjusted event count
    perm_p          numeric,
    fdr_q           numeric,
    hypothesis_lane text CHECK (hypothesis_lane IN ('confirmatory','exploratory')),
    regime_span     daterange,
    tier            int NOT NULL DEFAULT 0 CHECK (tier IN (0,1,2)),
    method_version  text NOT NULL,
    computed_at     timestamptz DEFAULT now(),
    PRIMARY KEY (axis_kind, axis_id, symbol, study_direction, lag, method_version)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. market_relation_public — the PRODUCT face of a discovered relation. EMPTY until
--    a relation reaches product (tier ≥ 1 in a lane; drawn only if #226 ever proves a
--    lead/lag). NO price, NO forward value, NO signed field — by construction it can
--    never carry a trade signal (design §8). is_directional stays false: the method is
--    magnitude-only (|move|), it has no stance model.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_relation_public (
    axis_kind       text NOT NULL,
    axis_id         text NOT NULL,
    symbol          text NOT NULL,
    tier            int NOT NULL DEFAULT 0 CHECK (tier IN (0,1,2)),
    label_text      text,                    -- past-tense, window visible, "NOT causal"
    measured_window daterange,
    perm_p          numeric,
    n_events        int,
    is_directional  boolean NOT NULL DEFAULT false,
    disclaimer      text NOT NULL DEFAULT 'descriptive co-variance, not investment advice',
    updated_at      timestamptz DEFAULT now(),
    PRIMARY KEY (axis_kind, axis_id, symbol)
);

CREATE INDEX IF NOT EXISTS ix_country_instr_country ON country_instrument_universe(country_code);
CREATE INDEX IF NOT EXISTS ix_cat_instr_slug        ON category_instrument_map(category_slug);
CREATE INDEX IF NOT EXISTS ix_comovement_symbol     ON comovement_result(symbol);
CREATE INDEX IF NOT EXISTS ix_relation_public_axis  ON market_relation_public(axis_kind, axis_id);

-- ── server-only hardening (086 pattern): RLS on, no policies, revoke from clients ──
ALTER TABLE market_series               ENABLE ROW LEVEL SECURITY;
ALTER TABLE country_instrument_universe ENABLE ROW LEVEL SECURITY;
ALTER TABLE category_instrument_map     ENABLE ROW LEVEL SECURITY;
ALTER TABLE comovement_result           ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_relation_public      ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON market_series               FROM anon, authenticated;
REVOKE ALL ON country_instrument_universe FROM anon, authenticated;
REVOKE ALL ON category_instrument_map     FROM anon, authenticated;
REVOKE ALL ON comovement_result           FROM anon, authenticated;
REVOKE ALL ON market_relation_public      FROM anon, authenticated;

-- ── seed: descriptive metadata (instrument identities) — safe now, no claim ──
INSERT INTO market_series (symbol, label, asset_class) VALUES
    ('CL=F',     'WTI crude, front-month',        'energy'),
    ('GC=F',     'Gold, front-month',             'metal'),
    ('HG=F',     'Copper, front-month',           'metal'),
    ('^GSPC',    'S&P 500',                       'equity-index'),
    ('DX-Y.NYB', 'US Dollar Index (DXY)',         'fx-index'),
    ('^VIX',     'CBOE Volatility Index',         'risk'),
    ('^DJI',     'Dow Jones Industrial Average',  'equity-index'),
    ('COP=X',    'Colombian peso (USD/COP)',      'fx'),
    ('GXG',      'Global X MSCI Colombia ETF',    'equity-etf'),
    ('EC',       'Ecopetrol (ADR)',               'equity-single'),
    ('CIB',      'Bancolombia (ADR)',             'equity-single'),
    ('KC=F',     'Coffee, front-month',           'ag'),
    ('BRL=X',    'Brazilian real (USD/BRL)',      'fx'),
    ('EWZ',      'iShares MSCI Brazil ETF',       'equity-etf'),
    ('PBR',      'Petrobras (ADR)',               'equity-single'),
    ('VALE',     'Vale (ADR)',                    'equity-single'),
    ('MXN=X',    'Mexican peso (USD/MXN)',        'fx'),
    ('EWW',      'iShares MSCI Mexico ETF',       'equity-etf')
ON CONFLICT (symbol) DO NOTHING;

INSERT INTO country_instrument_universe (country_code, symbol, role, note) VALUES
    ('US','^GSPC','index','US benchmark'),
    ('US','^DJI','index','US benchmark'),
    ('CO','COP=X','currency','Colombian peso'),
    ('CO','GXG','index','Colombia country ETF'),
    ('CO','EC','champion','Ecopetrol — state oil champion'),
    ('CO','CIB','champion','Bancolombia'),
    ('CO','KC=F','export-commodity','coffee (customs) — NOT a Brief country-card tile'),
    ('BR','BRL=X','currency','Brazilian real'),
    ('BR','EWZ','index','Brazil country ETF'),
    ('BR','PBR','champion','Petrobras'),
    ('BR','VALE','champion','Vale'),
    ('MX','MXN=X','currency','Mexican peso'),
    ('MX','EWW','index','Mexico country ETF')
ON CONFLICT (country_code, symbol, role) DO NOTHING;

INSERT INTO category_instrument_map (category_slug, symbol, note) VALUES
    ('oil-gas-supply-risk','CL=F','energy supply → crude'),
    ('oil-gas-supply-risk','NG=F','energy supply → natgas'),
    ('armed-conflict-escalation','CL=F','war risk premium → crude'),
    ('armed-conflict-escalation','GC=F','flight to gold'),
    ('armed-conflict-escalation','ITA','defense equities'),
    ('sanctions-diplomatic-pressure','GC=F','flight to gold'),
    ('sanctions-diplomatic-pressure','CL=F','supply disruption → crude'),
    ('agriculture-crop-risk','ZW=F','crop risk → wheat'),
    ('food-price-stress','ZW=F','food stress → wheat'),
    ('currency-debt-stress','GC=F','store of value'),
    ('gang-control-urban-security','COP=X','LatAm risk → COP'),
    ('gang-control-urban-security','MXN=X','LatAm risk → MXN'),
    ('migration-border-pressure','MXN=X','border → MXN'),
    ('cyberattack-infrastructure','ITA','infra/defense equities')
ON CONFLICT (category_slug, symbol) DO NOTHING;

COMMENT ON TABLE market_series IS 'L4 descriptive price node (thin, product-facing). No forecast/signal. See docs/research/markets-l4/2026-07-21-markets-relational-axis-design.md';
COMMENT ON TABLE market_relation_public IS 'L4 discovered-relation product face. EMPTY until #226 clears; never causal, never a trade signal.';
