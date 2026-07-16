-- Migration 078: NER places lane — nlp_places JSONB on signals_v2.
--
-- Places (GPE/LOC) were already extracted by the NER pass and stored inside
-- the mixed nlp_persons entity list; this projects them into their own
-- column, written by the same UPDATE that writes nlp_persons
-- (enrichment/nlp_pipeline.py places_from_entities: lowercase/strip, dedupe,
-- drop 1-2 char tokens, cap 10/signal). Consumed by
-- app/services/subject_geography.infer_receipt_subject_geography
-- (method "ner_place") once receipts carry places.
--
-- Mirrors migration 011 (nlp_persons): additive, nullable, no content index —
-- the column is read via receipt-sample SELECTs, never filtered on. The
-- 011 unprocessed-queue index keys on nlp_processed_at, unaffected.
-- Shadow column mirrors 014 (nlp_persons_xlm) for NLP_MULTILINGUAL_MODE=shadow.
--
-- Reversible: ALTER TABLE signals_v2 DROP COLUMN nlp_places, DROP COLUMN nlp_places_xlm;

BEGIN;

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS nlp_places      JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS nlp_places_xlm  JSONB DEFAULT NULL;

COMMENT ON COLUMN signals_v2.nlp_places IS
    'NER place-typed entities (GPE/LOC) as a lowercase deduped JSON array of strings, capped at 10; written alongside nlp_persons by the same NER pass.';
COMMENT ON COLUMN signals_v2.nlp_places_xlm IS
    'Shadow-mode counterpart of nlp_places (NLP_MULTILINGUAL_MODE=shadow).';

COMMIT;
