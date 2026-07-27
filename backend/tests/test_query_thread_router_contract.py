import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SRC = (BACKEND / "app" / "routers" / "search.py").read_text(encoding="utf-8")
MIG_090 = (BACKEND / "migrations" /
           "090_signals_themes_persons_trgm.sql").read_text(encoding="utf-8")


def _endpoint_src() -> str:
    """Just the /search/thread handler, not the whole router module.

    search.py holds several handlers whose queries touch the same columns —
    /search/unified has its own themes and persons segments spelled almost
    identically. A module-wide substring check therefore passes even when the
    branch has been deleted from THIS endpoint, so anything asserting about
    query_thread's SQL has to read the sliced body.
    """
    start = SRC.index('@router.get("/api/v2/search/thread")')
    nxt = SRC.find("@router.get(", start + 1)
    return SRC[start:nxt if nxt != -1 else len(SRC)]


ENDPOINT_SRC = _endpoint_src()


def test_query_thread_endpoint_registered():
    assert '@router.get("/api/v2/search/thread")' in SRC


def test_query_thread_uses_shared_builder():
    assert "from app.services.query_thread import build_query_thread" in SRC
    # The local holding the matched rows is free to be renamed (it was `rows`
    # before 8fc01e02 made the fetch degrade-on-timeout, `signal_rows` after);
    # the call SHAPE is the contract — same builder, same keyword arguments.
    assert re.search(
        r"build_query_thread\(\s*\w+\s*,\s*q\s*,\s*hours=hours\s*,\s*country=country_code\s*\)",
        ENDPOINT_SRC,
    ), "query_thread must assemble its payload through the shared builder"


def test_query_thread_selects_packet_columns():
    for col in ("source_url", "sentiment", "themes", "persons"):
        assert col in SRC


def test_query_thread_matches_persons_and_themes():
    """The themes/persons OR-branches exist AND stay on migration 090's indexes.

    These two branches carry most of /search/thread's recall (measured, 6h
    window: themes +794 rows for 'election', persons +703 for 'trump'), so
    dropping either is a silent recall regression.

    They must also be spelled EXACTLY as migration 090 indexed them. Before
    090 they read ``lower(array_to_string(themes, ' '))`` — unindexable,
    because array_to_string is only STABLE — and one rare keyword seq-scanned
    the window at >45s, blowing the 8s segment timeout. That failure is now
    silent from the client's side: the fetch degrades to an empty match set
    and returns a thin thread. So this asserts the predicates against the
    migration itself: drift in either file fails here rather than in prod
    latency.
    """
    index_exprs = re.findall(r"USING gin \((.+?) gin_trgm_ops\)", MIG_090)
    assert len(index_exprs) == 2, (
        f"expected 2 trigram indexes in migration 090, found {index_exprs}")

    body = ENDPOINT_SRC.lower()
    for expr in index_exprs:
        col = "themes" if "themes" in expr else "persons"
        # Identifier/function case is not significant to Postgres, so neither
        # is it here — only the expression shape has to match the index.
        assert expr.lower() in body, (
            f"/search/thread's {col} branch no longer matches its migration-090 "
            f"index expression {expr!r} — it will seq-scan and time out"
        )
        assert f"{col} is not null" in body, f"{col} branch missing from the query"


def test_query_thread_accepts_country_code_alias_used_by_theme_detail():
    assert "country_code: str | None = Query(None, min_length=2, max_length=2)" in SRC
    assert "selected_country = country_code or country" in SRC
