# #235 (2026-08-11): per-feed freshness watchdog — a stuck-cache feed is
# silent by construction (SANA's WordPress cache froze /en/feed/ on 07-28 and
# nothing anywhere said so for six days). The watchdog fetches every curated
# feed nightly, reads the NEWEST item's own timestamp, and ledgers an alert
# when the feed's newest item is older than the threshold — or when the feed
# is unreachable / unparseable / empty. The ledger line rides the exact
# runner `atlas_alert` format so alerts interleave with the shell-emitted
# ones (the label_hygiene precedent).

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from scripts.rss_feed_freshness_watchdog import (
    ALERT_TAGS,
    classify_feed,
    format_alert,
    newest_entry_time,
    watchdog_url,
)

_NOW = datetime(2026, 8, 11, 3, 0, 0, tzinfo=timezone.utc)
_MAX_AGE = timedelta(days=7)


def _entry(dt: datetime | None):
    if dt is None:
        return SimpleNamespace()
    return SimpleNamespace(published_parsed=dt.timetuple())


def test_newest_entry_time_takes_the_max_dated_entry():
    entries = [_entry(_NOW - timedelta(days=9)), _entry(_NOW - timedelta(days=2))]
    assert newest_entry_time(entries) == datetime(2026, 8, 9, 3, 0, 0, tzinfo=timezone.utc)


def test_newest_entry_time_is_none_when_no_entry_carries_a_date():
    # ingest's parse_entry_time falls back to now() for undated entries — the
    # watchdog must NOT inherit that fallback, or an undated stuck feed would
    # read as perpetually fresh (age 0). Honest absence instead.
    assert newest_entry_time([_entry(None), _entry(None)]) is None


def test_classify_fresh_feed_is_ok():
    status, age = classify_feed(
        fetched_ok=True, parsed_ok=True, entry_count=12,
        newest=_NOW - timedelta(days=1), now=_NOW, max_age=_MAX_AGE)
    assert status == "ok"
    assert age == timedelta(days=1)


def test_classify_stale_feed_past_threshold():
    # the SANA class: feed serves, parses, has items — every item old.
    status, age = classify_feed(
        fetched_ok=True, parsed_ok=True, entry_count=10,
        newest=_NOW - timedelta(days=14), now=_NOW, max_age=_MAX_AGE)
    assert status == "stale"
    assert age == timedelta(days=14)


def test_classify_unreachable_unparseable_empty_undated():
    assert classify_feed(fetched_ok=False, parsed_ok=False, entry_count=0,
                         newest=None, now=_NOW, max_age=_MAX_AGE)[0] == "unreachable"
    assert classify_feed(fetched_ok=True, parsed_ok=False, entry_count=0,
                         newest=None, now=_NOW, max_age=_MAX_AGE)[0] == "unparseable"
    assert classify_feed(fetched_ok=True, parsed_ok=True, entry_count=0,
                         newest=None, now=_NOW, max_age=_MAX_AGE)[0] == "empty"
    assert classify_feed(fetched_ok=True, parsed_ok=True, entry_count=5,
                         newest=None, now=_NOW, max_age=_MAX_AGE)[0] == "undated"


def test_every_non_ok_status_has_a_ledger_tag():
    # ok never ledgers; every failure class must map to a distinct [TAG].
    assert set(ALERT_TAGS) == {"stale", "unreachable", "unparseable", "empty", "undated"}
    assert all(t.startswith("FEED_") for t in ALERT_TAGS.values())


def test_format_alert_matches_the_runner_atlas_alert_line_shape():
    line = format_alert("stale", "sana_sy", "https://sana.sy/en/?feed=rss2",
                        age=timedelta(days=13, hours=6), now=_NOW)
    # `YYYY-MM-DD HH:MM:SS [TAG] message` — the label_hygiene/_alert contract,
    # so python- and shell-emitted alerts interleave in one ledger.
    assert line.startswith("2026-08-11 03:00:00 [FEED_STALE] ")
    assert "feed=sana_sy" in line
    assert "age_days=13.2" in line
    assert "https://sana.sy/en/?feed=rss2" in line


def test_watchdog_url_mirrors_the_ingestors_cache_bust_set():
    # the watchdog must measure what the INGESTOR sees: bust only the feeds
    # the ingestor busts — a stuck cache on any OTHER feed must stay visible
    # (that is the detection), and sana_sy must not false-alarm on its own
    # already-bypassed cache.
    assert "_cb=" in watchdog_url("sana_sy", "https://sana.sy/en/?feed=rss2")
    assert watchdog_url("rnz_nz", "https://www.rnz.co.nz/rss/national.xml") == \
        "https://www.rnz.co.nz/rss/national.xml"
