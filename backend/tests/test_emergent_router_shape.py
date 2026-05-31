"""Query-shape guardrails for the /api/v2/emergent router.

The emergent endpoint reads the latest snapshot from `emergent_clusters`
(mig 046) and returns the top N clusters sorted by velocity. These
guardrails freeze the key SQL/structure decisions:

- to_regclass guard so the endpoint degrades cleanly when the table is
  missing (deploys that lag behind the migration).
- `MAX(snapshot_at)` lookup bounded by the `hours` window.
- `ORDER BY velocity DESC NULLS LAST, n_signals DESC` ranking.
- No exposure of internal centroid_vec / raw_sample_ids / vendor_labels.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMERGENT_ROUTER = ROOT / "app" / "routers" / "emergent.py"


def _src() -> str:
    return EMERGENT_ROUTER.read_text(encoding="utf-8")


def test_emergent_router_registered_at_v2_path():
    source = _src()
    assert '@router.get("/api/v2/emergent")' in source


def test_emergent_router_guards_missing_table():
    """Endpoint must use to_regclass and return a typed warning when the
    table has not been created (mig 046 not yet applied)."""
    source = _src()
    assert "to_regclass('emergent_clusters')" in source
    assert "emergent_clusters_missing" in source


def test_emergent_router_picks_latest_snapshot_within_window():
    """Most-recent snapshot only, bounded by the `hours` query param."""
    source = _src()
    assert "MAX(snapshot_at)" in source
    assert "NOW() - INTERVAL" in source
    # hours is interpolated as int into the interval (avoids parameter
    # binding inside INTERVAL while staying type-safe via int()).
    assert "int(hours)" in source


def test_emergent_router_orders_by_velocity_then_size():
    """Default product ranking: velocity first, n_signals as tiebreaker.
    NULL velocities (first-ever snapshot) sink to the bottom."""
    source = _src()
    assert "ORDER BY velocity DESC NULLS LAST, n_signals DESC" in source


def test_emergent_router_limit_param():
    """Limit must be a query param, defaulted, and honored in the SQL."""
    source = _src()
    assert "limit: int = Query(" in source
    # the LIMIT $2 placeholder fed by the limit param
    assert "LIMIT $2" in source


def test_emergent_router_does_not_expose_internal_fields():
    """centroid_vec is internal (768 floats); raw_sample_ids is for audit;
    vendor_labels is for 3-vendor calibration internals. None should leak
    in the response payload."""
    source = _src()
    # not in the SELECT
    select_block = source[source.index("SELECT"): source.index("FROM emergent_clusters")]
    assert "centroid_vec" not in select_block
    assert "raw_sample_ids" not in select_block
    assert "vendor_labels" not in select_block


def test_emergent_router_response_shape_keys():
    """Stable contract: snapshot_at, window_hours, clusters, warnings."""
    source = _src()
    assert '"snapshot_at"' in source
    assert '"window_hours"' in source
    assert '"clusters"' in source
    assert '"warnings"' in source
    # Per-cluster keys we depend on in the frontend.
    for key in (
        '"label"',
        '"description"',
        '"raw_signal_count"',
        '"n_signals"',
        '"velocity"',
        '"cohesion"',
        '"top_country_codes"',
        '"sample_signal_ids"',
        '"vendor_agreement"',
        '"gate_threshold"',
    ):
        assert key in source, f"missing response key {key}"
