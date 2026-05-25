-- Migration 041: follow-up to migration 040.
--
-- Post-040 audit showed that several topics still admitted large theme-only
-- volumes through broad GDELT hints after their noisy lexicon terms were
-- removed. For these anchors, make the classifier lex-first until benchmark
-- labels justify reintroducing theme hints.

UPDATE atlas_topics
SET
    gdelt_theme_hints = ARRAY[]::text[],
    updated_at = NOW()
WHERE slug IN (
    'labor-strike-disruption',
    'transport-corridor-disruption',
    'forced-displacement',
    'water-stress-drought'
);
