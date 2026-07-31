"""Freeze the country-code correction layer (corrections-v1 consumer).

These tests lock the invariants that keep archive-derived writes safe:
single-hop (never chained) remap, GDELT-lane family scoping, the LS→LI
Liechtenstein headline split, and the documented PK-collision merge policy
for historical_topic_country_daily.
"""

import pytest

from app.services.country_corrections import (
    DAILY_MERGE_COLUMNS,
    correct_country_code,
    is_gdelt_lane_family,
    load_remap,
    merge_daily_rows,
)

# Buckets measured as mixed-population (two real countries under one code) —
# splitting them needs re-derivation from raw GDELT locations, never a remap.
CONTAMINATED = {"CN", "GB", "PL", "ZA", "MA", "LT", "TD", "PS"}
# Identified but deliberately unmapped in the artifact.
DELIBERATELY_SKIPPED = {"OS", "YI", "CR", "TK"}


def test_artifact_loads_with_expected_shape():
    remap = load_remap()
    assert remap["LS"] == "LB"
    assert remap["RB"] == "RS"
    assert remap["KV"] == "XK"
    assert remap["PA"] == "PY"
    assert len(remap) == 50
    # every entry moves somewhere else, targets are unique (no two buckets
    # ever fold into one code — collisions can only come from pre-existing
    # genuine rows, which the merge policy handles)
    assert all(old != new for old, new in remap.items())
    assert len(set(remap.values())) == len(remap)
    assert not (set(remap) & CONTAMINATED)
    assert not (set(remap) & DELIBERATELY_SKIPPED)


def test_single_hop_never_chains():
    # stored MN was produced by FIPS MN=Monaco; stored MC by FIPS MC=Macau.
    assert correct_country_code("MN") == "MC"
    assert correct_country_code("MC") == "MO"
    assert correct_country_code("MO") == "MO"  # not a key: unchanged
    assert correct_country_code("PA") == "PY"
    assert correct_country_code("PM") == "PA"


def test_non_key_codes_unchanged():
    assert correct_country_code("US") == "US"
    assert correct_country_code("GLOBAL") == "GLOBAL"
    assert correct_country_code("") == ""
    assert correct_country_code(None) == ""
    assert correct_country_code("ls") == "LB"  # normalized


def test_family_scoping_gdelt_lane_only():
    # gdelt lane and the measured pre-family era are corrected
    assert correct_country_code("LS", source_family="gdelt") == "LB"
    assert correct_country_code("LS", source_family="unknown") == "LB"
    assert correct_country_code("LS", source_family=None) == "LB"
    assert correct_country_code("LS", source_family="") == "LB"
    # real-outlet families write ISO and must never move
    assert correct_country_code("LS", source_family="press") == "LS"
    assert correct_country_code("PA", source_family="independent") == "PA"
    assert correct_country_code("MN", source_family="independent") == "MN"
    assert correct_country_code("BH", source_family="state") == "BH"


def test_is_gdelt_lane_family():
    assert is_gdelt_lane_family("gdelt")
    assert is_gdelt_lane_family("unknown")
    assert is_gdelt_lane_family(None)
    assert is_gdelt_lane_family("")
    assert not is_gdelt_lane_family("press")
    assert not is_gdelt_lane_family("independent")
    assert not is_gdelt_lane_family("wire")


def test_liechtenstein_headline_split():
    assert correct_country_code("LS", headline="Vaduz police blotter") == "LI"
    assert correct_country_code(
        "LS", headline="Liechtenstein heatwave warning") == "LI"
    assert correct_country_code(
        "LS", headline="Israeli airstrikes in southern Lebanon") == "LB"
    assert correct_country_code("LS", headline=None) == "LB"
    # the split never fires outside the LS bucket
    assert correct_country_code("RB", headline="Vaduz mention") == "RS"
    # and never fires for non-lane rows
    assert correct_country_code(
        "LS", source_family="press", headline="Vaduz") == "LS"


def _daily(cc="LB", n=10, avg=None, sc=0.0, tc=0.0, ec=0.0, lvr=None,
           sd=None, esc=0):
    return {
        "day": "2026-05-10", "topic_slug": "t", "country_code": cc,
        "source_family": "gdelt", "signal_class": "news",
        "model_version": "atlas-hist-v1",
        "signal_count": n, "avg_sentiment": avg, "sentiment_coverage": sc,
        "topic_coverage": tc, "entity_coverage": ec, "local_voice_ratio": lvr,
        "source_diversity": sd, "evidence_sample_count": esc,
    }


def test_merge_sums_counts_and_weights_coverages_exactly():
    target = _daily(n=10, sc=0.5, tc=1.0, ec=0.2, esc=2)
    source = _daily(cc="LS", n=30, sc=0.1, tc=0.5, ec=0.6, esc=3)
    out = merge_daily_rows(target, source)
    assert out["signal_count"] == 40
    assert out["evidence_sample_count"] == 5
    # coverage = covered/total → merged is the exact weighted average
    assert out["sentiment_coverage"] == pytest.approx((0.5 * 10 + 0.1 * 30) / 40)
    assert out["topic_coverage"] == pytest.approx((1.0 * 10 + 0.5 * 30) / 40)
    assert out["entity_coverage"] == pytest.approx((0.2 * 10 + 0.6 * 30) / 40)
    # PK columns come from the target
    assert out["country_code"] == "LB"


def test_merge_avg_sentiment_weighted_with_null_handling():
    both = merge_daily_rows(_daily(n=10, avg=-2.0), _daily(n=30, avg=2.0))
    assert both["avg_sentiment"] == pytest.approx((-2.0 * 10 + 2.0 * 30) / 40)
    left = merge_daily_rows(_daily(n=10, avg=None), _daily(n=30, avg=1.5))
    assert left["avg_sentiment"] == 1.5
    right = merge_daily_rows(_daily(n=10, avg=1.5), _daily(n=30, avg=None))
    assert right["avg_sentiment"] == 1.5
    neither = merge_daily_rows(_daily(n=10), _daily(n=30))
    assert neither["avg_sentiment"] is None


def test_merge_local_voice_ratio():
    both = merge_daily_rows(_daily(n=10, lvr=1.0), _daily(n=30, lvr=0.0))
    assert both["local_voice_ratio"] == pytest.approx(0.25)
    one = merge_daily_rows(_daily(n=10, lvr=None), _daily(n=30, lvr=0.4))
    assert one["local_voice_ratio"] == 0.4
    none = merge_daily_rows(_daily(n=10), _daily(n=30))
    assert none["local_voice_ratio"] is None


def test_merge_source_diversity_majority_side_wins():
    # source is the larger population → its diversity is kept
    out = merge_daily_rows(_daily(n=2, sd=1.0), _daily(n=500, sd=0.12))
    assert out["source_diversity"] == 0.12
    # target larger → target's kept
    out = merge_daily_rows(_daily(n=500, sd=0.12), _daily(n=2, sd=1.0))
    assert out["source_diversity"] == 0.12
    # tie → target's
    out = merge_daily_rows(_daily(n=5, sd=0.5), _daily(n=5, sd=0.9))
    assert out["source_diversity"] == 0.5
    # majority side null → fall back to the other side
    out = merge_daily_rows(_daily(n=2, sd=0.7), _daily(n=500, sd=None))
    assert out["source_diversity"] == 0.7


def test_merge_columns_constant_matches_policy():
    assert set(DAILY_MERGE_COLUMNS) == {
        "signal_count", "avg_sentiment", "sentiment_coverage",
        "topic_coverage", "entity_coverage", "local_voice_ratio",
        "source_diversity", "evidence_sample_count",
    }
