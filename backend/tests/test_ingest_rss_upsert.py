"""#235 attribution-race fix (2026-07-31): the RSS writer's conflict clause
must UPGRADE-ONLY (origin fills NULL, lang fills NULL/'xx', state-media only
turns ON) and must skip the write when nothing improves (anti-churn guard)."""
import inspect

from app.services import ingest_rss


def _writer_src() -> str:
    return inspect.getsource(ingest_rss.insert_rss_signals)


def test_conflict_upgrades_attribution_never_downgrades():
    src = _writer_src()
    assert "DO UPDATE SET" in src
    # origin: COALESCE(existing, new) — an existing value always wins
    assert "COALESCE(signals_v2.source_origin_country" in src
    # lang: only fills NULL/'xx'
    assert "signals_v2.source_lang = 'xx'" in src
    # state-media: OR — can only turn on
    assert "signals_v2.is_state_media OR EXCLUDED.is_state_media" in src


def test_conflict_write_is_guarded_against_churn():
    # the RSS overlap window re-encounters the same URLs every cycle; an
    # unguarded DO UPDATE would rewrite unchanged rows forever (WAL/bloat).
    src = _writer_src()
    assert "WHERE (signals_v2.source_origin_country IS NULL" in src
    assert "RETURNING (xmax = 0) AS was_insert" in src


def test_inserted_counter_excludes_upgrades():
    # xmax=0 -> new row; upgrades and no-ops must not inflate the count
    src = _writer_src()
    assert 'row["was_insert"]' in src
