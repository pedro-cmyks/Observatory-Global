"""#238: country-scoped /threads keyed on SUBJECT geography, not the coverage
dateline. Pure-helper tests for resolve_thread_country_keys / thread_matches_country.
"""

from app.services.thread_intelligence import (
    _DYNAMIC_TOPICS_COUNTRY_SQL,
    _DYNAMIC_TOPICS_SELECT,
    resolve_thread_country_keys,
    thread_matches_country,
)


def test_verified_subject_wins_over_coverage():
    # A domestic story carried by foreign wires: coverage says US, subject says VE.
    res = resolve_thread_country_keys(
        subject_countries=["VE"],
        subject_geography_status="verified",
        coverage_country_codes=["US", "GB"],
    )
    assert res["keying_basis"] == "subject"
    assert res["country_keys"] == ["VE"]
    # Keyed under its subject country, not its dateline.
    assert thread_matches_country("VE", ["VE"], "verified", ["US", "GB"]) is True
    assert thread_matches_country("US", ["VE"], "verified", ["US", "GB"]) is False


def test_partial_status_falls_back_to_coverage():
    # subject inference abstained -> honest fallback to the coverage countries.
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="partial",
        coverage_country_codes=["CO"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["CO"]
    assert thread_matches_country("CO", [], "partial", ["CO"]) is True


def test_unavailable_status_falls_back_to_coverage():
    assert thread_matches_country("FR", None, "unavailable", ["FR", "DE"]) is True
    assert thread_matches_country("DE", None, "unavailable", ["FR", "DE"]) is True
    assert thread_matches_country("ES", None, "unavailable", ["FR", "DE"]) is False


def test_missing_status_falls_back_to_coverage():
    # Default status 'missing' (no subject field served) never drops the thread.
    res = resolve_thread_country_keys(
        subject_countries=None,
        subject_geography_status="missing",
        coverage_country_codes=["JP"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["JP"]


def test_verified_but_empty_subject_falls_back_to_coverage():
    # Guard: status verified yet no verified countries -> coverage, not empty.
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="verified",
        coverage_country_codes=["IN"],
    )
    assert res["keying_basis"] == "coverage"
    assert res["country_keys"] == ["IN"]


def test_case_insensitive_matching():
    assert thread_matches_country("ve", ["VE"], "verified", []) is True
    assert thread_matches_country("VE", ["ve"], "verified", []) is True


def test_multi_country_verified_subject():
    # A genuinely multi-country subject (Israel-US-Iran); both key it.
    keys = resolve_thread_country_keys(
        subject_countries=["IL", "IR"],
        subject_geography_status="verified",
        coverage_country_codes=["US"],
    )["country_keys"]
    assert keys == ["IL", "IR"]
    assert thread_matches_country("IL", ["IL", "IR"], "verified", ["US"]) is True
    assert thread_matches_country("IR", ["IL", "IR"], "verified", ["US"]) is True
    assert thread_matches_country("US", ["IL", "IR"], "verified", ["US"]) is False


def test_empty_country_code_never_matches():
    assert thread_matches_country("", ["VE"], "verified", ["VE"]) is False


def test_no_coverage_and_abstain_yields_empty_keys():
    # Honest: nothing to key on -> empty (caller keeps prior behavior; never a crash).
    res = resolve_thread_country_keys(
        subject_countries=[],
        subject_geography_status="partial",
        coverage_country_codes=[],
    )
    assert res["country_keys"] == []
    assert res["keying_basis"] == "coverage"


# --- Dark-door defect (2026-07-29 court-enforcement simulation §9) -----------
# The country door's SQL EXISTS matched `top_country_codes[1]` over ALL
# snapshots while the served `top_country_codes` array is scoped to the topic's
# LATEST snapshot — thread_matches_country then re-filters on the served value
# and drops rows the SQL already selected. 13 of 34 doors served ZERO rows
# despite candidates (witness: topic 4237 was CO on 07-20/22/24, ES since
# 07-25 → passed the CO SQL, failed the CO Python check). These tests freeze
# the agreement: the EXISTS predicate must select exactly the coverage
# pre-image of what thread_matches_country accepts — the country present at
# ANY position of the topic's latest-snapshot codes.


def _extract_block(sql: str, opener: str) -> str:
    """Return the paren-balanced block starting at `opener` inside `sql`."""
    start = sql.index(opener)
    depth = 0
    for i in range(start, len(sql)):
        ch = sql[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return sql[start : i + 1]
    raise AssertionError(f"unbalanced parens after {opener!r}")


def test_country_door_exists_scoped_to_latest_snapshot():
    # The EXISTS clause must carry the SAME latest-snapshot scope as the served
    # top_country_codes array — a story that LEFT a country must not be
    # selected for (and then silently dropped from) that country's door.
    exists_block = _extract_block(_DYNAMIC_TOPICS_COUNTRY_SQL, "EXISTS (")
    assert "MAX(snapshot_at)" in exists_block, (
        "country-door EXISTS is not latest-snapshot scoped: it will select "
        "topics whose country membership is historical, and "
        "thread_matches_country will drop every one of them (dark doors)"
    )


def test_country_door_exists_matches_any_served_position():
    # thread_matches_country (coverage arm) accepts the requested country at
    # ANY position of the served array; a primary-only ([1]) EXISTS is a
    # narrower pre-filter than the arbiter and starves the door.
    exists_block = _extract_block(_DYNAMIC_TOPICS_COUNTRY_SQL, "EXISTS (")
    assert "= ANY(ecc.top_country_codes)" in exists_block, (
        "country-door EXISTS must match the requested country at any position "
        "of the latest-snapshot codes (the Python check's coverage pre-image), "
        "not only top_country_codes[1]"
    )


def test_served_country_array_deterministic_primary_first():
    # Latent hazard from the same §9: ARRAY(SELECT DISTINCT code ... LIMIT 5)
    # had no ORDER BY, so on a topic with >5 distinct codes the requested
    # country could be dropped arbitrarily — SQL selects the row, Python drops
    # it. The served array must rank primary (position-1) codes first and be
    # deterministic.
    # The country array is the ARRAY(...) expression aliased AS top_country_codes.
    head = _DYNAMIC_TOPICS_SELECT[: _DYNAMIC_TOPICS_SELECT.index("AS top_country_codes")]
    array_block = _extract_block(head[head.rindex("ARRAY(") :], "ARRAY(")
    assert "WITH ORDINALITY" in array_block and "ORDER BY" in array_block, (
        "served top_country_codes array must order codes deterministically "
        "with cluster-primary codes first (LIMIT 5 truncation must never drop "
        "a primary code)"
    )
