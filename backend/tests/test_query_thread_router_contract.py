from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app" / "routers" /
       "search.py").read_text(encoding="utf-8")


def test_query_thread_endpoint_registered():
    assert '@router.get("/api/v2/search/thread")' in SRC


def test_query_thread_uses_shared_builder():
    assert "from app.services.query_thread import build_query_thread" in SRC
    assert "build_query_thread(rows, q, hours=hours, country=country_code)" in SRC


def test_query_thread_selects_packet_columns():
    for col in ("source_url", "sentiment", "themes", "persons"):
        assert col in SRC


def test_query_thread_matches_persons_and_themes():
    assert "array_to_string(persons" in SRC
    assert "array_to_string(themes" in SRC


def test_query_thread_accepts_country_code_alias_used_by_theme_detail():
    assert "country_code: str | None = Query(None, min_length=2, max_length=2)" in SRC
    assert "selected_country = country_code or country" in SRC
