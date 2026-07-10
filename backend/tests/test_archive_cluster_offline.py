"""Tests for the archive-topics offline builder (pure helpers only)."""
from datetime import date

from scripts.archive_cluster_offline import (
    iter_windows, group_scopes, checkpoint_load, checkpoint_done, checkpoint_mark,
    sha1_of_headline, build_topic_row,
)


def test_iter_windows_walks_backward_in_weeks():
    ws = list(iter_windows(date(2026, 5, 3), date(2026, 5, 24)))
    # newest first, ≤7-day windows, inclusive bounds, contiguous, never before start
    assert ws[0] == (date(2026, 5, 18), date(2026, 5, 24))
    assert ws[-1][0] == date(2026, 5, 3)
    for (s1, _e1), (_s0, e0) in zip(ws, ws[1:]):
        assert (s1 - e0).days == 1
    assert all(s >= date(2026, 5, 3) for s, _ in ws)


def test_group_scopes_by_country_with_global_fallback():
    rows = [
        {"sha1": "a", "cc": "CO"}, {"sha1": "b", "cc": "CO"},
        {"sha1": "c", "cc": None}, {"sha1": "d", "cc": ""},
    ]
    scopes = group_scopes(rows)
    assert [r["sha1"] for r in scopes["CO"]] == ["a", "b"]
    assert [r["sha1"] for r in scopes["__global__"]] == ["c", "d"]


def test_checkpoint_roundtrip(tmp_path):
    p = tmp_path / "build-test.json"
    ck = checkpoint_load(p)
    assert not checkpoint_done(ck, date(2026, 6, 1), date(2026, 6, 7))
    checkpoint_mark(ck, p, date(2026, 6, 1), date(2026, 6, 7))
    ck2 = checkpoint_load(p)
    assert checkpoint_done(ck2, date(2026, 6, 1), date(2026, 6, 7))
    assert not checkpoint_done(ck2, date(2026, 6, 8), date(2026, 6, 14))


def test_sha1_matches_embed_pipeline_norm():
    # must reproduce archive_embed_pipeline._norm exactly (unescape+ws+lower)
    assert (sha1_of_headline("Peru&#x2019;s  Vote \n Count")
            == sha1_of_headline("peru’s vote count"))


def test_build_topic_row_shapes_the_upsert():
    import numpy as np
    members = [
        {"sha1": "a", "headline": "x", "cc": "CO", "date": "2026-06-02"},
        {"sha1": "b", "headline": "y", "cc": "CO", "date": "2026-06-03"},
    ]
    centroid = np.ones(4, dtype=np.float32)
    row = build_topic_row(
        label="Test topic", category="election-legitimacy", crisis=True,
        scope="CO", members=members, centroid=centroid, build_id="b1",
    )
    assert row["country_code"] == "CO" and row["n_stories"] == 2
    assert row["period_start"] == date(2026, 6, 2)
    assert row["period_end"] == date(2026, 6, 3)
    assert row["sample_story_ids"] == ["a", "b"]
    assert len(row["centroid_vec"]) == 4 and row["build_id"] == "b1"


def test_build_topic_row_global_scope_maps_to_null_country():
    import numpy as np
    members = [{"sha1": "a", "headline": "x", "cc": None, "date": "2026-06-02"}]
    row = build_topic_row(
        label="G", category=None, crisis=None, scope="__global__",
        members=members, centroid=np.zeros(3, dtype=np.float32), build_id="b1",
    )
    assert row["country_code"] is None
