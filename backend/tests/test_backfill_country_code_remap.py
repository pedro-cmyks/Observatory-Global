"""Freeze the country-code remap plan logic (b7ab7def backfill).

These tests lock the invariants that make the prod backfill safe:
single-hop chain resolution, override-row exclusion, ledger idempotency,
the Liechtenstein split, and the contaminated-bucket exclusion list.
"""

from scripts.backfill_country_code_remap import (
    OVERRIDE_GEO_CONFIDENCE,
    REMAP,
    build_plan,
    plan_row,
    summarize,
)

# Buckets measured as mixed-population — a blanket remap would corrupt
# correct rows. If one of these ever appears in REMAP, the script is wrong.
CONTAMINATED = {'CN', 'GB', 'PL', 'ZA', 'MA', 'LT', 'TD', 'PS'}
# Deliberately unmapped (no honest ISO target / bucket already correct).
DELIBERATELY_SKIPPED = {'OS', 'YI', 'CR', 'TK'}


def test_remap_never_touches_contaminated_or_skipped_buckets():
    assert not (set(REMAP) & CONTAMINATED)
    assert not (set(REMAP) & DELIBERATELY_SKIPPED)


def test_remap_has_no_identity_entries():
    assert all(old != new for old, new in REMAP.items())


def test_known_seven_day_measurement_classes_present():
    expected = {
        'LS': 'LB', 'PM': 'PA', 'PA': 'PY', 'MG': 'MN', 'MN': 'MC',
        'MC': 'MO', 'GA': 'GM', 'RB': 'RS', 'KV': 'XK', 'CS': 'CR',
        'OD': 'SS', 'PP': 'PG',
    }
    for old, new in expected.items():
        assert REMAP[old] == new


def test_chain_rows_move_exactly_one_hop():
    # MG→MN→MC→MO: each stored code moves once, to ITS OWN target — a row
    # already stored MN (Monaco) must land MC, never ride to MO.
    assert plan_row('MG', 0.85, 'x') == 'MN'
    assert plan_row('MN', 0.85, 'x') == 'MC'
    assert plan_row('MC', 0.85, 'x') == 'MO'
    # BP→SB→PM→PA→PY, the longest live chain:
    assert plan_row('BP', 0.85, 'x') == 'SB'
    assert plan_row('SB', 0.85, 'x') == 'PM'
    assert plan_row('PM', 0.85, 'x') == 'PA'
    assert plan_row('PA', 0.85, 'x') == 'PY'


def test_override_rows_are_never_remapped():
    # geo_confidence 0.35 = ingest outlet_origin_override → ISO code already.
    assert plan_row('PA', OVERRIDE_GEO_CONFIDENCE, 'Panama story') is None
    assert plan_row('LS', OVERRIDE_GEO_CONFIDENCE, 'x') is None
    # Other confidences (FIPS-derived paths) all remap.
    for conf in (0.85, 0.6, 0.4, None):
        assert plan_row('PA', conf, 'x') == 'PY'


def test_liechtenstein_split_in_lebanon_bucket():
    assert plan_row('LS', 0.85, 'Erwartete Hitzewelle in Liechtenstein') == 'LI'
    assert plan_row('LS', 0.85, 'Vaduz (FL): Illegale Feier') == 'LI'
    assert plan_row('LS', 0.85, 'Lebanese army begins takeover') == 'LB'
    assert plan_row('LS', 0.85, None) == 'LB'
    # The split exists ONLY inside the LS bucket.
    assert plan_row('PM', 0.85, 'Vaduz mentioned in a Panama story') == 'PA'


def test_unlisted_codes_untouched():
    assert plan_row('US', 0.85, 'x') is None
    assert plan_row('CN', 0.85, 'x') is None   # contaminated: must pass through
    assert plan_row('TK', 0.85, 'x') is None   # deliberately skipped
    assert plan_row('', 0.85, 'x') is None


def test_build_plan_excludes_ledgered_ids():
    rows = [
        (1, 'PM', 0.85, 'a'),   # fresh wrong row → PA
        (2, 'PA', 0.85, 'b'),   # fresh wrong row → PY
        (3, 'PA', 0.85, 'c'),   # ex-PM row remapped in a prior run: ledgered
        (4, 'PA', 0.35, 'd'),   # override row: excluded by confidence
    ]
    plan = build_plan(rows, ledgered_ids={3})
    assert plan == [(1, 'PM', 'PA'), (2, 'PA', 'PY')]
    assert summarize(plan) == {('PM', 'PA'): 1, ('PA', 'PY'): 1}


def test_char2_padding_tolerated():
    # signals_v2.country_code is character(2); asyncpg may hand back padded
    # values on other char widths — strip must keep the lookup working.
    assert plan_row('LS ', 0.85, 'Beirut') == 'LB'
