from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app" / "routers" /
       "signals.py").read_text(encoding="utf-8")


def test_signals_imports_relevance_scorer():
    assert "from app.services.stream_relevance import score_stream_signal" in SRC


def test_signals_exposes_lane_and_score():
    assert '"lane": relevance["lane"]' in SRC
    assert '"relevanceScore": relevance["relevanceScore"]' in SRC


def test_signals_supports_lane_filter_and_relevance_sort():
    assert 'lane: Optional[str] = Query(' in SRC
    assert 'sort: str = Query(' in SRC
    assert 'if sort == "relevance"' in SRC


def test_signals_widens_fetch_for_lane_ranking():
    assert "fetch_limit = max(limit, 200)" in SRC
    assert "LIMIT {fetch_limit}" in SRC
