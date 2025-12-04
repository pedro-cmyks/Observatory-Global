-- Migration 003: Add Crisis Classification to signals_v2
--
-- Adds columns for crisis classification, severity, and event categorization
-- to the existing signals_v2 table.

-- Add crisis columns to existing signals table
ALTER TABLE signals_v2 
ADD COLUMN IF NOT EXISTS is_crisis BOOLEAN DEFAULT FALSE;

ALTER TABLE signals_v2 
ADD COLUMN IF NOT EXISTS crisis_score FLOAT DEFAULT 0;

ALTER TABLE signals_v2 
ADD COLUMN IF NOT EXISTS crisis_themes TEXT[] DEFAULT '{}';

ALTER TABLE signals_v2 
ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'low';

ALTER TABLE signals_v2 
ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) DEFAULT 'other';

-- Create indexes for efficient crisis queries
CREATE INDEX IF NOT EXISTS idx_signals_crisis 
ON signals_v2(is_crisis, timestamp DESC) 
WHERE is_crisis = TRUE;

CREATE INDEX IF NOT EXISTS idx_signals_severity 
ON signals_v2(severity, timestamp DESC)
WHERE is_crisis = TRUE;

CREATE INDEX IF NOT EXISTS idx_signals_event_type
ON signals_v2(event_type, timestamp DESC);

-- Backfill existing signals with crisis classification
-- This identifies crisis-related signals based on theme keywords
UPDATE signals_v2 
SET 
    is_crisis = TRUE,
    crisis_score = 0.5,
    severity = 'medium'
WHERE 
    is_crisis = FALSE 
    AND EXISTS (
        SELECT 1 FROM unnest(themes) t 
        WHERE 
            t ILIKE '%CRISIS%' 
            OR t ILIKE '%KILL%' 
            OR t ILIKE '%WAR%'
            OR t ILIKE '%CONFLICT%'
            OR t ILIKE '%PROTEST%'
            OR t ILIKE '%TERROR%'
            OR t ILIKE '%DISASTER%'
            OR t ILIKE '%EARTHQUAKE%'
            OR t ILIKE '%FLOOD%'
            OR t ILIKE '%REFUGEE%'
            OR t ILIKE '%MILITARY%'
            OR t ILIKE '%RIOT%'
            OR t ILIKE '%COUP%'
            OR t ILIKE '%HURRICANE%'
            OR t ILIKE '%TYPHOON%'
            OR t ILIKE '%WILDFIRE%'
            OR t ILIKE '%TSUNAMI%'
            OR t ILIKE '%FAMINE%'
            OR t ILIKE '%EPIDEMIC%'
            OR t ILIKE '%PANDEMIC%'
    );

-- Verify backfill results
DO $$
DECLARE
    crisis_count INTEGER;
    total_count INTEGER;
    crisis_pct NUMERIC;
BEGIN
    SELECT COUNT(*) INTO crisis_count FROM signals_v2 WHERE is_crisis = TRUE;
    SELECT COUNT(*) INTO total_count FROM signals_v2;
    crisis_pct := ROUND((crisis_count::NUMERIC / NULLIF(total_count, 0) * 100), 2);
    
    RAISE NOTICE 'Migration 003 Complete:';
    RAISE NOTICE '  Total signals: %', total_count;
    RAISE NOTICE '  Crisis signals: % (%%)', crisis_count, crisis_pct;
    RAISE NOTICE '  Non-crisis signals: %', (total_count - crisis_count);
END $$;
