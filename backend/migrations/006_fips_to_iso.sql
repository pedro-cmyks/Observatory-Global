-- Migration 006: Convert FIPS country codes to ISO 3166-1 alpha-2
--
-- GDELT uses FIPS 10-4 codes, but maps and APIs expect ISO codes.
-- This migration converts all existing signals to use ISO codes.
--
-- Critical conversions:
-- - UK → GB (United Kingdom)
-- - GM → DE (Germany)  
-- - CH → CN (China, then SZ → CH for Switzerland)
-- - RS → RU (Russia)

-- Before migration - check what we have
DO $$
DECLARE
    uk_count INTEGER;
    gm_count INTEGER;
    ch_count INTEGER;
    sz_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO uk_count FROM signals_v2 WHERE country_code = 'UK';
    SELECT COUNT(*) INTO gm_count FROM signals_v2 WHERE country_code = 'GM';
    SELECT COUNT(*) INTO ch_count FROM signals_v2 WHERE country_code = 'CH';
    SELECT COUNT(*) INTO sz_count FROM signals_v2 WHERE country_code = 'SZ';
    
    RAISE NOTICE 'Pre-migration counts:';
    RAISE NOTICE '  UK (→GB): %', uk_count;
    RAISE NOTICE '  GM (→DE): %', gm_count;
    RAISE NOTICE '  CH (→CN): %', ch_count;
    RAISE NOTICE '  SZ (→CH): %', sz_count;
END $$;

-- Major conversions (most common in our data)
UPDATE signals_v2 SET country_code = 'GB' WHERE country_code = 'UK';
UPDATE signals_v2 SET country_code = 'DE' WHERE country_code = 'GM';
UPDATE signals_v2 SET country_code = 'RU' WHERE country_code = 'RS';
UPDATE signals_v2 SET country_code = 'JP' WHERE country_code = 'JA';
UPDATE signals_v2 SET country_code = 'IE' WHERE country_code = 'EI';
UPDATE signals_v2 SET country_code = 'ES' WHERE country_code = 'SP';
UPDATE signals_v2 SET country_code = 'ZA' WHERE country_code = 'SF';
UPDATE signals_v2 SET country_code = 'UA' WHERE country_code = 'UP';
UPDATE signals_v2 SET country_code = 'KR' WHERE country_code = 'KS';
UPDATE signals_v2 SET country_code = 'TR' WHERE country_code = 'TU';
UPDATE signals_v2 SET country_code = 'IL' WHERE country_code = 'IS';
UPDATE signals_v2 SET country_code = 'PL' WHERE country_code = 'PO';
UPDATE signals_v2 SET country_code = 'SE' WHERE country_code = 'SW';
UPDATE signals_v2 SET country_code = 'DK' WHERE country_code = 'DA';
UPDATE signals_v2 SET country_code = 'AT' WHERE country_code = 'AU';  -- Austria
UPDATE signals_v2 SET country_code = 'VN' WHERE country_code = 'VM';
UPDATE signals_v2 SET country_code = 'SG' WHERE country_code = 'SN';
UPDATE signals_v2 SET country_code = 'NG' WHERE country_code = 'NI';  -- Nigeria

-- CRITICAL: China/Switzerland fix
-- CH in FIPS = China, needs to become CN
-- SZ in FIPS = Switzerland, needs to become CH
-- Do Switzerland first to avoid collision
UPDATE signals_v2 SET country_code = 'CH_TEMP' WHERE country_code = 'SZ';  -- Switzerland temp
UPDATE signals_v2 SET country_code = 'CN' WHERE country_code = 'CH';       -- China
UPDATE signals_v2 SET country_code = 'CH' WHERE country_code = 'CH_TEMP';  -- Switzerland final

-- Additional common conversions
UPDATE signals_v2 SET country_code = 'BD' WHERE country_code = 'BG';  -- Bangladesh
UPDATE signals_v2 SET country_code = 'BG' WHERE country_code = 'BU';  -- Bulgaria
UPDATE signals_v2 SET country_code = 'CL' WHERE country_code = 'CI';  -- Chile
UPDATE signals_v2 SET country_code = 'VE' WHERE country_code = 'VE';  -- Venezuela (same)
UPDATE signals_v2 SET country_code = 'KH' WHERE country_code = 'CB';  -- Cambodia
UPDATE signals_v2 SET country_code = 'MM' WHERE country_code = 'BM';  -- Myanmar
UPDATE signals_v2 SET country_code = 'LK' WHERE country_code = 'CE';  -- Sri Lanka
UPDATE signals_v2 SET country_code = 'CZ' WHERE country_code = 'EZ';  -- Czech Republic
UPDATE signals_v2 SET country_code = 'SK' WHERE country_code = 'LO';  -- Slovakia
UPDATE signals_v2 SET country_code = 'EE' WHERE country_code = 'EN';  -- Estonia
UPDATE signals_v2 SET country_code = 'LV' WHERE country_code = 'LG';  -- Latvia
UPDATE signals_v2 SET country_code = 'LT' WHERE country_code = 'LH';  -- Lithuania
UPDATE signals_v2 SET country_code = 'BY' WHERE country_code = 'BO';  -- Belarus
UPDATE signals_v2 SET country_code = 'BO' WHERE country_code = 'BL';  -- Bolivia
UPDATE signals_v2 SET country_code = 'NI' WHERE country_code = 'NU';  -- Nicaragua
UPDATE signals_v2 SET country_code = 'HN' WHERE country_code = 'HO';  -- Honduras
UPDATE signals_v2 SET country_code = 'SV' WHERE country_code = 'ES';  -- El Salvador
UPDATE signals_v2 SET country_code = 'DO' WHERE country_code = 'DR';  -- Dominican Republic
UPDATE signals_v2 SET country_code = 'HT' WHERE country_code = 'HA';  -- Haiti
UPDATE signals_v2 SET country_code = 'MA' WHERE country_code = 'MO';  -- Morocco
UPDATE signals_v2 SET country_code = 'DZ' WHERE country_code = 'AG';  -- Algeria
UPDATE signals_v2 SET country_code = 'TN' WHERE country_code = 'TS';  -- Tunisia
UPDATE signals_v2 SET country_code = 'SD' WHERE country_code = 'SU';  -- Sudan
UPDATE signals_v2 SET country_code = 'CD' WHERE country_code = 'CG';  -- Congo (DRC)
UPDATE signals_v2 SET country_code = 'CG' WHERE country_code = 'CF';  -- Congo
UPDATE signals_v2 SET country_code = 'ZW' WHERE country_code = 'ZI';  -- Zimbabwe
UPDATE signals_v2 SET country_code = 'NA' WHERE country_code = 'WA';  -- Namibia
UPDATE signals_v2 SET country_code = 'BW' WHERE country_code = 'BC';  -- Botswana
UPDATE signals_v2 SET country_code = 'MW' WHERE country_code = 'MI';  -- Malawi
UPDATE signals_v2 SET country_code = 'CI' WHERE country_code = 'IV';  -- Ivory Coast
UPDATE signals_v2 SET country_code = 'NE' WHERE country_code = 'NG';  -- Niger  
UPDATE signals_v2 SET country_code = 'BF' WHERE country_code = 'UV';  -- Burkina Faso
UPDATE signals_v2 SET country_code = 'TG' WHERE country_code = 'TO';  -- Togo
UPDATE signals_v2 SET country_code = 'BJ' WHERE country_code = 'BN';  -- Benin
UPDATE signals_v2 SET country_code = 'CF' WHERE country_code = 'CT';  -- Central African Republic
UPDATE signals_v2 SET country_code = 'TD' WHERE country_code = 'CD';  -- Chad
UPDATE signals_v2 SET country_code = 'SZ' WHERE country_code = 'WZ';  -- Eswatini
UPDATE signals_v2 SET country_code = 'LS' WHERE country_code = 'LE';  -- Lesotho
UPDATE signals_v2 SET country_code = 'BI' WHERE country_code = 'BY';  -- Burundi
UPDATE signals_v2 SET country_code = 'SC' WHERE country_code = 'SE';  -- Seychelles
UPDATE signals_v2 SET country_code = 'MU' WHERE country_code = 'MP';  -- Mauritius
UPDATE signals_v2 SET country_code = 'GW' WHERE country_code = 'PU';  -- Guinea-Bissau
UPDATE signals_v2 SET country_code = 'GN' WHERE country_code = 'GV';  -- Guinea
UPDATE signals_v2 SET country_code = 'LR' WHERE country_code = 'LI';  -- Liberia
UPDATE signals_v2 SET country_code = 'IQ' WHERE country_code = 'IZ';  -- Iraq
UPDATE signals_v2 SET country_code = 'KP' WHERE country_code = 'KN';  -- North Korea
UPDATE signals_v2 SET country_code = 'AU' WHERE country_code = 'AS';  -- Australia

-- Update countries_v2 reference table
UPDATE countries_v2 SET code = 'GB' WHERE code = 'UK';
UPDATE countries_v2 SET code = 'DE' WHERE code = 'GM';
UPDATE countries_v2 SET code = 'RU' WHERE code = 'RS';
UPDATE countries_v2 SET code = 'JP' WHERE code = 'JA';
UPDATE countries_v2 SET code = 'IE' WHERE code = 'EI';
UPDATE countries_v2 SET code = 'ES' WHERE code = 'SP';
UPDATE countries_v2 SET code = 'ZA' WHERE code = 'SF';
UPDATE countries_v2 SET code = 'UA' WHERE code = 'UP';
UPDATE countries_v2 SET code = 'KR' WHERE code = 'KS';
UPDATE countries_v2 SET code = 'TR' WHERE code = 'TU';
UPDATE countries_v2 SET code = 'IL' WHERE code = 'IS';
UPDATE countries_v2 SET code = 'PL' WHERE code = 'PO';
UPDATE countries_v2 SET code = 'SE' WHERE code = 'SW';
UPDATE countries_v2 SET code = 'DK' WHERE code = 'DA';
UPDATE countries_v2 SET code = 'AT' WHERE code = 'AU';
UPDATE countries_v2 SET code = 'VN' WHERE code = 'VM';
UPDATE countries_v2 SET code = 'SG' WHERE code = 'SN';
UPDATE countries_v2 SET code = 'CH_TEMP' WHERE code = 'SZ';
UPDATE countries_v2 SET code = 'CN' WHERE code = 'CH';
UPDATE countries_v2 SET code = 'CH' WHERE code = 'CH_TEMP';

-- Verify the conversion
DO $$
DECLARE
    gb_count INTEGER;
    de_count INTEGER;
    cn_count INTEGER;
    ch_count INTEGER;
    old_codes INTEGER;
BEGIN
    SELECT COUNT(*) INTO gb_count FROM signals_v2 WHERE country_code = 'GB';
    SELECT COUNT(*) INTO de_count FROM signals_v2 WHERE country_code = 'DE';
    SELECT COUNT(*) INTO cn_count FROM signals_v2 WHERE country_code = 'CN';
    SELECT COUNT(*) INTO ch_count FROM signals_v2 WHERE country_code = 'CH';
    
    SELECT COUNT(*) INTO old_codes FROM signals_v2 
    WHERE country_code IN ('UK', 'GM', 'RS', 'JA', 'EI', 'SP', 'SF', 'UP', 'SZ');
    
    RAISE NOTICE 'Post-migration counts:';
    RAISE NOTICE '  GB (was UK): %', gb_count;
    RAISE NOTICE '  DE (was GM): %', de_count;
    RAISE NOTICE '  CN (was CH): %', cn_count;
    RAISE NOTICE '  CH (was SZ): %', ch_count;
    RAISE NOTICE '  Old FIPS codes remaining: %', old_codes;
    
    IF old_codes > 0 THEN
        RAISE WARNING 'Some FIPS codes still remain!';
    ELSE
        RAISE NOTICE '✅ Migration complete - all FIPS codes converted!';
    END IF;
END $$;
