"""Label Court pure-logic: verdict parsing + neutral-label building."""
from scripts.label_court import (
    parse_verdict, build_neutral_label, _dominant_geo,
    _judge_prompt, _flatten_family_receipts, _umbrella_clause,
    _CHILD_LABELS_RANKED_SQL, _UMBRELLA_MAX_CHILDREN, _UMBRELLA_RECEIPTS_PER_CHILD,
)


def test_parse_verdict_json():
    v, r = parse_verdict('{"verdict": "failed", "reason": "Greek traffic news, not a British teen"}')
    assert v == "failed"
    assert "Greek" in r


def test_parse_verdict_fenced_json():
    v, _ = parse_verdict('```json\n{"verdict": "entailed", "reason": "fits"}\n```')
    assert v == "entailed"


def test_parse_verdict_bare_word():
    assert parse_verdict("failed")[0] == "failed"
    assert parse_verdict("The verdict is PARTIAL here")[0] == "partial"


def test_parse_verdict_unknown_defaults_partial_never_entailed():
    # an unreadable judgment must NOT clear a label
    assert parse_verdict("")[0] == "partial"
    assert parse_verdict("¯\\_(ツ)_/¯")[0] == "partial"


def test_dominant_geo_ignores_xx_and_empty():
    assert _dominant_geo(["GR", "GR", "XX", "", "IR"]) == "GR"
    assert _dominant_geo(["XX", "", None]) == "Global"


def test_build_neutral_label_shape():
    receipts = [
        {"headline": "Family killed in Halkidiki tanker crash", "country_code": "GR"},
        {"headline": "Halkidiki road tragedy claims mother and baby", "country_code": "GR"},
        {"headline": "Two women die in Lesbos collision", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert lab.startswith("GR:")
    assert "from 3 receipts" in lab
    # subject drawn from the receipts, never a fabricated narrative
    assert "Halkidiki" in lab or "Lesbos" in lab or "crash" in lab.lower()


def test_build_neutral_label_decodes_html_entities():
    # the Greek-blob class: receipts arrive HTML-entity-encoded; without
    # html.unescape the tokens come out as 'x3c4x3bf' escape fragments
    receipts = [
        {"headline": "&#x3A4;&#x3C1;&#x3B1;&#x3B3;&#x3C9;&#x3B4;&#x3AF;&#x3B1; Halkidiki crash", "country_code": "GR"},
        {"headline": "Covid cases surge in hospitals", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert "x3c4" not in lab.lower() and "x3b1" not in lab.lower()
    assert "Halkidiki" in lab or "Covid" in lab or "cases" in lab


def test_build_neutral_label_drops_bare_numbers_and_dates():
    receipts = [
        {"headline": "2026 2026 World roundup 1500", "country_code": "US"},
        {"headline": "Election results tallied nationwide", "country_code": "US"},
    ]
    lab = build_neutral_label(receipts)
    assert "2026" not in lab and "1500" not in lab


def test_build_neutral_label_global_when_no_geo():
    receipts = [
        {"headline": "Markets mixed across regions today", "country_code": "XX"},
        {"headline": "Global roundup of financial reports", "country_code": None},
    ]
    assert build_neutral_label(receipts).startswith("Global:")


def test_fallback_sql_columns_match_live_schema():
    # 2026-07-18 general-review finding: the fallback SQL referenced
    # dtm.cluster_id (real column: emergent_cluster_id) — it crashed the court
    # on exactly the thin-substrate case it exists for, swallowed as non-fatal.
    # Freeze the column names against the migration files (no DB needed).
    from scripts.label_court import _RECEIPTS_FALLBACK_SQL
    assert "dtm.emergent_cluster_id" in _RECEIPTS_FALLBACK_SQL
    assert "dtm.cluster_id" not in _RECEIPTS_FALLBACK_SQL.replace("emergent_cluster_id", "")


# ---------------------------------------------------------------------------
# Lever B1 (2026-07-29): umbrella family lane — prompt builder + gating.
# ---------------------------------------------------------------------------

def _family(n_children=3, n_receipts=2):
    return [
        {"child_id": 100 + i, "child_label": f"Child Label {i}",
         "receipts": [{"headline": f"Child {i} headline {j}", "country_code": "GR"}
                      for j in range(n_receipts)]}
        for i in range(n_children)
    ]


def test_judge_prompt_family_includes_umbrella_and_child_labels_and_receipts():
    family = _family(n_children=2, n_receipts=2)
    prompt = _judge_prompt("Halkidiki Wildfire Family", [], family=True, family_children=family)
    assert 'FAMILY (UMBRELLA) LABEL: "Halkidiki Wildfire Family"' in prompt
    # every child's OWN label appears, not just a flat headline pool
    assert 'CHILD LABEL: "Child Label 0"' in prompt
    assert 'CHILD LABEL: "Child Label 1"' in prompt
    assert "Child 0 headline 0" in prompt
    assert "Child 1 headline 1" in prompt
    # the family question, not the single-headline-identity question
    assert "family" in prompt.lower()
    assert '"verdict": "entailed" | "partial" | "failed"' in prompt


def test_judge_prompt_family_bounded_to_ten_children_three_receipts():
    # the fetch layer (_umbrella_family_for) enforces the ≤10×3 bound before
    # the prompt builder ever sees it; freeze the constants so a future edit
    # can't silently widen the trial's cost.
    assert _UMBRELLA_MAX_CHILDREN == 10
    assert _UMBRELLA_RECEIPTS_PER_CHILD == 3
    family = _family(n_children=_UMBRELLA_MAX_CHILDREN, n_receipts=_UMBRELLA_RECEIPTS_PER_CHILD)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    assert prompt.count("CHILD LABEL:") == _UMBRELLA_MAX_CHILDREN
    for i in range(_UMBRELLA_MAX_CHILDREN):
        assert f"Child {i} headline {_UMBRELLA_RECEIPTS_PER_CHILD - 1}" in prompt


def test_judge_prompt_family_child_with_no_receipts_stays_visible():
    family = [{"child_id": 1, "child_label": "Thin Child", "receipts": []}]
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    assert 'CHILD LABEL: "Thin Child"' in prompt
    assert "no receipts" in prompt


def test_judge_prompt_family_falls_back_to_flat_receipts_without_children():
    # defensive: if family_children is None/empty, the prompt still renders
    # (never crashes) using the flat receipt list.
    receipts = [{"headline": "Some headline", "country_code": "GR"}]
    prompt = _judge_prompt("Umbrella", receipts, family=True, family_children=None)
    assert "Some headline" in prompt
    assert "HEADLINES:" in prompt


def test_judge_prompt_non_family_unaffected_by_family_children_param():
    # story-lane callers never pass family_children; make sure the default
    # doesn't leak into the ordinary single-topic question.
    receipts = [{"headline": "A headline", "country_code": "US"}]
    prompt = _judge_prompt("A Label", receipts, family=False)
    assert "FAMILY" not in prompt
    assert '"reason": "<one short sentence>"' in prompt


def test_flatten_family_receipts_dedupes_across_children():
    family = [
        {"child_id": 1, "child_label": "A", "receipts": [
            {"headline": "Shared headline text here", "country_code": "GR"}]},
        {"child_id": 2, "child_label": "B", "receipts": [
            {"headline": "Shared headline text here", "country_code": "GR"},
            {"headline": "Unique second headline", "country_code": "IT"}]},
    ]
    flat = _flatten_family_receipts(family)
    assert len(flat) == 2
    assert {r["headline"] for r in flat} == {"Shared headline text here", "Unique second headline"}


def test_flatten_family_receipts_empty_family_is_empty():
    assert _flatten_family_receipts([]) == []


def test_umbrella_clause_default_off_excludes_umbrellas():
    # the kill-switch default: umbrellas stay OUT of the trial until GB passes
    # and ATLAS_COURT_UMBRELLAS is flipped on.
    assert _umbrella_clause(only_umbrellas=False, umbrellas_enabled=False) == "AND is_umbrella = false "


def test_umbrella_clause_env_on_includes_both_lanes():
    assert _umbrella_clause(only_umbrellas=False, umbrellas_enabled=True) == ""


def test_umbrella_clause_only_umbrellas_wins_regardless_of_env():
    # --only-umbrellas is the scoped manual-run override; it must work even
    # when the cron gate is still off (it never touches the gate itself).
    assert _umbrella_clause(only_umbrellas=True, umbrellas_enabled=False) == "AND is_umbrella = true "
    assert _umbrella_clause(only_umbrellas=True, umbrellas_enabled=True) == "AND is_umbrella = true "


def test_child_labels_ranked_sql_schema_freeze():
    # schema-freeze (mirrors test_fallback_sql_columns_match_live_schema):
    # the family fetch must reference real dynamic_topics columns and stay
    # scoped to active, labeled children only, bounded by LIMIT $2.
    sql = _CHILD_LABELS_RANKED_SQL
    assert "parent_id = $1" in sql
    assert "state = 'active'" in sql
    assert "label IS NOT NULL" in sql
    assert "LIMIT $2" in sql
    assert "agg_n_signals DESC" in sql
