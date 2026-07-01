-- 060_topic_members_member_ref_pk.sql — R3.4b/R3.5 hot-PK swap (#229, R3 unification)
-- Widens topic_members to hold NON-signal members (events / trends / wiki) so the
-- movement + attention roles can bind. Signal rows are transparent via a default-ref
-- trigger (existing INSERTs that set only signal_id keep working). Fast (~38K rows),
-- reversible. Riskiest DDL of R3 — run once, verify the relationship endpoint after.
BEGIN;

-- default-ref trigger: a signal INSERT that omits member_ref/member_kind still works
CREATE OR REPLACE FUNCTION topic_members_default_ref() RETURNS trigger AS $$
BEGIN
  IF NEW.member_kind IS NULL THEN NEW.member_kind := 'signal'; END IF;
  IF NEW.member_ref IS NULL AND NEW.signal_id IS NOT NULL THEN
    NEW.member_ref := NEW.signal_id::text;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_topic_members_default_ref ON topic_members;
CREATE TRIGGER trg_topic_members_default_ref BEFORE INSERT ON topic_members
  FOR EACH ROW EXECUTE FUNCTION topic_members_default_ref();

-- backfill any rows inserted since mig 059 (before the trigger existed)
UPDATE topic_members SET member_ref = signal_id::text
  WHERE member_ref IS NULL AND signal_id IS NOT NULL;

-- DROP the old PK first (signal_id is in it → can't drop NOT NULL while it's a PK col)
ALTER TABLE topic_members DROP CONSTRAINT topic_members_pkey;

-- non-signal members carry NULL signal_id; member_ref becomes the identity
ALTER TABLE topic_members ALTER COLUMN signal_id DROP NOT NULL;
ALTER TABLE topic_members ALTER COLUMN member_ref SET NOT NULL;

ALTER TABLE topic_members DROP CONSTRAINT IF EXISTS topic_members_member_kind_check;
ALTER TABLE topic_members ADD CONSTRAINT topic_members_member_kind_check
  CHECK (member_kind IN ('signal','wiki','trend','event'));

-- add the new PK: (member_kind, member_ref, ...) — signal rows unchanged (member_kind
-- ='signal', member_ref=signal_id::text -> same uniqueness as the old PK)
ALTER TABLE topic_members ADD CONSTRAINT topic_members_pkey
  PRIMARY KEY (member_kind, member_ref, topic_id, role, engine_version);
CREATE INDEX IF NOT EXISTS idx_topic_members_ref ON topic_members (member_kind, member_ref);

COMMIT;

-- Reversible (down): drop the new PK + re-add PK(signal_id,topic_id,role,engine_version);
--   ALTER COLUMN signal_id SET NOT NULL; ALTER COLUMN member_ref DROP NOT NULL;
--   DROP TRIGGER trg_topic_members_default_ref; DROP FUNCTION topic_members_default_ref;
